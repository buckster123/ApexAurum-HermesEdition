# ApexAurum Cloud — Infrastructure Simplification Plan (Local-Only Mode)

**Date:** 2026-05-14
**Scope:** Convert cloud-native stack (FastAPI + PostgreSQL + Redis + Minio + ARQ + Stripe + Solana) to a simplified local-first deployment.

---

## Executive Summary

The codebase is already closer to local-only than it appears. **The Vault uses local filesystem already.** S3/Minio is configured but unused. Rate limiting is in-memory. The biggest blockers are: (1) PostgreSQL-specific raw SQL migrations and pgvector dependency, (2) ARQ worker dependency on Redis for dream cycles, (3) no direct local LLM endpoint provider in the LLM registry, and (4) deeply embedded Stripe/Solana billing assumptions.

**Recommended path:** Keep PostgreSQL via Docker (lightest lift), strip Redis/Minio, make billing optional, add local LLM providers, and make auth optional for LAN.

---

## 1. Database Simplification

### Option A: Keep PostgreSQL via Docker (RECOMMENDED)
- **Effort:** Minimal
- **What to do:** Keep the existing `postgres` service in docker-compose. Remove Redis and Minio dependencies.
- **Why:** The codebase uses extensive PostgreSQL-specific raw SQL that would be painful to port:
  - `database.py` init migrations: `DO $$ ... $$` PL/pgSQL blocks, `information_schema` queries, `RAISE NOTICE`, `jsonb` casts, `TIMESTAMP WITH TIME ZONE`, `NOW()`
  - `tools/vectors.py`: pgvector `<=>` operator for cosine distance
  - `api/v1/cortex.py`: `pgvector_extension` health check
  - `api/v1/admin.py`: `INTERVAL` arithmetic, `jsonb_array_length`
  - `api/v1/pocket.py`, `api/v1/athaverse.py`: `sqlalchemy.dialects.postgresql.ARRAY`
  - `models/vector.py`: `UserVector` commented out; vectors are raw SQL only
  - Cerebro memory (`pg_graph_store.py`): PostgreSQL-only raw SQL with `jsonb` and `vector` casts
- **Alembic:** Currently configured for async PostgreSQL. Would need full rewrite for SQLite.

### Option B: Migrate to SQLite + Optional PG
- **Effort:** High (2-3 weeks)
- **What breaks with SQLite:**
  1. **asyncpg driver** → swap to `aiosqlite` + `sqlalchemy[asyncio]`
  2. **pgvector extension** → SQLite has no native vector type. Options:
     - Use `sqlite-vec` extension (requires compilation)
     - Store embeddings as BLOB/text and do cosine similarity in Python (slow, but works for small local datasets)
     - Disable vector search entirely in local mode
  3. **Raw SQL migrations in `database.py`** (~1,400 lines):
     - `DO $$` blocks (PL/pgSQL) → SQLite does not support. Must rewrite as Python migration logic or skip.
     - `information_schema.columns` → SQLite uses `PRAGMA table_info(...)`
     - `CREATE EXTENSION IF NOT EXISTS vector` → noop on SQLite
     - `jsonb` casts → SQLite uses plain `json` (functions are mostly compatible: `json()`, `json_array_length`)
     - `gen_random_uuid()` → SQLite `uuid` generation requires `uuid()` extension or app-side UUIDs
     - `TIMESTAMP WITH TIME ZONE` → SQLite has no native timezone-aware datetime; store as ISO strings or UTC floats
     - `NOW()` → SQLite `datetime('now')`
     - `INTERVAL` math → SQLite `datetime('now', '-30 days')`
  4. **Vector tools (`tools/vectors.py`)**:
     - `embedding <=> :embedding` (pgvector distance) → compute in Python or use `sqlite-vec`
     - `RETURNING id` → SQLite 3.35+ supports this, but async drivers may vary
  5. **`pg_graph_store.py` (Cerebro)**:
     - Heavy use of `jsonb` casts and `vector` type. Would need abstraction layer.
  6. **Alembic:** `async_engine_from_config` with `NullPool` and offline mode would need `aiosqlite` dialect.

### Migration Path (if Option B is chosen later)
1. Add `aiosqlite` to requirements
2. Refactor `database.py` to abstract SQL dialect:
   - Detect driver from `database_url`
   - Skip `DO $$` blocks on SQLite
   - Replace `information_schema` queries with `PRAGMA table_info`
   - Use `datetime('now')` instead of `NOW()`
   - Store JSON as TEXT without `jsonb` cast
3. Add a `VectorBackend` abstraction:
   - `PgVectorBackend` (existing)
   - `PythonVectorBackend` (cosine sim in memory)
   - `SqliteVecBackend` (if sqlite-vec is available)
4. Update `config.py` `async_database_url` property to handle `sqlite+aiosqlite://`
5. Update `database.py` engine creation to skip `pool_size`, `max_overflow`, `pool_recycle` for SQLite

**VERDICT:** Keep PostgreSQL via Docker for now. It is the single container that unlocks everything else. The simplification wins are bigger elsewhere.

---

## 2. Auth Simplification

### Current State
- JWT Bearer auth with access/refresh tokens (2h / 30d)
- `HTTPBearer(auto_error=False)` for optional auth
- Frontend stores tokens in `localStorage`, has refresh interceptor
- `get_current_user` is used on nearly every endpoint
- Admin auto-created from `INITIAL_ADMIN_EMAIL` env var on startup

### Option A: Keep JWT but Single-User Default (RECOMMENDED)
- **What to do:**
  - On startup, auto-create a single default user (e.g., `local@apexaurum.local`) with a fixed or generated password
  - Expose a `/auth/local-token` endpoint that returns a long-lived token (e.g., 1 year) for the default user without requiring credentials
  - Frontend: if `VITE_LOCAL_MODE=true`, call `/auth/local-token` on first load and store the token
- **Pros:** Zero changes to auth deps, endpoints remain protected, works with existing `get_current_user`
- **Cons:** Still carries JWT complexity

### Option B: Simplify to API Key Only
- **What to do:**
  - Replace JWT with a single `X-API-Key` header
  - Store key in `localStorage` or env var
  - `get_current_user` looks up user by API key hash
- **Pros:** Simpler than JWT refresh dance
- **Cons:** Need to rewrite auth deps, frontend interceptors, and all secured endpoints' dependency declarations

### Option C: Optional No-Auth for LAN
- **What to do:**
  - Add `LOCAL_MODE=true` env var
  - Create `get_current_user_local()` dependency that:
    - If `LOCAL_MODE=true`, returns the default user without checking headers
    - Otherwise, delegates to existing JWT logic
  - Swap `Depends(get_current_user)` → `Depends(get_current_user_local)` globally (or via a router wrapper)
- **Pros:** Cleanest UX for LAN — open the app and it just works
- **Cons:** Slightly invasive dependency swap; must be careful not to leak into production builds

### Concrete Recommendation
**Implement Option A + Option C hybrid:**
1. Add `LOCAL_MODE: bool = False` to `Settings`
2. Add `local_default_user_email: str = "local@apexaurum.local"` and `local_default_user_password: str = "apex"` (or generate)
3. In `main.py` lifespan, if `LOCAL_MODE=True`, ensure the default user exists and print credentials to console
4. Add endpoint `POST /auth/local` → returns a long-lived JWT for the default user (no body required if LOCAL_MODE)
5. In `auth/deps.py`, add:
   ```python
   async def get_current_user_local(...):
       if settings.local_mode:
           return await get_or_create_default_user(db)
       return await get_current_user(...)
   ```
6. Frontend: if `import.meta.env.VITE_LOCAL_MODE`, auto-call `/auth/local` on app mount and suppress login UI
7. **Do NOT remove JWT entirely** — the billing/tier system, admin checks, and user-specific data (vault, conversations) all assume a `User` model exists.

---

## 3. Storage Simplification

### Current State
- **The Vault** (`backend/app/api/v1/files.py`) already stores files on **local filesystem**:
  - Path: `settings.vault_path / "users" / {user_id} / "files"`
  - Default `vault_path: str = "/data"` (Railway volume)
  - For local: change to `./data` or `~/.apexaurum/data`
- **S3/Minio** is configured in `config.py` (`s3_endpoint`, `s3_access_key`, etc.) but **never referenced in code**
- `boto3` is commented out in `requirements.txt`

### Action Items
1. **Remove Minio from docker-compose.dev.yml** entirely
2. **Remove S3 config** from `config.py` (or leave as optional but document unused)
3. **Update `vault_path` default** for local mode:
   ```python
   vault_path: str = os.getenv("APEX_VAULT_PATH", "./data")
   ```
4. **Add to `.gitignore`:** `/data`, `/.apexaurum`
5. No code changes needed in `files.py` — it already uses `Path` and `shutil`

---

## 4. Redis Removal

### Current State
- **Requirements:** `redis` and `arq` are **commented out** in `requirements.txt`
- **Docker:** `redis` service is defined in `docker-compose.dev.yml`
- **Code references to Redis:**
  - `backend/app/worker.py` — imports `arq`, `RedisSettings`, uses `ctx["redis"].enqueue_job()`
  - `backend/app/api/v1/dream.py` — `create_pool(RedisSettings.from_dsn(...))` for queuing dream cycles
  - `backend/app/api/v1/pocket.py` — same pattern for pocket jobs
  - `backend/app/config.py` — `redis_url: str = "redis://localhost:6379/0"`

### What uses Redis?
1. **ARQ Worker** (`worker.py`):
   - `run_dream_cycle` — Cerebro dream consolidation
   - `run_targeted_dream_cycle` — targeted dream for specific memories
   - `scheduled_dream_sweep` — cron job at 3 AM to queue dream cycles
2. **Dream API** (`api/v1/dream.py`):
   - Enqueues dream jobs via ARQ pool
3. **Pocket API** (`api/v1/pocket.py`):
   - Enqueues background jobs

### Can we remove Redis entirely?
**Yes, with a replacement for background job execution.**

Options:
1. **In-process background tasks** (RECOMMENDED for local):
   - Use `asyncio.create_task()` for fire-and-forget dream cycles
   - Add a simple `BackgroundTaskManager` singleton that tracks running tasks
   - For scheduled sweeps, add an `asyncio` cron-like loop in lifespan
   - Pros: Zero new dependencies, works fine for single-user local
   - Cons: Tasks die on restart, no persistence, no distributed queue
2. **Keep Redis but make it optional**:
   - If `REDIS_URL` is set, use ARQ; otherwise run in-process
   - More complex branching

### Concrete Recommendation
1. **Remove `redis` service from docker-compose**
2. **Add `Optional[arq]` wrapper**:
   - Try-import `arq`; if missing, set `_arq_available = False`
   - In `dream.py` and `pocket.py`, if `_arq_available` and `settings.redis_url`, use ARQ; else call function directly via `asyncio.create_task()`
3. **Rewrite `worker.py`** to be optional:
   ```python
   try:
       from arq import cron
       from arq.connections import RedisSettings
       ARQ_AVAILABLE = True
   except ImportError:
       ARQ_AVAILABLE = False
   ```
4. **Scheduled sweep in lifespan:**
   - In `main.py` lifespan, if `LOCAL_MODE` and not ARQ, start a background `asyncio.Task` that runs `scheduled_dream_sweep` daily at 3 AM
5. **Remove `redis>=5.0.0` and `arq>=0.25.0` from requirements** (keep commented or move to `requirements-worker.txt`)

---

## 5. Worker / ARQ

### Current State
- `worker.py` is a full ARQ worker definition
- Docker-compose sets `command: arq app.worker.WorkerSettings` for the API container (which is wrong — it should be a separate worker container or the API should run uvicorn)

### Concrete Recommendation
1. **Make ARQ optional** (see §4)
2. **For local mode, run dreams in-process**
3. **If keeping Docker for PG only**, the API container runs `uvicorn` directly, not ARQ
4. Document that for multi-user or production, ARQ + Redis can be re-enabled

---

## 6. Rate Limiting

### Current State
- `slowapi` is used with **in-memory** storage:
  ```python
  limiter = Limiter(key_func=get_remote_address, default_limits=["100/minute"])
  ```
- No Redis backend configured

### Verdict
**No changes needed.** Rate limiting already works without Redis. For local mode, you may want to disable or raise limits:
1. Add to `config.py`: `rate_limit_enabled: bool = True`
2. In `main.py`, only attach `app.state.limiter = limiter` if enabled
3. In `rate_limit.py`, return a no-op limiter if disabled

---

## 7. Local LLM Support

### Current State
- `services/llm_provider.py` supports: Anthropic, DeepSeek, Groq, Together, Qwen, Moonshot, OpenAI
- All are cloud APIs (OpenAI-compatible or native SDK)
- `services/bridge_inference.py` exists for **Bridge Relay** to local hardware (Ollama, LM Studio, vLLM) but requires the SensorHead bridge infrastructure
- No direct HTTP calls to `localhost:11434` (Ollama), `localhost:8000` (vLLM), or `localhost:1234` (LM Studio)

### What Changes Are Needed
1. **Add "local" providers to `PROVIDERS` registry** in `llm_provider.py`:
   ```python
   "ollama": {
       "name": "Ollama",
       "base_url": "http://localhost:11434/v1",
       "key_env": None,  # Ollama needs no key by default
       "default_model": "llama3.1",
       "supports_tools": False,  # Varies by model
   },
   "vllm": {
       "name": "vLLM",
       "base_url": "http://localhost:8000/v1",
       "key_env": "VLLM_API_KEY",
       "default_model": "meta-llama/Llama-3.1-8B-Instruct",
       "supports_tools": False,
   },
   "lmstudio": {
       "name": "LM Studio",
       "base_url": "http://localhost:1234/v1",
       "key_env": None,
       "default_model": "local-model",
       "supports_tools": False,
   },
   ```
2. **Update `create_llm_service()`** to allow `api_key=None` for local providers
3. **Frontend model selector** (`frontend/src/components/ModelSelector.vue` or similar):
   - Add "Local (Ollama)" / "Local (vLLM)" options
   - When selected, bypass BYOK validation (no key needed)
4. **Add environment defaults** in `config.py`:
   ```python
   local_llm_provider: Optional[str] = None  # "ollama", "vllm", "lmstudio"
   local_llm_base_url: Optional[str] = None
   local_llm_model: Optional[str] = None
   ```
5. **Update `DREAM_ELIGIBLE_MODELS`** to include local models if desired
6. **Embeddings** already support local via `fastembed` (`embedding_provider = "local"` is the default). No changes needed.

### Concrete Recommendation
- Add Ollama and vLLM as first-class providers in `llm_provider.py`
- Default `embedding_provider` is already `"local"` (FastEmbed) — keep it
- In local mode, set `LOCAL_LLM_PROVIDER=ollama` and `OLLAMA_HOST=http://host.docker.internal:11434` (if API is in Docker) or `http://localhost:11434` (if native)
- Since the app already uses OpenAI-compatible client for most providers, adding local endpoints is trivial — just different `base_url` and optional key

---

## 8. Stripe / Solana / Billing

### Current State
- `stripe` is in `requirements.txt` and used heavily in:
  - `api/v1/billing.py`, `webhooks.py`
  - `services/billing.py`
  - Models: `Subscription.stripe_customer_id`, `FeatureCreditBalance.stripe_payment_intent_id`
- `solana` API route exists (`api/v1/solana.py`)
- `TIER_LIMITS` in `config.py` gates features by subscription tier
- `aj_citizen` tier is designed to bypass Stripe (uses in-app currency)

### Simplification for Local Mode
1. **Make Stripe optional**:
   - If `STRIPE_SECRET_KEY` is unset, skip Stripe initialization
   - Return mock/empty data from billing endpoints
   - In `services/billing.py`, if no Stripe key, auto-return "azothic" tier (unlimited) or "aj_citizen"
2. **Local mode bypass**:
   - If `LOCAL_MODE=true`, override tier resolution to always return "azothic" (or configurable `local_default_tier`)
   - This unlocks all models, tools, council, vault, etc. without payment
3. **Solana**: Same treatment — if env vars missing, disable route
4. **No code deletion** — wrap with `if settings.stripe_secret_key:`

---

## 9. Docker Compose Simplification

### Target `docker-compose.local.yml`
```yaml
version: '3.8'
services:
  postgres:
    image: pgvector/pgvector:pg16
    container_name: apex_postgres
    environment:
      POSTGRES_DB: apex
      POSTGRES_USER: apex
      POSTGRES_PASSWORD: apex
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U apex -d apex"]
      interval: 5s
      timeout: 3s
      retries: 5

  api:
    build:
      context: ./backend
      dockerfile: Dockerfile.dev
    container_name: apex_api
    environment:
      DATABASE_URL: postgresql+asyncpg://apex:apex@postgres:5432/apex
      LOCAL_MODE: "true"
      LOCAL_DEFAULT_TIER: "azothic"
      ANTHROPIC_API_KEY: ${ANTHROPIC_API_KEY:-}
      LOCAL_LLM_PROVIDER: ${LOCAL_LLM_PROVIDER:-ollama}
      LOCAL_LLM_BASE_URL: ${LOCAL_LLM_BASE_URL:-http://host.docker.internal:11434/v1}
      VAULT_PATH: /data
    ports:
      - "8000:8000"
    volumes:
      - ./backend:/app
      - apex_data:/data
    depends_on:
      postgres:
        condition: service_healthy
    command: uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

  frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile.dev
    container_name: apex_frontend
    environment:
      VITE_API_URL: http://localhost:8000
      VITE_LOCAL_MODE: "true"
    ports:
      - "3000:3000"
    volumes:
      - ./frontend:/app
    depends_on:
      - api

volumes:
  postgres_data:
  apex_data:
```

### Removed
- `redis` service
- `minio` service
- `worker` service (dreams run in-process)
- `adminer` (optional, can stay with profile)

---

## 10. Implementation Priority

| Priority | Task | Effort | Impact |
|----------|------|--------|--------|
| P0 | Make billing optional + local mode tier bypass | 2h | Unlocks all features locally |
| P0 | Add local LLM providers (Ollama, vLLM) | 1h | Removes cloud LLM dependency |
| P0 | Auth: auto-login default user in local mode | 2h | Removes login friction |
| P1 | Remove Redis/Minio from docker-compose | 30min | Cleaner stack |
| P1 | Make ARQ optional (in-process dreams) | 3h | Removes Redis dependency |
| P1 | Disable rate limiting in local mode | 30min | Removes friction |
| P2 | S3 config cleanup | 30min | Dead code removal |
| P2 | SQLite feasibility spike (optional) | 1d | Future path |

---

## Files to Modify

1. `backend/app/config.py` — add `LOCAL_MODE`, `local_default_tier`, `local_llm_*`, make Stripe/S3 optional
2. `backend/app/main.py` — local mode lifespan: default user creation, optional ARQ sweep, optional rate limiter
3. `backend/app/auth/deps.py` — add `get_current_user_local`
4. `backend/app/api/v1/auth.py` — add `/auth/local` endpoint
5. `backend/app/rate_limit.py` — noop if disabled
6. `backend/app/worker.py` — optional ARQ imports
7. `backend/app/api/v1/dream.py` — fallback to in-process if no Redis
8. `backend/app/api/v1/pocket.py` — same
9. `backend/app/services/llm_provider.py` — add Ollama, vLLM, LM Studio providers
10. `backend/app/services/billing.py` — bypass if local mode
11. `docker-compose.dev.yml` — remove redis/minio/worker, fix api command
12. `frontend/src/services/api.js` — auto-local-auth if `VITE_LOCAL_MODE`
13. `frontend/src/stores/auth.js` — skip login UI in local mode

---

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Dream cycles block API if run in-process | Run them via `asyncio.create_task()` with timeout; add max concurrency limit |
| Local LLM (Ollama) not running | Graceful fallback message: "Local LLM not reachable at localhost:11434" |
| PostgreSQL still requires Docker | Document one-liner install; provide native PG install guide; consider SQLite later |
| Single-user assumption breaks multi-user code | Local mode creates one implicit user; all data is scoped to that user |
| Frontend build still hardcodes API URL | Use `VITE_API_URL` override in local docker-compose |
