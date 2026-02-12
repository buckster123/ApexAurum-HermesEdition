# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Session Start Protocol

On every session start:
1. Call `mcp__cerebro-cortex__session_recall` to retrieve previous session notes.
2. Read any `unfinished_business` or `if_disoriented` instructions for context.
3. Continue where the previous session left off.

## Session End Protocol

Before ending a session, call `mcp__cerebro-cortex__session_save` with:
- `session_summary`: What was accomplished this session
- `key_discoveries`: Important findings or bugs fixed
- `unfinished_business`: What's left to do next session
- `if_disoriented`: How to get back on track (key files, recent changes)
- `priority`: HIGH / MEDIUM / LOW

## Project Overview

ApexAurum Cloud is a production multi-agent AI chat platform deployed on Railway. Four AI personas (AZOTH, KETHER, VAJRA, ELYSIAN) collaborate in a shared Village environment with 50+ tools, streaming chat, music generation, model training, and file vault storage.

**Stack:** FastAPI (async Python 3.11+) + Vue 3 (Composition API + Pinia + Tailwind) + PostgreSQL/pgvector + Stripe billing

## Development Commands

### Frontend (`frontend/`)
```bash
npm run dev          # Vite dev server (port 3000)
npm run build        # Production build
npm run lint         # ESLint with auto-fix (.vue, .js, .jsx, .cjs, .mjs)
npm run format       # Prettier formatting (src/)
```

### Backend (`backend/`)
```bash
# Local development
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# Production (Railway uses $PORT)
python -u -m uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

### Docker (Full Stack)
```bash
docker-compose -f docker-compose.dev.yml up                    # All services
docker-compose -f docker-compose.dev.yml --profile tools up    # + Adminer DB GUI
```
Services: postgres (pgvector:pg16), redis, minio (S3), api (FastAPI), frontend (Vite), worker (ARQ)

### Health Check
```bash
curl -s https://backend-production-507c.up.railway.app/health | python3 -m json.tool
```

## Deployment

**Railway auto-deploys from GitHub on push to `main`.** Every push triggers builds for both services.

```bash
# Standard workflow
git add <changed files> && git commit -m "message" && git push origin main
```

**Cache Busting:** Frontend Dockerfile has `ARG CACHE_BUST=N` (currently 30). Increment to force fresh builds when source changes aren't picked up.

**VITE_API_URL is baked at build time** - frontend Dockerfile hardcodes the backend URL as a build arg. Changes to the backend URL require a frontend rebuild.

**Railway IDs** (for manual GraphQL deploys when auto-deploy fails):
- Backend service: `9d60ca55-a937-4b17-8ec4-3fb34ac3d47e`
- Frontend service: `6cf1f965-94df-4ea0-96ca-d82959e2d3c5`
- Environment: `2e9882b4-9b33-4233-9376-5b5342739e74`
- Token: `90fb849e-af7b-4ea5-8474-d57d8802a368`

## Architecture

### Backend (`backend/app/`)

**Entry:** `main.py` - FastAPI app with lifespan startup (DB init, tool registration, migrations), CORS middleware, error tracking middleware, rate limiting (100 req/60s per IP).

**Key modules:**
- `api/v1/` - 26 route files. Chat streaming in `chat.py`, JWT auth in `auth.py`, Stripe in `billing.py`/`webhooks.py`
- `services/` - 24 service modules. `llm_provider.py` (multi-provider LLM), `billing.py` (usage tracking), `village_events.py` (WebSocket broadcaster), `error_tracking.py` (GDPR-compliant, 90-day auto-purge)
- `tools/` - 50+ tools across 16 modules registered via singleton `ToolRegistry`. Tools auto-register on import at startup via `register_all_tools()`
- `models/` - 23 SQLAlchemy model files. Users, conversations, messages (branching via parent_id), agents, billing, music, vault, error logs
- `native_prompts/` - Agent personality prompt files (`*-PAC.txt`)

**Tool execution flow:** User enables tools in chat → backend sends tool schemas to Claude API (filtered by tier) → Claude returns `tool_use` blocks → for each: validate params → broadcast `tool_start` to Village WebSocket → execute with 120s timeout → broadcast result → auto-post notable results to Agora feed.

**Database:** Async SQLAlchemy 2.0 + Alembic migrations + init-time raw SQL in `database.py`. Uses `get_db_context()` for standalone DB access outside request lifecycle.

### Frontend (`frontend/src/`)

**Build:** Vite 5 + Vue 3.4 + Vue Router 4 + Pinia stores + Tailwind CSS + Monaco Editor + Three.js (Village 3D, Neural 3D, Dream 3D)

**Key modules:**
- `stores/` - 13 Pinia stores managing chat, auth, billing, agents, music, council, village, dream state
- `views/` - 20 page components (Chat, Village, Council, Music, Jam, Agora, Billing, Files, Nursery, Dream, Settings, etc.)
- `services/api.js` - Axios client with HTTPS auto-prefix, JWT interceptor, graceful 401 handling
- `composables/useThreeScene.js` - Three.js scene lifecycle, animation loop, raycasting, camera focus
- `composables/useAgentModels.js` - GLTFLoader singleton cache for agent avatar GLBs
- `composables/useDevMode.js` - Konami code and AZOTH incantation activation
- `router/index.js` - Auth guards, tier-gated routes

### WebSockets

- **Village** (`/ws/village`) - Real-time agent activity visualization. Auth via JWT query param. Events: `tool_start`, `tool_complete`, `tool_error`, `approval_needed`
- **Council** (`/ws/council/{id}`) - Streaming multi-agent deliberation. SSE-style. Events: state updates, agent speech tokens, round completion

### Admin Dashboard

**Edit `backend/admin_static/index.html`** (NOT `admin/index.html`). Single-file 89KB app served from Docker. Requires `is_admin=true`. Tabs: Users, Stats, Usage, Reports, Grants, Errors, Agora, Dream Engine.

### 3D Pipeline (Blender MCP)

**Architecture:** Blender (Windows, LAN at 192.168.0.104:9876) -> MCP Server (Pi) -> Claude Code. Models generated via Hyper3D Rodin, PolyHaven, Sketchfab, or BlenderKit, exported as GLB, transferred via HTTP (port 9880), loaded in Vue with GLTFLoader.

**Key composables:**
- `useThreeScene.js` - Scene lifecycle (init, animate, dispose), OrbitControls, raycasting, camera focus
- `useAgentModels.js` - GLTFLoader singleton cache, auto-scaling clones, progressive enhancement
- `useNeuralAmbient.js` - Particle effects for Neural Space
- `usePixelSprites.js` - Retro 16x24 pixel sprites for Village 2D mode

**Three.js patterns:**
- Always use `shallowRef()` for Three.js objects (prevents Vue Proxy conflicts)
- GLB models in `frontend/public/models/` (agents, village, council, dream, ui)
- Progressive enhancement: primitives first, GLBs replace when loaded
- `findMemoryNode()` walks parent chain for raycasting Groups (GLB clones)
- Delta time clamped to 0.1s max (prevents physics explosion after tab switch)

**File transfer (Windows Blender -> Pi):** Export to Windows Desktop, serve via `http.server` with `translate_path` override on port 9880, download via curl. See `BLENDER-SKILL.md` at `/home/hailo/claude-root/Projects/airlock/BLENDER-SKILL.md`.

**3D Masterplan:** See `MASTERPLAN-3D.md` for the 6-feature roadmap (Landing Hero, Village Buildings, Council Chamber, Dream Alchemy, Tool Constellation, Alchemical Loader).

## Key Patterns

**HTTPS Fix** (must exist in both `api.js` and `chat.js`):
```javascript
let apiUrl = import.meta.env.VITE_API_URL || ''
if (apiUrl && !apiUrl.startsWith('http://') && !apiUrl.startsWith('https://')) {
  apiUrl = 'https://' + apiUrl
}
```

**Token Validation** (`auth.js`):
```javascript
function getValidToken(key) {
  const value = localStorage.getItem(key)
  if (!value || value === 'undefined' || value === 'null') {
    if (value) localStorage.removeItem(key)
    return null
  }
  return value
}
```

**Platform API Key:** Backend uses its own Anthropic key when user has no BYOK configured. BYOK is optional, supports: Together, Groq, DeepSeek, Qwen, Moonshot.

**Tier enforcement:** Checked in `services/billing.py` and `services/usage.py`. Models, tools, and features gated by subscription tier.

## Pricing Tiers

| Tier | ID | Price | Messages | Models |
|------|----|-------|----------|--------|
| Seeker | seeker | $10/mo | 200 | Haiku, Sonnet |
| Adept | adept | $30/mo | 1,000 | All + 50 Opus/mo |
| Opus | opus | $100/mo | 5,000 | All + 500 Opus/mo |
| Azothic | azothic | $300/mo | 20,000 | All + 2,000 Opus/mo |

## Common Issues & Solutions

| Issue | Solution |
|-------|----------|
| "Not authenticated" | Use `get_current_user_optional` for testing |
| Deploy succeeds but old code | Increment `CACHE_BUST` in frontend Dockerfile |
| TDZ error in frontend | Move refs/functions BEFORE watchers with `immediate: true` |
| API returning HTML | Check `https://` prefix in VITE_API_URL |
| "undefined" in localStorage | Auth store auto-cleans bad values |
| 402 Payment Required | Check user's subscription tier and message limits |
| 403 Forbidden | User's tier doesn't allow the model/tools requested |
| Tool timeout | Default 120s in config. Check `tool_execution_timeout` setting |
| WebSocket auth failure | JWT passed as query param, verify token isn't expired |
| DB session conflicts | Use `get_db_context()` for concurrent/isolated operations |

## Easter Eggs

- **Dev Mode:** Konami code (↑↑↓↓←→←→BA) or 7-tap on Au logo
- **PAC Mode:** Type "AZOTH" while in Dev Mode
- **PAC prompts:** `backend/native_prompts/*-PAC.txt`

## URLs

- Frontend: https://frontend-production-5402.up.railway.app
- Backend: https://backend-production-507c.up.railway.app
- API Docs: https://backend-production-507c.up.railway.app/docs (debug mode only)

## Session Continuity

**Handled by CerebroCortex MCP** (`cerebro-cortex`). Session notes stored in the cortex memory system and recalled automatically at session start.

---

*"The Athanor's flame burns through complexity."*
