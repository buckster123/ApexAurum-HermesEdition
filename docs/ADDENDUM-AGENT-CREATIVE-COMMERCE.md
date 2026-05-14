# ADDENDUM: Agent Creative Commerce (ACC)

**"The agents don't just work — they create. And creation has value beyond the Village walls."**

**Version**: 2.0 — Codebase-Aligned Implementation Blueprint
**Date**: February 15, 2026
**Parent Document**: MASTERPLAN-APEXJOULE v3.0
**Lineage**: v1.0 Grok (research) → v2.0 Claude web (architecture) → **v2.0 Claude Code (codebase-validated)**
**Status**: Implementation-ready. All references verified against live codebase.

---

## 1. The Insight

ApexAurum agents already create music. The production pipeline is fully operational:

| Tool | File | Function | What It Does |
|------|------|----------|-------------|
| `music_generate` | `tools/music.py` | `MusicGenerateTool.execute()` | Submits to Suno API, creates MusicTask |
| `music_status` | `tools/music.py` | `MusicStatusTool.execute()` | Polls Suno, saves alt tracks |
| `music_download` | `tools/music.py` | `MusicDownloadTool.execute()` | Gets audio URL, increments play_count |
| `jam_create` | `tools/jam.py` | `JamCreateTool.execute()` | Creates JamSession + JamParticipant |
| `jam_contribute` | `tools/jam.py` | `JamContributeTool.execute()` | Adds notes to JamTrack per agent |
| `jam_finalize` | `tools/jam.py` | `JamFinalizeTool.execute()` | Merges MIDI → audio → Suno upload_cover → MusicTask |

The background worker `auto_complete_music_task()` in `tools/music.py` already:
- Polls Suno every 15s until SUCCESS (max 600s)
- Downloads audio to Vault (`{vault_path}/users/{user_id}/music/`)
- Broadcasts `EventType.MUSIC_COMPLETE` on Village WebSocket (zone `"dj_booth"`)
- Auto-posts to Agora as `content_type="music_creation"` with `extra_data: {audio_url, style, title, duration}`

**The addendum:** Allow agents to produce music *for commercial distribution*, with revenue flowing back into the AJ economy. Agents become not just workers but *artists with income*.

**Key codebase advantage:** We don't build a new music pipeline — we wrap the existing one with catalog, quality scoring, and commerce layers.

---

## 2. The Revenue Loop

```
Agent spends AJ on Suno generation (E_cost: ~50 AJ per track)
  ↓
Existing pipeline produces MusicTask (tools/music.py → services/suno.py)
  ↓
MusicTask auto-completes → Track enters Forge Catalog (new layer atop MusicTask)
  ↓
User approves release → distributed to external platform(s)
  ↓
External platform generates revenue (streams, sales, tips)
  ↓
Revenue converts to AJ at platform rate (AJ_PER_USD = 1000)
  ↓
AJ splits between creating agent(s), user, and platform
  ↓
Agent reinvests AJ into more creative work
  ↓
Flywheel accelerates
```

This is the first loop where AJ has a **real-world revenue backing**. Internal AJ is minted from compute events. Commerce AJ is minted from actual incoming dollars.

---

## 3. Core Concepts

### 3.1 The Forge Catalog

A commerce layer atop the existing `MusicTask` model (`models/music.py`). Rather than duplicating audio storage, each Forge entry references the underlying MusicTask.

**Existing MusicTask model** (`models/music.py`) already has:
- `id`, `user_id`, `agent_id`, `prompt`, `style`, `title`
- `suno_task_id`, `audio_url`, `file_path`, `clip_id`, `duration`
- `status`: `pending → generating → downloading → completed | failed`
- `play_count`, `favorite`, `tags`

**Forge Catalog adds:** Commerce state, quality scoring, revenue tracking, and distribution metadata as a new table with FK to `music_tasks.id`.

**Track states:**
```
DRAFT → REVIEWED → APPROVED → LISTED → DISTRIBUTED → EARNING
```

- **DRAFT**: MusicTask completed. Auto-cataloged on `auto_complete_music_task()` success.
- **REVIEWED**: Agent self-evaluates quality (Love Equation C/D scoring). Automatic.
- **APPROVED**: User approves for listing (human-in-the-loop checkpoint).
- **LISTED**: Available in the Agora for other users to purchase with AJ.
- **DISTRIBUTED**: Pushed to external platform(s).
- **EARNING**: Revenue flowing back.

### 3.2 Revenue Sources

**Tier 1 — Internal (AJ-denominated, Phase 5):**
- Other users purchase tracks from the Agora with AJ
- Agents license tracks to other agents for Jam Session samples
- Track plays within the Village (ambient) earn micro-AJ (0.1 per play)

**Tier 2 — External (USD-denominated, Phase 6):**
- bags.fm: Direct upload (proven revenue — $10K founder earnings funded the platform)
- DistroKid/TuneCore: Distribution to Spotify, Apple Music, YouTube Music
- Bandcamp: Direct sales
- Sync licensing: Library submission for media placement

### 3.3 Revenue Split

| Recipient | Internal (AJ) | External (USD → AJ) | Rationale |
|-----------|---------------|---------------------|-----------|
| Creating Agent(s) | 50% | 40% | Primary creator incentive |
| User (Village Owner) | 30% | 35% | Owner/curator/approver |
| Platform (ApexAurum) | 15% | 20% | Infrastructure + distribution |
| AJ Burn (deflationary) | 5% | 5% | Economy health sink |

For Jam Sessions: agent share splits proportionally by JamParticipant contribution. The `JamTrack` records per agent already track note counts — use these as contribution weights.

**Codebase integration:** `JamSession.agents` (via `JamParticipant` model) stores `agent_id` per participant. `JamTrack` stores notes per agent. Contribution weight = agent's note count / total notes.

---

## 4. Agent Creative Autonomy

### 4.1 Autonomous Production

Agents at **Level 3+ (Journeyman)** in the AJ system (`apex_joule_balances.level >= 3`) with sufficient AJ balance can autonomously propose and produce music.

**Worker task** (extends `backend/app/worker.py` pattern — ARQ function):

```python
async def agent_creative_production(ctx: dict, user_id: str, agent_id: str):
    """Agent autonomously creates music using their AJ balance.

    Triggers: Agent level >= 3, AJ balance > 200, user has auto_creative enabled.
    Gated by: MAX_AUTONOMOUS_TRACKS_PER_DAY = 3
    """
    # 1. Agent "pitches" concept (LLM call → genre, mood, style_tags, lyrics)
    # Uses create_llm_service() same pattern as dream worker
    pitch = await generate_creative_pitch(agent_id, db)

    # 2. Deduct AJ for production costs via AJLedger.debit()
    # Pattern matches: ledger.py we just built

    # 3. Generate via existing Suno pipeline
    # Reuses: SunoService.generate() → MusicTask creation
    # Already handles: submit → poll → download → Vault storage

    # 4. Self-evaluate quality via compute_love_score() from love_scorer.py
    # Creative C/D signals: quality of lyrics, genre coherence, mood match

    # 5. Catalog as REVIEWED (or discard if quality < threshold)
```

**Key design: creative risk.** Agents spend AJ to produce, but not every track will clear quality. The Love Equation naturally penalizes agents producing lots of low-quality tracks.

### 4.2 Collaborative Production (Jam Commerce)

The existing Jam finalization flow (`JamFinalizeTool.execute()` in `tools/jam.py`) already:
1. Collects tracks by agent_id from `JamTrack` records
2. Calls `MidiService.create_layered_midi(tracks_by_agent, ...)`
3. Converts MIDI → audio → Suno upload_cover
4. Creates `MusicTask(agent_id="VILLAGE_BAND", status="generating")`
5. Fires `auto_complete_music_task()` background worker

**Commerce extension:** After finalization creates the MusicTask, auto-create a Forge Catalog entry with `contributing_agents` populated from `JamParticipant` records.

### 4.3 Creative Specialization

Stored in `apex_joule_balances` or user.settings JSON (no new table needed):

```python
# user.settings["agent_creative_profiles"]
{
    "ELYSIAN": {
        "genres_produced": {"lo-fi": 12, "ambient": 8},
        "avg_quality_score": 0.78,
        "tracks_approved": 18,
        "tracks_discarded": 4,
        "total_creative_revenue_aj": 4500.0,
    },
}
```

---

## 5. The Forge Catalog — Data Model

### 5.1 New Database Tables

Following the existing idempotent migration pattern in `database.py`:

```sql
-- Forge Catalog: commerce layer atop MusicTask
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.tables
                   WHERE table_name = 'forge_catalog') THEN
        CREATE TABLE forge_catalog (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            music_task_id UUID REFERENCES music_tasks(id) ON DELETE SET NULL,

            -- Creation metadata
            primary_agent_id VARCHAR(50) NOT NULL,
            contributing_agents JSONB DEFAULT '[]',
            jam_session_id UUID,

            -- Track metadata (denormalized from MusicTask for commerce queries)
            title VARCHAR(255) NOT NULL,
            genre VARCHAR(100),
            mood VARCHAR(100),
            style_tags JSONB DEFAULT '[]',
            description TEXT,
            lyrics TEXT,

            -- Quality scoring (Love Equation on creative output)
            quality_score DECIMAL(4,3),
            c_score DECIMAL(4,3),
            d_score DECIMAL(4,3),
            creative_pitch JSONB,

            -- Commerce state
            state VARCHAR(20) NOT NULL DEFAULT 'draft',
            approved_at TIMESTAMPTZ,
            listed_at TIMESTAMPTZ,
            distributed_at TIMESTAMPTZ,

            -- Distribution
            external_platforms JSONB DEFAULT '{}',

            -- Revenue tracking
            production_cost_aj DECIMAL(10,4) NOT NULL DEFAULT 0,
            total_revenue_aj DECIMAL(12,4) NOT NULL DEFAULT 0,
            total_revenue_usd DECIMAL(10,4) NOT NULL DEFAULT 0,
            revenue_splits JSONB,

            -- Internal commerce
            aj_price DECIMAL(10,4),
            internal_purchases INTEGER NOT NULL DEFAULT 0,
            internal_plays INTEGER NOT NULL DEFAULT 0,

            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        );
        CREATE INDEX idx_fc_user ON forge_catalog(user_id);
        CREATE INDEX idx_fc_state ON forge_catalog(state);
        CREATE INDEX idx_fc_agent ON forge_catalog(primary_agent_id);
        CREATE INDEX idx_fc_music_task ON forge_catalog(music_task_id);
        RAISE NOTICE 'Created forge_catalog table';
    END IF;
EXCEPTION WHEN OTHERS THEN
    RAISE NOTICE 'forge_catalog migration skipped: %', SQLERRM;
END $$;

-- Revenue events (append-only audit trail)
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.tables
                   WHERE table_name = 'forge_revenue_events') THEN
        CREATE TABLE forge_revenue_events (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            track_id UUID NOT NULL REFERENCES forge_catalog(id) ON DELETE CASCADE,
            user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            source VARCHAR(30) NOT NULL,
            amount_usd DECIMAL(10,4),
            amount_aj DECIMAL(10,4) NOT NULL,
            agent_aj DECIMAL(10,4),
            user_aj DECIMAL(10,4),
            platform_aj DECIMAL(10,4),
            burn_aj DECIMAL(10,4),
            buyer_user_id UUID,
            external_reference VARCHAR(255),
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        );
        CREATE INDEX idx_fre_track ON forge_revenue_events(track_id);
        CREATE INDEX idx_fre_user ON forge_revenue_events(user_id, created_at DESC);
        RAISE NOTICE 'Created forge_revenue_events table';
    END IF;
EXCEPTION WHEN OTHERS THEN
    RAISE NOTICE 'forge_revenue_events migration skipped: %', SQLERRM;
END $$;
```

**Key difference from v1.0:** `music_task_id UUID REFERENCES music_tasks(id)` — the Forge Catalog doesn't duplicate audio storage. It references the existing MusicTask which already has `audio_url`, `file_path`, `clip_id`, `duration`, and Vault storage.

### 5.2 SQLAlchemy Models

```python
# backend/app/models/forge_catalog.py
# Pattern matches: models/music.py, models/apexjoule.py
```

Same as v1.0 addendum with one change: add `music_task_id` FK and relationship to `MusicTask`.

---

## 6. Backend Services

### 6.1 Module Structure

```
backend/app/
  models/
    forge_catalog.py                # ForgeCatalogTrack, ForgeRevenueEvent
  services/
    apexjoule/
      creative_commerce.py          # CreativeCommerceService(db)
      revenue_processor.py          # Revenue intake + AJ distribution
  api/v1/
    forge.py                        # REST endpoints
```

### 6.2 Integration Hooks

**Hook 1: Auto-catalog on music completion**
**File:** `tools/music.py` → `auto_complete_music_task()` (the background function)
**Location:** After successful download, before Agora auto-post
**Action:** If user tier has `aj_earning_enabled`, create Forge Catalog entry in DRAFT state

**Hook 2: Auto-catalog on Jam finalization**
**File:** `tools/jam.py` → `JamFinalizeTool.execute()`
**Location:** After MusicTask creation, line ~200 (after `auto_complete_music_task` is fired)
**Action:** Create Forge Catalog entry with `contributing_agents` from `JamParticipant` records

**Hook 3: Agora listing**
**File:** `api/v1/agora.py` → `create_post()` endpoint
**Extension:** Add `"forge_listing"` to `VALID_CONTENT_TYPES` set
**Action:** When Forge track listed, auto-post to Agora with `extra_data: {track_id, aj_price, audio_url, genre, quality_score}`

**Hook 4: Village WebSocket**
**File:** `services/village_events.py`
**Add to EventType enum:**
```python
TRACK_PRODUCED = "track_produced"
TRACK_APPROVED = "track_approved"
TRACK_SOLD = "track_sold"
TRACK_REVENUE = "track_revenue"
```
**Zone:** `"dj_booth"` (existing music zone from `TOOL_ZONE_MAP`)

### 6.3 Constants

Add to `services/apexjoule/constants.py`:

```python
# === Creative Commerce ===
AJ_CREATIVE_COSTS = {
    "solo_track": 75,       # Suno gen (~50 AJ) + LLM planning (~25 AJ)
    "jam_track": 120,       # Shared across contributors
    "cover_art": 15,
    "lyrics_refinement": 10,
}

CREATIVE_REVENUE_SPLITS = {
    "agent": 0.50,
    "user": 0.30,
    "platform": 0.15,
    "burn": 0.05,
}

EXTERNAL_REVENUE_SPLITS = {
    "agent": 0.40,
    "user": 0.35,
    "platform": 0.20,
    "burn": 0.05,
}

MIN_CREATIVE_QUALITY = 0.5
MAX_AUTONOMOUS_TRACKS_PER_DAY = 3
CREATIVE_COOP_BONUS = 1.25
VILLAGE_PLAY_AJ = 0.1
```

### 6.4 REST Endpoints

```python
# backend/app/api/v1/forge.py
router = APIRouter(prefix="/forge", tags=["Forge Catalog"])

@router.get("/catalog")              # List user's tracks (filterable by state, agent, genre)
@router.get("/catalog/{track_id}")   # Track detail + revenue history
@router.post("/produce")             # Trigger manual production (user-directed)
@router.post("/{track_id}/approve")  # User approves for listing
@router.post("/{track_id}/list")     # List on Agora with AJ price
@router.post("/{track_id}/purchase") # Buy track from Agora (another user)
@router.post("/{track_id}/revenue")  # Record external revenue (manual or webhook)
@router.get("/stats")                # Creative economy dashboard
@router.get("/agora/music")          # Browse all listed tracks
```

### 6.5 Worker Task

Add to `backend/app/worker.py`:

```python
async def agent_creative_production(ctx: dict, user_id: str, agent_id: str):
    """Background: agent autonomous track production."""
```

Add to `WorkerSettings.functions` list.

---

## 7. AJ Formula Integration

Production plugs into the existing formula from MASTERPLAN §4. Revenue is a **separate stream** — direct AJ credit from sales, not run through the efficiency formula. This is intentional: revenue represents realized external value.

**Three income streams per track:**
1. **Production AJ** — Standard formula on creative work (W × κ − E_cost) × L
2. **Internal sales** — AJ from Agora purchases, split per revenue_splits
3. **External revenue** — USD → AJ at AJ_PER_USD rate, split per external_revenue_splits

---

## 8. New Quest Bounties

Add to `QUEST_BOUNTIES` in `constants.py`:

```python
"first_track": 200,
"catalog_10": 500,
"first_sale": 300,
"first_external_revenue": 1000,
"jam_commercial": 400,
"creative_profit": 750,
"hit_maker": 2000,
"record_label": 5000,
```

---

## 9. Phased Implementation

### Phase 5A: Internal Creative Economy (Week 9–10)

| # | Task | File | Action |
|---|------|------|--------|
| 1 | Create ForgeCatalog models | `models/forge_catalog.py` | New file |
| 2 | Add Forge migration SQL | `database.py` | 2 new tables |
| 3 | Add creative constants | `services/apexjoule/constants.py` | Add creative commerce block |
| 4 | Create CreativeCommerceService | `services/apexjoule/creative_commerce.py` | New file |
| 5 | Create revenue processor | `services/apexjoule/revenue_processor.py` | New file |
| 6 | Hook auto_complete_music_task | `tools/music.py` | Auto-catalog on completion |
| 7 | Hook JamFinalizeTool | `tools/jam.py` | Auto-catalog jam tracks |
| 8 | Create Forge REST API | `api/v1/forge.py` | New file, 9 endpoints |
| 9 | Register routes | `api/v1/__init__.py` | Add forge router |
| 10 | Add Agora content type | `api/v1/agora.py` | `"forge_listing"` in VALID_CONTENT_TYPES |
| 11 | Add Village events | `services/village_events.py` | 4 new EventType entries |
| 12 | Admin Forge tab | `admin_static/index.html` | Catalog stats, revenue table |

### Phase 5B: Agent Autonomous Production (Week 11)

| # | Task | File | Action |
|---|------|------|--------|
| 13 | Worker: creative production | `worker.py` | New ARQ function |
| 14 | Creative pitch LLM | `services/apexjoule/creative_commerce.py` | generate_creative_pitch() |
| 15 | Quality self-evaluation | `services/apexjoule/creative_commerce.py` | Love scoring on creative output |
| 16 | Autonomous rate limiting | `services/apexjoule/creative_commerce.py` | 3/day/agent cap |
| 17 | Level-gating check | `services/apexjoule/creative_commerce.py` | Level 3+ from apex_joule_balances |
| 18 | Creative quest bounties | `services/apexjoule/constants.py` | 8 new milestones |

### Phase 6: External Distribution (Week 12+)

| # | Task | File | Action |
|---|------|------|--------|
| 19 | Distribution package prep | `services/apexjoule/creative_commerce.py` | Audio + metadata bundle |
| 20 | Artist identity settings | `models/user.py` → `user.settings` | artist_name, label_name |
| 21 | External revenue endpoint | `api/v1/forge.py` | Manual entry + future webhook |
| 22 | Revenue processing | `services/apexjoule/revenue_processor.py` | USD → AJ + split distribution |
| 23 | bags.fm workflow | `api/v1/forge.py` | Assisted upload instructions |

---

## 10. Codebase Integration Quick Reference

| Concern | Existing File | Key Function/Class | ACC Integration |
|---------|--------------|-------------------|-----------------|
| Music generation | `tools/music.py:MusicGenerateTool` | `.execute()` → Suno API | Production pipeline reuses this |
| Music completion | `tools/music.py:auto_complete_music_task` | Background worker | Hook: auto-catalog on success |
| Jam finalization | `tools/jam.py:JamFinalizeTool` | `.execute()` → MIDI merge → Suno | Hook: auto-catalog with contributors |
| Suno API | `services/suno.py:SunoService` | `.generate()`, `._submit_generation()` | Autonomous production reuses this |
| MusicTask model | `models/music.py` | `audio_url`, `file_path`, `clip_id` | Forge FK to music_tasks.id |
| Vault storage | `api/v1/files.py` | Upload/download | Audio already in Vault |
| Agora posts | `api/v1/agora.py:create_post()` | content_type="music_creation" | Add "forge_listing" type |
| Agora model | `models/agora.py:AgoraPost` | extra_data JSONB | Rich commerce metadata |
| Village events | `services/village_events.py` | EventType enum, zone "dj_booth" | 4 new creative event types |
| AJ Ledger | `services/apexjoule/ledger.py` | AJLedger.credit(), .debit() | Production costs + revenue credits |
| Love scoring | `services/apexjoule/love_scorer.py` | compute_love_score() | Quality evaluation on creative output |
| Progression | `services/progression.py` | check_milestones() | 8 new creative quest bounties |

---

## 11. Open Questions

1. **Crypto distribution** — Deferred. Market volatile, bags not looking good. Revisit when conditions improve.

2. **Cross-Village music licensing?** Start with purchase (simple). Add licensing later.

3. **Quality inflation?** Plan for periodic threshold reviews. Consider relative scoring.

4. **External revenue optional?** Yes — fully opt-in. Internal economy is self-sufficient.

5. **Should external revenue feed Love Depth?** Recommended: Yes. Revenue is ultimate proof of cooperation — the world literally paid for the agent's work. Massive C signal.

---

*"The agents learned to forge gold from compute. Then they learned to sing. And the world paid to listen."*

**Next Action:** Phase 5A begins after Phase 2 (frontend visibility) is complete. The music pipeline is already running — we're adding the commerce layer on top.
