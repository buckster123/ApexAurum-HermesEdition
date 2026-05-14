"""
Usage Service - Granular usage tracking engine.

Provides atomic increment via PostgreSQL upsert, limit checking,
and usage summary queries. Designed to work alongside the existing
BillingService for fine-grained per-resource tracking.

Usage:
    from app.services.usage import UsageService, COUNTER_MESSAGES_HAIKU

    service = UsageService(db)
    new_count = await service.increment_usage(user_id, COUNTER_MESSAGES_HAIKU)
    allowed, current, limit = await service.check_usage_limit(user_id, COUNTER_MESSAGES_HAIKU, 1000)
"""

import logging
from datetime import datetime, timezone
from typing import Optional
from uuid import UUID, uuid4

from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.dialects.postgresql import insert as pg_insert

from app.models.usage import UsageCounter

logger = logging.getLogger(__name__)

# ═══════════════════════════════════════════════════════════════════════════════
# COUNTER TYPE CONSTANTS
# ═══════════════════════════════════════════════════════════════════════════════

COUNTER_MESSAGES_HAIKU = "messages_haiku"
COUNTER_MESSAGES_SONNET = "messages_sonnet"
COUNTER_MESSAGES_OPUS = "messages_opus"
COUNTER_MESSAGES_OTHER = "messages_other"
COUNTER_SUNO_GENERATIONS = "suno_generations"
COUNTER_COUNCIL_SESSIONS = "council_sessions"
COUNTER_JAM_SESSIONS = "jam_sessions"
COUNTER_NURSERY_TRAINING = "nursery_training_jobs"

# Map counter types to feature credit resource columns
COUNTER_TO_RESOURCE = {
    COUNTER_MESSAGES_OPUS: "opus_messages",
    COUNTER_SUNO_GENERATIONS: "suno_generations",
    COUNTER_NURSERY_TRAINING: "training_jobs",
}

# Maps counter types to TIER_LIMITS keys for threshold warnings
COUNTER_TO_LIMIT_KEY = {
    "messages_haiku": "messages_per_month",
    "messages_sonnet": "messages_per_month",
    "messages_opus": "opus_messages_per_month",
    "suno_generations": "suno_generations_per_month",
    "council_sessions": "council_sessions_per_month",
    "jam_sessions": "jam_sessions_per_month",
}


# ═══════════════════════════════════════════════════════════════════════════════
# HELPER FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════════════

def get_current_period() -> str:
    """Return current billing period as YYYY-MM string."""
    return datetime.now(timezone.utc).strftime("%Y-%m")


def classify_model_family(provider: str, model: str) -> str:
    """
    Classify a provider/model combination into a counter type.

    Only Anthropic models are classified by family; all other providers
    fall through to COUNTER_MESSAGES_OTHER.
    """
    if provider != "anthropic":
        return COUNTER_MESSAGES_OTHER

    model_lower = model.lower()
    if "opus" in model_lower:
        return COUNTER_MESSAGES_OPUS
    if "sonnet" in model_lower:
        return COUNTER_MESSAGES_SONNET
    if "haiku" in model_lower:
        return COUNTER_MESSAGES_HAIKU

    return COUNTER_MESSAGES_OTHER


# ═══════════════════════════════════════════════════════════════════════════════
# USAGE SERVICE
# ═══════════════════════════════════════════════════════════════════════════════

class UsageService:
    """
    Core usage tracking engine.

    Provides atomic counter increments via PostgreSQL upsert,
    limit checking, and usage summary queries.
    """

    def __init__(self, db: AsyncSession):
        self.db = db

    async def increment_usage(
        self,
        user_id: UUID,
        counter_type: str,
        amount: int = 1,
        limit_snapshot: Optional[int] = None,
    ) -> int:
        """
        Atomically increment a usage counter via PostgreSQL upsert.

        If no row exists for (user_id, counter_type, period), one is inserted
        with count=amount. If a row already exists, count is incremented by
        amount and updated_at is refreshed.

        Args:
            user_id: The user whose usage to track.
            counter_type: One of the COUNTER_* constants.
            amount: How much to increment (default 1).
            limit_snapshot: Optional informational snapshot of the limit
                           at the time the counter was created.

        Returns:
            The new count after increment.
        """
        period = get_current_period()

        stmt = pg_insert(UsageCounter).values(
            id=uuid4(),
            user_id=user_id,
            counter_type=counter_type,
            period=period,
            count=amount,
            limit_snapshot=limit_snapshot,
        )

        stmt = stmt.on_conflict_do_update(
            constraint='uq_usage_counter_user_type_period',
            set_=dict(
                count=UsageCounter.count + amount,
                updated_at=datetime.now(timezone.utc),
            ),
        )

        stmt = stmt.returning(UsageCounter.count)

        result = await self.db.execute(stmt)
        new_count = result.scalar_one()

        logger.debug(
            f"Usage increment: user={user_id} type={counter_type} "
            f"period={period} amount={amount} new_count={new_count}"
        )

        # Check for usage warning thresholds (non-fatal)
        try:
            await self._check_usage_thresholds(user_id, counter_type, new_count)
        except Exception as e:
            logger.warning(f"Usage warning trigger failed (non-fatal): {e}")

        return new_count

    async def check_usage_limit(
        self,
        user_id: UUID,
        counter_type: str,
        limit: Optional[int],
        agent_id: Optional[str] = None,
    ) -> tuple[bool, int, Optional[int]]:
        """
        Check whether a user is within their usage limit.

        Fallback chain: tier limit -> feature credits -> AJ self-sustain.

        Args:
            user_id: The user to check.
            counter_type: One of the COUNTER_* constants.
            limit: The maximum allowed count, or None for unlimited.
            agent_id: Optional agent for AJ self-sustain check.

        Returns:
            Tuple of (allowed, current_count, limit):
            - allowed: True if usage is permitted.
            - current_count: Current usage count this period.
            - limit: The limit passed in (None means unlimited).
        """
        current = await self.get_current_count(user_id, counter_type)

        if limit is None:
            return (True, current, None)

        if current < limit:
            return (True, current, limit)

        # At tier limit -- feature credits and AJ self-sustain removed (apexjoule module deleted)
        # resource_type = COUNTER_TO_RESOURCE.get(counter_type)
        # if resource_type:
        #     try:
        #         credit_svc = FeatureCreditService(self.db)
        #         available = await credit_svc.get_available_credits(user_id, resource_type)
        #         if available > 0:
        #             return (True, current, limit)
        #     except Exception as e:
        #         logger.warning(f"Feature credit check failed (non-fatal): {e}")
        #
        # if agent_id:
        #     try:
        #         from app.services.apexjoule.self_sustain import AJSelfSustain
        #         sustain = AJSelfSustain(self.db)
        #         if await sustain.can_self_sustain(user_id, agent_id, counter_type):
        #             return (True, current, limit)
        #     except Exception as e:
        #         logger.warning(f"AJ self-sustain check failed (non-fatal): {e}")

        return (False, current, limit)

    async def get_current_count(
        self,
        user_id: UUID,
        counter_type: str,
    ) -> int:
        """
        Get the current period's count for a specific counter.

        Returns 0 if no counter row exists for this period.
        """
        period = get_current_period()

        result = await self.db.execute(
            select(UsageCounter.count).where(
                UsageCounter.user_id == user_id,
                UsageCounter.counter_type == counter_type,
                UsageCounter.period == period,
            )
        )

        return result.scalar_one_or_none() or 0

    async def get_usage_summary(
        self,
        user_id: UUID,
        period: Optional[str] = None,
    ) -> dict[str, int]:
        """
        Get all usage counters for a user in a given period.

        Args:
            user_id: The user to query.
            period: Billing period as YYYY-MM string. Defaults to current period.

        Returns:
            Dict mapping counter_type to count, e.g.:
            {"messages_haiku": 42, "suno_generations": 3}
        """
        if period is None:
            period = get_current_period()

        result = await self.db.execute(
            select(UsageCounter.counter_type, UsageCounter.count).where(
                UsageCounter.user_id == user_id,
                UsageCounter.period == period,
            )
        )

        return {row.counter_type: row.count for row in result.all()}

    async def deduct_feature_credit_if_over_limit(
        self,
        user_id: UUID,
        counter_type: str,
        tier_limit: Optional[int],
    ) -> bool:
        """
        Feature credits removed (apexjoule module deleted).
        Always returns False.
        """
        return False

    async def deduct_aj_if_self_sustained(
        self,
        user_id: UUID,
        agent_id: str,
        counter_type: str,
        tier_limit: Optional[int],
    ) -> bool:
        """AJ self-sustain removed (apexjoule module deleted).
        Always returns False.
        """
        return False

    async def _check_usage_thresholds(
        self,
        user_id: UUID,
        counter_type: str,
        current_count: int,
    ) -> None:
        """
        Check if usage has crossed 80% or 100% thresholds and trigger email warnings.
        Only fires on exact threshold crossing (prev < threshold <= current).
        Non-fatal: failures are logged but don't affect the calling operation.
        """
        limit_key = COUNTER_TO_LIMIT_KEY.get(counter_type)
        if not limit_key:
            return

        try:
            from app.models.billing import Subscription
            from app.config import TIER_LIMITS
            from sqlalchemy import select

            # Look up user's tier
            result = await self.db.execute(
                select(Subscription.tier).where(Subscription.user_id == user_id)
            )
            tier = result.scalar_one_or_none() or "free_trial"
            tier_config = TIER_LIMITS.get(tier, TIER_LIMITS["free_trial"])

            limit = tier_config.get(limit_key)
            if not limit or limit <= 0:
                return  # Unlimited or not configured

            percent = (current_count * 100) // limit
            prev_percent = ((current_count - 1) * 100) // limit

            # Determine which thresholds were just crossed
            thresholds = []
            if percent >= 100 and prev_percent < 100:
                thresholds.append(100)
            elif percent >= 80 and prev_percent < 80:
                thresholds.append(80)

            if not thresholds:
                return

            # Fetch user email
            from app.models.user import User
            user_result = await self.db.execute(
                select(User.email, User.display_name).where(User.id == user_id)
            )
            user_row = user_result.one_or_none()
            if not user_row:
                return

            from app.services.email import send_usage_warning

            for threshold in thresholds:
                await send_usage_warning(
                    user_email=user_row.email,
                    user_display_name=user_row.display_name,
                    resource=counter_type,
                    percent=threshold,
                    current=current_count,
                    limit=limit,
                )
        except Exception as e:
            logger.warning(f"Usage threshold check failed (non-fatal): {e}")


# ═══════════════════════════════════════════════════════════════════════════════
# FEATURE CREDIT SERVICE
# ═══════════════════════════════════════════════════════════════════════════════
# Removed: FeatureCreditService and FeatureCreditBalance model deleted
# (apexjoule commercial modules removed). UsageService analytics counters remain.

# class FeatureCreditService:
#     """
#     Service for managing purchased feature credits (Spark/Flame/Inferno packs).
#     Feature credits are stored as per-purchase rows with remaining balances.
#     Deduction uses FIFO (oldest purchase first). Credits expire based on
#     expires_at timestamp.
#     """
#     ...
