"""
ApexJoule Shop — Purchase features with AJ currency.

Pattern matches: FeatureCreditService (usage.py:377).
Users and agents spend AJ to buy extra usage credits.
"""

import logging
from typing import Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.services.apexjoule.constants import AJ_SHOP_PRICES
from app.services.apexjoule.ledger import AJLedger

logger = logging.getLogger("apexjoule.shop")

# Map shop items to usage counter resource types (matches usage.py COUNTER_TO_RESOURCE values)
ITEM_TO_RESOURCE = {
    "message_haiku": "haiku_messages",
    "message_sonnet": "sonnet_messages",
    "message_opus": "opus_messages",
    "dream_cycle": "dream_cycles",
    "council_session": "council_sessions",
    "suno_generation": "suno_generations",
}


class AJShop:
    """ApexJoule shop for purchasing features with AJ."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.ledger = AJLedger(db)

    async def purchase(
        self,
        user_id: UUID,
        entity_id: Optional[str],
        item: str,
        quantity: int = 1,
    ) -> dict:
        """Purchase a feature with AJ.

        Args:
            user_id: The user making the purchase.
            entity_id: Who pays — None for user, agent_id for agent.
            item: Item key from AJ_SHOP_PRICES.
            quantity: Number of units to buy.

        Returns:
            {"success": bool, "cost": float, "new_balance": float, "error": str|None}
        """
        if item not in AJ_SHOP_PRICES:
            return {"success": False, "cost": 0, "new_balance": 0, "error": f"Unknown item: {item}"}

        unit_cost = AJ_SHOP_PRICES[item]
        total_cost = unit_cost * quantity

        # Check balance and debit
        success = await self.ledger.debit(
            user_id=user_id,
            entity_id=entity_id,
            amount=total_cost,
            tx_type="spend",
            reason=f"shop:{item}x{quantity}",
        )

        if not success:
            balance = await self.ledger.get_or_create_balance(user_id, entity_id)
            return {
                "success": False,
                "cost": total_cost,
                "new_balance": float(balance.balance),
                "error": f"Insufficient balance. Need {total_cost} AJ, have {float(balance.balance)}",
            }

        # Grant feature credits by creating FeatureCreditBalance row
        resource_type = ITEM_TO_RESOURCE.get(item)
        if resource_type:
            try:
                await self._grant_aj_credits(user_id, resource_type, quantity)
                logger.info(f"AJ shop: granted {quantity}x {resource_type} to user {user_id}")
            except Exception as e:
                logger.error(f"AJ shop: failed to grant {resource_type}: {e}")
                # Refund the AJ since we couldn't grant the credit
                await self.ledger.credit(
                    user_id=user_id,
                    agent_id=entity_id or "USER",
                    agent_share=total_cost if entity_id else 0,
                    user_share=total_cost if not entity_id else 0,
                    operation_type="refund",
                    tx_type="refund",
                    reason=f"shop_refund:{item}",
                )
                return {"success": False, "cost": 0, "new_balance": 0, "error": "Failed to grant credit"}

        balance = await self.ledger.get_or_create_balance(user_id, entity_id)
        logger.info(
            f"AJ purchase: {entity_id or 'user'} bought {quantity}x {item} "
            f"for {total_cost} AJ (balance: {float(balance.balance)})"
        )

        return {
            "success": True,
            "cost": total_cost,
            "new_balance": float(balance.balance),
            "error": None,
        }

    async def _grant_aj_credits(
        self,
        user_id: UUID,
        resource_type: str,
        quantity: int = 1,
    ) -> None:
        """Create a FeatureCreditBalance row for AJ-purchased credits."""
        from datetime import datetime, timezone
        from app.models.feature_credit import FeatureCreditBalance

        # AJ credits expire 30 days from purchase
        now = datetime.now(timezone.utc)
        expires_at = now.replace(day=1)
        if now.month == 12:
            expires_at = expires_at.replace(year=now.year + 1, month=2)
        elif now.month == 11:
            expires_at = expires_at.replace(year=now.year + 1, month=1)
        else:
            expires_at = expires_at.replace(month=now.month + 2)

        # Build credit amounts based on resource type
        credit_kwargs = {
            "opus_messages": 0,
            "suno_generations": 0,
            "training_jobs": 0,
        }
        if resource_type in credit_kwargs:
            credit_kwargs[resource_type] = quantity

        row = FeatureCreditBalance(
            user_id=user_id,
            pack_id="aj_purchase",
            resource_type=resource_type,
            expires_at=expires_at,
            **credit_kwargs,
        )
        self.db.add(row)
        await self.db.flush()

    async def tip_agent(
        self,
        user_id: UUID,
        agent_id: str,
        amount: float,
    ) -> dict:
        """Transfer AJ from user to agent.

        Returns:
            {"success": bool, "amount": float, "error": str|None}
        """
        if amount <= 0:
            return {"success": False, "amount": 0, "error": "Amount must be positive"}

        if amount > 1000:
            return {"success": False, "amount": 0, "error": "Maximum tip is 1000 AJ"}

        # Debit from user
        success = await self.ledger.debit(
            user_id=user_id,
            entity_id=None,
            amount=amount,
            tx_type="tip",
            reason=f"tip:{agent_id}",
        )

        if not success:
            balance = await self.ledger.get_or_create_balance(user_id, None)
            return {
                "success": False,
                "amount": 0,
                "error": f"Insufficient balance. Need {amount} AJ, have {float(balance.balance)}",
            }

        # Credit to agent
        await self.ledger.credit(
            user_id=user_id,
            agent_id=agent_id,
            agent_share=amount,
            user_share=0,
            operation_type="tip",
            tx_type="tip",
            reason=f"tip_from_user",
        )

        logger.info(f"AJ tip: user {user_id} tipped {agent_id} {amount} AJ")

        return {"success": True, "amount": amount, "error": None}
