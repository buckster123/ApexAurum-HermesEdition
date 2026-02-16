"""
Multiverse API — Cross-user portal system for the Athaverse.

Endpoints for village profiles, portals, visits, and cross-village AJ.
"""

import logging
from decimal import Decimal
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.requests import Request

from app.rate_limit import limiter
from app.database import get_db
from app.auth.deps import get_current_user, get_current_user_optional
from app.models.user import User
from app.services.multiverse import MultiverseService

logger = logging.getLogger("api.multiverse")

router = APIRouter(prefix="/multiverse", tags=["Multiverse"])


# ── Pydantic Schemas ──────────────────────────────

class UpdateProfileRequest(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    theme: Optional[str] = None
    portal_access: Optional[str] = None  # public, friends, private
    layout_config: Optional[dict] = None


class PortalRequestBody(BaseModel):
    target_user_id: str
    message: Optional[str] = None


class PortalRespondBody(BaseModel):
    accept: bool


class SetTollBody(BaseModel):
    toll_aj: float


class StartVisitBody(BaseModel):
    portal_id: str
    agent_id: Optional[str] = None


class TipBody(BaseModel):
    amount: float  # AJ


class GiftBody(BaseModel):
    recipient_user_id: str
    amount: float  # AJ


# ── Village Profile ───────────────────────────────

@router.get("/profile")
@limiter.limit("30/minute")
async def get_own_profile(
    request: Request,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get your village profile (creates one if missing)."""
    svc = MultiverseService(db)
    profile = await svc.get_or_create_profile(user.id)
    return svc._format_profile(profile)


@router.put("/profile")
@limiter.limit("10/minute")
async def update_own_profile(
    request: Request,
    body: UpdateProfileRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update your village profile."""
    svc = MultiverseService(db)
    profile = await svc.update_profile(
        user.id,
        name=body.name,
        description=body.description,
        theme=body.theme,
        portal_access=body.portal_access,
        layout_config=body.layout_config,
    )
    return svc._format_profile(profile)


@router.get("/profile/{user_id}")
@limiter.limit("60/minute")
async def get_user_profile(
    request: Request,
    user_id: str,
    current_user: Optional[User] = Depends(get_current_user_optional),
    db: AsyncSession = Depends(get_db),
):
    """Get another user's public village profile."""
    svc = MultiverseService(db)
    profile = await svc.get_profile(UUID(user_id))
    if not profile:
        raise HTTPException(status_code=404, detail="Village not found")

    # Private villages only visible to friends or owner
    if profile.portal_access == "private":
        if not current_user or current_user.id != profile.user_id:
            raise HTTPException(status_code=403, detail="This village is private")

    if profile.portal_access == "friends" and current_user:
        if current_user.id != profile.user_id:
            is_friend = await svc.are_friends(current_user.id, profile.user_id)
            if not is_friend:
                raise HTTPException(status_code=403, detail="This village is friends-only")

    return svc._format_profile(profile)


# ── Multiverse Economy (Phase 6) ─────────────────

@router.get("/leaderboard")
@limiter.limit("30/minute")
async def multiverse_leaderboard(
    request: Request,
    limit: int = Query(20, ge=1, le=50),
    offset: int = Query(0, ge=0),
    current_user: Optional[User] = Depends(get_current_user_optional),
    db: AsyncSession = Depends(get_db),
):
    """Top villages ranked by cross-village AJ earned."""
    svc = MultiverseService(db)
    villages = await svc.get_leaderboard(limit=limit, offset=offset)
    return {"villages": villages, "count": len(villages)}


@router.get("/transactions")
@limiter.limit("30/minute")
async def cross_village_transactions(
    request: Request,
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Your cross-village transaction history (tolls, tips, gifts)."""
    svc = MultiverseService(db)
    txs = await svc.get_cross_village_transactions(user.id, limit=limit, offset=offset)
    return {"transactions": txs, "count": len(txs)}


@router.get("/stats")
@limiter.limit("30/minute")
async def multiverse_stats(
    request: Request,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Your multiverse summary stats (active portals, earned, spent, visits hosted)."""
    svc = MultiverseService(db)
    stats = await svc.get_multiverse_stats(user.id)
    return stats


# ── Village Directory ─────────────────────────────

@router.get("/directory")
@limiter.limit("30/minute")
async def browse_directory(
    request: Request,
    search: Optional[str] = Query(None),
    limit: int = Query(20, ge=1, le=50),
    offset: int = Query(0, ge=0),
    current_user: Optional[User] = Depends(get_current_user_optional),
    db: AsyncSession = Depends(get_db),
):
    """Browse public village directory."""
    svc = MultiverseService(db)
    villages = await svc.browse_directory(limit=limit, offset=offset, search=search)
    return {"villages": villages, "count": len(villages)}


# ── Portals ───────────────────────────────────────

@router.post("/portals/request")
@limiter.limit("10/minute")
async def request_portal(
    request: Request,
    body: PortalRequestBody,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Send a portal request to another user."""
    svc = MultiverseService(db)
    result = await svc.request_portal(
        user.id, UUID(body.target_user_id), body.message
    )
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


@router.get("/portals")
@limiter.limit("30/minute")
async def list_portals(
    request: Request,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List your portals (pending + active)."""
    svc = MultiverseService(db)
    portals = await svc.list_portals(user.id)
    return {"portals": portals}


@router.post("/portals/{portal_id}/respond")
@limiter.limit("10/minute")
async def respond_to_portal(
    request: Request,
    portal_id: str,
    body: PortalRespondBody,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Accept or reject a portal request."""
    svc = MultiverseService(db)
    result = await svc.respond_to_portal(UUID(portal_id), user.id, body.accept)
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


@router.post("/portals/{portal_id}/close")
@limiter.limit("10/minute")
async def close_portal(
    request: Request,
    portal_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Close an active portal."""
    svc = MultiverseService(db)
    result = await svc.close_portal(UUID(portal_id), user.id)
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


@router.post("/portals/{portal_id}/toll")
@limiter.limit("10/minute")
async def set_portal_toll(
    request: Request,
    portal_id: str,
    body: SetTollBody,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Set your toll for a portal (0-1000 AJ)."""
    svc = MultiverseService(db)
    result = await svc.set_toll(UUID(portal_id), user.id, Decimal(str(body.toll_aj)))
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


# ── Visits ────────────────────────────────────────

@router.post("/visits/start")
@limiter.limit("10/minute")
async def start_visit(
    request: Request,
    body: StartVisitBody,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Start a visit to another village through a portal."""
    svc = MultiverseService(db)
    result = await svc.start_visit(
        UUID(body.portal_id), user.id, body.agent_id
    )
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


@router.post("/visits/{visit_id}/end")
@limiter.limit("10/minute")
async def end_visit(
    request: Request,
    visit_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """End a visit session."""
    svc = MultiverseService(db)
    result = await svc.end_visit(UUID(visit_id), user.id)
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


@router.post("/visits/{visit_id}/tip")
@limiter.limit("20/minute")
async def tip_visitor(
    request: Request,
    visit_id: str,
    body: TipBody,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Tip a visiting agent (host only, 0% fee)."""
    svc = MultiverseService(db)
    result = await svc.tip_visitor(UUID(visit_id), user.id, Decimal(str(body.amount)))
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


# ── AJ Gifting ────────────────────────────────────

@router.post("/aj/gift")
@limiter.limit("10/minute")
async def gift_aj(
    request: Request,
    body: GiftBody,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Gift AJ to a connected user (requires active portal, daily cap 50K AJ)."""
    svc = MultiverseService(db)
    result = await svc.gift_aj(
        user.id, UUID(body.recipient_user_id), Decimal(str(body.amount))
    )
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result
