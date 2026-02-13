"""
Quest API Endpoints - The Quest Engine

Progression tracking, milestone checking, and stat syncing
for the Athaverse quest tier system.
"""

import logging

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.auth.deps import get_current_user
from app.models.user import User
from app.services.progression import (
    ProgressionService,
    MILESTONE_DEFINITIONS,
    ALL_MILESTONES,
    FEATURE_REGISTRY,
    check_feature_access,
    get_locked_feature_info,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/quest", tags=["Quest"])


# ═══════════════════════════════════════════════════════════════════════════════
# REQUEST MODELS
# ═══════════════════════════════════════════════════════════════════════════════

class TaskEventRequest(BaseModel):
    """Task completion event from frontend."""
    zone: Optional[str] = None
    agents: Optional[list[str]] = None
    mode: Optional[str] = None  # "chat" | "council"
    type: Optional[str] = None  # "chat" | "council" | "music" | "dream" | etc
    model: Optional[str] = None
    tools_used: Optional[list[str]] = None
    has_file_upload: bool = False
    success: bool = True


class SyncStatsRequest(BaseModel):
    """E5 localStorage stats sync from frontend."""
    agents: Optional[dict] = None
    zones: Optional[dict] = None
    achievements: Optional[list[str]] = None
    totalTasks: Optional[int] = None


class FeatureCheckRequest(BaseModel):
    """Check if user can access a feature."""
    feature: str


# ═══════════════════════════════════════════════════════════════════════════════
# ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════════════

@router.get("/progress")
async def get_quest_progress(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get full quest progress for the current user.

    Returns quest state, milestones, unlocked features, stats.
    Used by the frontend to render the Village quest UI.
    """
    service = ProgressionService(db)
    return await service.get_progress_response(user.id)


@router.post("/check-milestones")
async def check_milestones(
    event: TaskEventRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Check if a task completion triggers any new milestones.

    Called after each task execution in the Village.
    Returns newly completed milestones and unlocked features.
    """
    service = ProgressionService(db)
    result = await service.check_milestones(user.id, event.model_dump())
    await db.commit()
    return result


@router.get("/milestones")
async def get_milestone_definitions(
    stage: Optional[str] = None,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get milestone definitions for a quest stage.

    If no stage specified, returns milestones for the user's current stage.
    """
    service = ProgressionService(db)
    prog = await service.get_progression(user.id)

    target_stage = stage or (prog.quest_stage if prog else "seeker")

    milestones = MILESTONE_DEFINITIONS.get(target_stage, [])
    completed_ids = set(prog.milestones_completed or []) if prog else set()

    return {
        "stage": target_stage,
        "milestones": [
            {
                "id": m.id,
                "name": m.name,
                "description": m.description,
                "feature_unlocked": m.feature_unlocked,
                "completed": m.id in completed_ids,
            }
            for m in milestones
        ],
    }


@router.post("/sync-stats")
async def sync_stats(
    stats: SyncStatsRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Sync E5 localStorage gamification stats to server.

    Called periodically or after significant events to persist
    the frontend gamification state server-side.
    """
    service = ProgressionService(db)
    prog = await service.sync_stats(user.id, stats.model_dump(exclude_none=True))
    await db.commit()

    return {
        "synced": True,
        "total_tasks": prog.total_tasks,
        "quest_active": prog.quest_active,
    }


@router.post("/check-feature")
async def check_feature(
    request: FeatureCheckRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Check if the current user can access a specific feature.

    Returns access status and, if locked, info about how to unlock.
    """
    has_access = check_feature_access(user, request.feature)

    if has_access:
        return {"access": True, "feature": request.feature}

    # Return unlock hint
    info = get_locked_feature_info(request.feature)
    return {"access": False, **info}


@router.get("/features")
async def get_feature_registry(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get the full feature registry with user's unlock status.

    Useful for the frontend to know which features are locked/unlocked.
    """
    service = ProgressionService(db)
    prog = await service.get_progression(user.id)
    unlocked = set(prog.features_unlocked or []) if prog else set()
    quest_active = prog.quest_active if prog else False

    features = {}
    for feature_id, feature_def in FEATURE_REGISTRY.items():
        if quest_active:
            is_unlocked = feature_id in unlocked
        else:
            # Classic tier — check tier hierarchy
            is_unlocked = check_feature_access(user, feature_id)

        milestone_id = feature_def.get("quest_milestone")
        milestone = ALL_MILESTONES.get(milestone_id)

        features[feature_id] = {
            "unlocked": is_unlocked,
            "tier": feature_def["tier"],
            "milestone_id": milestone_id,
            "milestone_name": milestone.name if milestone else None,
        }

    return {
        "quest_active": quest_active,
        "features": features,
    }
