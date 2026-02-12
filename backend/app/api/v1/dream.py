"""Dream Engine API endpoints.

POST /cortex/dream/run    - Trigger a dream cycle (enqueues ARQ job)
GET  /cortex/dream/status - Current status + last report
GET  /cortex/dream/log    - Dream log history
"""

from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import get_current_user
from app.config import TIER_LIMITS
from app.database import get_db
from app.services.cerebro.pg_graph_store import PgGraphStore

router = APIRouter(prefix="/cortex/dream", tags=["CerebroCortex Dream"])


@router.post("/run")
async def trigger_dream_cycle(
    use_bridge: bool = False,
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Trigger a dream consolidation cycle.

    Enqueues an ARQ background job. Returns job_id for status polling.
    """
    # Get user's tier
    from app.services.billing import get_user_subscription
    sub = await get_user_subscription(db, user.id)
    tier = sub.tier if sub else "free_trial"
    tier_config = TIER_LIMITS.get(tier, TIER_LIMITS["free_trial"])

    # Check tier allows dreaming
    max_cycles = tier_config.get("dream_cycles_per_month", 0)
    if max_cycles == 0:
        from fastapi import HTTPException
        raise HTTPException(
            status_code=403,
            detail=f"Dream engine requires Seeker tier or above (current: {tier})",
        )

    # Check monthly usage
    if max_cycles is not None:
        store = PgGraphStore(db)
        month_start = datetime.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        used = await store.count_dream_cycles_since(user.id, month_start)
        if used >= max_cycles:
            from fastapi import HTTPException
            raise HTTPException(
                status_code=429,
                detail=f"Dream cycle limit reached ({used}/{max_cycles} this month)",
            )

    max_calls = tier_config.get("dream_max_llm_calls", 20)

    # Bridge relay for users with SensorHead
    if use_bridge:
        # Check if user has an active SensorHead
        from sqlalchemy import text
        device = await db.execute(
            text("SELECT id FROM devices WHERE user_id = :uid AND device_type = 'sensor_head' AND status = 'active' LIMIT 1"),
            {"uid": str(user.id)},
        )
        if not device.first():
            from fastapi import HTTPException
            raise HTTPException(
                status_code=400,
                detail="No active SensorHead found for bridge inference",
            )

    # Enqueue ARQ job
    try:
        from arq import create_pool
        from arq.connections import RedisSettings
        from app.config import get_settings
        settings = get_settings()

        pool = await create_pool(RedisSettings.from_dsn(settings.redis_url))
        job = await pool.enqueue_job(
            "run_dream_cycle",
            str(user.id),
            max_calls,
        )
        await pool.close()

        return {
            "status": "queued",
            "job_id": job.job_id,
            "max_llm_calls": max_calls,
            "tier": tier,
            "use_bridge": use_bridge,
        }

    except Exception as e:
        # Fallback: run synchronously if Redis unavailable
        from app.services.cerebro.dream import AsyncDreamEngine
        from app.services.llm_provider import create_llm_service

        llm = create_llm_service(provider="anthropic")
        engine = AsyncDreamEngine(
            user_id=user.id, llm=llm,
            model="claude-haiku-4-5-20251001",
            max_llm_calls=max_calls,
        )
        report = await engine.run_cycle()
        return {
            "status": "completed",
            "fallback": True,
            "report": report.to_dict(),
        }


@router.get("/status")
async def dream_status(
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get dream engine status and last report."""
    store = PgGraphStore(db)

    # Get last dream log entry
    log = await store.get_dream_log(user.id, limit=1)
    last_report = log[0] if log else None

    # Count this month
    month_start = datetime.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    cycles_used = await store.count_dream_cycles_since(user.id, month_start)

    # Get tier limit
    from app.services.billing import get_user_subscription
    sub = await get_user_subscription(db, user.id)
    tier = sub.tier if sub else "free_trial"
    tier_config = TIER_LIMITS.get(tier, TIER_LIMITS["free_trial"])
    max_cycles = tier_config.get("dream_cycles_per_month", 0)

    # Unconsolidated episodes
    episodes = await store.get_unconsolidated_episodes(user.id)

    return {
        "cycles_used": cycles_used,
        "cycles_limit": max_cycles,
        "unconsolidated_episodes": len(episodes),
        "last_report": last_report,
        "tier": tier,
    }


@router.get("/log")
async def dream_log(
    limit: int = 20,
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get dream log history."""
    store = PgGraphStore(db)
    log = await store.get_dream_log(user.id, limit=min(limit, 100))
    return {"entries": log, "count": len(log)}
