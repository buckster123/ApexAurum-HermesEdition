# Phase F: The Quest Engine

> *"The backend bones that make the Athaverse possible."*

## Context

E5 gamification tracks XP, levels, and achievements in localStorage. Phase F moves progression server-side, defines milestone trees per tier, adds feature gating middleware, and creates the Stripe quest tier. This is infrastructure — Phase G adds the visual/UX layer on top.

---

## F1: Progression Data Model (Backend)

### New DB Model: `user_progression`

```python
class UserProgression(Base):
    __tablename__ = "user_progressions"

    id = Column(UUID, primary_key=True, default=uuid4)
    user_id = Column(UUID, ForeignKey("users.id"), unique=True, nullable=False)

    # Quest state
    quest_active = Column(Boolean, default=False)       # True if on quest tier
    quest_stage = Column(String, default="seeker")       # seeker|adept|opus|azothic
    quest_started_at = Column(DateTime, nullable=True)

    # Milestone tracking (JSONB for flexibility)
    milestones_completed = Column(JSONB, default=list)   # ["first_chat", "web_search", ...]
    features_unlocked = Column(JSONB, default=list)      # ["basic_chat", "file_vault", ...]

    # Stats (server-side mirror of E5 localStorage)
    agent_stats = Column(JSONB, default=dict)            # {AZOTH: {xp, tasks, ...}, ...}
    zone_stats = Column(JSONB, default=dict)             # {workshop: {tasks, ...}, ...}
    achievements = Column(JSONB, default=list)           # Achievement IDs
    total_tasks = Column(Integer, default=0)

    # Timestamps
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
```

### Migration
- Alembic migration adds `user_progressions` table
- Backfill: existing users get `quest_active=False`, empty milestones
- No disruption to current tier system

---

## F2: Milestone Definitions

### Seeker Quest Milestones (unlock order)

| # | Milestone ID | What to do | Feature unlocked |
|---|-------------|-----------|-----------------|
| 1 | `first_chat` | Send first message to any agent | Basic chat (1 agent) |
| 2 | `meet_agents` | Chat with 2 different agents | All 4 agents |
| 3 | `zone_visit` | Complete a task at any Village zone | Village task dispatch |
| 4 | `web_search` | Use web_search tool via Library zone | Web search tools |
| 5 | `file_upload` | Upload a file in task dialog | File vault (basic) |
| 6 | `three_zones` | Complete tasks at 3 different zones | Tool categories unlock |
| 7 | `council_first` | Run a Council deliberation | Multi-agent council |
| 8 | `seeker_mastery` | Complete 15 total tasks | Full Seeker tier |

### Adept Quest Milestones (after Seeker complete)

| # | Milestone ID | What to do | Feature unlocked |
|---|-------------|-----------|-----------------|
| 9 | `music_gen` | Generate first music track at DJ Booth | Music generation |
| 10 | `memory_store` | Store a memory at Memory Garden | Memory system |
| 11 | `bridge_connect` | Use an external API via Bridge Portal | External integrations |
| 12 | `agent_level_3` | Get any agent to level 3 | Agent customization |
| 13 | `opus_model` | Use an Opus-tier model (monthly limit) | Opus model access (limited) |
| 14 | `zone_master` | Complete 10 tasks at one zone | Zone specialization bonus |
| 15 | `council_expert` | Run 5 Council sessions | Advanced council features |
| 16 | `adept_mastery` | Complete 50 total tasks | Full Adept tier |

### Opus Quest Milestones (after Adept complete)

| # | Milestone ID | What to do | Feature unlocked |
|---|-------------|-----------|-----------------|
| 17 | `dream_engine` | First Dream Engine session | Dream Engine access |
| 18 | `nursery_train` | Train a custom model in Nursery | Model training |
| 19 | `all_zones` | Complete tasks in all 8 zones | Full zone mastery |
| 20 | `agent_level_7` | Get any agent to level 7 | Enhanced agent capabilities |
| 21 | `full_opus` | 100 total tasks + all prior milestones | Full Opus tier |

### Azothic Quest Milestones (after Opus complete)

| # | Milestone ID | What to do | Feature unlocked |
|---|-------------|-----------|-----------------|
| 22 | `all_agents_5` | All 4 agents at level 5+ | PAC mode unlock |
| 23 | `council_master` | 20 Council sessions | Unlimited council |
| 24 | `athanor_complete` | 200 total tasks + all achievements | Full Azothic tier |
| 25 | `sensorhead_earned` | Complete the Azothic quest | SensorHead prize eligibility |

---

## F3: Feature Gating Middleware (Backend)

### Approach: Dual-check system

```python
async def check_feature_access(user, feature: str) -> bool:
    """Check if user can access a feature.
    Classic tier users: check tier level (existing behavior).
    Quest tier users: check progression milestones."""

    if not user.progression or not user.progression.quest_active:
        # Classic path — existing tier check (unchanged)
        return check_tier_access(user.subscription_tier, feature)

    # Quest path — check if feature is unlocked
    return feature in user.progression.features_unlocked
```

### Feature registry

```python
FEATURE_REGISTRY = {
    "basic_chat": {"tier": "seeker", "quest_milestone": "first_chat"},
    "all_agents": {"tier": "seeker", "quest_milestone": "meet_agents"},
    "web_search": {"tier": "seeker", "quest_milestone": "web_search"},
    "file_vault": {"tier": "seeker", "quest_milestone": "file_upload"},
    "multi_agent": {"tier": "seeker", "quest_milestone": "council_first"},
    "music_gen": {"tier": "adept", "quest_milestone": "music_gen"},
    "dream_engine": {"tier": "opus", "quest_milestone": "dream_engine"},
    "model_training": {"tier": "opus", "quest_milestone": "nursery_train"},
    "pac_mode": {"tier": "azothic", "quest_milestone": "all_agents_5"},
    # ... etc
}
```

### Integration points
- Chat endpoint: check `basic_chat`, `all_agents` (agent count), `opus_model`
- Tool execution: check tool category against unlocked features
- Council: check `multi_agent`
- Music: check `music_gen`
- Dream: check `dream_engine`
- Nursery: check `model_training`

### Response format for locked features

```json
{
  "error": "feature_locked",
  "feature": "music_gen",
  "milestone_required": "music_gen",
  "milestone_description": "Generate your first music track at the DJ Booth",
  "quest_stage": "adept"
}
```

Frontend shows this as a helpful nudge, not an error wall.

---

## F4: Progression API Endpoints

### GET /api/v1/quest/progress
Returns user's full quest state for frontend rendering.

```json
{
  "quest_active": true,
  "quest_stage": "seeker",
  "milestones": [
    {"id": "first_chat", "completed": true, "completed_at": "2026-02-13T..."},
    {"id": "meet_agents", "completed": true, "completed_at": "2026-02-13T..."},
    {"id": "zone_visit", "completed": false, "description": "Complete a task at any Village zone"},
    ...
  ],
  "features_unlocked": ["basic_chat", "all_agents"],
  "next_milestone": {"id": "zone_visit", "description": "..."},
  "stage_progress": 2,     // milestones completed in current stage
  "stage_total": 8,        // total milestones in current stage
  "agent_stats": {...},
  "zone_stats": {...},
  "achievements": [...]
}
```

### POST /api/v1/quest/check-milestones
Called after task completion. Checks if any new milestones are met.
Returns newly completed milestones and newly unlocked features.

```json
{
  "new_milestones": [{"id": "zone_visit", "feature_unlocked": "village_tasks"}],
  "new_achievements": [...],
  "stage_complete": false
}
```

### POST /api/v1/quest/upgrade
Quest user upgrades to classic tier (pays difference, unlocks everything immediately).

### GET /api/v1/quest/milestones
Returns milestone definitions for the current quest stage (for frontend display).

---

## F5: Stripe Quest Tier Integration

### New Stripe Products

| Product | Price | Stripe Price ID |
|---------|-------|----------------|
| Seeker Quest | $5/mo | Create via Stripe dashboard |
| Adept Quest | $15/mo | Create via Stripe dashboard |
| Opus Quest | $50/mo | Create via Stripe dashboard |
| Azothic Quest | $150/mo | Create via Stripe dashboard |

### Billing service changes
- `billing.py`: Add quest tier recognition
- Quest tiers map to base message limits of their classic equivalent
- `quest_active` flag set on subscription creation
- Upgrade path: quest -> classic = prorated difference

### Webhook handling
- `customer.subscription.created`: If quest tier, create UserProgression record
- `customer.subscription.updated`: Handle quest -> classic upgrade
- `customer.subscription.deleted`: Preserve progression data (can resume)

---

## F6: Sync E5 to Server

### Frontend -> Backend sync
After each task completion, the existing `recordGamificationTask()` call also:
1. POST /api/v1/quest/check-milestones (if quest user)
2. Receives newly unlocked milestones/features
3. Updates local E5 gamification state
4. Triggers Village unlock animations (Phase G)

### Backend milestone checker
```python
async def check_milestones(user_id: UUID, task_event: dict):
    """Check if task completion triggers any milestones."""
    prog = await get_user_progression(user_id)
    if not prog or not prog.quest_active:
        return []

    stage_milestones = MILESTONE_DEFINITIONS[prog.quest_stage]
    newly_completed = []

    for milestone in stage_milestones:
        if milestone.id in prog.milestones_completed:
            continue
        if milestone.check(prog, task_event):
            prog.milestones_completed.append(milestone.id)
            prog.features_unlocked.append(milestone.feature_unlocked)
            newly_completed.append(milestone)

    # Check stage completion
    if all(m.id in prog.milestones_completed for m in stage_milestones):
        prog.quest_stage = next_stage(prog.quest_stage)

    await save_progression(prog)
    return newly_completed
```

---

## Execution Order

```
F1  Data model + migration               ← Foundation
F2  Milestone definitions                 ← Game design (data)
F3  Feature gating middleware             ← Access control
F4  Progression API endpoints             ← Frontend communication
F5  Stripe quest tier integration         ← Billing
F6  E5 -> server sync                    ← Bridge existing gamification
```

F1-F4 can be built and tested without touching Stripe.
F5 requires Stripe dashboard setup (new products/prices).
F6 connects the existing E5 frontend to the new backend.

---

## Files to Create

| File | Purpose |
|------|---------|
| `backend/app/models/progression.py` | UserProgression SQLAlchemy model |
| `backend/app/services/progression.py` | Milestone checking, feature gating logic |
| `backend/app/api/v1/quest.py` | Quest API endpoints |
| `backend/alembic/versions/xxx_add_progression.py` | DB migration |

## Files to Modify

| File | Change |
|------|--------|
| `backend/app/main.py` | Register quest router |
| `backend/app/services/billing.py` | Quest tier recognition |
| `backend/app/api/v1/webhooks.py` | Quest subscription handling |
| `backend/app/api/v1/chat.py` | Feature gating check |
| `backend/app/api/v1/council.py` | Feature gating check |
| `frontend/src/composables/useVillageGamification.js` | Add server sync |
| `frontend/src/views/VillageGUIView.vue` | Quest progress integration |

---

## Verification

1. Create quest user via Stripe test mode
2. Login -> Village 3D shows locked buildings
3. Complete first_chat milestone -> basic_chat unlocks
4. Progress through seeker milestones -> features unlock one by one
5. Classic tier user unaffected — all features available as before
6. Quest -> classic upgrade works (pays difference, instant unlock)
7. Page refresh preserves progression (server-side)

---

*"The Quest Engine: where subscriptions become adventures."*
