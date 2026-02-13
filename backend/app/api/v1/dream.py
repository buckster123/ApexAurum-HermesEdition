"""Dream Engine API endpoints.

POST /cortex/dream/run            - Trigger a natural dream cycle
GET  /cortex/dream/status         - Current status + last report
GET  /cortex/dream/log            - Dream log history
POST /cortex/dream/queue          - Add memories to dream queue
GET  /cortex/dream/queue          - Get dream queue
DELETE /cortex/dream/queue        - Remove memories from dream queue
DELETE /cortex/dream/queue/clear  - Clear entire dream queue
POST /cortex/dream/run-targeted   - Trigger targeted dream cycle on queued memories
"""

from datetime import datetime
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import get_current_user
from app.config import TIER_LIMITS
from app.database import get_db
from app.services.cerebro.pg_graph_store import PgGraphStore


# =============================================================================
# Schemas
# =============================================================================

class DreamQueueRequest(BaseModel):
    memory_ids: list[str] = Field(..., max_length=50)
    source: str = "manual"

class DreamQueueRemoveRequest(BaseModel):
    memory_ids: list[str] = Field(..., max_length=50)

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
    from app.services.billing import BillingService
    billing = BillingService(db)
    sub = await billing.get_or_create_subscription(user.id)
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
    from app.services.billing import BillingService
    billing = BillingService(db)
    sub = await billing.get_or_create_subscription(user.id)
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


# =============================================================================
# Dream Queue (Targeted Dream Cycles — The Athanor Queue)
# =============================================================================

@router.post("/queue")
async def add_to_queue(
    request: DreamQueueRequest,
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Add memory IDs to the dream queue."""
    store = PgGraphStore(db)
    added = await store.add_to_dream_queue(user.id, request.memory_ids, request.source)
    return {"added": added, "total": len(await store.get_dream_queue_ids(user.id))}


@router.get("/queue")
async def get_queue(
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get the current dream queue with content previews."""
    store = PgGraphStore(db)
    queue = await store.get_dream_queue(user.id)
    return {"queue": queue, "count": len(queue)}


@router.delete("/queue")
async def remove_from_queue(
    request: DreamQueueRemoveRequest,
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Remove specific memory IDs from the dream queue."""
    store = PgGraphStore(db)
    removed = await store.remove_from_dream_queue(user.id, request.memory_ids)
    return {"removed": removed}


@router.delete("/queue/clear")
async def clear_queue(
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Clear the entire dream queue."""
    store = PgGraphStore(db)
    cleared = await store.clear_dream_queue(user.id)
    return {"cleared": cleared}


@router.post("/run-targeted")
async def trigger_targeted_dream(
    use_bridge: bool = False,
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Trigger a targeted dream cycle on queued memories.

    Same tier/budget checks as /run — targeted cycles count against monthly limit.
    """
    # Get queue
    store = PgGraphStore(db)
    queue_ids = await store.get_dream_queue_ids(user.id)
    if not queue_ids:
        raise HTTPException(status_code=400, detail="Dream queue is empty. Mark memories first.")
    if len(queue_ids) > 100:
        raise HTTPException(status_code=400, detail=f"Queue too large ({len(queue_ids)}). Maximum 100 memories per targeted cycle.")

    # Tier check (same as /run)
    from app.services.billing import BillingService
    billing = BillingService(db)
    sub = await billing.get_or_create_subscription(user.id)
    tier = sub.tier if sub else "free_trial"
    from app.config import QUEST_TIER_MAP
    base_tier = QUEST_TIER_MAP.get(tier, tier)
    tier_config = TIER_LIMITS.get(base_tier, TIER_LIMITS["free_trial"])

    max_cycles = tier_config.get("dream_cycles_per_month", 0)
    if max_cycles == 0:
        raise HTTPException(
            status_code=403,
            detail=f"Dream engine requires Seeker tier or above (current: {tier})",
        )

    if max_cycles is not None:
        month_start = datetime.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        used = await store.count_dream_cycles_since(user.id, month_start)
        if used >= max_cycles:
            raise HTTPException(
                status_code=429,
                detail=f"Dream cycle limit reached ({used}/{max_cycles} this month)",
            )

    max_calls = tier_config.get("dream_max_llm_calls", 20)

    # Try ARQ background job
    try:
        from arq import create_pool
        from arq.connections import RedisSettings
        from app.config import get_settings
        settings = get_settings()

        pool = await create_pool(RedisSettings.from_dsn(settings.redis_url))
        job = await pool.enqueue_job(
            "run_targeted_dream_cycle",
            str(user.id),
            queue_ids,
            max_calls,
        )
        await pool.close()

        return {
            "status": "queued",
            "job_id": job.job_id,
            "scope": "targeted",
            "target_count": len(queue_ids),
            "max_llm_calls": max_calls,
            "tier": tier,
        }

    except Exception:
        # Fallback: sync execution
        from app.services.cerebro.targeted_dream import TargetedDreamEngine
        from app.services.llm_provider import create_llm_service

        llm = create_llm_service(provider="anthropic")
        engine = TargetedDreamEngine(
            user_id=user.id,
            memory_ids=queue_ids,
            llm=llm,
            model="claude-haiku-4-5-20251001",
            max_llm_calls=max_calls,
        )
        report = await engine.run_cycle()

        # Clear queue on success
        if report.success:
            await store.clear_dream_queue(user.id)

        return {
            "status": "completed",
            "fallback": True,
            "scope": "targeted",
            "target_count": len(queue_ids),
            "report": report.to_dict(),
        }
