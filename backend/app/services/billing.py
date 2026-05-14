"""
Billing Service - Local Mode Stub

All gating functions return unlimited access.
No Stripe, no credits, no usage limits.
"""

import logging
from datetime import datetime, timezone as tz
from typing import Optional, Tuple
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.models.billing import Subscription
from app.models.user import User

logger = logging.getLogger(__name__)
settings = get_settings()


class BillingService:
    """Stub billing service for local mode. Always returns unlimited access."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_or_create_subscription(self, user_id: UUID) -> Subscription:
        """Get or create a local-tier subscription."""
        result = await self.db.execute(
            select(Subscription).where(Subscription.user_id == user_id)
        )
        subscription = result.scalar_one_or_none()
        if subscription:
            return subscription

        subscription = Subscription(
            id=uuid4(),
            user_id=user_id,
            tier="local",
            status="active",
        )
        self.db.add(subscription)
        await self.db.flush()
        logger.info(f"Created local subscription for user {user_id}")
        return subscription

    async def get_subscription_status(self, user_id: UUID) -> dict:
        """Return unlimited local status."""
        return {
            "tier": "local",
            "subscription_status": "active",
            "messages_used": 0,
            "messages_limit": None,
            "messages_remaining": None,
            "current_period_end": None,
            "cancel_at_period_end": False,
            "trial_end": None,
            "credit_balance_cents": 0,
            "credit_balance_usd": 0.0,
            "quest_active": False,
            "quest_stage": None,
            "features": {
                "models": [
                    "claude-haiku-4-5-20251001",
                    "claude-sonnet-4-5-20250929",
                    "claude-opus-4-6",
                    "claude-opus-4-5-20251101",
                    "claude-opus-4-1-20250805",
                    "claude-opus-4-20250514",
                    "claude-sonnet-4-20250514",
                    "claude-3-7-sonnet-20250219",
                    "claude-3-haiku-20240307",
                ],
                "tools_enabled": True,
                "multi_provider": True,
                "byok_allowed": True,
                "byok_providers": ["together", "groq", "deepseek", "qwen", "moonshot", "openai"],
                "api_access": True,
                "context_token_limit": None,
                "council_sessions_per_month": None,
                "council_max_rounds": None,
                "suno_generations_per_month": None,
                "jam_sessions_per_month": None,
                "nursery_access": True,
                "pac_mode": True,
                "dev_mode": True,
                "vault_storage_mb": None,
                "platform_grants": [],
                "dream_cycles_per_month": None,
                "dream_max_llm_calls": None,
                "dream_byok_allowed": True,
                "memory_imports_per_month": None,
                "import_max_file_mb": 100,
                "aj_earning_enabled": False,
            },
            "at_limit": False,
            "near_limit": False,
            "usage_counters": {},
            "feature_credits": {},
        }

    async def can_send_message(self, user_id: UUID) -> Tuple[bool, str]:
        """Always allow."""
        return True, "local"

    async def can_use_model(self, user_id: UUID, model: str) -> bool:
        """Always allow."""
        return True

    async def can_use_tools(self, user_id: UUID) -> bool:
        """Always allow."""
        return True

    async def can_use_multi_provider(self, user_id: UUID) -> bool:
        """Always allow."""
        return True

    async def record_message_usage(
        self,
        user_id: UUID,
        provider: str,
        model: str,
        input_tokens: int,
        output_tokens: int,
        message_id: Optional[UUID] = None,
    ) -> dict:
        """Record usage without billing."""
        return {
            "provider": provider,
            "model": model,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "cost_cents": 0,
            "billing_type": "local",
            "messages_remaining": None,
        }
