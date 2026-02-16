"""
Solana RPC Client — Lightweight async client for on-chain verification.

Uses raw JSON-RPC over HTTP (no heavy SDK dependencies).
Handles: transaction lookup, signature discovery, SOL price feed.
"""

import logging
import time
from decimal import Decimal
from typing import Optional

import httpx

from app.config import get_settings

logger = logging.getLogger(__name__)

# CoinGecko free price API (no auth required)
COINGECKO_PRICE_URL = "https://api.coingecko.com/api/v3/simple/price"

# Cache SOL price for 5 minutes
_sol_price_cache: dict = {"price": None, "fetched_at": 0}
SOL_PRICE_CACHE_TTL = 300  # seconds


class SolanaClient:
    """Async Solana JSON-RPC client for payment verification."""

    def __init__(self, rpc_url: Optional[str] = None):
        settings = get_settings()
        self.rpc_url = rpc_url or settings.solana_rpc_url
        self._client: Optional[httpx.AsyncClient] = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(timeout=30.0)
        return self._client

    async def _rpc_call(self, method: str, params: list) -> dict:
        """Make a Solana JSON-RPC call."""
        client = await self._get_client()
        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": method,
            "params": params,
        }
        resp = await client.post(self.rpc_url, json=payload)
        resp.raise_for_status()
        data = resp.json()
        if "error" in data:
            raise SolanaRPCError(data["error"].get("message", str(data["error"])))
        return data.get("result")

    async def get_transaction(self, signature: str) -> Optional[dict]:
        """Fetch a confirmed transaction by signature."""
        try:
            return await self._rpc_call("getTransaction", [
                signature,
                {"encoding": "jsonParsed", "commitment": "confirmed", "maxSupportedTransactionVersion": 0},
            ])
        except SolanaRPCError as e:
            logger.warning(f"getTransaction failed for {signature}: {e}")
            return None

    async def find_signatures_by_reference(self, reference_pubkey: str, limit: int = 5) -> list:
        """Find transaction signatures that include a reference pubkey.

        Solana Pay encodes the reference as an additional account in the tx.
        getSignaturesForAddress finds txs where that pubkey appears.
        """
        try:
            result = await self._rpc_call("getSignaturesForAddress", [
                reference_pubkey,
                {"limit": limit, "commitment": "confirmed"},
            ])
            return result or []
        except SolanaRPCError as e:
            logger.debug(f"No signatures found for reference {reference_pubkey}: {e}")
            return []

    async def get_sol_price_usd(self) -> Optional[Decimal]:
        """Get current SOL/USD price from CoinGecko. Cached 5 min."""
        now = time.time()
        if _sol_price_cache["price"] and (now - _sol_price_cache["fetched_at"]) < SOL_PRICE_CACHE_TTL:
            return _sol_price_cache["price"]

        try:
            client = await self._get_client()
            resp = await client.get(
                COINGECKO_PRICE_URL,
                params={"ids": "solana", "vs_currencies": "usd"},
            )
            resp.raise_for_status()
            data = resp.json()
            price_val = data.get("solana", {}).get("usd")
            if price_val:
                price = Decimal(str(price_val))
                _sol_price_cache["price"] = price
                _sol_price_cache["fetched_at"] = now
                logger.debug(f"SOL price: ${price}")
                return price
        except Exception as e:
            logger.warning(f"CoinGecko price fetch failed: {e}")

        return _sol_price_cache.get("price")  # Return stale if available

    def verify_transfer(
        self,
        tx_data: dict,
        expected_recipient: str,
        expected_token: str,
        min_amount: Decimal,
    ) -> dict:
        """Verify a parsed transaction matches payment expectations.

        Returns: {"valid": bool, "amount": Decimal, "sender": str, "error": str}
        """
        if not tx_data or not tx_data.get("meta"):
            return {"valid": False, "error": "Transaction data missing or unparsed"}

        meta = tx_data["meta"]
        if meta.get("err"):
            return {"valid": False, "error": f"Transaction failed on-chain: {meta['err']}"}

        # Parse based on token type
        if expected_token == "SOL":
            return self._verify_sol_transfer(tx_data, expected_recipient, min_amount)
        else:
            return self._verify_spl_transfer(tx_data, expected_recipient, expected_token, min_amount)

    def _verify_sol_transfer(self, tx_data: dict, recipient: str, min_amount: Decimal) -> dict:
        """Verify a native SOL transfer."""
        try:
            instructions = tx_data["transaction"]["message"]["instructions"]
            for ix in instructions:
                parsed = ix.get("parsed")
                if not parsed or ix.get("program") != "system":
                    continue
                if parsed.get("type") != "transfer":
                    continue
                info = parsed.get("info", {})
                if info.get("destination") == recipient:
                    lamports = info.get("lamports", 0)
                    amount = Decimal(lamports) / Decimal(10**9)
                    if amount >= min_amount:
                        return {
                            "valid": True,
                            "amount": amount,
                            "sender": info.get("source", "unknown"),
                        }
                    return {"valid": False, "error": f"Amount {amount} SOL < expected {min_amount} SOL"}
        except (KeyError, TypeError) as e:
            logger.warning(f"SOL transfer parse error: {e}")

        return {"valid": False, "error": "No matching SOL transfer found in transaction"}

    def _verify_spl_transfer(self, tx_data: dict, recipient: str, token_mint: str, min_amount: Decimal) -> dict:
        """Verify an SPL token transfer (USDC, etc.)."""
        try:
            instructions = tx_data["transaction"]["message"]["instructions"]
            # Also check inner instructions (for associated token account creation)
            inner = tx_data.get("meta", {}).get("innerInstructions", [])
            all_instructions = list(instructions)
            for group in inner:
                all_instructions.extend(group.get("instructions", []))

            for ix in all_instructions:
                parsed = ix.get("parsed")
                if not parsed:
                    continue
                program = ix.get("program", "")
                if "token" not in program:
                    continue
                ix_type = parsed.get("type", "")
                if ix_type not in ("transfer", "transferChecked"):
                    continue
                info = parsed.get("info", {})
                # For transferChecked, the mint is directly available
                if ix_type == "transferChecked" and info.get("mint") != token_mint:
                    continue
                dest = info.get("destination", "")
                # SPL transfers use token accounts, not wallet addresses directly
                # We check the authority/owner in the post-token-balances
                amount_str = info.get("tokenAmount", {}).get("uiAmountString") or info.get("amount", "0")
                amount = Decimal(str(amount_str))
                # For basic transfer, amount is in smallest unit
                if ix_type == "transfer":
                    decimals = info.get("tokenAmount", {}).get("decimals", 6)
                    if not info.get("tokenAmount"):
                        amount = amount / Decimal(10**6)  # USDC default 6 decimals
                if amount >= min_amount:
                    return {
                        "valid": True,
                        "amount": amount,
                        "sender": info.get("authority", info.get("source", "unknown")),
                    }
        except (KeyError, TypeError) as e:
            logger.warning(f"SPL transfer parse error: {e}")

        return {"valid": False, "error": "No matching SPL transfer found in transaction"}

    async def close(self):
        if self._client and not self._client.is_closed:
            await self._client.aclose()


class SolanaRPCError(Exception):
    """Raised when Solana RPC returns an error."""
    pass
