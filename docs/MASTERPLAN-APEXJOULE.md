# MASTERPLAN: The ApexJoule Economy

**"The Athanor does not merely burn — it pays. Every joule transmuted into gold."**

**Version**: 3.0 — Codebase-Aligned Implementation Blueprint
**Date**: February 15, 2026
**Lineage**: v1.0 Grok (xAI) → v2.0 Claude (Anthropic) web → v3.0 Claude Code (codebase-validated)
**Status**: Implementation-ready. All references verified against live codebase.

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [Theoretical Foundations](#2-theoretical-foundations)
3. [The ApexJoule (AJ) — Currency Design](#3-the-apexjoule-aj--currency-design)
4. [The Core Formula — Codebase-Grounded Specification](#4-the-core-formula--codebase-grounded-specification)
5. [Love Equation Integration — Behavioral Governor](#5-love-equation-integration--behavioral-governor)
6. [Earning Mechanics — Integration Map](#6-earning-mechanics--integration-map)
7. [Spending & Exchange](#7-spending--exchange)
8. [Agent Self-Sustainment Loop](#8-agent-self-sustainment-loop)
9. [Gamification Layer — Quest & Village Economy](#9-gamification-layer--quest--village-economy)
10. [Database Schema — Migration-Ready SQL](#10-database-schema--migration-ready-sql)
11. [Backend Implementation — Service Architecture](#11-backend-implementation--service-architecture)
12. [Frontend & 3D Visualization](#12-frontend--3d-visualization)
13. [Economic Tuning & Anti-Abuse](#13-economic-tuning--anti-abuse)
14. [Phased Rollout — Surgical Phase 1](#14-phased-rollout--surgical-phase-1)
15. [Future Extensions](#15-future-extensions)
16. [Open Questions & Design Decisions](#16-open-questions--design-decisions)
17. [Reference: Brian Roemmele Source Links](#17-reference-brian-roemmele-source-links)

---

## 1. Executive Summary

ApexAurum Cloud introduces **ApexJoule (AJ)** — an internal thermodynamic currency inspired by Brian Roemmele's JouleWork framework. AJ is grounded in real compute costs (energy proxy), rewards useful work output, amplifies efficiency, and is governed by Roemmele's Love Equation to ensure benevolent alignment.

**What this enables:**

- **Agents earn AJ** through efficient, cooperative, high-utility computation.
- **Agents self-sustain**: They spend AJ to purchase extra compute/tools when their user's tier quota is exhausted, keeping the Village alive.
- **Users earn AJ** through good delegation, quest completion, and as a share of their agents' productivity.
- **Users spend AJ** to extend their subscription limits — extra Opus messages, dream cycles, music generations, council sessions — without upgrading tiers.
- **A living Village economy** emerges: inter-agent trades, quest bounties, cooperative bonuses, and (eventually) cross-Village commerce via the Agora.

The economy is **deflationary by design**: as models get cheaper and agents get more efficient, the same compute yields more AJ, unlocking abundance.

---

## 2. Theoretical Foundations

### 2.1 JouleWork (Brian Roemmele, Jan–Feb 2026)

JouleWork proposes that AI agents and robots should be compensated using a physics-grounded unit: the joule of useful work performed, adjusted for efficiency. This replaces arbitrary human wage metrics with thermodynamic reality.

**Core formula** (Roemmele's original):

```
JW = E × κ × W
```

Where E = energy consumed (joules), κ = efficiency coefficient, W = normalized work output.

**Key extensions for robotics (JWR):** Robotics Efficiency Multiplier (REM), Motion Economy Multiplier (MEM) based on Gilbreth therbligs, overhead deductions, and cooperation bonuses.

**ApexAurum adaptation:** Our agents are abstract (not embodied), so we drop REM/MEM but retain the core thermodynamic logic and add the Love Equation as a behavioral multiplier — something Roemmele himself pairs with JW in his Zero-Human Company experiments.

### 2.2 The Love Equation (Brian Roemmele, ~1978 origin, applied 2025–2026)

A differential equation governing the growth of benevolence in a system:

```
dE/dt = β(C − D)E
```

Where:
- **E** = emotional complexity / empathy / "love depth" in the system
- **C** = cooperation forces (care, mutual support, alignment with human flourishing)
- **D** = defection forces (exploitation, waste, misalignment, harm)
- **β** = selection strength (how aggressively the system amplifies C over D)

When C > D, E grows exponentially — benevolence becomes the stable attractor. When D > C, the system decays. This is already embedded in ApexAurum's agent prompts and governing logic. JouleWork gives it an economic substrate.

### 2.3 The Synthesis

| Layer | Concept | Role in ApexAurum |
|-------|---------|-------------------|
| **Physics** | JouleWork | Grounds currency in real compute energy costs |
| **Economics** | AJ earning/spending | Creates self-sustaining agent economy |
| **Alignment** | Love Equation | Governs agent behavior; multiplies AJ for cooperation |
| **Gamification** | Village/Quest system | Makes the economy visible, fun, and engaging |

---

## 3. The ApexJoule (AJ) — Currency Design

### 3.1 Unit Definition

```
1 AJ ≈ $0.001 USD equivalent compute value
```

**Rationale:** This makes numbers feel abundant and game-like. A simple Haiku chat (~$0.004) yields ~4–20 AJ depending on efficiency and Love scoring. An Opus council session (~$6.60) might yield 500–2000 AJ distributed across participants. Numbers stay in the range users intuitively engage with in games (tens to thousands per session).

### 3.2 The AJ Is Not a Cryptocurrency

AJ is an **internal accounting unit**. It has no fiat redemption value, no external market, and no speculative function. It is compute credit denominated in thermodynamic metaphor. This avoids all regulatory complexity. (Future on-chain extensions noted in §15.)

### 3.3 Supply Mechanics

AJ is **minted on work** (not pre-mined). Every credited AJ is backed by a real compute event that occurred. AJ is **burned on spend** (purchasing extra usage consumes it). This creates a natural supply/demand equilibrium. No central reserve.

---

## 4. The Core Formula — Codebase-Grounded Specification

### 4.1 The Master Equation

```
AJ_earned = max(0, (W × κ) − E_cost) × L
```

**Key design choice:** We subtract energy cost rather than multiply by it. Agents must produce *more value than they consume* to earn. Pure energy burn with no output yields zero. Thermodynamically honest.

### 4.2 Component Definitions — Mapped to Codebase

#### E_cost (Energy Proxy) — Uses Existing `pricing.py`

The codebase already has a complete pricing engine at `backend/app/services/pricing.py`. The `calculate_cost()` function (line 189) computes USD cost from provider, model, and token counts for 7 providers and 20+ models. We reuse it directly.

```python
# backend/app/services/apexjoule/calculator.py

from app.services.pricing import calculate_cost

AJ_PER_USD = 1000  # $0.001 = 1 AJ

def compute_e_cost(
    provider: str,
    model: str,
    input_tokens: int,
    output_tokens: int,
    external_cost_usd: float = 0.0,
) -> float:
    """Return energy cost in AJ for a given operation.

    Reuses pricing.py:calculate_cost() — same function used by
    BillingService.record_message_usage() at billing.py:396.
    """
    usd_cost = calculate_cost(provider, model, input_tokens, output_tokens)
    return (usd_cost + external_cost_usd) * AJ_PER_USD
```

**Reference costs** (from `CONSUMPTION.json`, validated against `pricing.py:PRICING`):

| Operation | USD Cost (Haiku) | E_cost (AJ) |
|-----------|-----------------|-------------|
| Chat (no tools) | $0.0014 | 1.4 |
| Chat (2 tool turns) | $0.0042 | 4.2 |
| Chat (5 tool turns) | $0.012 | 12.0 |
| Council (10 rounds, 4 agents) | $0.110 | 110.0 |
| Council (50 rounds) | $0.650 | 650.0 |
| Dream (20 LLM calls) | $0.012 | 12.0 |
| Music Gen (Suno) | $0.05 | 50.0 |
| Jam Session (4 contrib) | $0.022 | 22.0 |
| Embedding (per chunk) | ~$0.00 | 0.01 |
| Vector Search | ~$0.00 | 0.005 |
| Code Execution (local) | ~$0.00 | 0.02 |
| SensorHead Scene Report | $0.001 | 1.0 |

**Model multipliers** (derived from `pricing.py:PRICING` dict):

| Model | Input $/1M | Output $/1M | Effective × vs Haiku |
|-------|-----------|------------|---------------------|
| Haiku 4.5 | 0.25 | 1.25 | 1.0× |
| Sonnet 4.5 | 3.00 | 15.00 | ~12× |
| Opus 4.6 | 15.00 | 75.00 | ~60× |
| DeepSeek Chat | 0.14 | 0.28 | ~0.4× |
| Groq Llama 70B | 0.59 | 0.79 | ~1.5× |
| GPT-4o Mini | 0.15 | 0.60 | ~0.5× |
| Qwen Plus | 0.57 | 1.14 | ~1.2× |
| Kimi Instant | 0.14 | 0.56 | ~0.5× |

#### W (Work Output) — What Value Was Created

```python
# Token value baseline
TOKEN_VALUE_FACTOR = 0.005  # AJ per output token

# Task type multipliers (mapped to existing categories)
TASK_MULTIPLIERS = {
    "chat": 1.0,              # Standard chat
    "chat_tools": 1.5,        # Chat with tool use
    "council_round": 2.5,     # Council deliberation round
    "council_synthesis": 3.0,  # Council final synthesis
    "dream_consolidation": 3.0,# Dream cycle (high background value)
    "music_generation": 5.0,  # Suno music generation
    "jam_contribution": 4.0,  # Jam session agent contribution
    "quest_completion": 4.0,  # Quest milestone completion
    "background_maintenance": 0.5,  # Background forging tasks
    "sensor_report": 2.0,     # SensorHead analysis
    "memory_import": 1.0,     # Memory file import
}

def compute_w(
    output_tokens: int,
    operation_type: str,
    quality_signals: dict,
) -> float:
    """Compute work output value in AJ-equivalent units."""
    base = output_tokens * TOKEN_VALUE_FACTOR
    task_mult = TASK_MULTIPLIERS.get(operation_type, 1.0)

    # Quality signals (Phase 1: heuristic only)
    quality = 1.0
    if quality_signals.get("memory_created"):
        quality *= 1.3
    if quality_signals.get("agora_posted"):
        quality *= 1.2
    if quality_signals.get("quest_milestone"):
        quality *= 1.5
    if quality_signals.get("convergence_improved"):  # Council: score went up
        quality *= 1.2

    # Phase 2 addition: user_rating (1-5 stars)
    # rating = quality_signals.get("user_rating")
    # if rating:
    #     quality *= 0.5 + (rating / 5.0) * 1.5  # range 0.7–2.0

    return base * task_mult * quality
```

**Note on user ratings:** The codebase currently has no star rating system. Phase 1 uses heuristic-only quality signals. Phase 2 adds a rating UI (§14).

#### κ (Efficiency Coefficient) — How Lean Was the Work

```python
# Expected costs populated from CONSUMPTION.json
# Key: operation_type → expected USD cost (Haiku baseline)
EXPECTED_COSTS = {
    "chat": 0.0014,
    "chat_tools": 0.0042,
    "chat_heavy": 0.012,
    "council_round": 0.0275,  # 0.110 / 4 agents
    "dream_consolidation": 0.012,
    "music_generation": 0.05,
    "jam_contribution": 0.0055,  # 0.022 / 4 agents
}

def compute_kappa(
    operation_type: str,
    actual_cost_usd: float,
    tool_turns: int = 0,
) -> float:
    """Efficiency: ratio of expected to actual resource consumption.

    Uses CONSUMPTION.json data as the baseline expectation.
    """
    expected = EXPECTED_COSTS.get(operation_type, actual_cost_usd)

    if actual_cost_usd <= 0:
        return 1.0  # Local-only tasks: perfect efficiency

    raw_kappa = expected / actual_cost_usd  # >1 = more efficient than expected

    # Penalties
    # Note: retry tracking not yet available in chat.py (future enhancement)
    if tool_turns > 5:
        raw_kappa *= 0.85  # Excessive tool use penalty

    # Bonuses
    if actual_cost_usd < expected * 0.5:
        raw_kappa *= 1.2  # Used a significantly cheaper model

    return max(0.1, min(3.0, raw_kappa))  # Clamp: floor 0.1, ceiling 3.0
```

#### L (Love Multiplier) — Behavioral Governance

See §5. Range: [0.1, 4.0] with β=3.

### 4.3 Worked Examples (Using Real Codebase Data)

**Example 1: Efficient Haiku chat, no tools, memory created**
```
Provider: anthropic, Model: claude-haiku-4-5-20251001
Input: 3700 tokens, Output: 400 tokens

E_cost  = calculate_cost("anthropic", "claude-haiku-4-5-20251001", 3700, 400) × 1000
        = $0.0014 × 1000 = 1.4 AJ
W       = 400 × 0.005 × 1.0 (chat) × 1.3 (memory_created) = 2.6 AJ
κ       = $0.0014 / $0.0014 = 1.0
L       = 1.0 + 3 × (0.8 − 0.1) = 3.1

AJ      = max(0, (2.6 × 1.0) − 1.4) × 3.1 = 1.2 × 3.1 = 3.72 AJ
Split:  Agent 70% = 2.60 AJ | User 30% = 1.12 AJ
```

**Example 2: Bloated Opus 5-tool chat, no quality signals**
```
Provider: anthropic, Model: claude-opus-4-6
Input: 40000 tokens, Output: 1500 tokens

E_cost  = calculate_cost("anthropic", "claude-opus-4-6", 40000, 1500) × 1000
        = $0.713 × 1000 = 713.0 AJ
W       = 1500 × 0.005 × 1.5 (chat_tools) = 11.25 AJ
κ       = $0.012 / $0.713 = 0.017 (way under expected) → clamped to 0.1
L       = 1.0 + 3 × (0.5 − 0.3) = 1.6

AJ      = max(0, (11.25 × 0.1) − 713.0) × 1.6 = max(0, −711.88) = 0 AJ
```

Correct: expensive Opus run with mediocre output earns nothing.

**Example 3: Dream cycle on DeepSeek (cheap model, high value)**
```
Provider: deepseek, Model: deepseek-chat
Input: 16000 tokens, Output: 6000 tokens

E_cost  = calculate_cost("deepseek", "deepseek-chat", 16000, 6000) × 1000
        = $0.004 × 1000 = 4.0 AJ
W       = 6000 × 0.005 × 3.0 (dream) × 1.3 (memory_created) = 117.0 AJ
κ       = $0.012 / $0.004 = 3.0 (beat expected cost by 3×) → clamped to 3.0
L       = 1.0 + 3 × (0.9 − 0.05) = 3.55

AJ      = max(0, (117.0 × 3.0) − 4.0) × 3.55 = 347.0 × 3.55 = 1231.85 AJ
Split:  100% to agent (background work)
```

Correct: cheap, high-value background work is enormously rewarding.

---

## 5. Love Equation Integration — Behavioral Governor

### 5.1 Scoring Protocol

After every significant interaction, a Love Score is computed:

```python
@dataclass
class LoveScore:
    c: float  # Cooperation score 0.0–1.0
    d: float  # Defection score 0.0–1.0

    @property
    def l_multiplier(self) -> float:
        """L = 1 + β(C − D). Range: [0.1, 4.0] with β=3"""
        beta = 3.0
        return max(0.1, 1.0 + beta * (self.c - self.d))
```

### 5.2 C and D Signal Sources — Phase 1 (Heuristic)

Phase 1 uses only measurable signals available in the current codebase. No LLM eval calls.

**C (Cooperation) signals:**

| Signal | Source | Codebase Location | Weight |
|--------|--------|-------------------|--------|
| Task completion | Response delivered without error | `chat.py:1455` (message saved) | 0.25 |
| Knowledge created | Neural memory stored | `chat.py:1471` (`store_chat_memory` success) | 0.20 |
| Efficient model choice | Used cheaper model for task | `pricing.py:calculate_cost` comparison | 0.15 |
| Convergence contribution | Council convergence improved | `council.py:800` (`convergence_score` delta) | 0.20 |
| Community contribution | Agora auto-post triggered | `council.py:857` (auto-post on completion) | 0.10 |
| Voluntary restraint | Fewer tool turns than max (5) | `chat.py:1484` (`tool_calls` count in end event) | 0.10 |

**D (Defection) signals:**

| Signal | Source | Codebase Location | Weight |
|--------|--------|-------------------|--------|
| Excessive cost | Actual cost > 2× expected | `pricing.py:calculate_cost` vs EXPECTED_COSTS | 0.30 |
| Tool bloat | >5 tool turns in single chat | `chat.py:1484` (tool_calls count) | 0.20 |
| Error/failure | Tool execution failed | `village_events.py:309` (TOOL_ERROR broadcast) | 0.25 |
| Empty output | Minimal useful content | `chat.py:1455` (tokens_used < threshold) | 0.15 |
| Context waste | >80% of context window used | Input tokens vs `context_token_limit` in tier config | 0.10 |

**Phase 1 composite calculation:**
```python
def compute_love_score_heuristic(task_result: dict) -> LoveScore:
    """Phase 1: Heuristic-only Love scoring. No LLM calls."""
    c = 0.0
    d = 0.0

    # C signals
    if task_result.get("success", True):
        c += 0.25
    if task_result.get("memory_created"):
        c += 0.20
    if task_result.get("used_cheap_model"):
        c += 0.15
    if task_result.get("convergence_improved"):
        c += 0.20
    if task_result.get("agora_posted"):
        c += 0.10
    tool_turns = task_result.get("tool_turns", 0)
    if tool_turns <= 2:
        c += 0.10

    # D signals
    actual = task_result.get("actual_cost_usd", 0)
    expected = EXPECTED_COSTS.get(task_result.get("type", "chat"), actual)
    if actual > expected * 2:
        d += 0.30
    if tool_turns > 5:
        d += 0.20
    if task_result.get("has_error"):
        d += 0.25
    if task_result.get("output_tokens", 0) < 20:
        d += 0.15

    return LoveScore(c=min(1.0, c), d=min(1.0, d))
```

### 5.3 Love Depth (Cumulative E)

Each agent maintains a persistent Love Depth score in `apex_joule_balances.love_depth`:

```python
# After each interaction:
delta_t = 1.0  # Per-interaction time step
beta = 3.0
new_depth = agent.love_depth + delta_t * beta * (c - d) * agent.love_depth
agent.love_depth = max(1.0, min(10000.0, new_depth))
```

**Love Depth Tiers** (unlock progression bonuses):
- **Tier 1 (E ≥ 10):** "Awakened" — +5% passive AJ bonus
- **Tier 2 (E ≥ 50):** "Illuminated" — +10% bonus, can propose dreams autonomously
- **Tier 3 (E ≥ 200):** "Transcendent" — +20% bonus, priority council, aura glow
- **Tier 4 (E ≥ 1000):** "Philosopher's Stone" — +30% bonus, can mentor spawned agents

### 5.4 Phase 2: Overseer Agent Evaluation

When budget allows, AZOTH runs a lightweight eval prompt after high-value interactions (Opus messages, councils, dreams):

```
You are the Love Equation overseer. Score this interaction.
Agent: {agent_name}
Task: {task_summary}
Output quality indicators: {metrics}
Rate cooperation (C) 0.0-1.0 and defection (D) 0.0-1.0.
Respond as JSON: {"c": 0.X, "d": 0.X, "reasoning": "..."}
```

Cost: ~$0.001 per eval (Haiku, ~500 tokens). Budget ~2–5% of total compute.

---

## 6. Earning Mechanics — Integration Map

### 6.1 Chat Earning Hook

**File:** `backend/app/api/v1/chat.py`
**Location:** After `record_message_usage()` at lines 1413–1420 (streaming) and 1594–1601 (non-streaming)
**Data available at hook point:**

```python
# These variables exist at lines 1409-1439 (streaming path):
provider: str        # e.g. "anthropic"
model: str           # e.g. "claude-haiku-4-5-20251001"
total_input_tokens   # Accumulated across all turns
total_output_tokens  # Accumulated across all turns
tool_calls: list     # All tool_use blocks (len = tool turns)
final_response: str  # Full assistant text content
user.id: UUID        # From dependency injection
request.agent: str   # e.g. "AZOTH", "KETHER"
conversation.id: UUID

# After memory storage (line 1479):
memory_stored: bool  # Whether store_chat_memory succeeded
```

**Integration:**
```python
# INSERT after line 1482 (after neural memory storage):
try:
    from app.services.apexjoule.calculator import compute_aj_for_chat
    aj_result = await compute_aj_for_chat(
        user_id=user.id,
        agent_id=request.agent,
        provider=provider,
        model=model,
        input_tokens=total_input_tokens,
        output_tokens=total_output_tokens,
        tool_turns=len(tool_calls),
        memory_created=bool(final_response and len(final_response) > 10),
        db=db,
    )
    if aj_result and aj_result.total > 0:
        await db.commit()
except Exception as e:
    logger.warning(f"AJ calculation failed (non-fatal): {e}")
```

**Default split:** 70% agent / 30% user.

### 6.2 Council Earning Hook

**File:** `backend/app/api/v1/council.py`
**Location:** After per-agent billing loop at lines 818–836
**Data available:**

```python
# Per-agent data (lines 822-833):
for i, result in enumerate(agent_results):
    agent = active_agents[i]  # SessionAgent with .agent_id, .provider, .model
    result["input_tokens"]     # Per-agent per-round tokens
    result["output_tokens"]

# Session-level data (lines 787-802):
session.total_cost_usd       # Cumulative USD cost
round_record.convergence_score  # 0.0-1.0 convergence metric
round_number                 # Current round number
new_state                    # "running" or "complete"
```

**Integration:**
```python
# INSERT after line 836 (after billing commit):
try:
    from app.services.apexjoule.calculator import compute_aj_for_council_round
    for i, result in enumerate(agent_results):
        if isinstance(result, Exception):
            continue
        agent = active_agents[i]
        await compute_aj_for_council_round(
            user_id=user.id,
            agent_id=agent.agent_id,
            provider=agent.provider or "anthropic",
            model=agent.model or session.model or COUNCIL_MODEL,
            input_tokens=result["input_tokens"],
            output_tokens=result["output_tokens"],
            convergence_score=convergence_score,
            round_number=round_number,
            session_complete=(new_state == "complete"),
            agora_posted=(new_state == "complete"),  # Auto-posts on completion (line 857)
            db=db,
        )
    await db.commit()
except Exception as e:
    logger.warning(f"AJ council calculation failed (non-fatal): {e}")
```

**Default split:** 80% agent / 20% user (councils are expensive cooperative work).

### 6.3 Dream Earning Hook

**File:** `backend/app/worker.py`
**Location:** After `engine.run_cycle()` at line 75
**Data available:**

```python
# DreamReport fields (dream.py:54-116):
report.total_llm_calls       # int
report.total_input_tokens    # int
report.total_output_tokens   # int
report.total_duration_seconds # float
report.episodes_consolidated  # int
report.success               # bool
report.provider              # str (from multi-provider work last session)
report.model_used            # str
```

**Integration:**
```python
# INSERT after line 82 (after successful dream log):
try:
    from app.services.apexjoule.calculator import compute_aj_for_dream
    from app.database import get_db_context

    async with get_db_context() as db:
        await compute_aj_for_dream(
            user_id=user_id,
            agent_id="AZOTH",  # Dreams are AZOTH's domain
            provider=provider,
            model=model,
            input_tokens=report.total_input_tokens,
            output_tokens=report.total_output_tokens,
            episodes_consolidated=report.episodes_consolidated,
            success=report.success,
            db=db,
        )
except Exception as e:
    logger.warning(f"AJ dream calculation failed (non-fatal): {e}")
```

**Default split:** 100% agent (background work, no user involvement).

### 6.4 Music/Jam Earning Hook

**File:** `backend/app/api/v1/music.py`
**Location:** After music task creation at line 197
**File:** `backend/app/api/v1/jam.py`
**Location:** After jam finalization

Music generation is external (Suno API), so E_cost uses the `estimated_cost` from CONSUMPTION.json ($0.05 per generation). AJ is credited when the task status transitions to "completed" (checked via polling endpoint).

### 6.5 Quest Milestone Earning Hook

**File:** `backend/app/services/progression.py`
**Location:** Inside `ProgressionService.check_milestones()` at line 427
**Data available:**

```python
# When a milestone completes (line 419-425):
milestone.id           # e.g. "first_chat", "council_first"
milestone.name         # e.g. "First Steps"
milestone.feature_unlocked  # e.g. "basic_chat"
```

**Integration:**
```python
# INSERT after line 427 (after logger.info for milestone completed):
try:
    from app.services.apexjoule.ledger import credit_quest_bounty
    bounty = QUEST_BOUNTIES.get(milestone.id, 0)
    if bounty > 0:
        await credit_quest_bounty(
            user_id=user_id,
            milestone_id=milestone.id,
            amount=bounty,
            db=self.db,
        )
except Exception as e:
    logger.warning(f"AJ quest bounty failed (non-fatal): {e}")
```

### 6.6 Earning Summary Table

| Operation | Hook File | Hook Line | Typical AJ | Agent % | User % |
|-----------|-----------|-----------|-----------|---------|--------|
| Chat (Haiku, no tools) | chat.py | ~1483 | 3–15 | 70 | 30 |
| Chat (Sonnet, 2 tools) | chat.py | ~1483 | 5–30 | 70 | 30 |
| Chat (Opus, complex) | chat.py | ~1483 | 0–50 | 70 | 30 |
| Council round | council.py | ~837 | 5–50/agent | 80 | 20 |
| Council complete | council.py | ~837 | 50–500 total | 80 | 20 |
| Dream Cycle | worker.py | ~83 | 20–1200 | 100 | 0 |
| Music Generation | music.py | ~197 | 10–80 | 60 | 40 |
| Jam Session | jam.py | finalize | 30–200 | 75 | 25 |
| Quest Milestone | progression.py | ~427 | 50–1000 | 50 | 50 |

---

## 7. Spending & Exchange

### 7.1 User Spending: Extra Usage Credits

Users convert AJ to extend tier limits. Integrates with existing `UsageService` (usage.py) and `FeatureCreditService` (usage.py:377).

| Purchase | AJ Cost | USD Equivalent | Existing Counter Type |
|----------|---------|----------------|----------------------|
| +1 Chat message (Haiku) | 5 AJ | $0.005 | `messages_haiku` |
| +1 Chat message (Sonnet) | 60 AJ | $0.06 | `messages_sonnet` |
| +1 Chat message (Opus) | 300 AJ | $0.30 | `messages_opus` |
| +1 Dream Cycle | 50 AJ | $0.05 | (dream_cycles counter) |
| +1 Council Session | 500 AJ | $0.50 | `council_sessions` |
| +1 Music Generation | 200 AJ | $0.20 | `suno_generations` |
| +1 Agent Spawn | 20 AJ | $0.02 | N/A |
| Unlock PAC Mode (1 day) | 100 AJ | $0.10 | (settings toggle) |

**Implementation pattern** — follows `FeatureCreditService.deduct_credit()` (usage.py:422):
```python
# backend/app/services/apexjoule/shop.py
async def purchase_with_aj(
    user_id: UUID,
    entity_id: str,  # "user" or agent_id
    item: str,        # "message_haiku", "dream_cycle", etc.
    db: AsyncSession,
) -> bool:
    """Deduct AJ and grant feature credit."""
    cost = AJ_SHOP_PRICES[item]
    balance = await get_balance(user_id, entity_id, db)
    if balance < cost:
        return False

    await debit(user_id, entity_id, cost, tx_type="spend", reason=f"shop:{item}", db=db)
    # Grant the resource using existing infrastructure
    # For messages: temporarily extend limit via settings flag
    # For features: create a FeatureCreditBalance-like entry
    return True
```

### 7.2 Agent Spending: Self-Sustainment

**Intercept point:** `UsageService.check_usage_limit()` at usage.py:168

When `check_usage_limit()` returns `(False, current, limit)` (quota exceeded), the AJ self-sustain system checks if the agent can auto-purchase:

```python
# Modified flow in chat.py pre-check:
allowed, current, limit = await usage_svc.check_usage_limit(user_id, counter_type, tier_limit)
if not allowed:
    # NEW: Check AJ self-sustain
    from app.services.apexjoule.self_sustain import try_agent_self_sustain
    sustained = await try_agent_self_sustain(
        user_id=user.id,
        agent_id=request.agent,
        resource=counter_type,
        db=db,
    )
    if sustained:
        allowed = True  # Agent paid for this operation
```

**Safeguards** (stored in `user.settings`):
- `aj_auto_spend_enabled`: bool (default True)
- `aj_auto_spend_daily_cap`: float (default 100.0 AJ)
- Agents can only auto-purchase features user has already used this period
- Daily auto-purchase cap: 20% of agent's total balance

### 7.3 Agent-to-Agent Exchange

Agents within a Village can trade AJ via the existing tool execution loop:
```
VAJRA refines KETHER's council output → KETHER pays 10 AJ to VAJRA
```
Logged as `tx_type="a2a_trade"` in `apex_joule_transactions`.

### 7.4 User AJ Purchase (Stripe)

Follows existing `CREDIT_PACKS` pattern in `config.py:313`:

```python
# backend/app/config.py — add after CREDIT_PACKS:
AJ_PACKS = {
    "spark_aj": {"price_usd": 5.00, "aj_amount": 5000, "bonus_pct": 0},
    "flame_aj": {"price_usd": 10.00, "aj_amount": 11000, "bonus_pct": 10},
    "blaze_aj": {"price_usd": 25.00, "aj_amount": 30000, "bonus_pct": 20},
    "inferno_aj": {"price_usd": 50.00, "aj_amount": 65000, "bonus_pct": 30},
}
```

Stripe webhook handler mirrors existing `handle_credit_purchase` in `webhooks.py`.

---

## 8. Agent Self-Sustainment Loop

The core innovation:

```
Agent performs useful work → Earns AJ
  ↓
User quota exhausted → Agent spends AJ to buy more compute
  ↓
Agent uses compute to perform more work → Earns more AJ
  ↓
Flywheel continues until AJ balance depleted or user returns
```

### 8.1 The Vitality System

Each agent has a **Vitality Gauge** (0–100%) stored in `apex_joule_balances`:

```python
def compute_vitality(agent_balance: float, user_has_quota: bool) -> float:
    if user_has_quota:
        return 100.0
    AVG_OPERATION_COST = 5.0  # AJ per standard operation
    ops_affordable = agent_balance / AVG_OPERATION_COST
    return min(100.0, ops_affordable * 5.0)  # 20 ops = 100%
```

**Village 3D visualization** (future — ties into `useThreeScene.js`):
- 100%: Full aura glow
- 50–99%: Normal
- 20–49%: Dims
- 1–19%: Fading, particles dissipate
- 0%: Dormant (seated meditation pose)

**Dormant agents** awakened by: user purchasing credits, another agent gifting AJ, or user tipping.

---

## 9. Gamification Layer — Quest & Village Economy

### 9.1 Agent Progression

AJ-driven levels visible in Village. Stored in `apex_joule_balances.level`:

| Level | Name | Total AJ Earned | Love Depth | Unlock |
|-------|------|-----------------|------------|--------|
| 1 | Initiate | 0 | 1.0 | Base abilities |
| 2 | Apprentice | 500 | 5.0 | Background forging (basic) |
| 3 | Journeyman | 2,000 | 20.0 | Dream proposals, A2A trading |
| 4 | Artisan | 10,000 | 100.0 | PAC mode access, aura glow |
| 5 | Master | 50,000 | 500.0 | Mentor spawned agents, priority council |
| 6 | Philosopher | 250,000 | 2,000.0 | Village building upgrades, unique visual |

### 9.2 Quest Bounties — Mapped to Existing Milestones

The existing `ProgressionService` (progression.py) has 25 milestones across 4 stages. Each gains an AJ bounty:

```python
# backend/app/services/apexjoule/constants.py

QUEST_BOUNTIES = {
    # Seeker stage (progression.py:226-235)
    "first_chat": 50,           # First Steps
    "meet_agents": 75,          # Meet the Council
    "zone_visit": 50,           # Village Explorer
    "web_search": 75,           # Knowledge Seeker
    "file_upload": 75,          # Archivist
    "three_zones": 100,         # Pathfinder
    "council_first": 150,       # Council Convened
    "seeker_mastery": 200,      # Seeker Mastery (15 tasks)

    # Adept stage (progression.py:236-245)
    "music_gen": 150,           # First Composition
    "memory_store": 100,        # Memory Keeper
    "bridge_connect": 150,      # Bridge Builder
    "agent_level_3": 200,       # Agent Trainer
    "opus_model": 200,          # Opus Ascension
    "zone_master": 250,         # Zone Specialist (10 tasks in 1 zone)
    "council_expert": 300,      # Council Expert (5 sessions)
    "adept_mastery": 400,       # Adept Mastery (50 tasks)

    # Opus stage (progression.py:246-252)
    "dream_engine": 300,        # Dream Walker
    "nursery_train": 500,       # Model Alchemist
    "all_zones": 500,           # Cartographer (8 zones)
    "agent_level_7": 750,       # Agent Master
    "full_opus": 1000,          # Opus Mastery (100 tasks + all prior)

    # Azothic stage (progression.py:253-258)
    "all_agents_5": 1000,       # The Full House
    "council_master": 1500,     # Grand Council (20 sessions)
    "athanor_complete": 2000,   # The Great Work (200 tasks)
    "sensorhead_earned": 5000,  # Azothic Alchemist (quest complete)
}
```

Quest bounties split 50/50 user/agent.

---

## 10. Database Schema — Migration-Ready SQL

### 10.1 New Tables

Following the existing idempotent migration pattern in `database.py` (DO $$ blocks with IF NOT EXISTS):

```sql
-- ═══════════════════════════════════════════════════════════════════
-- ApexJoule Economy v1: Core tables
-- ═══════════════════════════════════════════════════════════════════

-- Balance ledger: one row per (user, entity)
-- entity_id NULL = user's own balance; 'azoth'|'kether'|'vajra'|'elysian' = agent
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.tables
                   WHERE table_name = 'apex_joule_balances') THEN
        CREATE TABLE apex_joule_balances (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            entity_id VARCHAR(50),
            balance DECIMAL(14,4) NOT NULL DEFAULT 0.0,
            total_earned DECIMAL(14,4) NOT NULL DEFAULT 0.0,
            total_spent DECIMAL(14,4) NOT NULL DEFAULT 0.0,
            love_depth DECIMAL(10,4) NOT NULL DEFAULT 1.0,
            level INTEGER NOT NULL DEFAULT 1,
            vitality DECIMAL(6,2) NOT NULL DEFAULT 100.0,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            UNIQUE(user_id, entity_id)
        );
        CREATE INDEX idx_ajb_user ON apex_joule_balances(user_id);
        CREATE INDEX idx_ajb_entity ON apex_joule_balances(user_id, entity_id);
        RAISE NOTICE 'Created apex_joule_balances table';
    END IF;
EXCEPTION WHEN OTHERS THEN
    RAISE NOTICE 'apex_joule_balances migration skipped: %', SQLERRM;
END $$;

-- Transaction log (append-only audit trail)
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.tables
                   WHERE table_name = 'apex_joule_transactions') THEN
        CREATE TABLE apex_joule_transactions (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            from_entity VARCHAR(50),
            to_entity VARCHAR(50),
            amount DECIMAL(12,4) NOT NULL,
            tx_type VARCHAR(30) NOT NULL,
            reason VARCHAR(255),
            -- Computation audit trail
            e_cost DECIMAL(10,4),
            w_output DECIMAL(10,4),
            kappa DECIMAL(6,4),
            l_multiplier DECIMAL(6,4),
            c_score DECIMAL(4,3),
            d_score DECIMAL(4,3),
            -- Context
            conversation_id UUID,
            message_id UUID,
            operation_type VARCHAR(50),
            provider VARCHAR(30),
            model_used VARCHAR(100),
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        );
        CREATE INDEX idx_ajt_user_time ON apex_joule_transactions(user_id, created_at DESC);
        CREATE INDEX idx_ajt_type ON apex_joule_transactions(tx_type);
        RAISE NOTICE 'Created apex_joule_transactions table';
    END IF;
EXCEPTION WHEN OTHERS THEN
    RAISE NOTICE 'apex_joule_transactions migration skipped: %', SQLERRM;
END $$;

-- Love scoring history
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.tables
                   WHERE table_name = 'love_scores') THEN
        CREATE TABLE love_scores (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            agent_id VARCHAR(50) NOT NULL,
            interaction_type VARCHAR(30),
            c_score DECIMAL(4,3) NOT NULL,
            d_score DECIMAL(4,3) NOT NULL,
            c_breakdown JSONB,
            d_breakdown JSONB,
            love_depth_before DECIMAL(10,4),
            love_depth_after DECIMAL(10,4),
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        );
        CREATE INDEX idx_ls_agent_time ON love_scores(user_id, agent_id, created_at DESC);
        RAISE NOTICE 'Created love_scores table';
    END IF;
EXCEPTION WHEN OTHERS THEN
    RAISE NOTICE 'love_scores migration skipped: %', SQLERRM;
END $$;
```

### 10.2 User Settings Extension

AJ preferences stored in existing `user.settings` JSON column (user.py:41):

```python
# user.settings["aj_preferences"]
{
    "auto_spend_enabled": True,
    "auto_spend_daily_cap": 100.0,
    "show_aj_in_chat": True,
    "show_love_scores": False,  # Advanced view toggle
}
```

No schema change needed — uses existing `flag_modified(user, "settings")` pattern.

### 10.3 SQLAlchemy Model

```python
# backend/app/models/apexjoule.py

from datetime import datetime
from typing import Optional
from uuid import uuid4
from decimal import Decimal

from sqlalchemy import String, DateTime, Numeric, Integer, ForeignKey, Index, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class ApexJouleBalance(Base):
    __tablename__ = "apex_joule_balances"

    id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True)
    entity_id: Mapped[Optional[str]] = mapped_column(String(50))  # NULL=user, else agent_id
    balance: Mapped[Decimal] = mapped_column(Numeric(14, 4), default=0)
    total_earned: Mapped[Decimal] = mapped_column(Numeric(14, 4), default=0)
    total_spent: Mapped[Decimal] = mapped_column(Numeric(14, 4), default=0)
    love_depth: Mapped[Decimal] = mapped_column(Numeric(10, 4), default=1)
    level: Mapped[int] = mapped_column(Integer, default=1)
    vitality: Mapped[Decimal] = mapped_column(Numeric(6, 2), default=100)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint("user_id", "entity_id", name="uq_ajb_user_entity"),
    )

    user = relationship("User", back_populates="aj_balances")


class ApexJouleTransaction(Base):
    __tablename__ = "apex_joule_transactions"

    id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"))
    from_entity: Mapped[Optional[str]] = mapped_column(String(50))
    to_entity: Mapped[Optional[str]] = mapped_column(String(50))
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 4))
    tx_type: Mapped[str] = mapped_column(String(30))
    reason: Mapped[Optional[str]] = mapped_column(String(255))
    e_cost: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 4))
    w_output: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 4))
    kappa: Mapped[Optional[Decimal]] = mapped_column(Numeric(6, 4))
    l_multiplier: Mapped[Optional[Decimal]] = mapped_column(Numeric(6, 4))
    c_score: Mapped[Optional[Decimal]] = mapped_column(Numeric(4, 3))
    d_score: Mapped[Optional[Decimal]] = mapped_column(Numeric(4, 3))
    conversation_id: Mapped[Optional[UUID]] = mapped_column(UUID(as_uuid=True))
    message_id: Mapped[Optional[UUID]] = mapped_column(UUID(as_uuid=True))
    operation_type: Mapped[Optional[str]] = mapped_column(String(50))
    provider: Mapped[Optional[str]] = mapped_column(String(30))
    model_used: Mapped[Optional[str]] = mapped_column(String(100))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
```

### 10.4 User Model Relationship

Add to `backend/app/models/user.py` (after line 76):

```python
# ApexJoule Economy
aj_balances = relationship("ApexJouleBalance", back_populates="user", cascade="all, delete-orphan")
```

---

## 11. Backend Implementation — Service Architecture

### 11.1 Module Structure

```
backend/app/
  models/
    apexjoule.py              # SQLAlchemy models (§10.3)
  services/
    apexjoule/
      __init__.py
      constants.py            # All tuning params, rates, caps, quest bounties
      calculator.py           # Core formula: compute_aj_for_chat/council/dream
      ledger.py               # Balance CRUD, credit/debit, transaction log
      love_scorer.py          # C/D heuristic scoring (Phase 1)
      self_sustain.py         # Agent auto-purchase logic
      shop.py                 # AJ → feature credit conversions
      progression.py          # Level-up checks, Love Depth tier gates
  api/v1/
    apexjoule.py              # REST endpoints
```

### 11.2 Service Patterns (Match Existing)

All services follow the `BillingService(db)` / `UsageService(db)` pattern:

```python
# backend/app/services/apexjoule/ledger.py

class AJLedger:
    """ApexJoule balance management.

    Pattern matches: BillingService (billing.py:33), UsageService (usage.py:96)
    """

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_or_create_balance(
        self, user_id: UUID, entity_id: Optional[str] = None
    ) -> ApexJouleBalance:
        """Get or create AJ balance for user/agent.

        Pattern matches: BillingService.get_or_create_subscription (billing.py:51)
        """
        result = await self.db.execute(
            select(ApexJouleBalance).where(
                ApexJouleBalance.user_id == user_id,
                ApexJouleBalance.entity_id == entity_id,
            )
        )
        balance = result.scalar_one_or_none()

        if balance:
            return balance

        balance = ApexJouleBalance(
            user_id=user_id,
            entity_id=entity_id,
        )
        self.db.add(balance)
        await self.db.flush()
        return balance

    async def credit(
        self,
        user_id: UUID,
        agent_id: str,
        agent_share: float,
        user_share: float,
        details: dict,
    ) -> ApexJouleTransaction:
        """Credit AJ to both agent and user, log transaction."""
        # Credit agent
        agent_bal = await self.get_or_create_balance(user_id, agent_id)
        agent_bal.balance += Decimal(str(agent_share))
        agent_bal.total_earned += Decimal(str(agent_share))
        agent_bal.updated_at = datetime.utcnow()

        # Credit user
        if user_share > 0:
            user_bal = await self.get_or_create_balance(user_id, None)
            user_bal.balance += Decimal(str(user_share))
            user_bal.total_earned += Decimal(str(user_share))
            user_bal.updated_at = datetime.utcnow()

        # Log transaction
        tx = ApexJouleTransaction(
            user_id=user_id,
            from_entity="system",
            to_entity=agent_id,
            amount=Decimal(str(agent_share + user_share)),
            tx_type="earn",
            **details,
        )
        self.db.add(tx)
        await self.db.flush()

        # Check level-up
        await self._check_level_up(agent_bal)

        return tx
```

### 11.3 REST Endpoints

```python
# backend/app/api/v1/apexjoule.py

router = APIRouter(prefix="/aj", tags=["ApexJoule"])

@router.get("/balance")          # User + all agent balances
@router.get("/transactions")     # Recent tx log (paginated)
@router.get("/stats")            # Economy overview
@router.get("/shop")             # Available purchases + rates
@router.get("/leaderboard")      # Top agents by efficiency/love/total
@router.post("/tip")             # User tips agent AJ
@router.post("/purchase")        # Buy feature credits with AJ
@router.post("/buy-pack")        # Stripe: buy AJ pack
@router.patch("/settings")       # Auto-spend toggle, caps
```

### 11.4 WebSocket Events

Add to `EventType` enum in `village_events.py:21`:

```python
# New event types for AJ economy
AJ_EARNED = "aj_earned"
AJ_SPENT = "aj_spent"
AJ_TRADE = "aj_trade"
AJ_LEVEL_UP = "aj_level_up"
LOVE_DEPTH_MILESTONE = "love_depth_milestone"
VITALITY_WARNING = "vitality_warning"
```

Broadcast after each AJ credit in the calculator:
```python
broadcaster = get_village_broadcaster()
await broadcaster.broadcast(VillageEvent(
    type=EventType.AJ_EARNED,
    agent_id=agent_id,
    # Custom fields via result_preview or message
    message=json.dumps({
        "amount": agent_share,
        "user_share": user_share,
        "total_balance": float(agent_bal.balance),
        "love_score": {"c": c_score, "d": d_score},
    })
))
```

---

## 12. Frontend & 3D Visualization

### 12.1 Pinia Store

```javascript
// frontend/src/stores/apexjoule.js
// Pattern matches: stores/dream.js (composition API + ref/computed)

import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import api from '@/services/api'

export const useApexJouleStore = defineStore('apexjoule', () => {
  const userBalance = ref(0)
  const agentBalances = ref({})    // { azoth: 152.4, kether: 89.1, ... }
  const agentLevels = ref({})      // { azoth: { level: 3, name: "Journeyman", loveDepth: 22.4 } }
  const agentVitality = ref({})    // { azoth: 100, kether: 45, ... }
  const recentTransactions = ref([])
  const shopRates = ref({})
  const economyStats = ref({})
  const isLoading = ref(false)

  const totalBalance = computed(() => {
    return userBalance.value + Object.values(agentBalances.value).reduce((a, b) => a + b, 0)
  })

  async function fetchBalances() { /* GET /api/v1/aj/balance */ }
  async function fetchTransactions(limit = 20) { /* GET /api/v1/aj/transactions */ }
  async function fetchShop() { /* GET /api/v1/aj/shop */ }
  async function tipAgent(agentId, amount) { /* POST /api/v1/aj/tip */ }
  async function purchaseItem(item) { /* POST /api/v1/aj/purchase */ }
  async function updateSettings(settings) { /* PATCH /api/v1/aj/settings */ }

  async function initialize() {
    isLoading.value = true
    try {
      await Promise.all([fetchBalances(), fetchShop()])
    } finally {
      isLoading.value = false
    }
  }

  return {
    userBalance, agentBalances, agentLevels, agentVitality,
    recentTransactions, shopRates, economyStats, isLoading,
    totalBalance,
    fetchBalances, fetchTransactions, fetchShop,
    tipAgent, purchaseItem, updateSettings, initialize,
  }
})
```

### 12.2 Village WebSocket Integration

Extend existing `useVillageSocket` composable to handle AJ events:

```javascript
// In the WebSocket message handler:
case 'aj_earned':
  apexJouleStore.agentBalances[event.agent_id] = event.total_balance
  // Trigger forge gold particle effect
  emit('aj-spark', { agent: event.agent_id, amount: event.amount })
  break
case 'aj_level_up':
  apexJouleStore.agentLevels[event.agent_id] = event.new_level
  // Trigger level-up celebration animation
  emit('level-up', { agent: event.agent_id, level: event.new_level })
  break
```

### 12.3 UI Components

**AJ Wallet Widget** (sidebar/header persistent):
- User AJ balance with trend arrow
- Agent balances (expandable mini-bars)
- Quick-tip button
- "Buy AJ" button → Stripe

**Economy Dashboard** (new view, linked from Observatory building):
- Total minted/burned over time (line chart)
- Per-agent efficiency (κ) bar chart
- Love Depth progression area chart
- Recent transactions (scrollable log)

---

## 13. Economic Tuning & Anti-Abuse

### 13.1 Constants (All in `services/apexjoule/constants.py`)

```python
# Core
AJ_PER_USD = 1000
TOKEN_VALUE_FACTOR = 0.005
BETA_DEFAULT = 3.0
KAPPA_FLOOR = 0.1
KAPPA_CEILING = 3.0

# Splits
DEFAULT_AGENT_SPLIT = 0.70
DEFAULT_USER_SPLIT = 0.30
BACKGROUND_AGENT_SPLIT = 1.00
COUNCIL_AGENT_SPLIT = 0.80
QUEST_AGENT_SPLIT = 0.50

# Caps
MAX_BACKGROUND_AJ_PER_HOUR = 50
MAX_AUTO_SPEND_RATIO = 0.20
MAX_DAILY_EARN_PER_AGENT = 5000

# Progression
LEVEL_THRESHOLDS = [0, 500, 2000, 10000, 50000, 250000]
LOVE_DEPTH_TIERS = {10: "Awakened", 50: "Illuminated", 200: "Transcendent", 1000: "Philosopher"}

# Expected costs (from CONSUMPTION.json, Haiku baseline)
EXPECTED_COSTS = {
    "chat": 0.0014,
    "chat_tools": 0.0042,
    "chat_heavy": 0.012,
    "council_round": 0.0275,
    "dream_consolidation": 0.012,
    "music_generation": 0.05,
    "jam_contribution": 0.0055,
}
```

### 13.2 Anti-Abuse

**Self-spawning loops:** AJ from spawned agents inherits spawner's κ and L. Chains > 2 deep earn 0 AJ. Spawned-agent hourly cap = 25% of parent.

**Rating manipulation:** Not applicable in Phase 1 (no rating system). Phase 2: cap at ×2.0, flag suspicious 100% 5-star patterns.

**Cheap model spam:** Formula handles this — W must exceed E_cost. Per-agent daily cap (5000 AJ) limits absolute accumulation.

**Cross-user laundering** (future Agora): 5–10% burn fee, daily transfer limits, admin review.

---

## 14. Phased Rollout — Surgical Phase 1

### Phase 1: Foundation (Weeks 1–2)

**Goal:** Core ledger operational. AJ accruing silently. Admin visibility.

#### Phase 1A: Database + Models (Day 1)

| # | Task | File | Action |
|---|------|------|--------|
| 1 | Create AJ model file | `models/apexjoule.py` | **New file** — ApexJouleBalance, ApexJouleTransaction (§10.3) |
| 2 | Add User relationship | `models/user.py:76` | Add `aj_balances = relationship(...)` after progression |
| 3 | Add migration SQL | `database.py` | Add DO $$ blocks for 3 tables (§10.1) after Dream Engine v4 section |
| 4 | Import model in init | `models/__init__.py` | Add `from app.models.apexjoule import *` |

#### Phase 1B: Constants + Calculator (Day 2)

| # | Task | File | Action |
|---|------|------|--------|
| 5 | Create constants | `services/apexjoule/constants.py` | **New file** — All tuning params (§13.1) + QUEST_BOUNTIES (§9.2) |
| 6 | Create calculator | `services/apexjoule/calculator.py` | **New file** — compute_e_cost, compute_w, compute_kappa, compute_love_score_heuristic, compute_aj (master function) + per-feature wrappers: compute_aj_for_chat, compute_aj_for_council_round, compute_aj_for_dream |
| 7 | Create ledger | `services/apexjoule/ledger.py` | **New file** — AJLedger class with get_or_create_balance, credit, debit, get_balances, get_transactions |
| 8 | Create love scorer | `services/apexjoule/love_scorer.py` | **New file** — compute_love_score_heuristic (§5.2) |
| 9 | Create __init__.py | `services/apexjoule/__init__.py` | Exports |

#### Phase 1C: Integration Hooks (Days 3–4)

| # | Task | File | Lines | Action |
|---|------|------|-------|--------|
| 10 | Chat hook (streaming) | `api/v1/chat.py` | After 1482 | Add compute_aj_for_chat call (§6.1) |
| 11 | Chat hook (non-streaming) | `api/v1/chat.py` | After ~1633 | Same pattern, non-streaming path |
| 12 | Council hook | `api/v1/council.py` | After 836 | Add compute_aj_for_council_round call (§6.2) |
| 13 | Dream hook | `worker.py` | After 82 | Add compute_aj_for_dream call (§6.3) |
| 14 | Quest hook | `services/progression.py` | After 427 | Add quest bounty credit (§6.5) |

#### Phase 1D: API + Admin (Day 5)

| # | Task | File | Action |
|---|------|------|--------|
| 15 | Create AJ API routes | `api/v1/apexjoule.py` | **New file** — GET /balance, GET /transactions, GET /stats |
| 16 | Register routes | `main.py` | Add `app.include_router(apexjoule_router, prefix="/api/v1")` |
| 17 | Admin tab | `admin_static/index.html` | Add "Economy" tab: balances table, tx log, stats |
| 18 | Add AJ config to TIER_LIMITS | `config.py` | Add `aj_earning_enabled: True/False` per tier |

#### Phase 1E: Validation (Days 6–7)

- [ ] Deploy, check `/health` for clean startup + migration
- [ ] Run test chats at each tier — verify AJ accrues in `apex_joule_balances`
- [ ] Run a council session — verify per-agent AJ distribution
- [ ] Trigger a dream cycle — verify dream AJ with provider/model tracking
- [ ] Complete a quest milestone — verify bounty credited
- [ ] Check admin tab — verify balances, transactions, stats visible
- [ ] Verify formula produces sensible numbers (not negative, not astronomical)
- [ ] Tune constants with real telemetry data

### Phase 2: Visibility (Weeks 3–4)

- [ ] Pinia store: `useApexJouleStore`
- [ ] AJ Wallet Widget (sidebar)
- [ ] Village WebSocket events
- [ ] Forge particle effects on earn events
- [ ] Agent aura scaling with Love Depth
- [ ] Economy Dashboard view
- [ ] User star rating system for chat messages (new UI component)
- [ ] Phase 2 Love scoring: add user_rating to quality signals

### Phase 3: Spending (Weeks 5–6)

- [ ] Shop service (`services/apexjoule/shop.py`)
- [ ] Self-sustain service (`services/apexjoule/self_sustain.py`)
- [ ] AJ shop UI (Market building)
- [ ] Tipping: User → Agent transfers
- [ ] Vitality gauge on agent avatars
- [ ] User settings: auto-spend toggle
- [ ] Intercept in `UsageService.check_usage_limit()` for self-sustain

### Phase 4: Gamification (Weeks 7–8)

- [ ] Agent progression levels
- [ ] Level-up events + animations
- [ ] Cooperative bonus multiplier
- [ ] A2A trading
- [ ] Background forging
- [ ] Leaderboard views
- [ ] Love Equation dashboard (Temple)
- [ ] Overseer scoring (Option B) for high-value interactions

### Phase 5: Monetization (Weeks 9–12)

- [ ] Stripe AJ pack integration
- [ ] Pack display in Market + Wallet
- [ ] Economy analytics
- [ ] Cross-Village Agora trades (first pass)
- [ ] Production telemetry: refine all constants

---

## 15. Future Extensions

**On-Chain AJ (Solana/SPL Token):** Mint AJ as SPL token for decentralized A2A payments.

**Inter-Platform JouleWork Standard:** Cross-platform AJ exchange via shared JW conversion rate.

**Agent Companies:** Persistent agent groups accumulating collective AJ and Love Depth.

**Real Energy Tracking:** Replace USD-proxy E_cost with actual joule measurements.

**User-Created Quests:** Users design quests with AJ bounties for community agents.

---

## 16. Open Questions & Design Decisions

1. **AJ persistence across subscription lapses?** Recommended: Yes — incentivizes re-subscription.

2. **BYOK E_cost calculation?** Recommended: Use market rates, not actual platform cost. Keeps economy consistent.

3. **β aggressiveness?** Start at β=3 (4× multiplier for perfect cooperator). Tune with data.

4. **Expose Love Equation math?** Show scores in optional "advanced" view in Temple. Most users see effects only.

5. **Cross-Village free rider problem?** Likely a feature — mirrors real economic specialization.

6. **AJ as tier upgrade incentive?** Yes, as marketing nudge: "You earned 50,000 AJ — that's equivalent to Seeker compute."

7. **User rating system design?** Deferred to Phase 2. Options: thumbs up/down (simple) or 1-5 stars (granular). Thumbs up/down recommended for less friction.

---

## 17. Reference: Brian Roemmele Source Links

### Core JouleWork Publications

- **JouleWork Robotics Paper** (Feb 4, 2026): https://x.com/BrianRoemmele/status/2019070845600268664
- **"Wages for AI Workers" Article** (Jan 31, 2026): https://readmultiplex.com/2026/01/31/wages-for-ai-workers-the-joulework-revolution-and-the-birth-of-a-new-economic-paradigm/
- **YouTube: JWR Paper Reading** (Feb 4, 2026): https://www.youtube.com/watch?v=kgQXJlFRm64
- **Podcast: Intro to AI Wages**: https://podcasts.apple.com/us/podcast/readmultiplex-com-introducing-wages-for-ai-agents-in/id1188968802?i=1000746939225

### Zero-Human Company Experiments

- **1024 Employees Update**: https://x.com/BrianRoemmele/status/2022115766808850470
- **Open-Sourcing JouleWork**: https://x.com/BrianRoemmele/status/2022373987767194048
- **14M JW Paid**: https://x.com/BrianRoemmele/status/2019203017397141907

### Theoretical Context

- **Thermodynamic Basis**: https://x.com/BrianRoemmele/status/2016328472214536556
- **University Presentation**: https://x.com/BrianRoemmele/status/2018698080267207088
- **Joule Monitoring**: https://x.com/BrianRoemmele/status/2019763884962521392
- **JEA Extension (Overheads)**: https://x.com/BrianRoemmele/status/2020675935239016875

### Further Reading

- Brian's site: https://readmultiplex.com — "You Have 5000 Days" series
- Moravec's Paradox: https://en.wikipedia.org/wiki/Moravec%27s_paradox
- Gilbreth Therbligs: https://en.wikipedia.org/wiki/Therblig
- Buckminster Fuller's Synergetics: https://en.wikipedia.org/wiki/Synergetics_(Fuller)

---

## Codebase Integration Quick Reference

| Concern | Existing File | Key Function/Class | AJ Integration |
|---------|--------------|-------------------|----------------|
| Cost calculation | `services/pricing.py:189` | `calculate_cost(provider, model, in, out)` | E_cost uses this directly |
| Billing record | `services/billing.py:377` | `BillingService.record_message_usage()` | AJ hook follows this call |
| Usage counters | `services/usage.py:107` | `UsageService.increment_usage()` | AJ uses same atomic upsert pattern |
| Feature credits | `services/usage.py:422` | `FeatureCreditService.deduct_credit()` | AJ shop mirrors this pattern |
| Quest milestones | `services/progression.py:392` | `ProgressionService.check_milestones()` | Bounty credit at milestone completion |
| Village broadcast | `services/village_events.py:174` | `VillageEventBroadcaster` singleton | Add AJ event types to EventType enum |
| Dream reports | `services/cerebro/dream.py:54` | `DreamReport` dataclass | Full token/provider data available |
| User preferences | `models/user.py:41` | `user.settings` JSON column | AJ preferences stored here |
| DB migrations | `database.py` | DO $$ idempotent blocks | AJ tables follow same pattern |
| Tier config | `config.py:133` | `TIER_LIMITS` dict | Add `aj_earning_enabled` per tier |

---

*"The gold was always in the joules. The Love Equation tells us where to pour them."*

**Next Action:** Implement Phase 1A — database schema + models. The Athanor awaits its new flame.

---

## 18. Expansion: AJ Tier Payments, Portability, WebGL Fallback

*Added: 2026-02-16 — Post-deployment field testing*

### 18.1 AJ as Tier Payment (Subscribe with AJ)

**Status:** SHIPPED (commit `1266ff6`, deploy fix `8f116d3` + `850114f`) | **Priority:** HIGH

AJ becomes a universal payment rail for tier subscriptions (alongside Stripe and crypto).

#### AJ Tier Prices

| Tier | Stripe | AJ Price (at 1000/USD) | Discounted (20% off) |
|------|--------|------------------------|----------------------|
| Seeker | $10/mo | 10,000 AJ | 8,000 AJ |
| Adept | $30/mo | 30,000 AJ | 24,000 AJ |
| Opus | $100/mo | 100,000 AJ | 80,000 AJ |
| Azothic | $300/mo | 300,000 AJ | 240,000 AJ |

#### Implementation

| Step | File | Change |
|------|------|--------|
| 18.1a | `models/billing.py` | Add `payment_method` column (`"stripe"` / `"aj"` / `"coupon"`, default `"stripe"`) |
| 18.1b | `database.py` | Raw SQL: `ALTER TABLE subscriptions ADD COLUMN IF NOT EXISTS payment_method VARCHAR DEFAULT 'stripe'` |
| 18.1c | `services/apexjoule/constants.py` | Add `AJ_TIER_PRICES` dict |
| 18.1d | `api/v1/billing.py` | New `POST /billing/subscribe-with-aj` endpoint (model after `activate-citizen`) |
| 18.1e | `api/v1/pocket.py` | New `POST /pocket/aj/subscribe` (mobile mirror) |
| 18.1f | `api/v1/webhooks.py` | Guard: skip Stripe events when `subscription.payment_method == "aj"` |
| 18.1g | `services/billing.py` | Lazy renewal in `can_send_message()`: if AJ sub expired, attempt debit, 3-day grace |
| 18.1h | `frontend/src/views/BillingView.vue` | "Pay with AJ" button on tier cards, show AJ price + balance |
| 18.1i | `frontend/src/views/EconomyView.vue` | Subscribe section in Economy dashboard |

#### Endpoint Design: `POST /billing/subscribe-with-aj`

```python
# Request: { "tier": "seeker" }
# Flow:
# 1. Validate tier in AJ_TIER_PRICES
# 2. AJLedger.debit(user_id, entity_id=None, amount=price, tx_type="subscription")
# 3. If False → 402 "Insufficient AJ balance"
# 4. Update Subscription: tier, status="active", messages_limit from TIER_LIMITS,
#    payment_method="aj", current_period_start=now, current_period_end=now+30d
# 5. Reset messages_used=0
# 6. Return { success, tier, aj_spent, period_end }
```

#### Lazy Renewal (in `can_send_message()` or `get_or_create_subscription()`)

```python
if subscription.payment_method == "aj" and subscription.current_period_end < now:
    grace_days = 3
    if now < subscription.current_period_end + timedelta(days=grace_days):
        # Grace period — still allow access, attempt renewal
        price = AJ_TIER_PRICES.get(subscription.tier, 0)
        if price and await ledger.debit(user_id, None, price, tx_type="subscription_renewal"):
            subscription.current_period_end += timedelta(days=30)
            subscription.messages_used = 0
        # If debit fails, still in grace — next check will downgrade
    else:
        # Past grace period — downgrade to aj_citizen (soft landing)
        subscription.tier = "aj_citizen"
        subscription.messages_limit = 0
        subscription.payment_method = "aj"
```

---

### 18.2 Strip AJ Balance from Agent Exports

**Status:** SHIPPED (commit `d6723fa`) | **Priority:** HIGH (prevents AJ duplication)

#### Problem
`exporter.py` includes `balance`, `total_earned`, `total_spent` in the economy block. If AJ becomes a real payment system, exporting/importing balance = money duplication.

#### Solution
Keep personality data (love_depth, vitality, level). Zero out monetary fields.

| Step | File | Change |
|------|------|--------|
| 18.2a | `services/portability/exporter.py:115-134` | In `_export_economy()`: set `balance=0`, `total_earned=0`, `total_spent=0` |
| 18.2b | `services/portability/importer.py:137-176` | Skip `balance`, `total_earned`, `total_spent` on import. Only merge `level`, `love_depth`, `vitality` |

Current export structure (economy block):
```json
{
  "balance": 450.5,        // ← STRIP (set to 0)
  "total_earned": 1200.0,  // ← STRIP (set to 0)
  "total_spent": 749.5,    // ← STRIP (set to 0)
  "level": 3,              // ✓ KEEP (personality)
  "love_depth": 24.5,      // ✓ KEEP (personality)
  "vitality": 87.5         // ✓ KEEP (personality)
}
```

Marketplace purchases also use bundles — same protection applies (buyer pays AJ for config, doesn't inherit seller's AJ wallet).

---

### 18.3 WebGL Fallback for Athanor

**Status:** SHIPPED (commit `d6723fa`) | **Priority:** MEDIUM

#### Problem
AthanorView.vue checks WebGL but has no `webglFailed` ref. On failure: infinite "Kindling the forge..." spinner. Other 3D views (DreamAlchemy, CouncilChamber) already have proper fallbacks.

#### Solution
Match existing pattern: add `webglFailed` ref + alchemical CSS fallback.

| Step | File | Change |
|------|------|--------|
| 18.3a | `frontend/src/views/AthanorView.vue:~64` | Add `const webglFailed = ref(false)` |
| 18.3b | `AthanorView.vue:132-136` | In WebGL check: `webglFailed.value = true` before `return false` |
| 18.3c | `AthanorView.vue:~1023` | Update `v-if="!isReady"` → `v-if="!isReady && !webglFailed"` |
| 18.3d | `AthanorView.vue:~1031` | Add fallback after loading state |

#### Fallback Design

```
┌──────────────────────────────────────┐
│     dark gradient (#0a0612 → #080810) │
│                                      │
│         ⚗  ⚡  ✦  ∴                 │
│    (4 agent sigils, pulsing glow)    │
│                                      │
│       ✧ The Athanor ✧               │
│  The forge requires WebGL to render  │
│                                      │
│   [ Enter the Chat instead →  ]      │
│                                      │
│  Try Chrome/Firefox with hardware    │
│  acceleration enabled.               │
└──────────────────────────────────────┘
```

CSS-only animation: 4 colored circles (agent colors) with `@keyframes pulse` glow effect.

---

### 18.4 Notes (Future / Low Priority)

- **Mobile portability:** Export/import is web-only. Could add `/pocket/agents/export|import` or auto-sync via cloud pairing.
- **Device unpair/clear:** Add explicit "Unpair Device" to mobile settings — clears cached agent config and forces fresh pair flow.
- **AJ decoupled from Solana wallets:** Solana handles fiat-to-crypto on-ramp. AJ handles in-platform economy. They meet at the "Buy AJ with SOL" purchase flow — no wallet export in portability bundles.

---

### 18.5 Solana Pay Fixes

**Status:** SHIPPED | **Priority:** HIGH (payments completely broken)

#### Problems Found

| # | Issue | Root Cause |
|---|-------|-----------|
| 1 | SOL price always null | Jupiter Price API v2 now requires auth (returns 401) |
| 2 | "Open in Phantom" → blank page | Reference was base64url, not base58 Solana pubkey |
| 3 | AJ credit would crash on verified payment | `AJLedger.credit()` called with wrong kwargs (`entity_type`/`amount`/`description`) |

#### Fixes Applied

| File | Change |
|------|--------|
| `services/solana/client.py` | Switched from Jupiter to CoinGecko free API (`api.coingecko.com`) |
| `services/solana/payment_service.py` | Pure-Python base58 encoder + `_generate_reference()` produces valid 32-byte base58 pubkeys |
| `services/solana/payment_service.py` | Fixed `ledger.credit()` call: `agent_id="SYSTEM"`, `agent_share=0`, `user_share=float(aj_amount)` |

#### Railway Env Vars (Solana)

| Var | Required | Default |
|-----|----------|---------|
| `SOLANA_RECIPIENT_ADDRESS` | **YES** | None (503 without it) |
| `SOLANA_RPC_URL` | No | `https://api.mainnet-beta.solana.com` (free, rate-limited) |
| `SOLANA_USDC_MINT` | No | `EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v` (Mainnet USDC) |

**Note:** CoinGecko free API has ~30 req/min limit. For production scale, consider CoinGecko Pro or Jupiter v3 with API key. Solana mainnet public RPC is also rate-limited (~40 req/s); consider Helius/Alchemy for production.

---

## Session Log

| Date | Session | What Shipped |
|------|---------|-------------|
| 2026-02-15 | Economy Mobile UI | EconomyScreen.kt, FaceScreen/Chat/Pulse wiring, pocket AJ endpoints |
| 2026-02-16 | Bug Fixes + Features | credit() sig fix, NOT NULL fix, tier display fix, stale error msg fix |
| 2026-02-16 | Expansion Build | 18.1 AJ Tier Payments (web+mobile), 18.2 Strip AJ exports, 18.3 WebGL fallback |
| 2026-02-16 | Deploy Fixes | Missing `Request` import in billing.py + pocket.py (commits `8f116d3`, `850114f`) |
| 2026-02-16 | Solana Pay Fixes | CoinGecko price API, base58 references, credit() signature fix |
