"""ARQ Worker - Background job processing for ApexAurum Cloud.

Handles:
- Dream cycle execution (CerebroCortex consolidation)
- Scheduled dream sweeps (3 AM UTC daily)

Docker expects: arq app.worker.WorkerSettings
"""

import logging
from datetime import datetime, timedelta
from typing import Optional
from uuid import UUID

from arq import cron
from arq.connections import RedisSettings

from app.config import get_settings, TIER_LIMITS

logger = logging.getLogger("arq-worker")
settings = get_settings()


async def _resolve_dream_api_key(user_id: str, provider: str) -> Optional[str]:
    """Resolve API key for a dream provider at worker execution time.

    Keys are never serialized to Redis — resolved fresh at execution.
    """
    if provider == "anthropic":
        return None  # Let create_llm_service resolve from env

    from app.database import get_db_context
    from app.services.provider_access import resolve_provider_access
    from app.services.billing import BillingService
    from sqlalchemy import select
    from app.models.user import User

    async with get_db_context() as db:
        result = await db.execute(select(User).where(User.id == UUID(user_id)))
        user = result.scalar_one_or_none()
        if not user:
            return None

        billing = BillingService(db)
        sub = await billing.get_or_create_subscription(UUID(user_id))
        tier = sub.tier if sub else "free_trial"

        access = await resolve_provider_access(user, provider, tier, db)
        return access.get("api_key")


async def run_dream_cycle(
    ctx: dict, user_id: str, max_llm_calls: int = 20,
    provider: str = "anthropic", model: str = "claude-haiku-4-5-20251001",
) -> dict:
    """Run a CerebroCortex dream consolidation cycle for a user.

    Called by: POST /cortex/dream/run or scheduled_dream_sweep
    """
    logger.info(f"Dream cycle starting for user {user_id} (provider={provider}, model={model})")

    try:
        from app.services.cerebro.dream import AsyncDreamEngine
        from app.services.llm_provider import create_llm_service

        api_key = await _resolve_dream_api_key(user_id, provider)
        llm = create_llm_service(provider=provider, api_key=api_key)
        engine = AsyncDreamEngine(
            user_id=UUID(user_id),
            llm=llm,
            model=model,
            max_llm_calls=max_llm_calls,
            provider=provider,
        )
        report = await engine.run_cycle()

        logger.info(
            f"Dream cycle complete for {user_id}: "
            f"{report.total_llm_calls} LLM calls, "
            f"{report.episodes_consolidated} episodes consolidated, "
            f"{report.total_duration_seconds:.1f}s"
        )
        return report.to_dict()

    except Exception as e:
        logger.error(f"Dream cycle failed for {user_id}: {e}", exc_info=True)
        return {"success": False, "error": str(e)}


async def run_targeted_dream_cycle(
    ctx: dict, user_id: str, memory_ids: list[str], max_llm_calls: int = 20,
    provider: str = "anthropic", model: str = "claude-haiku-4-5-20251001",
) -> dict:
    """Run a targeted dream cycle for specific queued memories.

    Called by: POST /cortex/dream/run-targeted
    """
    logger.info(f"Targeted dream cycle starting for user {user_id} ({len(memory_ids)} memories)")

    try:
        from app.services.cerebro.targeted_dream import TargetedDreamEngine
        from app.services.llm_provider import create_llm_service

        api_key = await _resolve_dream_api_key(user_id, provider)
        llm = create_llm_service(provider=provider, api_key=api_key)
        engine = TargetedDreamEngine(
            user_id=UUID(user_id),
            memory_ids=memory_ids,
            llm=llm,
            model=model,
            max_llm_calls=max_llm_calls,
            provider=provider,
        )
        report = await engine.run_cycle()

        # Clear queue on success
        if report.success:
            from app.database import get_db_context
            from app.services.cerebro.pg_graph_store import PgGraphStore
            async with get_db_context() as db:
                store = PgGraphStore(db)
                await store.clear_dream_queue(UUID(user_id))

        logger.info(
            f"Targeted dream complete for {user_id}: "
            f"{report.total_llm_calls} LLM calls, "
            f"{report.total_duration_seconds:.1f}s"
        )
        return report.to_dict()

    except Exception as e:
        logger.error(f"Targeted dream failed for {user_id}: {e}", exc_info=True)
        return {"success": False, "error": str(e)}


async def scheduled_dream_sweep(ctx: dict) -> dict:
    """3 AM UTC sweep: find users with unconsolidated episodes, queue dream jobs.

    Respects tier limits (dream_cycles_per_month).
    Always uses platform default (anthropic/haiku) — not user preferences.
    """
    logger.info("Scheduled dream sweep starting...")

    try:
        from app.database import get_db_context
        from sqlalchemy import text

        queued = 0
        skipped = 0

        async with get_db_context() as db:
            # Find users with unconsolidated episodes
            result = await db.execute(text("""
                SELECT DISTINCT e.user_id, s.tier
                FROM cerebro_episodes e
                LEFT JOIN subscriptions s ON s.user_id = e.user_id AND s.status = 'active'
                WHERE e.consolidated = FALSE
            """))
            rows = result.mappings().all()

            for row in rows:
                uid = str(row["user_id"])
                tier = row.get("tier") or "free_trial"
                tier_config = TIER_LIMITS.get(tier, TIER_LIMITS["free_trial"])

                # Check tier allows dreaming
                max_cycles = tier_config.get("dream_cycles_per_month", 0)
                if max_cycles == 0:
                    skipped += 1
                    continue

                # Check monthly usage
                if max_cycles is not None:
                    from app.services.cerebro.pg_graph_store import PgGraphStore
                    store = PgGraphStore(db)
                    month_start = datetime.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
                    used = await store.count_dream_cycles_since(UUID(uid), month_start)
                    if used >= max_cycles:
                        skipped += 1
                        continue

                max_calls = tier_config.get("dream_max_llm_calls", 20)
                await ctx["redis"].enqueue_job(
                    "run_dream_cycle", uid, max_calls,
                )
                queued += 1

        logger.info(f"Dream sweep complete: {queued} queued, {skipped} skipped (tier/limit)")
        return {"queued": queued, "skipped": skipped}

    except Exception as e:
        logger.error(f"Dream sweep failed: {e}", exc_info=True)
        return {"error": str(e)}


class WorkerSettings:
    """ARQ worker configuration."""
    functions = [run_dream_cycle, run_targeted_dream_cycle]
    cron_jobs = [cron(scheduled_dream_sweep, hour=3, minute=0)]
    redis_settings = RedisSettings.from_dsn(settings.redis_url)
    max_jobs = 5
    job_timeout = 600  # 10 minutes max per dream cycle
