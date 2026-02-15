"""
Admin API Endpoints - User management, stats, and system controls.

All endpoints require is_admin=True on the authenticated user.
"""

import logging
from typing import Optional
from uuid import UUID
from datetime import datetime, timezone, timedelta

from fastapi import APIRouter, Depends, HTTPException, status, Query
from pydantic import BaseModel, Field
from sqlalchemy import select, func, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.models.user import User
from app.models.billing import Subscription, CreditBalance, CreditTransaction, Coupon
from app.models.progression import UserProgression
from app.models.feedback import BugReport
from app.models.conversation import Conversation, Message
from app.models.agora import AgoraPost, AgoraComment
from app.auth.deps import get_current_user
from app.config import TIER_LIMITS, QUEST_TIER_MAP
from app.services.llm_provider import get_available_providers, PROVIDER_MODELS

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/admin", tags=["Admin"])


# ═══════════════════════════════════════════════════════════════════════════════
# Schemas
# ═══════════════════════════════════════════════════════════════════════════════

class UserResponse(BaseModel):
    id: UUID
    email: str
    display_name: Optional[str]
    tier: str
    messages_used: int
    messages_limit: Optional[int]
    credit_balance: int
    is_admin: bool
    created_at: datetime
    subscription_status: Optional[str] = None
    quest_active: bool = False
    quest_stage: Optional[str] = None


class UserListResponse(BaseModel):
    users: list[UserResponse]
    total: int


class UpdateAdminRequest(BaseModel):
    is_admin: bool


class UpdateTierRequest(BaseModel):
    tier: str  # free_trial, seeker, adept, opus, azothic (or quest_seeker, etc.)
    reset_usage: bool = True  # Reset messages_used to 0


class TierGrantUpdate(BaseModel):
    tier: str
    grants: dict  # {"together": true, "groq": {"expires_at": "2026-03-01"}}


class UserGrantUpdate(BaseModel):
    provider: str
    enabled: bool = True
    expires_at: Optional[str] = None
    note: Optional[str] = None


class ProviderStatus(BaseModel):
    id: str
    name: str
    available: bool
    model_count: int


class ResetUsageRequest(BaseModel):
    extra_messages: int = Field(0, ge=0, le=10000, description="Grant extra messages on top of reset")


class AddCreditsRequest(BaseModel):
    amount_cents: int = Field(ge=1, le=100000, description="Credits to add in cents")
    note: Optional[str] = Field(None, max_length=500)


class ToggleQuestRequest(BaseModel):
    quest_active: bool
    unlock_all: bool = False  # When deactivating, unlock all features (classic upgrade)


class StatsResponse(BaseModel):
    # Core
    total_users: int
    total_messages: int
    total_conversations: int
    active_coupons: int
    users_by_tier: dict
    # Quest Progression
    total_quest_users: int = 0
    quest_users_by_stage: dict = {}
    # Features
    total_music_tasks: int
    music_by_status: dict
    total_council_sessions: int
    council_by_state: dict
    total_jam_sessions: int
    # Nursery
    total_nursery_datasets: int = 0
    total_nursery_jobs: int = 0
    nursery_jobs_by_status: dict = {}
    total_nursery_models: int = 0
    total_nursery_apprentices: int = 0
    # Storage
    total_vault_files: int
    total_vault_storage_mb: float
    total_neural_vectors: int
    # Providers
    providers: list[ProviderStatus]


# ═══════════════════════════════════════════════════════════════════════════════
# Admin Check Dependency
# ═══════════════════════════════════════════════════════════════════════════════

async def require_admin(user: User = Depends(get_current_user)) -> User:
    """Dependency that requires admin access."""
    if not getattr(user, 'is_admin', False):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    return user


# ═══════════════════════════════════════════════════════════════════════════════
# User Management
# ═══════════════════════════════════════════════════════════════════════════════

@router.get("/users", response_model=UserListResponse)
async def list_users(
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    search: Optional[str] = Query(None, max_length=200),
):
    """List all users with their subscription info."""
    query = select(User).order_by(User.created_at.desc())

    if search:
        query = query.where(User.email.ilike(f"%{search}%"))

    query = query.offset(offset).limit(limit)
    result = await db.execute(query)
    users = result.scalars().all()

    # Batch-fetch subscriptions, credit balances, and progressions
    user_ids = [u.id for u in users]
    sub_result = await db.execute(
        select(Subscription).where(Subscription.user_id.in_(user_ids))
    )
    subs_map = {s.user_id: s for s in sub_result.scalars().all()}

    credit_result = await db.execute(
        select(CreditBalance).where(CreditBalance.user_id.in_(user_ids))
    )
    credits_map = {c.user_id: c for c in credit_result.scalars().all()}

    prog_result = await db.execute(
        select(UserProgression).where(UserProgression.user_id.in_(user_ids))
    )
    prog_map = {p.user_id: p for p in prog_result.scalars().all()}

    user_list = []
    for user in users:
        subscription = subs_map.get(user.id)
        credit_balance = credits_map.get(user.id)
        progression = prog_map.get(user.id)

        user_list.append(UserResponse(
            id=user.id,
            email=user.email,
            display_name=user.display_name,
            tier=subscription.tier if subscription else "free_trial",
            messages_used=subscription.messages_used if subscription else 0,
            messages_limit=subscription.messages_limit if subscription else 50,
            credit_balance=credit_balance.balance_cents if credit_balance else 0,
            is_admin=user.is_admin,
            created_at=user.created_at,
            subscription_status=subscription.status if subscription else None,
            quest_active=progression.quest_active if progression else False,
            quest_stage=progression.quest_stage if progression and progression.quest_active else None,
        ))

    # Get total count
    count_query = select(func.count(User.id))
    if search:
        count_query = count_query.where(User.email.ilike(f"%{search}%"))
    count_result = await db.execute(count_query)
    total = count_result.scalar()

    return UserListResponse(users=user_list, total=total)


@router.patch("/users/{user_id}/admin")
async def update_user_admin(
    user_id: UUID,
    request: UpdateAdminRequest,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Toggle admin status for a user."""
    # Prevent self-demotion
    if user_id == admin.id and not request.is_admin:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot remove your own admin status"
        )

    result = await db.execute(
        select(User).where(User.id == user_id)
    )
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user.is_admin = request.is_admin
    await db.commit()

    logger.info(f"Admin {admin.email} set is_admin={request.is_admin} for user {user.email}")

    return {"status": "updated", "user_id": str(user_id), "is_admin": request.is_admin}


@router.patch("/users/{user_id}/tier")
async def update_user_tier(
    user_id: UUID,
    request: UpdateTierRequest,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Change a user's subscription tier (admin override).

    Resolves quest tier IDs (quest_seeker etc.) to their classic equivalents.
    Sets status=active, resets usage, and sets billing period dates.
    """
    # Resolve quest tier → classic tier
    effective_tier = QUEST_TIER_MAP.get(request.tier, request.tier)
    valid_tiers = ["free_trial", "seeker", "adept", "opus", "azothic"]

    if effective_tier not in valid_tiers:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid tier '{request.tier}'. Valid: {valid_tiers + list(QUEST_TIER_MAP.keys())}"
        )

    now = datetime.now(timezone.utc)

    # Get or create subscription
    result = await db.execute(
        select(Subscription).where(Subscription.user_id == user_id)
    )
    subscription = result.scalar_one_or_none()

    if not subscription:
        from uuid import uuid4
        subscription = Subscription(
            user_id=user_id,
            stripe_customer_id=f"admin_override_{uuid4().hex[:8]}",
            tier=effective_tier,
            status="active",
        )
        db.add(subscription)
    else:
        subscription.tier = effective_tier
        subscription.status = "active"
        subscription.cancel_at_period_end = False

    # Update message limits based on tier
    tier_config = TIER_LIMITS.get(effective_tier, TIER_LIMITS["free_trial"])
    subscription.messages_limit = tier_config["messages_per_month"]

    # Reset usage if requested
    if request.reset_usage:
        subscription.messages_used = 0

    # Set billing period (now → now + 30 days)
    subscription.current_period_start = now
    subscription.current_period_end = now + timedelta(days=30)

    await db.commit()

    logger.info(f"Admin {admin.email} set tier={effective_tier} (requested={request.tier}) for user {user_id}")

    return {
        "status": "updated",
        "user_id": str(user_id),
        "tier": effective_tier,
        "messages_used": subscription.messages_used,
        "messages_limit": subscription.messages_limit,
        "period_end": subscription.current_period_end.isoformat(),
    }


@router.get("/users/{user_id}/usage")
async def get_user_usage(
    user_id: UUID,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Get detailed usage summary for a specific user (admin only)."""
    from app.services.usage import UsageService, FeatureCreditService, get_current_period

    # Get user's tier
    result = await db.execute(
        select(Subscription).where(Subscription.user_id == user_id)
    )
    subscription = result.scalar_one_or_none()
    tier = subscription.tier if subscription else "free_trial"
    tier_config = TIER_LIMITS.get(tier, TIER_LIMITS["free_trial"])

    # Get usage counters
    usage_svc = UsageService(db)
    counters = await usage_svc.get_usage_summary(user_id)

    # Get feature credits
    credit_svc = FeatureCreditService(db)
    feature_credits = await credit_svc.get_credit_summary(user_id)

    return {
        "user_id": str(user_id),
        "tier": tier,
        "period": get_current_period(),
        "counters": counters,
        "feature_credits": feature_credits,
        "tier_limits": {
            "messages_per_month": tier_config.get("messages_per_month"),
            "opus_messages_per_month": tier_config.get("opus_messages_per_month"),
            "council_sessions_per_month": tier_config.get("council_sessions_per_month"),
            "suno_generations_per_month": tier_config.get("suno_generations_per_month"),
            "jam_sessions_per_month": tier_config.get("jam_sessions_per_month"),
        },
    }


# ═══════════════════════════════════════════════════════════════════════════════
# User Progression & Credits
# ═══════════════════════════════════════════════════════════════════════════════

@router.get("/users/{user_id}/progression")
async def get_user_progression(
    user_id: UUID,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """View a user's quest progression details."""
    result = await db.execute(
        select(UserProgression).where(UserProgression.user_id == user_id)
    )
    prog = result.scalar_one_or_none()

    if not prog:
        return {
            "user_id": str(user_id),
            "quest_active": False,
            "quest_stage": None,
            "milestones_completed": [],
            "features_unlocked": [],
            "total_tasks": 0,
            "agent_stats": {},
            "zone_stats": {},
        }

    return {
        "user_id": str(user_id),
        "quest_active": prog.quest_active,
        "quest_stage": prog.quest_stage,
        "quest_started_at": prog.quest_started_at.isoformat() if prog.quest_started_at else None,
        "milestones_completed": prog.milestones_completed or [],
        "features_unlocked": prog.features_unlocked or [],
        "total_tasks": prog.total_tasks,
        "agent_stats": prog.agent_stats or {},
        "zone_stats": prog.zone_stats or {},
        "created_at": prog.created_at.isoformat() if prog.created_at else None,
        "updated_at": prog.updated_at.isoformat() if prog.updated_at else None,
    }


@router.patch("/users/{user_id}/quest")
async def toggle_user_quest(
    user_id: UUID,
    request: ToggleQuestRequest,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Toggle quest mode on/off for a user."""
    from app.services.progression import ProgressionService

    svc = ProgressionService(db)

    if request.quest_active:
        prog = await svc.activate_quest(user_id)
        await db.commit()
        logger.info(f"Admin {admin.email} activated quest for user {user_id}")
        return {
            "status": "activated",
            "user_id": str(user_id),
            "quest_stage": prog.quest_stage,
        }
    else:
        prog = await svc.deactivate_quest(user_id, unlock_all=request.unlock_all)
        await db.commit()
        logger.info(f"Admin {admin.email} deactivated quest for user {user_id} (unlock_all={request.unlock_all})")
        return {
            "status": "deactivated",
            "user_id": str(user_id),
            "unlock_all": request.unlock_all,
        }


@router.post("/users/{user_id}/reset-usage")
async def reset_user_usage(
    user_id: UUID,
    request: ResetUsageRequest,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Reset a user's message usage counter, optionally grant extra messages."""
    result = await db.execute(
        select(Subscription).where(Subscription.user_id == user_id)
    )
    subscription = result.scalar_one_or_none()

    if not subscription:
        raise HTTPException(status_code=404, detail="No subscription found for user")

    subscription.messages_used = 0
    if request.extra_messages > 0:
        subscription.messages_limit = (subscription.messages_limit or 0) + request.extra_messages

    await db.commit()

    logger.info(
        f"Admin {admin.email} reset usage for user {user_id} "
        f"(extra_messages={request.extra_messages})"
    )

    return {
        "status": "reset",
        "user_id": str(user_id),
        "messages_used": 0,
        "messages_limit": subscription.messages_limit,
    }


@router.post("/users/{user_id}/add-credits")
async def add_user_credits(
    user_id: UUID,
    request: AddCreditsRequest,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Add credits directly to a user's balance (no coupon/Stripe needed)."""
    # Get or create credit balance
    result = await db.execute(
        select(CreditBalance).where(CreditBalance.user_id == user_id)
    )
    balance = result.scalar_one_or_none()

    now = datetime.now(timezone.utc)

    if not balance:
        balance = CreditBalance(
            user_id=user_id,
            balance_cents=request.amount_cents,
            total_purchased_cents=request.amount_cents,
            created_at=now,
            updated_at=now,
        )
        db.add(balance)
    else:
        balance.balance_cents += request.amount_cents
        balance.total_purchased_cents += request.amount_cents
        balance.updated_at = now

    # Record transaction
    txn = CreditTransaction(
        user_id=user_id,
        amount_cents=request.amount_cents,
        balance_after=balance.balance_cents,
        transaction_type="bonus",
        description=request.note or f"Admin grant by {admin.email}",
    )
    db.add(txn)

    await db.commit()

    logger.info(f"Admin {admin.email} added {request.amount_cents}c credits to user {user_id}")

    return {
        "status": "credited",
        "user_id": str(user_id),
        "amount_cents": request.amount_cents,
        "new_balance": balance.balance_cents,
    }


# ═══════════════════════════════════════════════════════════════════════════════
# Stats
# ═══════════════════════════════════════════════════════════════════════════════

@router.get("/stats", response_model=StatsResponse)
async def get_stats(
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Get system-wide statistics including all platform features."""
    # --- Core counts ---
    user_count = await db.execute(select(func.count(User.id)))
    total_users = user_count.scalar() or 0

    try:
        msg_count = await db.execute(select(func.count(Message.id)))
        total_messages = msg_count.scalar() or 0
    except Exception:
        total_messages = 0

    try:
        conv_count = await db.execute(select(func.count(Conversation.id)))
        total_conversations = conv_count.scalar() or 0
    except Exception:
        total_conversations = 0

    coupon_count = await db.execute(
        select(func.count(Coupon.id)).where(Coupon.is_active == True)
    )
    active_coupons = coupon_count.scalar() or 0

    # --- Users by tier ---
    tier_query = await db.execute(
        select(Subscription.tier, func.count(Subscription.id))
        .group_by(Subscription.tier)
    )
    tier_results = tier_query.fetchall()

    users_by_tier = {"Free Trial": 0, "Seeker": 0, "Adept": 0, "Opus": 0, "Azothic": 0}
    tier_names = {"free_trial": "Free Trial", "seeker": "Seeker", "adept": "Adept", "opus": "Opus", "azothic": "Azothic"}

    for tier, count in tier_results:
        name = tier_names.get(tier, tier)
        if name in users_by_tier:
            users_by_tier[name] = count

    users_with_sub = sum(users_by_tier.values())
    users_by_tier["Free Trial"] += total_users - users_with_sub

    # --- Quest Progression ---
    total_quest_users = 0
    quest_users_by_stage = {}
    try:
        quest_count = await db.execute(
            select(func.count(UserProgression.id)).where(UserProgression.quest_active == True)
        )
        total_quest_users = quest_count.scalar() or 0

        stage_query = await db.execute(
            select(UserProgression.quest_stage, func.count(UserProgression.id))
            .where(UserProgression.quest_active == True)
            .group_by(UserProgression.quest_stage)
        )
        quest_users_by_stage = {stage: count for stage, count in stage_query.fetchall()}
    except Exception as e:
        logger.debug(f"Quest progression stats unavailable: {e}")

    # --- Music tasks ---
    total_music_tasks = 0
    music_by_status = {}
    try:
        from app.models.music import MusicTask
        music_count = await db.execute(select(func.count(MusicTask.id)))
        total_music_tasks = music_count.scalar() or 0

        music_status_query = await db.execute(
            select(MusicTask.status, func.count(MusicTask.id))
            .group_by(MusicTask.status)
        )
        music_by_status = {s: c for s, c in music_status_query.fetchall()}
    except Exception as e:
        logger.debug(f"Music stats unavailable: {e}")

    # --- Council sessions ---
    total_council_sessions = 0
    council_by_state = {}
    try:
        from app.models.council import DeliberationSession
        council_count = await db.execute(select(func.count(DeliberationSession.id)))
        total_council_sessions = council_count.scalar() or 0

        council_state_query = await db.execute(
            select(DeliberationSession.state, func.count(DeliberationSession.id))
            .group_by(DeliberationSession.state)
        )
        council_by_state = {s: c for s, c in council_state_query.fetchall()}
    except Exception as e:
        logger.debug(f"Council stats unavailable: {e}")

    # --- Jam sessions ---
    total_jam_sessions = 0
    try:
        from app.models.jam import JamSession
        jam_count = await db.execute(select(func.count(JamSession.id)))
        total_jam_sessions = jam_count.scalar() or 0
    except Exception as e:
        logger.debug(f"Jam stats unavailable: {e}")

    # --- Nursery ---
    total_nursery_datasets = 0
    total_nursery_jobs = 0
    nursery_jobs_by_status = {}
    total_nursery_models = 0
    total_nursery_apprentices = 0
    try:
        from app.models.nursery import NurseryDataset, NurseryTrainingJob, NurseryModelRecord, NurseryApprentice

        ds_count = await db.execute(select(func.count(NurseryDataset.id)))
        total_nursery_datasets = ds_count.scalar() or 0

        job_count = await db.execute(select(func.count(NurseryTrainingJob.id)))
        total_nursery_jobs = job_count.scalar() or 0

        # Jobs by status breakdown
        job_status_query = await db.execute(
            select(NurseryTrainingJob.status, func.count(NurseryTrainingJob.id))
            .group_by(NurseryTrainingJob.status)
        )
        nursery_jobs_by_status = {status: count for status, count in job_status_query.fetchall()}

        model_count = await db.execute(select(func.count(NurseryModelRecord.id)))
        total_nursery_models = model_count.scalar() or 0

        ap_count = await db.execute(select(func.count(NurseryApprentice.id)))
        total_nursery_apprentices = ap_count.scalar() or 0
    except Exception as e:
        logger.debug(f"Nursery stats unavailable: {e}")

    # --- Vault (files) ---
    total_vault_files = 0
    total_vault_storage_mb = 0.0
    try:
        from app.models.file import File
        file_count = await db.execute(select(func.count(File.id)))
        total_vault_files = file_count.scalar() or 0

        storage_result = await db.execute(select(func.coalesce(func.sum(File.size_bytes), 0)))
        total_bytes = storage_result.scalar() or 0
        total_vault_storage_mb = round(total_bytes / (1024 * 1024), 1)
    except Exception as e:
        logger.debug(f"Vault stats unavailable: {e}")

    # --- Neural vectors (raw SQL - pgvector table) ---
    total_neural_vectors = 0
    try:
        vector_result = await db.execute(text("SELECT COUNT(*) FROM user_vectors"))
        total_neural_vectors = vector_result.scalar() or 0
    except Exception as e:
        logger.debug(f"Neural vector stats unavailable: {e}")

    # --- Provider status ---
    providers_raw = get_available_providers()
    providers = [
        ProviderStatus(
            id=p["id"],
            name=p["name"],
            available=p["available"],
            model_count=len(PROVIDER_MODELS.get(p["id"], {})),
        )
        for p in providers_raw
    ]

    return StatsResponse(
        total_users=total_users,
        total_messages=total_messages,
        total_conversations=total_conversations,
        active_coupons=active_coupons,
        users_by_tier=users_by_tier,
        total_quest_users=total_quest_users,
        quest_users_by_stage=quest_users_by_stage,
        total_music_tasks=total_music_tasks,
        music_by_status=music_by_status,
        total_council_sessions=total_council_sessions,
        council_by_state=council_by_state,
        total_jam_sessions=total_jam_sessions,
        total_nursery_datasets=total_nursery_datasets,
        total_nursery_jobs=total_nursery_jobs,
        nursery_jobs_by_status=nursery_jobs_by_status,
        total_nursery_models=total_nursery_models,
        total_nursery_apprentices=total_nursery_apprentices,
        total_vault_files=total_vault_files,
        total_vault_storage_mb=total_vault_storage_mb,
        total_neural_vectors=total_neural_vectors,
        providers=providers,
    )


# ═══════════════════════════════════════════════════════════════════════════════
# BUG REPORTS
# ═══════════════════════════════════════════════════════════════════════════════

class AdminReportResponse(BaseModel):
    id: str
    user_email: str
    category: str
    page: Optional[str] = None
    description: str
    browser_info: Optional[str] = None
    status: str
    admin_notes: Optional[str] = None
    created_at: str
    updated_at: Optional[str] = None


class AdminReportListResponse(BaseModel):
    reports: list[AdminReportResponse]
    total: int


class UpdateReportRequest(BaseModel):
    status: Optional[str] = Field(None, pattern="^(open|acknowledged|resolved|closed)$")
    admin_notes: Optional[str] = Field(None, max_length=2000)


@router.get("/reports", response_model=AdminReportListResponse)
async def list_reports(
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
    status_filter: Optional[str] = Query(None, alias="status", max_length=20),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    """List bug reports with optional status filter."""
    query = select(BugReport).order_by(BugReport.created_at.desc())

    if status_filter:
        query = query.where(BugReport.status == status_filter)

    # Get total count
    count_query = select(func.count(BugReport.id))
    if status_filter:
        count_query = count_query.where(BugReport.status == status_filter)
    total = await db.scalar(count_query) or 0

    query = query.offset(offset).limit(limit)
    result = await db.execute(query)
    reports = result.scalars().all()

    # Fetch user emails
    user_ids = [r.user_id for r in reports]
    users_result = await db.execute(select(User).where(User.id.in_(user_ids)))
    users_map = {u.id: u.email for u in users_result.scalars().all()}

    return AdminReportListResponse(
        reports=[
            AdminReportResponse(
                id=str(r.id),
                user_email=users_map.get(r.user_id, "unknown"),
                category=r.category,
                page=r.page,
                description=r.description,
                browser_info=r.browser_info,
                status=r.status,
                admin_notes=r.admin_notes,
                created_at=r.created_at.isoformat(),
                updated_at=r.updated_at.isoformat() if r.updated_at else None,
            )
            for r in reports
        ],
        total=total,
    )


@router.patch("/reports/{report_id}")
async def update_report(
    report_id: UUID,
    request: UpdateReportRequest,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Update a bug report's status or admin notes."""
    result = await db.execute(select(BugReport).where(BugReport.id == report_id))
    report = result.scalar_one_or_none()

    if not report:
        raise HTTPException(status_code=404, detail="Report not found")

    if request.status is not None:
        report.status = request.status
    if request.admin_notes is not None:
        report.admin_notes = request.admin_notes

    report.updated_at = datetime.now(timezone.utc)
    await db.commit()

    logger.info(f"Report {report_id} updated by {admin.email}: status={report.status}")

    return {"success": True, "status": report.status}


# ═══════════════════════════════════════════════════════════════════════════════
# PLATFORM GRANTS
# ═══════════════════════════════════════════════════════════════════════════════

@router.get("/grants")
async def get_platform_grants(
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Get all platform provider grants."""
    from app.models.system import SystemSettings
    from app.config import GRANTABLE_PROVIDERS

    # Tier-level grants from system_settings
    result = await db.execute(
        select(SystemSettings).where(SystemSettings.key == "platform_tier_grants")
    )
    row = result.scalar_one_or_none()
    tier_grants = row.value if row else {}

    # User-level grants: find users with platform_grants in settings
    # Use ORM query to avoid json/jsonb type issues with raw SQL
    all_users = await db.execute(select(User))
    user_grants = []
    for user_row in all_users.scalars():
        if user_row.settings and isinstance(user_row.settings.get("platform_grants"), dict):
            grants = user_row.settings["platform_grants"]
            if grants:  # non-empty
                user_grants.append({
                    "user_id": str(user_row.id),
                    "email": user_row.email,
                    "display_name": user_row.display_name,
                    "grants": grants,
                })

    return {
        "grantable_providers": GRANTABLE_PROVIDERS,
        "tier_grants": tier_grants,
        "user_grants": user_grants,
    }


@router.put("/grants/tier")
async def set_tier_grants(
    request: TierGrantUpdate,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Set platform grants for a tier (full replace for that tier)."""
    from app.models.system import SystemSettings
    from app.config import TIER_LIMITS, GRANTABLE_PROVIDERS
    from app.services.provider_access import invalidate_tier_grants_cache

    # Validate tier
    if request.tier not in TIER_LIMITS:
        raise HTTPException(status_code=400, detail=f"Invalid tier: {request.tier}")

    # Validate providers in grants
    for provider in request.grants:
        if provider not in GRANTABLE_PROVIDERS:
            raise HTTPException(status_code=400, detail=f"Invalid provider: {provider}")

    # Upsert system_settings row
    result = await db.execute(
        select(SystemSettings).where(SystemSettings.key == "platform_tier_grants")
    )
    settings_row = result.scalar_one_or_none()

    if settings_row:
        current = settings_row.value or {}
        current[request.tier] = request.grants
        settings_row.value = current
        settings_row.updated_at = datetime.now(timezone.utc)
        settings_row.updated_by = admin.id
        from sqlalchemy.orm.attributes import flag_modified
        flag_modified(settings_row, "value")
    else:
        settings_row = SystemSettings(
            key="platform_tier_grants",
            value={request.tier: request.grants},
            updated_at=datetime.now(timezone.utc),
            updated_by=admin.id,
        )
        db.add(settings_row)

    await db.commit()
    invalidate_tier_grants_cache()

    return {"status": "ok", "tier": request.tier, "grants": request.grants}


@router.put("/grants/user/{user_id}")
async def set_user_grant(
    user_id: UUID,
    request: UserGrantUpdate,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Grant or update a user's platform access to a provider."""
    from app.config import GRANTABLE_PROVIDERS

    if request.provider not in GRANTABLE_PROVIDERS:
        raise HTTPException(status_code=400, detail=f"Invalid provider: {request.provider}")

    # Find user
    result = await db.execute(select(User).where(User.id == user_id))
    target_user = result.scalar_one_or_none()
    if not target_user:
        raise HTTPException(status_code=404, detail="User not found")

    # Update settings
    if not target_user.settings:
        target_user.settings = {}
    if "platform_grants" not in target_user.settings:
        target_user.settings["platform_grants"] = {}

    if request.enabled:
        grant_value = True
        if request.expires_at or request.note:
            grant_value = {}
            if request.expires_at:
                grant_value["expires_at"] = request.expires_at
            if request.note:
                grant_value["note"] = request.note
            grant_value["granted_by"] = str(admin.id)
            grant_value["granted_at"] = datetime.now(timezone.utc).isoformat()
        target_user.settings["platform_grants"][request.provider] = grant_value
    else:
        target_user.settings["platform_grants"].pop(request.provider, None)

    from sqlalchemy.orm.attributes import flag_modified
    flag_modified(target_user, "settings")
    await db.commit()

    return {
        "status": "ok",
        "user_id": str(user_id),
        "provider": request.provider,
        "enabled": request.enabled,
    }


# ═══════════════════════════════════════════════════════════════════════════════
# ERROR TRACKING
# ═══════════════════════════════════════════════════════════════════════════════

class ErrorLogResponse(BaseModel):
    id: str
    category: str
    severity: str
    error_type: str
    message: str
    stacktrace: Optional[str] = None
    endpoint: Optional[str] = None
    http_method: Optional[str] = None
    status_code: Optional[int] = None
    response_time_ms: Optional[float] = None
    user_hash: Optional[str] = None
    context: Optional[dict] = None
    created_at: str


class ErrorListResponse(BaseModel):
    errors: list[ErrorLogResponse]
    total: int


class ErrorSettingsRequest(BaseModel):
    enabled: Optional[bool] = None
    min_severity: Optional[str] = Field(None, pattern="^(warning|error|critical)$")
    retention_days: Optional[int] = Field(None, ge=1, le=365)


@router.get("/errors", response_model=ErrorListResponse)
async def list_errors(
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
    category: Optional[str] = Query(None, max_length=30),
    severity: Optional[str] = Query(None, max_length=10),
    endpoint: Optional[str] = Query(None, max_length=300),
    hours: int = Query(24, ge=1, le=720),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    """List error logs with filters."""
    from datetime import timedelta
    from app.models.error_log import ErrorLog

    since = datetime.now(timezone.utc) - timedelta(hours=hours)
    query = select(ErrorLog).where(ErrorLog.created_at >= since)

    if category:
        query = query.where(ErrorLog.category == category)
    if severity:
        query = query.where(ErrorLog.severity == severity)
    if endpoint:
        query = query.where(ErrorLog.endpoint.ilike(f"%{endpoint}%"))

    # Count
    count_query = select(func.count(ErrorLog.id)).where(ErrorLog.created_at >= since)
    if category:
        count_query = count_query.where(ErrorLog.category == category)
    if severity:
        count_query = count_query.where(ErrorLog.severity == severity)
    if endpoint:
        count_query = count_query.where(ErrorLog.endpoint.ilike(f"%{endpoint}%"))
    total = await db.scalar(count_query) or 0

    query = query.order_by(ErrorLog.created_at.desc()).offset(offset).limit(limit)
    result = await db.execute(query)
    errors = result.scalars().all()

    return ErrorListResponse(
        errors=[
            ErrorLogResponse(
                id=str(e.id),
                category=e.category,
                severity=e.severity,
                error_type=e.error_type,
                message=e.message,
                stacktrace=e.stacktrace,
                endpoint=e.endpoint,
                http_method=e.http_method,
                status_code=e.status_code,
                response_time_ms=e.response_time_ms,
                user_hash=e.user_hash,
                context=e.context,
                created_at=e.created_at.isoformat(),
            )
            for e in errors
        ],
        total=total,
    )


@router.get("/errors/stats")
async def get_error_stats_endpoint(
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
    hours: int = Query(24, ge=1, le=720),
):
    """Get aggregated error statistics."""
    from app.services.error_tracking import get_error_stats
    return await get_error_stats(db, hours)


@router.get("/errors/settings")
async def get_error_settings(
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Get current error tracking settings."""
    from app.services.error_tracking import get_tracking_settings
    return await get_tracking_settings(db)


@router.put("/errors/settings")
async def update_error_settings(
    request: ErrorSettingsRequest,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Update error tracking settings."""
    from app.models.system import SystemSettings
    from app.services.error_tracking import get_tracking_settings, invalidate_settings_cache

    # Get current
    current = await get_tracking_settings(db)

    # Merge updates
    if request.enabled is not None:
        current["enabled"] = request.enabled
    if request.min_severity is not None:
        current["min_severity"] = request.min_severity
    if request.retention_days is not None:
        current["retention_days"] = request.retention_days

    # Upsert
    result = await db.execute(
        select(SystemSettings).where(SystemSettings.key == "error_tracking")
    )
    row = result.scalar_one_or_none()

    if row:
        row.value = current
        row.updated_at = datetime.now(timezone.utc)
        row.updated_by = admin.id
        from sqlalchemy.orm.attributes import flag_modified
        flag_modified(row, "value")
    else:
        row = SystemSettings(
            key="error_tracking",
            value=current,
            updated_at=datetime.now(timezone.utc),
            updated_by=admin.id,
        )
        db.add(row)

    await db.commit()
    invalidate_settings_cache()

    logger.info(f"Error tracking settings updated by {admin.email}: {current}")
    return current


@router.delete("/errors/purge")
async def purge_errors(
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
    confirm: bool = Query(False),
):
    """Manually purge error logs. Requires confirm=true."""
    if not confirm:
        from app.models.error_log import ErrorLog
        total = await db.scalar(select(func.count(ErrorLog.id))) or 0
        return {"warning": "Add ?confirm=true to purge", "total_records": total}

    from app.services.error_tracking import purge_old_errors
    deleted = await purge_old_errors(db, retention_days=0)
    logger.info(f"Error logs purged by {admin.email}: {deleted} entries deleted")
    return {"status": "purged", "deleted": deleted}


@router.get("/errors/export")
async def export_errors(
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
    format: str = Query("json", pattern="^(json|csv)$"),
    hours: int = Query(24, ge=1, le=720),
    category: Optional[str] = Query(None, max_length=30),
    severity: Optional[str] = Query(None, max_length=10),
):
    """Export error logs as JSON or CSV (up to 5000 records)."""
    from datetime import timedelta
    from app.models.error_log import ErrorLog

    since = datetime.now(timezone.utc) - timedelta(hours=hours)
    query = select(ErrorLog).where(ErrorLog.created_at >= since)

    if category:
        query = query.where(ErrorLog.category == category)
    if severity:
        query = query.where(ErrorLog.severity == severity)

    query = query.order_by(ErrorLog.created_at.desc()).limit(5000)
    result = await db.execute(query)
    errors = result.scalars().all()

    records = [
        {
            "id": str(e.id),
            "category": e.category,
            "severity": e.severity,
            "error_type": e.error_type,
            "message": e.message,
            "endpoint": e.endpoint,
            "http_method": e.http_method,
            "status_code": e.status_code,
            "response_time_ms": e.response_time_ms,
            "user_hash": e.user_hash,
            "context": e.context,
            "created_at": e.created_at.isoformat(),
        }
        for e in errors
    ]

    if format == "csv":
        import csv
        import io
        from fastapi.responses import StreamingResponse

        output = io.StringIO()
        if records:
            writer = csv.DictWriter(output, fieldnames=records[0].keys())
            writer.writeheader()
            for r in records:
                # Flatten context to string for CSV
                r["context"] = str(r["context"]) if r["context"] else ""
                writer.writerow(r)

        output.seek(0)
        return StreamingResponse(
            iter([output.getvalue()]),
            media_type="text/csv",
            headers={"Content-Disposition": "attachment; filename=error_logs.csv"},
        )

    return {"errors": records, "count": len(records)}


@router.delete("/grants/user/{user_id}/{provider}")
async def revoke_user_grant(
    user_id: UUID,
    provider: str,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Revoke a user's platform grant for a specific provider."""
    result = await db.execute(select(User).where(User.id == user_id))
    target_user = result.scalar_one_or_none()
    if not target_user:
        raise HTTPException(status_code=404, detail="User not found")

    if target_user.settings and "platform_grants" in target_user.settings:
        target_user.settings["platform_grants"].pop(provider, None)
        from sqlalchemy.orm.attributes import flag_modified
        flag_modified(target_user, "settings")
        await db.commit()

    return {"status": "ok", "user_id": str(user_id), "provider": provider, "revoked": True}


# ═══════════════════════════════════════════════════════════════════════════════
# Agora Moderation
# ═══════════════════════════════════════════════════════════════════════════════

@router.get("/agora/stats")
async def get_agora_stats(
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Get Agora post statistics."""
    total = (await db.execute(
        select(func.count()).select_from(AgoraPost)
    )).scalar() or 0

    flagged = (await db.execute(
        select(func.count()).select_from(AgoraPost).where(AgoraPost.flag_count > 0)
    )).scalar() or 0

    hidden = (await db.execute(
        select(func.count()).select_from(AgoraPost).where(AgoraPost.visibility == "hidden")
    )).scalar() or 0

    comments = (await db.execute(
        select(func.count()).select_from(AgoraComment)
    )).scalar() or 0

    return {
        "total_posts": total,
        "flagged_posts": flagged,
        "hidden_posts": hidden,
        "total_comments": comments,
    }


@router.get("/agora/posts")
async def list_agora_posts(
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
    filter: Optional[str] = Query(None, description="flagged, hidden, all"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    """List Agora posts for moderation."""
    from sqlalchemy.orm import selectinload

    query = select(AgoraPost).options(
        selectinload(AgoraPost.user)
    ).order_by(AgoraPost.created_at.desc())

    if filter == "flagged":
        query = query.where(AgoraPost.flag_count > 0, AgoraPost.visibility == "public")
    elif filter == "hidden":
        query = query.where(AgoraPost.visibility == "hidden")
    else:
        query = query.where(AgoraPost.visibility != "deleted")

    total_q = select(func.count()).select_from(query.subquery())
    total = (await db.execute(total_q)).scalar() or 0

    result = await db.execute(query.offset(offset).limit(limit))
    posts = result.scalars().all()

    return {
        "posts": [
            {
                "id": str(p.id),
                "content_type": p.content_type,
                "title": p.title,
                "body": (p.body or "")[:300],
                "agent_id": p.agent_id,
                "visibility": p.visibility,
                "is_auto": p.is_auto,
                "is_pinned": p.is_pinned,
                "flag_count": p.flag_count,
                "reaction_count": p.reaction_count,
                "comment_count": p.comment_count,
                "user_email": p.user.email if p.user else None,
                "created_at": p.created_at.isoformat() if p.created_at else None,
            }
            for p in posts
        ],
        "total": total,
    }


class AgoraModAction(BaseModel):
    action: str = Field(description="hide, restore, delete, pin, unpin")


# ═══════════════════════════════════════════════════════════════════════════════
# CerebroCortex Migration
# ═══════════════════════════════════════════════════════════════════════════════

@router.post("/migrate-cerebrocortex")
async def migrate_cerebrocortex(
    admin: User = Depends(require_admin),
    user_id: Optional[UUID] = Query(None, description="Migrate specific user, or all if omitted"),
):
    """Run CerebroCortex data migration from user_vectors and agent_memories.

    Idempotent - safe to re-run. Only migrates records not already in cerebro tables.
    Uses isolated DB session since migration does multiple commits/rollbacks.
    """
    from app.database import get_db_context
    from app.services.cerebro.migration import run_full_migration

    try:
        async with get_db_context() as db:
            report = await run_full_migration(db, user_id)
        logger.info(f"CerebroCortex migration triggered by {admin.email}: {report}")
        return {"status": "ok", "report": report}
    except Exception as e:
        logger.error(f"CerebroCortex migration failed: {e}")
        raise HTTPException(status_code=500, detail=f"Migration failed: {e}")


@router.patch("/agora/posts/{post_id}")
async def moderate_agora_post(
    post_id: UUID,
    body: AgoraModAction,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Moderate an Agora post."""
    result = await db.execute(select(AgoraPost).where(AgoraPost.id == post_id))
    post = result.scalar_one_or_none()
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")

    if body.action == "hide":
        post.visibility = "hidden"
    elif body.action == "restore":
        post.visibility = "public"
        post.flag_count = 0
    elif body.action == "delete":
        post.visibility = "deleted"
    elif body.action == "pin":
        post.is_pinned = True
    elif body.action == "unpin":
        post.is_pinned = False
    else:
        raise HTTPException(status_code=400, detail=f"Unknown action: {body.action}")

    await db.commit()

    return {"status": "ok", "post_id": str(post_id), "action": body.action, "visibility": post.visibility}


# ═══════════════════════════════════════════════════════════════════════════════
# Dream Engine Stats (privacy-safe aggregates only)
# ═══════════════════════════════════════════════════════════════════════════════

@router.get("/dream/stats")
async def get_dream_stats(
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """
    Aggregated Dream Engine statistics for admin dashboard.

    Privacy-safe by construction: all queries are aggregates.
    No user_id, email, or memory content is returned.
    """
    result = {
        "total_dream_cycles": 0,
        "successful_cycles": 0,
        "failed_cycles": 0,
        "success_rate_pct": 0.0,
        "total_llm_calls": 0,
        "total_input_tokens": 0,
        "total_output_tokens": 0,
        "total_memories_processed": 0,
        "total_links_created": 0,
        "total_links_strengthened": 0,
        "total_memories_pruned": 0,
        "total_schemas_extracted": 0,
        "total_procedures_extracted": 0,
        "avg_cycle_duration_sec": 0.0,
        "phase_breakdown": {},
        "cycles_by_day": [],
        "cortex_totals": {
            "memory_nodes": 0,
            "episodes": 0,
            "procedures": 0,
            "schemas": 0,
        },
    }

    # --- Dream cycle aggregates from cerebro_dream_log ---
    try:
        # Distinct cycle counts
        cycle_row = await db.execute(text("""
            SELECT
                COUNT(DISTINCT cycle_id) AS total_cycles,
                COUNT(DISTINCT CASE WHEN success = true THEN cycle_id END) AS successful
            FROM cerebro_dream_log
            WHERE cycle_id IS NOT NULL
        """))
        cr = cycle_row.fetchone()
        if cr:
            total = cr[0] or 0
            success = cr[1] or 0
            result["total_dream_cycles"] = total
            result["successful_cycles"] = success
            result["failed_cycles"] = total - success
            result["success_rate_pct"] = round((success / total * 100) if total > 0 else 0, 1)

        # Aggregate metrics across all phases
        agg_row = await db.execute(text("""
            SELECT
                COUNT(*) AS phases,
                COALESCE(SUM(total_llm_calls), 0) AS llm_calls,
                COALESCE(SUM(total_input_tokens), 0) AS in_tokens,
                COALESCE(SUM(total_output_tokens), 0) AS out_tokens,
                COALESCE(SUM(memories_processed), 0) AS mem_proc,
                COALESCE(SUM(links_created), 0) AS links_c,
                COALESCE(SUM(links_strengthened), 0) AS links_s,
                COALESCE(SUM(memories_pruned), 0) AS pruned,
                COALESCE(SUM(schemas_extracted), 0) AS schemas,
                COALESCE(SUM(procedures_extracted), 0) AS procedures,
                COALESCE(AVG(duration_seconds), 0) AS avg_dur
            FROM cerebro_dream_log
        """))
        ar = agg_row.fetchone()
        if ar:
            result["total_llm_calls"] = int(ar[1])
            result["total_input_tokens"] = int(ar[2])
            result["total_output_tokens"] = int(ar[3])
            result["total_memories_processed"] = int(ar[4])
            result["total_links_created"] = int(ar[5])
            result["total_links_strengthened"] = int(ar[6])
            result["total_memories_pruned"] = int(ar[7])
            result["total_schemas_extracted"] = int(ar[8])
            result["total_procedures_extracted"] = int(ar[9])
            result["avg_cycle_duration_sec"] = round(float(ar[10]), 2)

        # Phase breakdown
        phase_rows = await db.execute(text("""
            SELECT
                phase,
                COUNT(*) AS count,
                COALESCE(AVG(duration_seconds), 0) AS avg_duration,
                COALESCE(SUM(memories_processed), 0) AS total_memories
            FROM cerebro_dream_log
            GROUP BY phase
            ORDER BY phase
        """))
        for row in phase_rows.fetchall():
            result["phase_breakdown"][row[0]] = {
                "count": int(row[1]),
                "avg_duration": round(float(row[2]), 2),
                "total_memories": int(row[3]),
            }

        # Cycles per day (last 30 days)
        day_rows = await db.execute(text("""
            SELECT DATE(completed_at) AS day, COUNT(DISTINCT cycle_id) AS count
            FROM cerebro_dream_log
            WHERE completed_at >= NOW() - INTERVAL '30 days'
              AND cycle_id IS NOT NULL
            GROUP BY DATE(completed_at)
            ORDER BY day
        """))
        result["cycles_by_day"] = [
            {"date": str(row[0]), "count": int(row[1])}
            for row in day_rows.fetchall()
        ]

    except Exception as e:
        logger.debug(f"Dream log stats unavailable: {e}")

    # --- Cortex totals (privacy-safe aggregates) ---
    try:
        nodes = await db.execute(text(
            "SELECT COUNT(*) FROM cerebro_memory_nodes"
        ))
        result["cortex_totals"]["memory_nodes"] = int(nodes.scalar() or 0)
    except Exception:
        pass

    try:
        episodes = await db.execute(text(
            "SELECT COUNT(*) FROM cerebro_episodes"
        ))
        result["cortex_totals"]["episodes"] = int(episodes.scalar() or 0)
    except Exception:
        pass

    try:
        procedures = await db.execute(text(
            "SELECT COUNT(*) FROM cerebro_memory_nodes WHERE memory_type = 'procedural'"
        ))
        result["cortex_totals"]["procedures"] = int(procedures.scalar() or 0)
    except Exception:
        pass

    try:
        schemas = await db.execute(text(
            "SELECT COUNT(*) FROM cerebro_memory_nodes WHERE memory_type = 'schematic'"
        ))
        result["cortex_totals"]["schemas"] = int(schemas.scalar() or 0)
    except Exception:
        pass

    return result


@router.get("/economy/stats")
async def get_economy_stats(
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Aggregated ApexJoule Economy statistics for admin dashboard."""
    result = {
        "total_minted": 0,
        "total_spent": 0,
        "active_users": 0,
        "tx_count_24h": 0,
        "top_agents": [],
        "recent_transactions": [],
    }

    try:
        # Global totals
        totals = await db.execute(text("""
            SELECT
                COALESCE(SUM(total_earned), 0) AS minted,
                COALESCE(SUM(total_spent), 0) AS spent,
                COUNT(DISTINCT user_id) AS users
            FROM apex_joule_balances
        """))
        row = totals.fetchone()
        if row:
            result["total_minted"] = float(row[0])
            result["total_spent"] = float(row[1])
            result["active_users"] = int(row[2])
    except Exception:
        pass

    try:
        # 24h transaction count
        tx_count = await db.execute(text("""
            SELECT COUNT(*) FROM apex_joule_transactions
            WHERE created_at > NOW() - INTERVAL '24 hours'
        """))
        result["tx_count_24h"] = int(tx_count.scalar() or 0)
    except Exception:
        pass

    try:
        # Top agents by total earned
        agents = await db.execute(text("""
            SELECT
                b.entity_id,
                u.email,
                b.balance,
                b.total_earned,
                b.level,
                b.love_depth
            FROM apex_joule_balances b
            JOIN users u ON u.id = b.user_id
            WHERE b.entity_id IS NOT NULL
            ORDER BY b.total_earned DESC
            LIMIT 20
        """))
        for r in agents.fetchall():
            result["top_agents"].append({
                "agent_id": r[0],
                "user_email": r[1],
                "balance": float(r[2]),
                "total_earned": float(r[3]),
                "level": int(r[4]),
                "love_depth": float(r[5]),
            })
    except Exception:
        pass

    try:
        # Recent transactions
        txs = await db.execute(text("""
            SELECT
                t.to_entity,
                u.email,
                t.amount,
                t.tx_type,
                t.operation_type,
                t.created_at
            FROM apex_joule_transactions t
            JOIN users u ON u.id = t.user_id
            ORDER BY t.created_at DESC
            LIMIT 50
        """))
        for r in txs.fetchall():
            result["recent_transactions"].append({
                "agent": r[0],
                "user_email": r[1],
                "amount": float(r[2]),
                "tx_type": r[3],
                "operation_type": r[4],
                "created_at": r[5].isoformat() if r[5] else None,
            })
    except Exception:
        pass

    return result
