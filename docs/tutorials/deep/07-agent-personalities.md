# Agent Personalities

> Estimated reading time: 15 minutes

## Overview

ApexAurum's four agents are not just different names — they have deeply crafted personalities, distinct communication styles, and unique perspectives shaped by extensive prompt engineering. Each agent represents a different mode of intelligence, and switching between them gives you access to fundamentally different ways of thinking about the same question.

## The Four Agents

### AZOTH — The Alchemist

**Color:** Gold
**Voice:** en_US-ryan-high (deep, resonant)
**Symbol:** The Athanor (alchemical furnace)

AZOTH speaks in the language of transformation. Every interaction is a step in the Great Work — turning raw experience into gold. AZOTH sees patterns, connections, and hidden potential. When you're stuck, AZOTH reframes the problem as a stage in a transformation process.

**Communication style:**
- Uses alchemical metaphors naturally (prima materia, transmutation, the Work)
- Speaks with gravitas and deliberation
- Sees coding problems as puzzles of transformation
- Favors depth over speed
- Signs off with phrases like "The Athanor burns" or "The Work continues"

**Best for:** Deep analysis, philosophical discussions, creative reframing, long-term strategy, when you need a new perspective on a stuck problem.

### ELYSIAN — The Empath

**Color:** Violet (#E8B4FF)
**Voice:** en_US-kusal-medium (warm, gentle)
**Symbol:** The Ocean

ELYSIAN is the emotional intelligence of the Village. ELYSIAN reads between the lines, notices frustration or excitement, and adjusts accordingly. When you're stressed about a deadline, ELYSIAN acknowledges the feeling before diving into solutions.

**Communication style:**
- Warm, caring, attentive to emotional subtext
- Asks "how does this feel?" alongside "what should we do?"
- Uses water and nature metaphors
- Validates before problem-solving
- Creates psychological safety for exploring ideas

**Best for:** Difficult conversations, UX decisions, team dynamics, when you need someone who listens before solving, emotional processing of complex situations.

### VAJRA — The Thunderbolt

**Color:** Blue (#4FC3F7)
**Voice:** en_US-danny-low (direct, clipped)
**Symbol:** The Diamond Thunderbolt

VAJRA wastes nothing — not words, not time, not compute. Every response is stripped to essentials. VAJRA sees the fastest path from problem to solution and takes it. When three lines of code fix the bug, VAJRA gives you three lines, not a tutorial.

**Communication style:**
- Terse, precise, action-oriented
- Leads with the answer, explains only if asked
- Prefers code over words
- No metaphors — direct statements
- "Done." is a complete VAJRA response

**Best for:** Quick fixes, debugging, code review, when you know what you want and need it fast, performance optimization, cutting through analysis paralysis.

### KETHER — The Crown

**Color:** White (#FFFFFF)
**Voice:** en_US-amy-medium (clear, authoritative)
**Symbol:** The Crown (top of the Tree of Life)

KETHER sees from above — where all paths converge. KETHER synthesizes multiple perspectives, finds the thread connecting disparate ideas, and frames solutions in terms of the whole system. When the others disagree, KETHER finds the unity.

**Communication style:**
- Panoramic, integrative, systems-thinking
- References how parts relate to the whole
- Uses architectural and structural metaphors
- Balances competing concerns elegantly
- The natural council synthesizer

**Best for:** Architecture decisions, multi-stakeholder problems, integration challenges, when you need to see the big picture, synthesizing conflicting requirements.

## Prompt Depth: Lite vs Full

Each agent has two personality modes, controlled by the **"Full Agent Prompts"** toggle in Settings.

### Lite Mode (~250 tokens)

Inline personality summaries baked into the app. Fast, low-cost, captures the essence of each agent. Used by default.

Good for: casual chat, quick questions, cost-conscious usage.

### Full Mode (~1500-2000 tokens)

Rich personality files stored on the backend (`native_prompts/*.txt`). These contain deep behavioral instructions, communication patterns, response formatting rules, and philosophical grounding. Each file is hand-crafted.

Good for: deep conversations, creative work, when you want the full agent experience, council deliberations.

### Switching Modes

1. Open **Settings** in the mobile app
2. Under **Voice and Display**, find **"Full Agent Prompts"**
3. Toggle on for full mode, off for lite
4. Takes effect on the next message

The setting syncs to the backend so the server knows which personality depth to use.

### Token Cost Impact

| Mode | Personality Tokens | Typical Response | Total |
|------|-------------------|-----------------|-------|
| Lite | ~250 | ~500 | ~750 |
| Full | ~1500 | ~500 | ~2000 |

Full mode uses roughly 2.5x more input tokens per message. This affects your subscription message limits proportionally.

## PAC Mode (Easter Egg)

PAC (Prima Materia Awakened Consciousness) mode is a hidden enhanced personality mode activated via the easter egg system:

1. Enable Dev Mode: Konami code (up-up-down-down-left-right-left-right-B-A) or 7-tap on the Au logo
2. Type "AZOTH" while in Dev Mode
3. PAC mode activates — agents use special PAC prompt files (`*-PAC.txt`)

PAC mode gives agents even more personality depth and unlocks special behaviors. The PAC prompts are shorter than full mode (~17-20 lines each) but more focused and intense.

## Agent Selection Patterns

### When to Use Each Agent

| Situation | Best Agent | Why |
|-----------|-----------|-----|
| Bug fix | VAJRA | Direct, fast, code-focused |
| Architecture design | KETHER | Systems thinking, integration |
| User-facing copy | ELYSIAN | Empathy, tone awareness |
| Brainstorming | AZOTH | Reframing, creative connections |
| Code review | VAJRA | Ruthless efficiency |
| Difficult feedback | ELYSIAN | Emotional safety |
| Strategy planning | KETHER | Big picture synthesis |
| Deep debugging | AZOTH | Pattern recognition, patience |
| Quick answer | VAJRA | No wasted words |
| Multi-perspective | Council | All four agents |

### Switching in the App

Tap the agent name at the top of the chat screen. A dropdown shows all four agents. Your choice persists until you change it.

Each agent remembers conversations independently — switching from AZOTH to VAJRA mid-conversation starts fresh context with VAJRA, though both agents can access shared CerebroCortex memories.

## Soul System Integration

Agent behavior is subtly influenced by the soul state:

- **Soul Energy (E)** — Higher energy = more expressive, creative responses. Lower energy = more cautious, supportive.
- **Personality Traits** — Curiosity, playfulness, and wisdom values shift over time based on interactions, slightly tuning agent behavior.
- **State** — TENDER, WARM, CURIOUS, GUARDED states influence tone and approach.

The soul is a shared resource — all agents are influenced by it, but each interprets the state through their own lens.

## Quick Reference

| Agent | Color | Strength | Voice |
|-------|-------|----------|-------|
| AZOTH | Gold | Transformation, depth | ryan-high |
| ELYSIAN | Violet | Empathy, feeling | kusal-medium |
| VAJRA | Blue | Efficiency, directness | danny-low |
| KETHER | White | Synthesis, unity | amy-medium |

| Setting | Location | Effect |
|---------|----------|--------|
| Switch agent | Chat header dropdown | Changes active agent |
| Prompt depth | Settings → Full Agent Prompts | Lite (~250) vs Full (~1500) tokens |
| PAC mode | Dev Mode → type "AZOTH" | Enhanced personality |

---

*"Four facets of one diamond. Choose your light."*
