"""Dream Engine API endpoints.

POST /cortex/dream/run            - Trigger a natural dream cycle
GET  /cortex/dream/status         - Current status + last report
GET  /cortex/dream/log            - Dream log history
GET  /cortex/dream/models         - Available dream models for user's tier
PUT  /cortex/dream/models/preference - Set dream model preference
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
from sqlalchemy.orm.attributes import flag_modified

from app.auth import get_current_user
from app.config import TIER_LIMITS, DREAM_ELIGIBLE_MODELS
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

class DreamTriggerRequest(BaseModel):
    provider: Optional[str] = None
    model: Optional[str] = None

class DreamModelPreference(BaseModel):
    provider: str = "anthropic"
    model: str = "claude-haiku-4-5-20251001"

router = APIRouter(prefix="/cortex/dream", tags=["CerebroCortex Dream"])


# =============================================================================
# Helpers
# =============================================================================

async def _resolve_dream_model(
    user, tier: str, tier_config: dict,
    req_provider: Optional[str], req_model: Optional[str],
    db: AsyncSession,
) -> tuple[str, str, Optional[str]]:
    """Resolve provider, model, and api_key for a dream cycle.

    Priority: explicit request > stored preference > platform default.

    Returns: (provider, model, api_key_or_none)
    Raises HTTPException on access denied or invalid model.
    """
    from app.services.provider_access import resolve_provider_access
    from app.services.llm_provider import PROVIDERS

    # 1. Determine desired provider+model
    provider = req_provider
    model = req_model

    if not provider:
        pref = (user.settings or {}).get("dream_model_preference", {})
        provider = pref.get("provider", "anthropic")
        model = model or pref.get("model")

    if not model:
        provider_config = PROVIDERS.get(provider, {})
        model = provider_config.get("default_model", "claude-haiku-4-5-20251001")

    # 2. Validate model is dream-eligible
    eligible = DREAM_ELIGIBLE_MODELS.get(provider, [])
    if model not in eligible:
        raise HTTPException(
            status_code=400,
            detail=f"Model {model} is not available for dream cycles. "
                   f"Eligible: {', '.join(eligible) if eligible else 'none for this provider'}",
        )

    # 3. Check access
    if provider != "anthropic":
        can_byok = tier_config.get("dream_byok_allowed", False)
        can_multi = tier_config.get("multi_provider", False)
        if not can_byok and not can_multi:
            raise HTTPException(
                status_code=403,
                detail="Dream model selection requires Seeker tier with BYOK or Adept+",
            )

        access = await resolve_provider_access(user, provider, tier, db)
        if not access["allowed"]:
            raise HTTPException(
                status_code=403,
                detail=f"No access to {provider}. Add your API key in Settings > API Keys.",
            )
        return provider, model, access["api_key"]

    # Anthropic: always available via platform key
    access = await resolve_provider_access(user, "anthropic", tier, db)
    return "anthropic", model, access.get("api_key")


# =============================================================================
# Dream Model Selection
# =============================================================================

@router.get("/models")
async def get_dream_models(
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get available dream models for the user's tier."""
    from app.services.billing import BillingService
    from app.services.provider_access import resolve_provider_access
    from app.services.llm_provider import PROVIDERS, PROVIDER_MODELS

    billing = BillingService(db)
    sub = await billing.get_or_create_subscription(user.id)
    tier = sub.tier if sub else "free_trial"
    tier_config = TIER_LIMITS.get(tier, TIER_LIMITS["free_trial"])

    models = []

    for provider_id, eligible_model_ids in DREAM_ELIGIBLE_MODELS.items():
        # Check if user can access this provider
        if provider_id != "anthropic":
            can_byok = tier_config.get("dream_byok_allowed", False)
            can_multi = tier_config.get("multi_provider", False)
            if not can_byok and not can_multi:
                continue
            access = await resolve_provider_access(user, provider_id, tier, db)
            if not access["allowed"]:
                continue

        provider_config = PROVIDERS.get(provider_id, {})
        provider_models = PROVIDER_MODELS.get(provider_id, {})

        for model_id in eligible_model_ids:
            model_info = provider_models.get(model_id, {})
            models.append({
                "provider": provider_id,
                "provider_name": provider_config.get("name", provider_id),
                "id": model_id,
                "name": model_info.get("name", model_id),
                "tier": model_info.get("tier", "standard"),
            })

    # Current preference
    current_pref = (user.settings or {}).get("dream_model_preference", {
        "provider": "anthropic",
        "model": "claude-haiku-4-5-20251001",
    })

    return {
        "models": models,
        "current_preference": current_pref,
    }


@router.put("/models/preference")
async def set_dream_model_preference(
    pref: DreamModelPreference,
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Set the user's preferred dream model."""
    from app.services.billing import BillingService

    billing = BillingService(db)
    sub = await billing.get_or_create_subscription(user.id)
    tier = sub.tier if sub else "free_trial"
    tier_config = TIER_LIMITS.get(tier, TIER_LIMITS["free_trial"])

    # Validate model is dream-eligible
    eligible = DREAM_ELIGIBLE_MODELS.get(pref.provider, [])
    if pref.model not in eligible:
        raise HTTPException(
            status_code=400,
            detail=f"Model {pref.model} is not eligible for dream cycles",
        )

    # Validate access (skip for anthropic — always available)
    if pref.provider != "anthropic":
        from app.services.provider_access import resolve_provider_access
        can_byok = tier_config.get("dream_byok_allowed", False)
        can_multi = tier_config.get("multi_provider", False)
        if not can_byok and not can_multi:
            raise HTTPException(status_code=403, detail="Dream BYOK requires Seeker tier or above")
        access = await resolve_provider_access(user, pref.provider, tier, db)
        if not access["allowed"]:
            raise HTTPException(status_code=403, detail=f"No access to {pref.provider}")

    # Store preference
    if not user.settings:
        user.settings = {}
    user.settings["dream_model_preference"] = {
        "provider": pref.provider,
        "model": pref.model,
    }
    flag_modified(user, "settings")
    await db.commit()

    return {
        "success": True,
        "preference": user.settings["dream_model_preference"],
    }


# =============================================================================
# Dream Cycle Triggers
# =============================================================================

@router.post("/run")
async def trigger_dream_cycle(
    request: Optional[DreamTriggerRequest] = None,
    use_bridge: bool = False,
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Trigger a dream consolidation cycle.

    Enqueues an ARQ background job. Returns job_id for status polling.
    Accepts optional provider/model override in request body.
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
            raise HTTPException(
                status_code=429,
                detail=f"Dream cycle limit reached ({used}/{max_cycles} this month)",
            )

    max_calls = tier_config.get("dream_max_llm_calls", 20)

    # Resolve dream model
    req_provider = request.provider if request else None
    req_model = request.model if request else None
    provider, model, api_key = await _resolve_dream_model(
        user, tier, tier_config, req_provider, req_model, db,
    )

    # Bridge relay for users with SensorHead
    if use_bridge:
        from sqlalchemy import text
        device = await db.execute(
            text("SELECT id FROM devices WHERE user_id = :uid AND device_type = 'sensor_head' AND status = 'active' LIMIT 1"),
            {"uid": str(user.id)},
        )
        if not device.first():
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
            provider,
            model,
        )
        await pool.close()

        return {
            "status": "queued",
            "job_id": job.job_id,
            "max_llm_calls": max_calls,
            "tier": tier,
            "provider": provider,
            "model": model,
            "use_bridge": use_bridge,
        }

    except Exception:
        # Fallback: run synchronously if Redis unavailable
        from app.services.cerebro.dream import AsyncDreamEngine
        from app.services.llm_provider import create_llm_service

        llm = create_llm_service(provider=provider, api_key=api_key)
        engine = AsyncDreamEngine(
            user_id=user.id, llm=llm,
            model=model,
            max_llm_calls=max_calls,
            provider=provider,
        )
        report = await engine.run_cycle()
        return {
            "status": "completed",
            "fallback": True,
            "provider": provider,
            "model": model,
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

    # Current dream model preference
    current_preference = (user.settings or {}).get("dream_model_preference", {
        "provider": "anthropic",
        "model": "claude-haiku-4-5-20251001",
    })

    return {
        "cycles_used": cycles_used,
        "cycles_limit": max_cycles,
        "unconsolidated_episodes": len(episodes),
        "last_report": last_report,
        "tier": tier,
        "current_preference": current_preference,
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
    request: Optional[DreamTriggerRequest] = None,
    use_bridge: bool = False,
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Trigger a targeted dream cycle on queued memories.

    Same tier/budget checks as /run — targeted cycles count against monthly limit.
    Accepts optional provider/model override in request body.
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

    # Resolve dream model
    req_provider = request.provider if request else None
    req_model = request.model if request else None
    provider, model, api_key = await _resolve_dream_model(
        user, tier, tier_config, req_provider, req_model, db,
    )

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
            provider,
            model,
        )
        await pool.close()

        return {
            "status": "queued",
            "job_id": job.job_id,
            "scope": "targeted",
            "target_count": len(queue_ids),
            "max_llm_calls": max_calls,
            "tier": tier,
            "provider": provider,
            "model": model,
        }

    except Exception:
        # Fallback: sync execution
        from app.services.cerebro.targeted_dream import TargetedDreamEngine
        from app.services.llm_provider import create_llm_service

        llm = create_llm_service(provider=provider, api_key=api_key)
        engine = TargetedDreamEngine(
            user_id=user.id,
            memory_ids=queue_ids,
            llm=llm,
            model=model,
            max_llm_calls=max_calls,
            provider=provider,
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
            "provider": provider,
            "model": model,
            "report": report.to_dict(),
        }
