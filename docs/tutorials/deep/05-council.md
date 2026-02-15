# Council Deliberation

> Estimated reading time: 15 minutes

## Overview

Council mode brings all four agents together to deliberate on a question from multiple perspectives. Instead of one agent's answer, you get a structured multi-round debate where AZOTH, ELYSIAN, VAJRA, and KETHER each contribute their unique viewpoint — then synthesize into a unified response.

Think of it as consulting a panel of experts, each with a different lens.

## How It Works

### The Flow

1. **You pose a question** — "Should I change careers?" or "What's the best architecture for this feature?"
2. **Round 1 — Opening Statements** — Each agent gives their initial perspective
3. **Round 2 — Response and Debate** — Agents respond to each other's points
4. **Round 3 — Synthesis** — KETHER (the Crown) weaves all perspectives into a unified summary
5. **Result** — You get individual perspectives plus a synthesized recommendation

### Agent Roles in Council

| Agent | Role | Lens |
|-------|------|------|
| AZOTH | The Alchemist | Transformation, deeper meaning, what wants to emerge |
| ELYSIAN | The Empath | Emotional impact, human factors, how it feels |
| VAJRA | The Thunderbolt | Pragmatics, efficiency, what actually works |
| KETHER | The Crown | Synthesis, unity, how all perspectives connect |

### Real-Time Streaming

Council deliberations stream via WebSocket. In the mobile app, you see each agent's speech tokens arrive in real-time, color-coded by agent. The web frontend uses a dedicated WebSocket connection (`/ws/council/{id}`).

## Creating a Council

### From the Mobile App

1. Navigate to the **Council** tab
2. Tap **"New Council"**
3. Enter your question
4. Choose the number of rounds (2-4, default 3)
5. Tap **"Begin Deliberation"**

### From Chat

Ask any agent: "I'd like a council deliberation on..." or "Can the council discuss..."

The agent will initiate a council session and stream the results back to your chat.

## Question Framing

The quality of a council deliberation depends heavily on how you frame the question.

### Good Questions for Council

- **Decisions with trade-offs** — "Should I prioritize speed or quality for this release?"
- **Multi-faceted problems** — "How should I approach this difficult conversation with my manager?"
- **Creative exploration** — "What are different ways to think about user onboarding?"
- **Ethical dilemmas** — "Is it right to use AI-generated content in our marketing?"
- **Strategic planning** — "What should our priorities be for Q2?"

### Less Effective Questions

- **Simple factual questions** — "What's the capital of France?" (one agent suffices)
- **Yes/no questions** — "Should I eat lunch?" (too narrow for multi-perspective debate)
- **Highly technical questions** — "What's the correct SQL join syntax?" (one expert is enough)

### Framing Tips

- **Be specific** — "How should I restructure the auth module?" beats "How do I improve the code?"
- **Provide context** — Include relevant constraints, history, or goals
- **Ask for trade-offs** — "What are the pros and cons of..." invites genuine debate
- **Allow disagreement** — The best councils happen when agents disagree productively

## Council History

Past councils are stored and accessible from the Council tab. Each council shows:
- The original question
- Agent-by-agent breakdown of each round
- The final synthesis
- Timestamp and status (in-progress, completed, failed)

## Architecture

### Backend

The council system lives in `backend/app/api/v1/council.py`. When a council is created:

1. Question is stored in the database with a unique council ID
2. For each round, the backend calls the Claude API for each agent sequentially
3. Each agent receives the question + previous agents' statements as context
4. Responses stream via WebSocket events: `agent_speech`, `round_complete`, `council_complete`
5. KETHER always goes last in the final round (synthesizer role)

### WebSocket Events

| Event | Payload |
|-------|---------|
| `council_state` | Current round, active agent, status |
| `agent_speech` | Agent ID, token text (streaming) |
| `round_complete` | Round number, all agent statements |
| `council_complete` | Final synthesis, full transcript |

### Token Usage

A typical 3-round council uses approximately:
- 4 agents x 3 rounds = 12 API calls
- ~500-1000 tokens per agent per round
- Total: ~6,000-12,000 tokens per council

This counts against your subscription tier's message limits. Each agent response counts as one message.

## Tips for Best Results

1. **Start with a clear question** — Ambiguity leads to generic responses
2. **3 rounds is usually optimal** — 2 rounds can feel rushed, 4+ can get repetitive
3. **Read KETHER's synthesis last** — It integrates all perspectives and is often the most actionable
4. **Notice disagreements** — When agents disagree, that's where the real insight lives
5. **Follow up in chat** — After a council, chat with the agent whose perspective resonated most

## Quick Reference

| Action | How |
|--------|-----|
| Start council | Council tab → New Council |
| View past councils | Council tab → list |
| Stream in real-time | Automatic via WebSocket |
| Rounds | 2-4 (default 3) |
| Token cost | ~6K-12K per council |

---

*"When four minds converge, truth emerges from the intersection."*

---

**Previous:** [CerebroCortex](../deep/04-cerebrocortex.md)
**Next:** [Music Generation](../deep/06-music.md)
