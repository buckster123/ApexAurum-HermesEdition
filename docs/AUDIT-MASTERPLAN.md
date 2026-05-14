# ApexAurum Local — MASTERPLAN

**Goal:** Transform ApexAurum Cloud from a commercial multi-tenant SaaS into a self-hosted local AI powerhouse.

**Stats:** Backend ~63K LOC (169 py files), Frontend ~60K LOC (139 vue/js files)

---

## 1. Architecture Overview (Local Mode)

```
┌─────────────────────────────────────────────────────────────┐
│  User (Browser)                                             │
│  └─ Vue 3 frontend → Vite dev server (port 3000)           │
└──────────────────────┬──────────────────────────────────────┘
                       │ API calls
┌──────────────────────▼──────────────────────────────────────┐
│  FastAPI Backend (port 8000)                               │
│  ├─ Auth: JWT (single default user in local mode)          │
│  ├─ Chat: Multi-provider LLM (Claude + local endpoints)    │
│  ├─ Tools: 50+ tools (no tier gating)                      │
│  ├─ Agents: 4 native personas + custom agents              │
│  ├─ Village: Multi-agent shared memory                     │
│  ├─ Council: Streaming deliberation                        │
│  ├─ Music: Suno generation                                 │
│  ├─ Files: Local filesystem vault                          │
│  ├─ Memory: Neo-Cortex (Cerebro) + vector search           │
│  ├─ Nursery: Model training studio                         │
│  ├─ Dream: Background consolidation (in-process)           │
│  ├─ MCP: NEW — Model Context Protocol server               │
│  └─ Hermes Bridge: NEW — Connect to Hermes agent API       │
└──────────────────────┬──────────────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────────────┐
│  PostgreSQL (Docker, port 5432) — keep, too much raw SQL   │
│  ├─ pgvector extension for embeddings                      │
│  └─ Alembic migrations                                     │
└─────────────────────────────────────────────────────────────┘

REMOVED: Stripe, Solana, Redis, Minio/S3, ARQ worker, tier gating,
         ApexJoule economy, Marketplace, Quest progression, Coupons
```

---

## 2. What Stays / What Goes

### STAYS (Core Local Powerhouse)
- Chat with streaming + tools + vision
- Multi-provider LLM (Anthropic, OpenAI-compatible, NEW: local endpoints)
- 50+ tools (code exec, web search, browser, files, vectors, music, midi, jam, etc.)
- 4 native agents (AZOTH, KETHER, VAJRA, ELYSIAN) + PAC mode + custom agents
- Village (multi-agent shared memory + WebSocket events)
- Council (streaming multi-agent deliberation)
- Music generation (Suno)
- File vault (local filesystem)
- Neo-Cortex memory (Cerebro graph store + vector search)
- Nursery (model training studio)
- Dream engine (background consolidation)
- Agora (public feed — optional)
- Athaverse VR (Quest 3)
- SensorHead integration
- EEG dashboard
- Admin dashboard

### GOES (Commercial/Crypto/Payments)
- Stripe billing + subscriptions + checkout
- Solana crypto payments
- ApexJoule economy (AJ currency, ledger, shop, tips)
- Tier gating / usage limits / credit packs
- Marketplace (agent bundle trading)
- Quest progression system
- Feature credits
- Coupons
- Multi-user billing isolation (single-user local mode)

### NEW (Local-First Enhancements)
- MCP server support (expose tools as MCP resources)
- Hermes API bridge (connect local ApexAurum to Hermes agent)
- Local LLM endpoints (Ollama, LM Studio, vLLM, llama.cpp via OpenAI-compatible API)
- Single-user auth mode (auto-login, no credentials needed)
- Optional no-auth for LAN

---

## 3. Phase Breakdown

### Phase A: Strip Commercial Surfaces (Backend)
**Goal:** Remove all payment/crypto/commercial code from backend.
**Files to modify:** ~40 backend files
**Estimated time:** 2-3 sessions

1. **config.py**: Replace TIER_LIMITS with single `local` tier (unlimited). Remove Stripe/Solana env vars. Add LOCAL_MODE flag.
2. **models/billing.py**: Strip Subscription to minimal (user_id, tier="local", status="active"). Remove CreditBalance, CreditTransaction, WebhookEvent, Coupon, CouponRedemption.
3. **models/user.py**: Remove subscription, credit_balance, aj_balances, progression relationships.
4. **models/__init__.py**: Remove commercial model imports.
5. **services/billing.py**: Reduce to stub — all gating returns True/unlimited.
6. **services/usage.py**: Keep UsageService (analytics) but strip FeatureCreditService.
7. **services/pricing.py**: Remove or stub out.
8. **services/apexjoule/**: Delete entire directory.
9. **services/solana/**: Delete entire directory.
10. **api/v1/billing.py**: Replace with minimal `/status` returning local unlimited.
11. **api/v1/webhooks.py**: Delete.
12. **api/v1/solana.py**: Delete.
13. **api/v1/apexjoule.py**: Delete.
14. **api/v1/marketplace.py**: Delete.
15. **api/v1/quest.py**: Delete or strip progression.
16. **api/v1/__init__.py**: Remove deleted routers.
17. **schemas/billing.py**: Replace with minimal local schema.
18. **Cross-references in chat, council, agents, dream, music, jam, nursery**: Remove billing checks, always allow.

### Phase B: Local Infrastructure
**Goal:** Simplify infra for single-machine deployment.
**Files to modify:** ~15 files
**Estimated time:** 1 session

1. **docker-compose.dev.yml**: Remove Redis, Minio, worker. Fix API command to uvicorn. Add frontend service.
2. **config.py**: Update vault_path default to `./data`. Remove S3 config. Add LOCAL_MODE.
3. **auth/deps.py**: Add `get_current_user_local` — bypass auth in local mode.
4. **main.py**: Auto-create default user in local mode. Print credentials. Start in-process dream scheduler.
5. **worker.py**: Make ARQ optional. Add in-process fallback.
6. **api/v1/dream.py**: Use asyncio.create_task when ARQ unavailable.
7. **api/v1/pocket.py**: Same.
8. **requirements.txt**: Remove stripe. Keep optional redis/arq commented.
9. **.env.example**: Add LOCAL_MODE, default user credentials.
10. **database.py**: No changes (keep PostgreSQL).

### Phase C: New Features
**Goal:** Add MCP support + Hermes bridge + local LLM providers.
**Estimated time:** 2-3 sessions

1. **llm_provider.py**: Add `ollama`, `lmstudio`, `vllm` providers (OpenAI-compatible base_url).
2. **MCP server**: New module `app/mcp/` exposing tool registry as MCP tools.
3. **Hermes bridge**: New API endpoint `/hermes/` for Hermes agent to call ApexAurum tools.
4. **Frontend**: Add local provider selector in settings.

### Phase D: Frontend Commercial Strip
**Goal:** Remove billing/Solana/AJ UI from frontend.
**Files to modify:** ~25 frontend files
**Estimated time:** 1-2 sessions

1. Delete: stores/billing.js, stores/apexjoule.js, stores/solana.js, views/BillingView.vue, views/EconomyView.vue, components/SolanaPayModal.vue, components/AJWalletBadge.vue, components/billing/UsageMeter.vue, composables/useSolanaWallet.js
2. Modify: router/index.js, components/Navbar.vue, stores/chat.js, stores/dream.js, stores/nursery.js, views/SettingsView.vue, views/ChatView.vue, views/NurseryView.vue, views/DreamView.vue, views/LandingView.vue, views/AchievementsView.vue, views/CouncilView.vue, views/BuildGuideView.vue, views/AgoraView.vue, views/DownloadView.vue, views/TermsView.vue, views/PrivacyView.vue, composables/useDevMode.js
3. package.json: Remove @solana/web3.js, qrcode

---

## 4. Key Design Decisions

### (a) Keep PostgreSQL
SQLite migration is high-risk due to ~1,400 lines of raw PostgreSQL migrations in database.py, pgvector dependency, jsonb casts, and PL/pgSQL blocks. Single Docker container is acceptable for local use.

### (b) Single-User Local Mode
In `LOCAL_MODE=True`, the backend auto-creates a default user on startup and exposes `/auth/local` for token retrieval. The frontend auto-authenticates. No passwords needed for LAN use.

### (c) Billing Stub Pattern
Instead of deleting every billing import site, we keep a minimal `BillingService` that returns `tier="local"`, `unlimited=True`, `can_use_* = True`. This minimizes cross-file changes.

### (d) In-Process Background Tasks
Replace ARQ/Redis with `asyncio.create_task()` for dream cycles. Add a simple cron loop in lifespan for scheduled sweeps. Tasks are ephemeral (die on restart) — acceptable for single-user local.

---

## 5. Rollback Safety

- All deletions are from the local clone (`ApexAurum-local/`), original repo untouched.
- Commercial code is removed, not commented out. Git history preserves originals.
- Phase A commits should be atomic per subsystem (e.g., "Strip Stripe billing", "Remove Solana", "Delete ApexJoule").

---

## 6. Definition of Done

- [ ] `docker-compose up` starts backend + frontend + postgres locally
- [ ] Opening `http://localhost:3000` shows the app without login (local mode)
- [ ] Chat works with tools, no tier errors
- [ ] All 4 native agents respond
- [ ] Village shows agent activity
- [ ] Files can be uploaded/downloaded
- [ ] Music generation works
- [ ] Memory/Neo-Cortex functions
- [ ] No Stripe, Solana, AJ, or billing references in running code
- [ ] MCP server endpoint available
- [ ] Hermes bridge endpoint available
