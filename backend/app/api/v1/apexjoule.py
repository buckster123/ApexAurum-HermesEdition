"""
ApexJoule Economy — REST API Endpoints

Balance queries, transaction log, economy stats.
Phase 1: read-only visibility. Phase 3 adds spending/tipping.
"""

import logging
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import get_current_user
from app.database import get_db
from app.models.user import User
from app.services.apexjoule.ledger import AJLedger
from app.services.apexjoule.love_scorer import love_depth_tier_name
from app.services.apexjoule.constants import (
    LEVEL_NAMES,
    AJ_SHOP_PRICES,
    QUEST_BOUNTIES,
    LEVEL_THRESHOLDS,
    LOVE_DEPTH_TIERS,
)

logger = logging.getLogger("api.apexjoule")

router = APIRouter(prefix="/aj", tags=["ApexJoule Economy"])


@router.get("/balance")
async def get_balance(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get user + all agent AJ balances."""
    ledger = AJLedger(db)
    balances = await ledger.get_all_balances(user.id)

    user_balance = None
    agents = {}

    for b in balances:
        entry = {
            "balance": float(b.balance),
            "total_earned": float(b.total_earned),
            "total_spent": float(b.total_spent),
            "level": b.level,
            "level_name": LEVEL_NAMES[min(b.level - 1, len(LEVEL_NAMES) - 1)],
            "love_depth": float(b.love_depth),
            "love_depth_tier": love_depth_tier_name(float(b.love_depth)),
            "vitality": float(b.vitality),
        }
        if b.entity_id:
            agents[b.entity_id] = entry
        else:
            user_balance = entry

    return {
        "user": user_balance or {"balance": 0, "total_earned": 0, "total_spent": 0, "level": 1, "level_name": "Initiate"},
        "agents": agents,
        "total_balance": sum(float(b.balance) for b in balances),
    }


@router.get("/transactions")
async def get_transactions(
    limit: int = Query(default=50, le=200),
    offset: int = Query(default=0, ge=0),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get recent AJ transactions."""
    ledger = AJLedger(db)
    txs = await ledger.get_transactions(user.id, limit=limit, offset=offset)

    return {
        "transactions": [
            {
                "id": str(tx.id),
                "from_entity": tx.from_entity,
                "to_entity": tx.to_entity,
                "amount": float(tx.amount),
                "tx_type": tx.tx_type,
                "reason": tx.reason,
                "operation_type": tx.operation_type,
                "provider": tx.provider,
                "model_used": tx.model_used,
                "e_cost": float(tx.e_cost) if tx.e_cost else None,
                "w_output": float(tx.w_output) if tx.w_output else None,
                "kappa": float(tx.kappa) if tx.kappa else None,
                "l_multiplier": float(tx.l_multiplier) if tx.l_multiplier else None,
                "c_score": float(tx.c_score) if tx.c_score else None,
                "d_score": float(tx.d_score) if tx.d_score else None,
                "created_at": tx.created_at.isoformat() if tx.created_at else None,
            }
            for tx in txs
        ],
        "limit": limit,
        "offset": offset,
    }


@router.get("/stats")
async def get_economy_stats(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get economy overview stats."""
    ledger = AJLedger(db)
    stats = await ledger.get_economy_stats(user.id)
    return stats


@router.get("/shop")
async def get_shop_rates(
    user: User = Depends(get_current_user),
):
    """Get available AJ shop purchases and rates."""
    return {
        "prices": AJ_SHOP_PRICES,
        "quest_bounties": QUEST_BOUNTIES,
        "level_thresholds": LEVEL_THRESHOLDS,
        "level_names": LEVEL_NAMES,
        "love_depth_tiers": LOVE_DEPTH_TIERS,
    }


@router.get("/leaderboard")
async def get_leaderboard(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get agent leaderboard by total earned."""
    ledger = AJLedger(db)
    balances = await ledger.get_all_balances(user.id)

    agents = []
    for b in balances:
        if b.entity_id:
            agents.append({
                "agent_id": b.entity_id,
                "balance": float(b.balance),
                "total_earned": float(b.total_earned),
                "level": b.level,
                "level_name": LEVEL_NAMES[min(b.level - 1, len(LEVEL_NAMES) - 1)],
                "love_depth": float(b.love_depth),
                "love_depth_tier": love_depth_tier_name(float(b.love_depth)),
            })

    agents.sort(key=lambda a: a["total_earned"], reverse=True)
    return {"agents": agents}
