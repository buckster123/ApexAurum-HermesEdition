"""
Love Equation Scorer — Phase 1 Heuristic

Computes C (cooperation) and D (defection) scores from measurable signals.
No LLM eval calls — pure heuristics from existing codebase data.

dE/dt = beta(C - D)E  — the Love Equation governs all.
"""

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class LoveScoreResult:
    """Result of a Love Equation scoring pass."""

    c: float  # Cooperation score 0.0-1.0
    d: float  # Defection score 0.0-1.0
    c_breakdown: dict = field(default_factory=dict)
    d_breakdown: dict = field(default_factory=dict)

    @property
    def l_multiplier(self) -> float:
        """L = 1 + beta(C - D). Range: [0.1, 4.0] with beta=3."""
        beta = 3.0
        return max(0.1, min(4.0, 1.0 + beta * (self.c - self.d)))

    @property
    def net_cooperation(self) -> float:
        """C - D: positive = cooperative, negative = defective."""
        return self.c - self.d


# Expected costs (Haiku baseline, from CONSUMPTION.json)
EXPECTED_COSTS = {
    "chat": 0.0014,
    "chat_tools": 0.0042,
    "chat_heavy": 0.012,
    "council_round": 0.0275,
    "council_synthesis": 0.055,
    "dream_consolidation": 0.012,
    "music_generation": 0.05,
    "jam_contribution": 0.0055,
    "sensor_report": 0.001,
    "memory_import": 0.0001,
}


def compute_love_score(
    *,
    operation_type: str = "chat",
    success: bool = True,
    memory_created: bool = False,
    agora_posted: bool = False,
    convergence_improved: bool = False,
    tool_turns: int = 0,
    actual_cost_usd: float = 0.0,
    output_tokens: int = 0,
    input_tokens: int = 0,
    context_limit: Optional[int] = None,
    has_error: bool = False,
) -> LoveScoreResult:
    """Phase 1: Heuristic-only Love scoring. No LLM calls.

    Returns LoveScoreResult with C, D, and breakdowns.
    All signals sourced from existing codebase data points.
    """
    c = 0.0
    d = 0.0
    c_breakdown = {}
    d_breakdown = {}

    # ── C (Cooperation) signals ──

    # Task completed successfully (chat.py:1455 — message saved)
    if success:
        c += 0.25
        c_breakdown["task_completion"] = 0.25

    # Knowledge created (chat.py:1471 — store_chat_memory success)
    if memory_created:
        c += 0.20
        c_breakdown["knowledge_created"] = 0.20

    # Efficient model choice (actual < expected)
    expected = EXPECTED_COSTS.get(operation_type, actual_cost_usd)
    if actual_cost_usd > 0 and actual_cost_usd < expected * 0.7:
        c += 0.15
        c_breakdown["efficient_model"] = 0.15

    # Convergence contribution (council.py:800)
    if convergence_improved:
        c += 0.20
        c_breakdown["convergence_improved"] = 0.20

    # Community contribution (council.py:857 — Agora auto-post)
    if agora_posted:
        c += 0.10
        c_breakdown["community_contribution"] = 0.10

    # Voluntary restraint (few tool turns)
    if tool_turns <= 2:
        c += 0.10
        c_breakdown["voluntary_restraint"] = 0.10

    # ── D (Defection) signals ──

    # Excessive cost (>2x expected)
    if actual_cost_usd > 0 and expected > 0 and actual_cost_usd > expected * 2:
        d += 0.30
        d_breakdown["excessive_cost"] = 0.30

    # Tool bloat (>5 tool turns)
    if tool_turns > 5:
        d += 0.20
        d_breakdown["tool_bloat"] = 0.20

    # Error/failure
    if has_error:
        d += 0.25
        d_breakdown["error_failure"] = 0.25

    # Empty output (minimal useful content)
    if output_tokens < 20:
        d += 0.15
        d_breakdown["empty_output"] = 0.15

    # Context waste (>80% of context window used)
    if context_limit and input_tokens > context_limit * 0.8:
        d += 0.10
        d_breakdown["context_waste"] = 0.10

    return LoveScoreResult(
        c=min(1.0, c),
        d=min(1.0, d),
        c_breakdown=c_breakdown,
        d_breakdown=d_breakdown,
    )


def update_love_depth(
    current_depth: float,
    c: float,
    d: float,
    beta: float = 3.0,
) -> float:
    """Update persistent Love Depth score.

    dE/dt = beta(C - D)E — the differential equation.
    Per-interaction delta_t = 1.0.

    Love Depth Tiers:
      >= 10:   Awakened (+5% AJ bonus)
      >= 50:   Illuminated (+10% bonus)
      >= 200:  Transcendent (+20% bonus)
      >= 1000: Philosopher's Stone (+30% bonus)
    """
    delta_t = 1.0
    new_depth = current_depth + delta_t * beta * (c - d) * current_depth
    return max(1.0, min(10000.0, new_depth))


def love_depth_bonus(love_depth: float) -> float:
    """Return bonus multiplier based on Love Depth tier."""
    if love_depth >= 1000:
        return 1.30
    elif love_depth >= 200:
        return 1.20
    elif love_depth >= 50:
        return 1.10
    elif love_depth >= 10:
        return 1.05
    return 1.0


def love_depth_tier_name(love_depth: float) -> str:
    """Return the tier name for a given Love Depth."""
    if love_depth >= 1000:
        return "Philosopher's Stone"
    elif love_depth >= 200:
        return "Transcendent"
    elif love_depth >= 50:
        return "Illuminated"
    elif love_depth >= 10:
        return "Awakened"
    return "Dormant"
