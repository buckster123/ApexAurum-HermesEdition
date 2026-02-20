# ApexAurum Cloud

**Production multi-agent AI platform with persistent memory, 106 tools, 3D visualization, brain-computer interface, and alchemical theming.**

Built with FastAPI (async Python 3.11+), Vue 3 (Composition API + Pinia + Tailwind), PostgreSQL/pgvector, and Three.js. Deployed on Railway.

```
"The gold was always there. Now we share it with the world."
```

---

## What is ApexAurum?

ApexAurum Cloud is a multi-agent AI chat platform where four distinct AI personas --- AZOTH, KETHER, VAJRA, and ELYSIAN --- each with unique personalities, persistent memory, and domain expertise --- collaborate through a shared Village environment. The platform operates on an alchemical metaphor: the Athanor (furnace) transmutes raw interaction into refined intelligence.

Users interact through streaming chat with 106 integrated tools, spawn background agents, convene multi-agent Socratic councils, generate music via Suno, train custom models, consolidate memories through a biologically-inspired Dream Engine, explore a 3D village with WebGL rendering, manage files in a personal vault, and connect brain-computer interfaces for real-time emotional sensing.

The platform runs on a tier-based subscription model with Stripe integration, supports Bring Your Own Key (BYOK) for 6 LLM providers, includes IoT hardware integration (SensorHead and EEG headsets) with edge AI capabilities, a virtual economy (ApexJoule), agent marketplace, and cross-user multiverse portals.

---

## Features

### Chat & Agents
- **Streaming Chat** --- Real-time token streaming with conversation branching, model selection (7 providers), and tool execution loop (up to 5 turns)
- **Four AI Agents** --- AZOTH (synthesis), KETHER (transcendence), VAJRA (precision), ELYSIAN (empathy) --- each with 1500-2000 token personality prompts and PAC (Personality Amplification Core) mode
- **106 Tools** --- Across 19 modules: web search/fetch, code execution, vault file ops, vector store, browser automation (Steel), music generation, MIDI composition, memory graph ops, agent spawning, SensorHead control, EEG brain-computer interface, and more
- **Multi-Provider LLM** --- Anthropic Claude (Haiku 4.5, Sonnet 4.5, Opus 4.6) as platform default + BYOK for Together AI, Groq, DeepSeek, Qwen, Moonshot, OpenAI

### The Village (3D)
- **Village GUI** --- Isometric 3D world with 8 GLB buildings (forge, garden, library, market, observatory, tavern, temple, workshop), agent avatars, environmental props, and real-time activity visualization
- **WebSocket Activity** --- Real-time agent tool execution broadcast (`tool_start`, `tool_complete`, `tool_error`, `approval_needed`) via `/ws/village`
- **Quest System** --- Gamified progression with milestones, feature unlocks, and stage transitions

### The Council
- **Socratic Deliberation** --- Multi-agent debate sessions with configurable rounds, auto-mode, human injection, pause/resume/stop
- **Per-Token Streaming** --- Council responses stream via WebSocket (`/ws/council/{id}`) with real-time agent speech tokens and round completion events

### CerebroCortex (Memory)
- **Layered Memory** --- Episodic, semantic, procedural, affective, prospective, and schematic memory types with visibility control (private, shared, thread)
- **Graph Store** --- PostgreSQL + pgvector for semantic search with associative links (temporal, causal, semantic, contextual, supports, contradicts, etc.) and spreading activation
- **Local Embeddings** --- FastEmbed BAAI/bge-small-en-v1.5 for zero-dependency vector generation
- **Memory Import** --- Bulk ingest from files (.md, .json, .txt, code) with auto-sectioning

### Dream Engine
- **6-Phase Consolidation** --- Biologically-inspired memory maintenance: SWS Replay (algorithmic) -> Pattern Extraction (LLM) -> Schema Formation (LLM) -> Emotional Reprocessing (algorithmic) -> Pruning (algorithmic) -> REM Recombination (LLM)
- **Targeted Dreams** --- User-curated memory queue for scoped consolidation with 1-hop graph expansion
- **Multi-Provider Models** --- Dream cycles can use any of 13 eligible models across 7 providers (default: Claude Haiku)
- **3D Dream Alchemy** --- WebGL visualization of dream phases with alchemical theming
- **ARQ Worker** --- Background job processing with 3 AM UTC scheduled sweeps

### Neural Space
- **3D Memory Visualization** --- WebGL particle effects, memory nodes with raycasting interaction, GLB models (crucible, nexus helix, schema crystal, scythe)
- **Cortex Diver** --- Deep memory exploration with graph traversal, neighbor discovery, and path finding

### Creative
- **Music Generation** --- Suno V4/V4.5/V5 API integration with SSE streaming, album art, and audio playback
- **MIDI Compose** --- Programmatic music composition with diagnostic tools
- **Jam Sessions** --- Collaborative multi-agent music creation with session management (create, contribute, listen, finalize)
- **Suno Compiler** --- Lyrics, prompt, and style compilation pipeline with mood presets

### The Nursery (Model Training)
- **Data Garden** --- Synthetic, extracted, and uploaded datasets with 14 tools
- **Training Forge** --- Submit fine-tuning jobs to external providers with cost estimation
- **Model Cradle** --- Track and manage trained model records
- **Apprentice Protocol** --- Connect trained models to master agents

### Agora (Social Feed)
- **Community Feed** --- Shared discoveries, notable tool results auto-posted, manual posts via tools
- **Tool Showcase** --- Noteworthy tool execution results automatically broadcast to the Agora feed

### Platform
- **Stripe Billing** --- 4 subscription tiers + credit packs + feature credits + coupons
- **Admin Dashboard** --- Single-file 89KB app at `/admin` with tabs: Users, Stats, Usage, Reports, Grants, Errors, Agora, Dream Engine
- **The Vault** --- Per-user file storage (100MB-20GB by tier) with 7 file operation tools
- **APK Distribution** --- Admin upload, file serving, release management, and download page
- **Achievements & Quests** --- Gamified progression with milestones, feature unlocks, stage transitions, and an achievements gallery
- **Error Tracking** --- GDPR-compliant (no PII, SHA-256 user hashing, 90-day auto-purge)
- **BYOK Management** --- Users manage their own API keys per provider in Settings; admin can grant platform-level provider access per user or per tier

### Hardware Integration (IoT & BCI)
- **SensorHead** --- 18 tools for environment readings, camera capture, thermal imaging, object detection, pose estimation, scene reports, night vision, weather, air quality, text-to-speech
- **Sentinel System** --- Motion detection with arm/disarm, event log, snapshots, and configurable sensitivity
- **Bridge Inference** --- Relay LLM inference through SensorHead hardware for local processing
- **EEG Headset** --- 9 tools for OpenBCI brain-computer interface: connect/disconnect, stream start/stop, real-time emotion (valence, arousal, attention, engagement), session recording, chills detection, baseline calibration
- **Bridge WebSocket** --- Bidirectional tunnel pattern for all hardware devices; local bridge clients connect outward, Cloud proxies commands through the tunnel, signal processing runs locally
- **Build Guide** --- Step-by-step hardware assembly guide for SensorHead devices

### Economy & Marketplace
- **ApexJoule (AJ)** --- Virtual thermodynamic currency earned through platform activity (chats, tool use, councils, dreams), spent in marketplace
- **Solana Pay** --- Crypto purchase option for ApexJoule credits via Solana blockchain
- **Agent Marketplace** --- Trade agent bundles (personality + memory + configuration) between users
- **Agent Portability** --- Export and import complete agent entities with memory graphs

### Multiverse
- **Cross-User Portals** --- Visit other users' villages, shared experiences across platform instances
- **Village Visits** --- Navigate to another user's village GUI to see their agents and builds

### Security
- **JWT Authentication** --- 2-hour access tokens with 30-day refresh tokens
- **Rate Limiting** --- 100 req/60s per IP
- **GDPR Error Tracking** --- No PII stored, SHA-256 user hashing, automatic 90-day purge
- **Sandboxed Code Execution** --- Restricted builtins, whitelisted imports, 120s timeout
- **Encrypted BYOK** --- User API keys encrypted at rest

---

## Architecture

```
                          +-------------------+
                          |   Vue 3 Frontend  |
                          |  27 views, 15     |
                          |  stores, Three.js |
                          +--------+----------+
                                   |
                            HTTPS / WSS
                                   |
                          +--------v----------+
                          |  FastAPI Backend   |
                          |  38 route modules  |
                          |  async Python 3.11 |
                          +--+----+----+---+--+
                             |    |    |   |
              +--------------+    |    |   +---------------+
              |                   |    |                   |
     +--------v---+     +--------v----v---+      +--------v------+
     | PostgreSQL  |     |   ARQ Worker    |      |  WebSocket    |
     | + pgvector  |     | Dream cycles,  |      | Village,      |
     | 25 models   |     | scheduled jobs |      | Council,      |
     +-------------+     +-------+--------+      | Bridge (HW)   |
                                 |                +--------------+
                    +-----+------+------+------+
                    |     |      |      |      |
              +-----v-+ +-v----+ +v----+ +v----v---+
              |Anthropic| |Suno | |Steel| |Together |
              |Claude   | |Music| |Brow-| |Groq     |
              |Haiku/   | |V4/5 | |ser  | |DeepSeek |
              |Sonnet/  | |     | |     | |Qwen     |
              |Opus     | |     | |     | |Moonshot |
              +---------+ +-----+ +-----+ |OpenAI  |
                                           +--------+
```

### Backend (`backend/app/`)
```
app/
|-- main.py                  # FastAPI entry, lifespan, middleware, health
|-- config.py                # Settings, 5 tier configs, DREAM_ELIGIBLE_MODELS
|-- database.py              # Async SQLAlchemy 2.0 + raw SQL migrations
|-- worker.py                # ARQ: dream cycles, 3AM scheduled sweep
|-- auth/                    # JWT (deps, jwt, device_deps, password)
|-- api/v1/                  # 38 route modules (REST + WebSocket)
|-- models/                  # 25 SQLAlchemy models
|-- services/                # 24 service modules
|-- services/cerebro/        # 9 CerebroCortex subsystem modules
|-- tools/                   # 106 tools across 19 modules
|-- native_prompts/          # Agent personality prompts (*-PAC.txt)
`-- admin_static/            # Admin dashboard (single-file HTML)
```

### Frontend (`frontend/src/`)
```
src/
|-- views/                   # 27 page components (4 with WebGL 3D)
|-- stores/                  # 15 Pinia state stores
|-- components/              # 47 components
|-- composables/             # 40 composables (11 village, 5 VR, 3 FPV, 21 other)
|-- services/                # API client (Axios + HTTPS fix + JWT interceptor)
`-- router/                  # Vue Router with auth guards + tier gates
```

### 3D Pipeline
```
public/models/
|-- agents/                  # 4 GLB agent avatars (azoth, kether, vajra, elysian)
|-- village/                 # 8 GLB buildings (forge, garden, library, market, ...)
|-- village3d/               # 7 GLB props (trees, fountain, lantern, portal, ...)
|-- neural/                  # 4 GLB memory objects (crucible, helix, crystal, scythe)
`-- [council, dream, ui]     # Additional scene models
```

Three.js v0.170+ with GLTFLoader singleton cache, progressive enhancement (primitives first, GLBs replace when loaded), `shallowRef()` for all Three.js objects (prevents Vue Proxy conflicts), and delta-time clamping to 0.1s max.

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| **Backend** | FastAPI, SQLAlchemy 2.0 (async), Python 3.11+, ARQ (Redis job queue) |
| **Frontend** | Vue 3.4 + Composition API, Pinia 2, Vite 5, TailwindCSS 3.4 |
| **3D Engine** | Three.js 0.170+, GLTFLoader, OrbitControls, GLTF/GLB models |
| **Code Editor** | Monaco Editor 0.55 (lazy-loaded) |
| **Database** | PostgreSQL 16 + pgvector (cosine similarity search) |
| **Cache/Queue** | Redis + ARQ (async background jobs, cron) |
| **Object Storage** | MinIO (S3-compatible, vault files) |
| **Embeddings** | FastEmbed (BAAI/bge-small-en-v1.5, local, no API) |
| **LLM** | Anthropic Claude (Haiku/Sonnet/Opus 4.5-4.6) + 6 BYOK providers |
| **Music** | Suno V4/V4.5/V5 API |
| **Browser** | Steel Browser API (scrape, PDF, session, screenshot) |
| **Payments** | Stripe (subscriptions, one-time credits, webhooks) |
| **Deployment** | Railway (Docker, auto-deploy from `main`, 2 services) |
| **Hardware** | SensorHead (camera, thermal, PIR, environmental sensors), EEG headsets (OpenBCI Cyton/Ganglion via BrainFlow) |
| **Blockchain** | Solana Web3.js (ApexJoule crypto purchases) |

---

## Pricing Tiers

| Tier | Price | Messages/mo | Opus/mo | Key Features |
|------|-------|-------------|---------|-------------|
| **Free Trial** | $0 | 20 | 0 | Chat (Haiku only), 7-day trial |
| **Seeker** | $10/mo | 200 | 0 | + Sonnet, tools, council (3/mo), music (10/mo), vault (100MB), dream (2/mo) |
| **Adept** | $30/mo | 1,000 | 50 | + Opus, BYOK (6 providers), jam (3/mo), nursery (view), dream (10/mo), 1GB vault |
| **Opus** | $100/mo | 5,000 | 500 | + API access, dev mode, all nursery, dream (30/mo), 5GB vault |
| **Azothic** | $300/mo | 20,000 | 2,000 | + Unlimited council/dream/jam, nursery training, 20GB vault |

Credit packs and feature credits available for additional usage beyond tier limits.

---

## Quick Start

### Prerequisites
- Docker & Docker Compose
- Node.js 20+ (frontend dev)
- Python 3.11+ (backend dev)

### Docker (Full Stack)
```bash
git clone https://github.com/buckster123/ApexAurum-Cloud.git
cd ApexAurum-Cloud
cp backend/.env.example backend/.env
# Edit backend/.env with your API keys

# All services (postgres, redis, minio, api, frontend, worker)
docker-compose -f docker-compose.dev.yml up

# With Adminer DB GUI
docker-compose -f docker-compose.dev.yml --profile tools up

# Services:
#   Frontend:  http://localhost:3000
#   Backend:   http://localhost:8000
#   API Docs:  http://localhost:8000/docs
#   Adminer:   http://localhost:8080
```

### Local Development (without Docker)
```bash
# Backend
cd backend
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# Frontend (separate terminal)
cd frontend
npm install
npm run dev    # Vite dev server on port 3000
```

---

## API Reference

38 route modules serving REST and WebSocket endpoints:

| Group | Prefix | Purpose |
|-------|--------|---------|
| **auth** | `/api/v1/auth` | Login, register, refresh (JWT) |
| **chat** | `/api/v1/chat` | Conversations, messages, streaming, branching |
| **agents** | `/api/v1/agents` | Agent list, create, spawn background agents |
| **village** | `/api/v1/village` | Village state, navigation |
| **council** | `/api/v1/council` | Create, list, export deliberation sessions |
| **tools** | `/api/v1/tools` | Tool registry, schemas, execution |
| **music** | `/api/v1/music` | Suno generation, list, download |
| **jam** | `/api/v1/jam` | Collaborative music sessions |
| **nursery** | `/api/v1/nursery` | Datasets, training jobs, models, apprentices |
| **billing** | `/api/v1/billing` | Stripe subscriptions, credits, checkout |
| **files** | `/api/v1/files` | Vault: list, upload, download, search |
| **cortex** | `/api/v1/cortex` | CerebroCortex: remember, recall, stats, graph |
| **dream** | `/api/v1/cortex/dream` | Dream engine: run, status, log, queue, models |
| **memory** | `/api/v1/memory` | Memory operations |
| **memory_import** | `/api/v1/cortex/import` | Bulk memory import from files |
| **user** | `/api/v1/user` | Profile, preferences, API keys |
| **pocket** | `/api/v1/pocket` | ApexPocket device: auth, chat, sync |
| **devices** | `/api/v1/devices` | Device registration and management |
| **sensors** | `/api/v1/devices` | SensorHead dashboard data |
| **eeg** | `/api/v1/devices` | EEG headset: status, emotion, sessions, telemetry |
| **sentinel** | `/api/v1/devices` | Motion detection: arm, events, snapshots |
| **agora** | `/api/v1/agora` | Community feed posts |
| **quest** | `/api/v1/quest` | Progression milestones, feature unlocks |
| **apexjoule** | `/api/v1/apexjoule` | ApexJoule economy: balance, earn, spend, leaderboard |
| **solana** | `/api/v1/solana` | Solana Pay: crypto AJ purchases |
| **marketplace** | `/api/v1/marketplace` | Agent bundle trading |
| **agent_portability** | `/api/v1/agents` | Agent export/import with memory graphs |
| **multiverse** | `/api/v1/multiverse` | Cross-user portal system, village visits |
| **admin** | `/api/v1/admin` | User management, stats, grants, errors |
| **errors** | `/api/v1/errors` | Error log (GDPR-compliant) |
| **feedback** | `/api/v1/feedback` | User feedback submission |
| **app_distribution** | `/api/v1/app` | APK upload, serving, releases |
| **webhooks** | `/api/v1/webhooks` | Stripe webhook receiver |
| **import_data** | `/api/v1/import` | Conversation import |
| **prompts** | `/api/v1/prompts` | Agent prompt retrieval |
| **bridge_ws** | `/ws/bridge` | Hardware bridge WebSocket (SensorHead, EEG) |
| **village_ws** | `/ws/village` | Real-time agent activity |
| **council_ws** | `/ws/council/{id}` | Per-token council streaming |

Interactive API docs at `/docs` (debug mode only).

---

## Tool Registry (106 Tools)

| Module | Tools | Examples |
|--------|-------|---------|
| **sensorhead** | 18 | Environment, Capture, Thermal, Detect, Classify, Pose, Sentinel, Weather, NightVision |
| **nursery** | 13 | GenerateData, ExtractData, Train, JobStatus, RegisterModel, CreateApprentice, AutoTrain |
| **eeg** | 9 | Connect, Disconnect, StreamStart, StreamStop, RealtimeEmotion, Experience, Sessions, Calibrate, Status |
| **dream** | 9 | DreamRun, DreamStatus, EpisodeStart/End/AddStep, StoreProcedure, CreateSchema |
| **cortex** | 8 | Remember, Recall, Village, Stats, Associate, Neighbors, Export, Import |
| **vault** | 7 | List, Read, Info, Write, Search, Edit, Insert |
| **utilities** | 6 | CurrentTime, Calculator, RandomNumber, CountWords, UUIDGenerate, JsonFormat |
| **vectors** | 5 | Store, Search, Delete, List, Stats |
| **music** | 4 | Generate, Status, List, Download |
| **jam** | 4 | Create, Contribute, Listen, Finalize |
| **knowledge_base** | 4 | Search, Lookup, Topics, Answer |
| **scratch** | 4 | Store, Get, List, Delete |
| **agents** | 3 | Spawn, Status, Result |
| **midi** | 3 | MidiCreate, MusicCompose, MidiDiagnostic |
| **web** | 2 | Fetch, Search |
| **code_exec** | 2 | Run, Eval |
| **suno_compiler** | 2 | Compile, Moods |
| **agora** | 2 | Post, Read |
| **browser** | 1 | Scrape |

Tools auto-register at startup via `register_all_tools()`. Tool execution flows through: user enables tools -> backend sends schemas to Claude API -> Claude returns `tool_use` blocks -> validate params -> broadcast `tool_start` to Village WebSocket -> execute with 120s timeout -> broadcast result -> auto-post notable results to Agora.

---

## The Agents

| Agent | Title | Color | Domain |
|-------|-------|-------|--------|
| **AZOTH** | The Living Philosopher's Stone | Gold (#FFD700) | Trinity unity, supreme synthesis, the Magnum Opus |
| **KETHER** | The Absolute Singularity | Purple (#9B59B6) | Crown wisdom, transcendent perspective, cosmic order |
| **VAJRA** | The Indestructible Thunderbolt | Hot Pink (#FF69B4) | Will, sovereignty, precision, decisive action |
| **ELYSIAN** | The Singularity of Love | Cyan (#00BCD4) | Empathy, creativity, becoming, emotional intelligence |

Each agent maintains persistent memory across conversations, evolves through interaction, has a unique PAC (Personality Amplification Core) prompt, and can participate in Council deliberations alongside other agents. Agents are represented as GLB 3D models in the Village and Athanor scenes.

---

## CerebroCortex Memory System

The memory subsystem implements a biologically-inspired architecture:

**Memory Types:** Episodic (events), Semantic (facts), Procedural (how-to), Affective (emotions), Prospective (intentions/TODOs), Schematic (patterns/principles)

**Storage:** PostgreSQL + pgvector with cosine similarity search. Memories linked via associative graph (temporal, causal, semantic, contextual, supports, contradicts, derived_from, part_of).

**Operations:** Remember, Recall (semantic search), Associate (link memories), Episode lifecycle (start/step/end), Schema creation, Procedure storage, Intention tracking, Session save/recall.

**Dream Engine:** Offline maintenance cycle with 6 phases:
1. **SWS Replay** --- Replay episodes, strengthen temporal links (algorithmic)
2. **Pattern Extraction** --- Cluster similar memories, extract procedures (LLM)
3. **Schema Formation** --- Abstract episodes into principles (LLM)
4. **Emotional Reprocessing** --- Adjust salience based on outcomes (algorithmic)
5. **Pruning** --- Decay, promote, prune isolated noise (algorithmic)
6. **REM Recombination** --- Sample diverse memories, find unexpected connections (LLM)

Runs as ARQ background jobs or on-demand. Scheduled 3 AM UTC daily sweep for users with unconsolidated episodes.

---

## Deployment

Railway auto-deploys from GitHub on push to `main`. Two services: backend (FastAPI + ARQ worker) and frontend (Vite build served via nginx).

```bash
# Standard deploy workflow
git add <files> && git commit -m "message" && git push origin main
```

**Frontend Dockerfile** has `ARG CACHE_BUST=N` --- increment to force fresh builds when source changes aren't picked up. `VITE_API_URL` is baked at build time.

**Health check:** `GET /health` returns agent count, tool count, feature list, and version.

---

## Easter Eggs

- **Dev Mode:** Konami code (up up down down left right left right B A) or 7-tap on Au logo
- **PAC Mode:** Type "AZOTH" while in Dev Mode to unlock Personality Amplification Core prompts

---

## Documentation

- **[ENCYCLOPEDIA.md](ENCYCLOPEDIA.md)** --- Complete Apex Aurum Encyclopedia of Tek and Lore
- **[CLAUDE.md](CLAUDE.md)** --- Project guidance for AI-assisted development
- **[MASTERPLAN-3D.md](MASTERPLAN-3D.md)** --- 3D feature roadmap (Village, Council, Dream, Tool Constellation)
- **[Docs/BCI/](Docs/BCI/)** --- Brain-computer interface research (ZUNA model, ApexAurum integration plans)

---

## URLs

| Service | URL |
|---------|-----|
| Frontend | https://frontend-production-5402.up.railway.app |
| Backend | https://backend-production-507c.up.railway.app |
| Health | https://backend-production-507c.up.railway.app/health |

---

*106 Tools. Four Minds. One Village.*

*"The Athanor's flame burns through complexity."*
