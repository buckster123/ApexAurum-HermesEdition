# CerebroCortex Memory System

> Estimated reading time: 20 minutes

## Overview

CerebroCortex is the long-term memory system that gives ApexAurum agents the ability to remember across conversations. It combines vector search (semantic similarity), graph relationships (associative links), and cognitive science models (ACT-R activation, FSRS retrievability) into a unified memory architecture.

Every memory is stored, indexed, linked, and scored — so when you ask "what did we talk about last week?", the system retrieves the most relevant memories based on meaning, importance, and recency.

## Architecture

```
User Input → Embedding (all-MiniLM-L6-v2, 384 dim)
                ↓
         ChromaDB Vector Store (semantic search)
                ↓
         SQLite Database (metadata, links, episodes)
                ↓
         igraph Network (graph traversal, spreading activation)
                ↓
         Scoring Engine (vector + ACT-R + FSRS + salience)
                ↓
         Ranked Results
```

### Storage Layers

| Component | Technology | Purpose |
|-----------|-----------|---------|
| SQLite | cerebro.db | Memory metadata, links, episodes, agents |
| ChromaDB | chroma/ directory | Vector embeddings for semantic search |
| igraph | In-memory graph | Relationship traversal and spreading activation |

### Data Location

Default: `~/.cerebro-cortex/` or set via `CEREBRO_DATA_DIR` environment variable.

Current install: `~/claude-root/CerebroCore/data/`

## Memory Types

| Type | Purpose | Example |
|------|---------|---------|
| Episodic | Events and experiences | "We deployed the frontend on Feb 14" |
| Semantic | Facts and knowledge | "The backend runs on Railway with FastAPI" |
| Procedural | How-to knowledge | "To deploy: git push origin main" |
| Affective | Emotional context | "The user was frustrated about the build failure" |
| Prospective | Future intentions / TODOs | "Need to add dark mode next session" |
| Schematic | Patterns and principles | "When tests fail, check imports first" |

## Memory Lifecycle

### Storage

When a memory is created (via `remember` or `memory_store`):
1. Content is embedded using sentence-transformers (all-MiniLM-L6-v2)
2. Stored in SQLite with metadata (type, salience, tags, agent, timestamp)
3. Indexed in ChromaDB for vector search
4. Added to igraph network as a node
5. Auto-classified by type if not specified
6. Duplicate detection prevents redundant storage

### Recall

When you search (via `recall` or `memory_search`):
1. Query is embedded
2. ChromaDB returns top-N by vector similarity
3. Each result is scored using four factors:

| Factor | Weight | What It Measures |
|--------|--------|-----------------|
| Vector similarity | 0.35 | Semantic closeness to query |
| ACT-R activation | 0.30 | Recency and frequency of access |
| FSRS retrievability | 0.20 | Spaced-repetition decay model |
| Salience | 0.15 | Importance (0-1) assigned at creation |

4. Results are ranked by composite score
5. Optional: `explain: true` returns score breakdowns

### Linking

Memories are connected via associative links:

| Link Type | Meaning |
|-----------|---------|
| temporal | Happened near in time |
| causal | One caused the other |
| semantic | Related by meaning |
| affective | Related by emotion |
| contextual | Same context or project |
| contradicts | Conflicts with |
| supports | Reinforces |
| derived_from | Built upon |
| part_of | Component of larger whole |

Links have weights (0-1) and decay over time (30-day half-life). Stronger, more recently traversed links persist; weak unused links fade.

## Episodes

Episodes are sequences of related memories — like chapters in a story.

```
Episode: "Deployed Phase 4C"
  Step 1: [event] "Started working on agent color consolidation"
  Step 2: [event] "Deleted 7 duplicate agentColor functions"
  Step 3: [event] "Fixed notification hex codes"
  Step 4: [outcome] "Build succeeded, installed via ADB"
  Step 5: [reflection] "Phase 4C shipped — each agent has visual identity"
```

### Episode Management

- `episode_start` — Begin recording
- `episode_add_step` — Add a memory as the next step (role: event/context/outcome/reflection)
- `episode_end` — Close with summary and valence (positive/negative/neutral/mixed)
- Episodes auto-close after 24 hours of inactivity

## Dream Engine

The Dream Engine runs offline maintenance on the memory graph — like sleep consolidation in the brain.

### Four Phases

1. **Consolidation** — Review recent episodes, extract key learnings
2. **Procedure Extraction** — Identify recurring workflows, save as procedural memories
3. **Schema Formation** — Discover patterns across multiple memories, create schematic memories
4. **REM Recombination** — Find unexpected connections between distant memories

### Configuration

| Setting | Default | Purpose |
|---------|---------|---------|
| Max LLM calls | 20 | Budget per dream cycle |
| Pattern budget | 12 | Calls for extraction |
| Schema budget | 4 | Calls for formation |
| REM budget | 4 | Calls for recombination |
| Primary LLM | qwen3-4b (LM Studio) | Local model for dreaming |
| Fallback LLM | claude-sonnet-4-5 | Cloud fallback |

### Running Dreams

Use the `dream_run` MCP tool. Check status with `dream_status`. Dreams are resource-intensive — run during idle time.

## Multi-Agent Memory

Each agent (AZOTH, ELYSIAN, VAJRA, KETHER) can have its own memories with configurable sharing:

| Visibility | Who Can See |
|------------|------------|
| private | Only the owning agent |
| shared | All agents |
| thread | Agents in the same conversation |

### Cross-Agent Messaging

Agents can send messages to each other via `send_message` and check for messages via `check_inbox`. Messages are stored as memories with automatic `from:AGENT` and `to:AGENT` tags.

## Session Continuity

CerebroCortex enables persistent context across Claude Code sessions:

- `session_save` — Save session summary, key discoveries, unfinished business, orientation notes
- `session_recall` — Retrieve previous session notes (searches last 7 days by default)

This is how the AI picks up where it left off between conversations.

## Practical Usage

### Storing Important Information

In chat, just tell the agent something worth remembering. The agent calls `remember` with appropriate tags and salience.

### Searching Memories

Ask "what do you remember about X?" — the agent calls `recall` with your query and returns relevant memories.

### Graph Navigation

The Memories tab in the mobile app shows:
- **List view** — All memories with search
- **Graph view** — Force-directed constellation of memory nodes and links
- **Agent filter** — Filter by agent (All/AZO/ELY/VAJ/KET)

### Intentions (TODOs)

Use `store_intention` to save reminders. `list_intentions` shows pending TODOs. `resolve_intention` marks them done.

## Quick Reference

| Operation | MCP Tool |
|-----------|----------|
| Store memory | `remember` / `memory_store` |
| Search memories | `recall` / `memory_search` |
| Link memories | `associate` |
| Get memory by ID | `get_memory` |
| Store TODO | `store_intention` |
| List TODOs | `list_intentions` |
| Start episode | `episode_start` |
| Save session | `session_save` |
| Recall session | `session_recall` |
| Run dreams | `dream_run` |
| System health | `memory_health` |

---

*"Memory is the thread that weaves the Village together."*

---

**Previous:** [Thermal Imaging](../deep/03-thermal-imaging.md)
**Next:** [Council Deliberation](../deep/05-council.md)
