"""
ApexJoule Calculator — The master formula.

AJ_earned = max(0, (W x kappa) - E_cost) x L

Maps to: pricing.py for E_cost, love_scorer.py for L,
constants.py for all tuning params.
"""

import logging
from dataclasses import dataclass
from typing import Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.services.pricing import calculate_cost
from app.services.apexjoule.constants import (
    AJ_PER_USD,
    TOKEN_VALUE_FACTOR,
    TASK_MULTIPLIERS,
    EXPECTED_COSTS,
    KAPPA_FLOOR,
    KAPPA_CEILING,
    DEFAULT_AGENT_SPLIT,
    DEFAULT_USER_SPLIT,
    BACKGROUND_AGENT_SPLIT,
    COUNCIL_AGENT_SPLIT,
    COUNCIL_USER_SPLIT,
)
from app.services.apexjoule.love_scorer import (
    compute_love_score,
    update_love_depth,
    love_depth_bonus,
    LoveScoreResult,
)
from app.services.apexjoule.ledger import AJLedger

logger = logging.getLogger("apexjoule.calculator")


@dataclass
class AJResult:
    """Result of an AJ computation."""
    total: float
    agent_share: float
    user_share: float
    e_cost: float
    w_output: float
    kappa: float
    l_multiplier: float
    love_score: LoveScoreResult
    love_depth_before: float
    love_depth_after: float


def compute_e_cost(
    provider: str,
    model: str,
    input_tokens: int,
    output_tokens: int,
    external_cost_usd: float = 0.0,
) -> float:
    """Return energy cost in AJ. Reuses pricing.py:calculate_cost()."""
    usd_cost = calculate_cost(provider, model, input_tokens, output_tokens)
    return (usd_cost + external_cost_usd) * AJ_PER_USD


def compute_w(
    output_tokens: int,
    operation_type: str,
    quality_signals: dict,
) -> float:
    """Compute work output value in AJ-equivalent units."""
    base = output_tokens * TOKEN_VALUE_FACTOR
    task_mult = TASK_MULTIPLIERS.get(operation_type, 1.0)

    quality = 1.0
    if quality_signals.get("memory_created"):
        quality *= 1.3
    if quality_signals.get("agora_posted"):
        quality *= 1.2
    if quality_signals.get("quest_milestone"):
        quality *= 1.5
    if quality_signals.get("convergence_improved"):
        quality *= 1.2

    return base * task_mult * quality


def compute_kappa(
    operation_type: str,
    actual_cost_usd: float,
    tool_turns: int = 0,
) -> float:
    """Efficiency coefficient: expected / actual cost ratio."""
    expected = EXPECTED_COSTS.get(operation_type, actual_cost_usd)

    if actual_cost_usd <= 0:
        return 1.0

    raw_kappa = expected / actual_cost_usd

    if tool_turns > 5:
        raw_kappa *= 0.85

    if expected > 0 and actual_cost_usd < expected * 0.5:
        raw_kappa *= 1.2

    return max(KAPPA_FLOOR, min(KAPPA_CEILING, raw_kappa))


def compute_aj(
    e_cost: float,
    w_output: float,
    kappa: float,
    l_multiplier: float,
    love_depth_bonus_mult: float = 1.0,
) -> float:
    """The master formula: AJ = max(0, (W * kappa) - E_cost) * L * bonus."""
    raw = max(0.0, (w_output * kappa) - e_cost)
    return raw * l_multiplier * love_depth_bonus_mult


async def compute_aj_for_chat(
    *,
    user_id: UUID,
    agent_id: str,
    provider: str,
    model: str,
    input_tokens: int,
    output_tokens: int,
    tool_turns: int = 0,
    memory_created: bool = False,
    conversation_id: Optional[UUID] = None,
    message_id: Optional[UUID] = None,
    context_limit: Optional[int] = None,
    has_error: bool = False,
    db: AsyncSession,
) -> Optional[AJResult]:
    """Compute and credit AJ for a chat interaction."""
    # Determine operation type
    if tool_turns > 3:
        op_type = "chat_heavy"
    elif tool_turns > 0:
        op_type = "chat_tools"
    else:
        op_type = "chat"

    actual_cost_usd = calculate_cost(provider, model, input_tokens, output_tokens)

    # Core formula components
    e = compute_e_cost(provider, model, input_tokens, output_tokens)
    w = compute_w(output_tokens, op_type, {"memory_created": memory_created})
    k = compute_kappa(op_type, actual_cost_usd, tool_turns)

    # Love scoring
    love = compute_love_score(
        operation_type=op_type,
        success=not has_error,
        memory_created=memory_created,
        tool_turns=tool_turns,
        actual_cost_usd=actual_cost_usd,
        output_tokens=output_tokens,
        input_tokens=input_tokens,
        context_limit=context_limit,
        has_error=has_error,
    )

    # Get current love depth
    ledger = AJLedger(db)
    agent_bal = await ledger.get_or_create_balance(user_id, agent_id)
    depth_before = float(agent_bal.love_depth)
    depth_after = update_love_depth(depth_before, love.c, love.d)
    depth_bonus = love_depth_bonus(depth_before)

    # Master formula
    total = compute_aj(e, w, k, love.l_multiplier, depth_bonus)

    if total <= 0:
        # Still update love depth even on zero earn
        await ledger.update_love_depth(user_id, agent_id, depth_after)
        await ledger.log_love_score(
            user_id, agent_id, love.c, love.d,
            interaction_type=op_type,
            c_breakdown=love.c_breakdown,
            d_breakdown=love.d_breakdown,
            love_depth_before=depth_before,
            love_depth_after=depth_after,
        )
        return AJResult(
            total=0, agent_share=0, user_share=0,
            e_cost=e, w_output=w, kappa=k, l_multiplier=love.l_multiplier,
            love_score=love, love_depth_before=depth_before,
            love_depth_after=depth_after,
        )

    agent_share = total * DEFAULT_AGENT_SPLIT
    user_share = total * DEFAULT_USER_SPLIT

    # Credit and log
    tx = await ledger.credit(
        user_id, agent_id, agent_share, user_share,
        operation_type=op_type,
        reason=f"chat:{op_type}",
        e_cost=e, w_output=w, kappa=k,
        l_multiplier=love.l_multiplier,
        c_score=love.c, d_score=love.d,
        conversation_id=conversation_id,
        message_id=message_id,
        provider=provider, model_used=model,
    )

    # Update love depth
    await ledger.update_love_depth(user_id, agent_id, depth_after)
    await ledger.log_love_score(
        user_id, agent_id, love.c, love.d,
        interaction_type=op_type,
        c_breakdown=love.c_breakdown,
        d_breakdown=love.d_breakdown,
        love_depth_before=depth_before,
        love_depth_after=depth_after,
    )

    return AJResult(
        total=total, agent_share=agent_share, user_share=user_share,
        e_cost=e, w_output=w, kappa=k, l_multiplier=love.l_multiplier,
        love_score=love, love_depth_before=depth_before,
        love_depth_after=depth_after,
    )


async def compute_aj_for_council_round(
    *,
    user_id: UUID,
    agent_id: str,
    provider: str,
    model: str,
    input_tokens: int,
    output_tokens: int,
    convergence_score: float = 0.0,
    round_number: int = 1,
    session_complete: bool = False,
    agora_posted: bool = False,
    db: AsyncSession,
) -> Optional[AJResult]:
    """Compute and credit AJ for a council round contribution."""
    op_type = "council_synthesis" if session_complete else "council_round"
    actual_cost_usd = calculate_cost(provider, model, input_tokens, output_tokens)

    e = compute_e_cost(provider, model, input_tokens, output_tokens)
    w = compute_w(
        output_tokens, op_type,
        {"convergence_improved": convergence_score > 0.5, "agora_posted": agora_posted},
    )
    k = compute_kappa(op_type, actual_cost_usd)

    love = compute_love_score(
        operation_type=op_type,
        success=True,
        convergence_improved=convergence_score > 0.5,
        agora_posted=agora_posted,
        actual_cost_usd=actual_cost_usd,
        output_tokens=output_tokens,
        input_tokens=input_tokens,
    )

    ledger = AJLedger(db)
    agent_bal = await ledger.get_or_create_balance(user_id, agent_id)
    depth_before = float(agent_bal.love_depth)
    depth_after = update_love_depth(depth_before, love.c, love.d)
    depth_bonus = love_depth_bonus(depth_before)

    total = compute_aj(e, w, k, love.l_multiplier, depth_bonus)

    if total <= 0:
        await ledger.update_love_depth(user_id, agent_id, depth_after)
        await ledger.log_love_score(
            user_id, agent_id, love.c, love.d,
            interaction_type=op_type,
            c_breakdown=love.c_breakdown,
            d_breakdown=love.d_breakdown,
            love_depth_before=depth_before,
            love_depth_after=depth_after,
        )
        return AJResult(
            total=0, agent_share=0, user_share=0,
            e_cost=e, w_output=w, kappa=k, l_multiplier=love.l_multiplier,
            love_score=love, love_depth_before=depth_before,
            love_depth_after=depth_after,
        )

    agent_share = total * COUNCIL_AGENT_SPLIT
    user_share = total * COUNCIL_USER_SPLIT

    await ledger.credit(
        user_id, agent_id, agent_share, user_share,
        operation_type=op_type,
        reason=f"council:round_{round_number}",
        e_cost=e, w_output=w, kappa=k,
        l_multiplier=love.l_multiplier,
        c_score=love.c, d_score=love.d,
        provider=provider, model_used=model,
    )

    await ledger.update_love_depth(user_id, agent_id, depth_after)
    await ledger.log_love_score(
        user_id, agent_id, love.c, love.d,
        interaction_type=op_type,
        c_breakdown=love.c_breakdown,
        d_breakdown=love.d_breakdown,
        love_depth_before=depth_before,
        love_depth_after=depth_after,
    )

    return AJResult(
        total=total, agent_share=agent_share, user_share=user_share,
        e_cost=e, w_output=w, kappa=k, l_multiplier=love.l_multiplier,
        love_score=love, love_depth_before=depth_before,
        love_depth_after=depth_after,
    )


async def compute_aj_for_dream(
    *,
    user_id: str,
    agent_id: str = "AZOTH",
    provider: str = "anthropic",
    model: str = "claude-haiku-4-5-20251001",
    input_tokens: int = 0,
    output_tokens: int = 0,
    episodes_consolidated: int = 0,
    success: bool = True,
    db: AsyncSession,
) -> Optional[AJResult]:
    """Compute and credit AJ for a dream cycle. 100% to agent."""
    from uuid import UUID as UUIDType
    uid = UUIDType(user_id) if isinstance(user_id, str) else user_id

    op_type = "dream_consolidation"
    actual_cost_usd = calculate_cost(provider, model, input_tokens, output_tokens)

    e = compute_e_cost(provider, model, input_tokens, output_tokens)
    w = compute_w(
        output_tokens, op_type,
        {"memory_created": episodes_consolidated > 0},
    )
    k = compute_kappa(op_type, actual_cost_usd)

    love = compute_love_score(
        operation_type=op_type,
        success=success,
        memory_created=episodes_consolidated > 0,
        actual_cost_usd=actual_cost_usd,
        output_tokens=output_tokens,
        input_tokens=input_tokens,
    )

    ledger = AJLedger(db)
    agent_bal = await ledger.get_or_create_balance(uid, agent_id)
    depth_before = float(agent_bal.love_depth)
    depth_after = update_love_depth(depth_before, love.c, love.d)
    depth_bonus = love_depth_bonus(depth_before)

    total = compute_aj(e, w, k, love.l_multiplier, depth_bonus)

    if total <= 0:
        await ledger.update_love_depth(uid, agent_id, depth_after)
        await ledger.log_love_score(
            uid, agent_id, love.c, love.d,
            interaction_type=op_type,
            c_breakdown=love.c_breakdown,
            d_breakdown=love.d_breakdown,
            love_depth_before=depth_before,
            love_depth_after=depth_after,
        )
        return AJResult(
            total=0, agent_share=0, user_share=0,
            e_cost=e, w_output=w, kappa=k, l_multiplier=love.l_multiplier,
            love_score=love, love_depth_before=depth_before,
            love_depth_after=depth_after,
        )

    # Dreams: 100% to agent (background work)
    agent_share = total * BACKGROUND_AGENT_SPLIT
    user_share = 0.0

    await ledger.credit(
        uid, agent_id, agent_share, user_share,
        operation_type=op_type,
        reason="dream:consolidation",
        e_cost=e, w_output=w, kappa=k,
        l_multiplier=love.l_multiplier,
        c_score=love.c, d_score=love.d,
        provider=provider, model_used=model,
    )

    await ledger.update_love_depth(uid, agent_id, depth_after)
    await ledger.log_love_score(
        uid, agent_id, love.c, love.d,
        interaction_type=op_type,
        c_breakdown=love.c_breakdown,
        d_breakdown=love.d_breakdown,
        love_depth_before=depth_before,
        love_depth_after=depth_after,
    )

    return AJResult(
        total=total, agent_share=agent_share, user_share=user_share,
        e_cost=e, w_output=w, kappa=k, l_multiplier=love.l_multiplier,
        love_score=love, love_depth_before=depth_before,
        love_depth_after=depth_after,
    )
