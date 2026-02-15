"""
ApexJoule Self-Sustain — Agents fund their own operations.

When a user's tier quota is exhausted and no feature credits remain,
agents can spend their earned AJ to keep operating. This is the
self-sustain loop: agents earn AJ through quality work, then spend
it to continue serving when quotas run dry.

User controls: aj_auto_spend (bool), aj_auto_spend_daily_cap (int).
"""

import logging
from datetime import datetime
from typing import Optional
from uuid import UUID

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.apexjoule import ApexJouleTransaction
from app.services.apexjoule.constants import AJ_SHOP_PRICES
from app.services.apexjoule.ledger import AJLedger

logger = logging.getLogger("apexjoule.self_sustain")

# Map usage counter types to AJ shop item keys
COUNTER_TO_AJ_ITEM = {
    "messages_haiku": "message_haiku",
    "messages_sonnet": "message_sonnet",
    "messages_opus": "message_opus",
    "council_sessions": "council_session",
    "suno_generations": "suno_generation",
    "dream_cycles": "dream_cycle",
}


class AJSelfSustain:
    """Agent self-funding when user quotas run out."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.ledger = AJLedger(db)

    async def can_self_sustain(
        self,
        user_id: UUID,
        agent_id: str,
        counter_type: str,
    ) -> bool:
        """Check if an agent can self-fund this operation.

        Checks:
        1. User has enabled aj_auto_spend in settings
        2. Counter type has an AJ price mapping
        3. Agent (or user) has sufficient AJ balance
        4. Agent hasn't exceeded daily auto-spend cap
        """
        # 1. Check user settings
        settings = await self._get_user_settings(user_id)
        if not settings.get("aj_auto_spend", False):
            return False

        # 2. Check price mapping
        item_key = COUNTER_TO_AJ_ITEM.get(counter_type)
        if not item_key or item_key not in AJ_SHOP_PRICES:
            return False

        cost = AJ_SHOP_PRICES[item_key]

        # 3. Check agent balance first, then user balance
        agent_bal = await self.ledger.get_or_create_balance(user_id, agent_id)
        has_funds = float(agent_bal.balance) >= cost
        if not has_funds:
            user_bal = await self.ledger.get_or_create_balance(user_id, None)
            has_funds = float(user_bal.balance) >= cost

        if not has_funds:
            return False

        # 4. Check daily auto-spend cap
        daily_cap = settings.get("aj_auto_spend_daily_cap", 500)
        daily_spent = await self._daily_auto_spent(user_id, agent_id)
        if daily_spent + cost > daily_cap:
            logger.info(
                f"AJ self-sustain daily cap reached: {agent_id} "
                f"spent={daily_spent}, cap={daily_cap}"
            )
            return False

        return True

    async def deduct_self_sustain(
        self,
        user_id: UUID,
        agent_id: str,
        counter_type: str,
    ) -> bool:
        """Deduct AJ for a self-sustained operation.

        Called AFTER the operation succeeds.
        Tries agent balance first, falls back to user balance.
        """
        item_key = COUNTER_TO_AJ_ITEM.get(counter_type)
        if not item_key:
            return False

        cost = AJ_SHOP_PRICES.get(item_key, 0)
        if cost <= 0:
            return False

        # Try agent balance first
        agent_bal = await self.ledger.get_or_create_balance(user_id, agent_id)
        if float(agent_bal.balance) >= cost:
            success = await self.ledger.debit(
                user_id=user_id,
                entity_id=agent_id,
                amount=cost,
                tx_type="self_sustain",
                reason=f"self_sustain:{item_key}",
            )
            if success:
                logger.info(
                    f"AJ self-sustain: {agent_id} spent {cost} AJ on {item_key}"
                )
                return True

        # Fallback: user balance
        success = await self.ledger.debit(
            user_id=user_id,
            entity_id=None,
            amount=cost,
            tx_type="self_sustain",
            reason=f"self_sustain:{item_key}:user_fallback",
        )
        if success:
            logger.info(
                f"AJ self-sustain (user fallback): {cost} AJ for {item_key}"
            )
        return success

    async def _get_user_settings(self, user_id: UUID) -> dict:
        """Get user's settings from the User model."""
        from app.models.user import User

        result = await self.db.execute(
            select(User.settings).where(User.id == user_id)
        )
        settings = result.scalar_one_or_none()
        return settings or {}

    async def _daily_auto_spent(self, user_id: UUID, agent_id: str) -> float:
        """Get total AJ auto-spent by an agent today."""
        today_start = datetime.utcnow().replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        result = await self.db.execute(
            select(func.coalesce(func.sum(ApexJouleTransaction.amount), 0))
            .where(
                ApexJouleTransaction.user_id == user_id,
                ApexJouleTransaction.from_entity == agent_id,
                ApexJouleTransaction.tx_type == "self_sustain",
                ApexJouleTransaction.created_at >= today_start,
            )
        )
        return float(result.scalar() or 0)
