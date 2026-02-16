"""
Solana Payment Service — Manages the full payment lifecycle.

Flow:
1. create_payment_request() -> generates reference + solana: URI
2. check_payment() -> polls on-chain, verifies, credits AJ
3. expire_stale_payments() -> background cleanup

"Where the blockchain meets the Athanor."
"""

import logging
import os
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Optional
from urllib.parse import quote
from uuid import UUID, uuid4

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.models.solana_payment import SolanaPayment
from app.services.apexjoule.constants import AJ_PER_USD
from app.services.solana.client import SolanaClient

logger = logging.getLogger(__name__)

# Payment request expiry
PAYMENT_EXPIRY_MINUTES = 30

# AJ packs (pre-defined bundles for the UI)
AJ_PACKS = {
    "spark": {"aj": 5_000, "usd": 5.00, "label": "Spark"},
    "flame": {"aj": 11_000, "usd": 10.00, "label": "Flame"},
    "blaze": {"aj": 30_000, "usd": 25.00, "label": "Blaze"},
}

# Solana/Bitcoin base58 alphabet
_B58_ALPHABET = b"123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"


def _b58encode(data: bytes) -> str:
    """Pure-Python base58 encoder (Solana/Bitcoin alphabet)."""
    n = int.from_bytes(data, "big")
    result = []
    while n > 0:
        n, remainder = divmod(n, 58)
        result.append(_B58_ALPHABET[remainder:remainder + 1])
    # Preserve leading zero bytes as '1' characters
    for byte in data:
        if byte == 0:
            result.append(b"1")
        else:
            break
    return b"".join(reversed(result)).decode("ascii")


def _generate_reference() -> str:
    """Generate a Solana Pay reference as a base58-encoded 32-byte public key.

    Solana Pay spec requires references to be valid base58 pubkeys so wallets
    can include them as non-signer accounts and getSignaturesForAddress can find them.
    """
    raw = os.urandom(32)
    return _b58encode(raw)


class SolanaPaymentService:
    """Manages Solana Pay payment lifecycle."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.settings = get_settings()
        self.client = SolanaClient()

    async def create_payment_request(
        self,
        user_id: UUID,
        amount_usd: Decimal,
        token: str = "SOL",
    ) -> dict:
        """Create a new payment request with Solana Pay URI.

        Args:
            user_id: Who is paying
            amount_usd: USD value of the purchase
            token: "SOL" or "USDC"

        Returns:
            {reference, solana_url, aj_amount, amount_token, token, status, expires_at}
        """
        if not self.settings.solana_recipient_address:
            raise ValueError("Solana recipient address not configured")

        recipient = self.settings.solana_recipient_address
        reference = _generate_reference()

        # Calculate token amount
        if token == "USDC":
            amount_token = amount_usd  # 1:1
            token_mint = self.settings.solana_usdc_mint
            sol_price = None
        elif token == "SOL":
            sol_price = await self.client.get_sol_price_usd()
            if not sol_price or sol_price <= 0:
                raise ValueError("Unable to fetch SOL price. Try again shortly.")
            amount_token = amount_usd / sol_price
            token_mint = "SOL"
        else:
            raise ValueError(f"Unsupported token: {token}")

        # Calculate AJ credit
        aj_amount = Decimal(str(amount_usd)) * AJ_PER_USD

        # Build Solana Pay URI
        # https://docs.solanapay.com/spec#transfer-request
        if token == "SOL":
            solana_url = (
                f"solana:{recipient}"
                f"?amount={amount_token:.9f}"
                f"&reference={reference}"
                f"&label={quote('ApexAurum')}"
                f"&message={quote(f'Buy {aj_amount:.0f} AJ')}"
            )
        else:
            solana_url = (
                f"solana:{recipient}"
                f"?amount={amount_token:.6f}"
                f"&spl-token={token_mint}"
                f"&reference={reference}"
                f"&label={quote('ApexAurum')}"
                f"&message={quote(f'Buy {aj_amount:.0f} AJ')}"
            )

        # Create DB record
        payment = SolanaPayment(
            id=uuid4(),
            user_id=user_id,
            reference=reference,
            amount_decimal=amount_token,
            token_mint=token_mint,
            token_symbol=token,
            sol_price_usd=sol_price,
            usd_equivalent=amount_usd,
            aj_credited=0,  # Set when confirmed
            status="pending",
        )
        self.db.add(payment)
        await self.db.flush()

        expires_at = payment.created_at + timedelta(minutes=PAYMENT_EXPIRY_MINUTES)

        return {
            "reference": reference,
            "solana_url": solana_url,
            "aj_amount": float(aj_amount),
            "amount_token": float(amount_token),
            "token": token,
            "usd_equivalent": float(amount_usd),
            "status": "pending",
            "expires_at": expires_at.isoformat(),
        }

    async def check_payment(self, reference: str) -> dict:
        """Check if a payment has been confirmed on-chain.

        Returns current status and AJ credited if complete.
        """
        # Find the payment record
        result = await self.db.execute(
            select(SolanaPayment).where(SolanaPayment.reference == reference)
        )
        payment = result.scalar_one_or_none()
        if not payment:
            return {"status": "not_found", "error": "Payment request not found"}

        # Already credited — return success
        if payment.status == "credited":
            return {
                "status": "credited",
                "aj_credited": float(payment.aj_credited),
                "tx_signature": payment.tx_signature,
            }

        # Already failed/expired
        if payment.status in ("failed", "expired"):
            return {"status": payment.status}

        # Check expiry
        expiry = payment.created_at + timedelta(minutes=PAYMENT_EXPIRY_MINUTES)
        if datetime.now(timezone.utc) > expiry:
            payment.status = "expired"
            await self.db.flush()
            return {"status": "expired"}

        # Poll Solana for matching transactions
        signatures = await self.client.find_signatures_by_reference(reference)
        if not signatures:
            return {"status": "pending"}

        # Found a signature — fetch and verify the transaction
        for sig_info in signatures:
            signature = sig_info.get("signature")
            if not signature:
                continue

            # Idempotency: check if this signature is already used
            existing = await self.db.execute(
                select(SolanaPayment).where(SolanaPayment.tx_signature == signature)
            )
            if existing.scalar_one_or_none():
                logger.warning(f"Duplicate tx_signature detected: {signature}")
                continue

            tx_data = await self.client.get_transaction(signature)
            if not tx_data:
                continue

            # Verify the transfer matches expectations
            verification = self.client.verify_transfer(
                tx_data=tx_data,
                expected_recipient=self.settings.solana_recipient_address,
                expected_token=payment.token_mint if payment.token_symbol != "SOL" else "SOL",
                min_amount=payment.amount_decimal * Decimal("0.99"),  # 1% tolerance for fees
            )

            if not verification.get("valid"):
                logger.warning(f"Transfer verification failed: {verification.get('error')}")
                continue

            # Verified! Update payment record
            aj_amount = payment.usd_equivalent * AJ_PER_USD
            payment.tx_signature = signature
            payment.slot = tx_data.get("slot")
            payment.status = "confirmed"
            payment.confirmed_at = datetime.now(timezone.utc)

            # Credit AJ
            try:
                from app.services.apexjoule.ledger import AJLedger
                ledger = AJLedger(self.db)
                await ledger.credit(
                    user_id=payment.user_id,
                    agent_id="SYSTEM",
                    agent_share=0,
                    user_share=float(aj_amount),
                    tx_type="crypto_purchase",
                    reason=f"Solana Pay: {payment.token_symbol} -> {aj_amount:.0f} AJ",
                )
                payment.aj_credited = aj_amount
                payment.status = "credited"
                await self.db.flush()

                logger.info(
                    f"Solana payment credited: user={payment.user_id} "
                    f"tx={signature[:16]}... {payment.token_symbol} "
                    f"${payment.usd_equivalent} -> {aj_amount} AJ"
                )

                return {
                    "status": "credited",
                    "aj_credited": float(aj_amount),
                    "tx_signature": signature,
                }
            except Exception as e:
                logger.error(f"AJ credit failed after verification: {e}")
                payment.status = "confirmed"  # Keep confirmed, retry credit later
                await self.db.flush()
                return {"status": "confirmed", "error": "Payment verified but AJ credit pending"}

        return {"status": "pending"}

    async def get_rates(self) -> dict:
        """Get current conversion rates + wallet config for frontend."""
        sol_price = await self.client.get_sol_price_usd()
        aj_per_usd = AJ_PER_USD

        return {
            "sol_usd": float(sol_price) if sol_price else None,
            "aj_per_usd": aj_per_usd,
            "aj_per_sol": float(sol_price * aj_per_usd) if sol_price else None,
            "aj_per_usdc": aj_per_usd,
            "packs": {
                k: {**v, "sol": float(Decimal(str(v["usd"])) / sol_price) if sol_price else None}
                for k, v in AJ_PACKS.items()
            },
            # Wallet config for frontend tx building
            "recipient_address": self.settings.solana_recipient_address,
            "rpc_url": self.settings.solana_rpc_url,
            "usdc_mint": self.settings.solana_usdc_mint,
        }

    async def get_payment_history(self, user_id: UUID, limit: int = 20) -> list:
        """Get user's Solana payment history."""
        result = await self.db.execute(
            select(SolanaPayment)
            .where(SolanaPayment.user_id == user_id)
            .order_by(SolanaPayment.created_at.desc())
            .limit(limit)
        )
        payments = result.scalars().all()
        return [
            {
                "id": str(p.id),
                "reference": p.reference,
                "token": p.token_symbol,
                "amount": float(p.amount_decimal),
                "usd_equivalent": float(p.usd_equivalent),
                "aj_credited": float(p.aj_credited),
                "status": p.status,
                "tx_signature": p.tx_signature,
                "created_at": p.created_at.isoformat(),
                "confirmed_at": p.confirmed_at.isoformat() if p.confirmed_at else None,
            }
            for p in payments
        ]

    async def expire_stale_payments(self) -> int:
        """Background task: expire pending payments older than 30 min."""
        cutoff = datetime.now(timezone.utc) - timedelta(minutes=PAYMENT_EXPIRY_MINUTES)
        result = await self.db.execute(
            update(SolanaPayment)
            .where(SolanaPayment.status == "pending")
            .where(SolanaPayment.created_at < cutoff)
            .values(status="expired")
        )
        count = result.rowcount
        if count:
            logger.info(f"Expired {count} stale Solana payment(s)")
        return count
