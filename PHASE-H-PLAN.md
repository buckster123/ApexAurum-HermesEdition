# Phase H: The Grand Prizes

> *"The summit of the Athaverse — where digital achievement meets social proof."*

## Context

Phases A-G complete: 4 agents, Village 3D with zone locks/ceremonies/tutorial, Quest Engine with 25 milestones across 4 stages, Agora social feed, 10 E5 achievements. Phase H celebrates quest completion with an achievement gallery, social proof on Agora, community leaderboard, an evolving 3D pedestal, and shareable cards.

**Physical SensorHead deferred** — prototype exists but needs HW optimizations, custom enclosure, and servo work. Gets a software placeholder + "coming soon" messaging. Two future tiers noted: basic 3D-printed edition + limited oak/power-servo premium edition.

---

## H1: Achievement Gallery — The Trophy Case

**A dedicated view showcasing all 35 achievements (10 E5 + 25 quest milestones).**

### What it does
- New route `/achievements` — linked from navbar
- Card grid: locked (grey, padlock) vs unlocked (gold glow, checkmark, date)
- Grouped by stage: "Seeker Path" (8) / "Adept Path" (8) / "Opus Path" (5) / "Azothic Path" (4) / "Village Mastery" (10 E5)
- Progress bar at top: "12/35 Achievements" with percentage
- Each card: name, description, feature unlocked (quest milestones), completion date
- Responsive: 1→2→3→4 columns

### Implementation
- **Create**: `frontend/src/views/AchievementsView.vue` (~250 lines)
  - Calls `fetchQuestProgress()` on mount
  - Merges `questProgress.milestones` (25) + E5 `ACHIEVEMENTS` array (10) into unified list
  - Groups by stage + E5 category
  - Unlock dates from `questProgress.milestones[].completed` flag (quest) or `stats.achievements` array (E5)
- **Modify**: `frontend/src/router/index.js` — add `/achievements` route (requiresAuth: true)
- **Modify**: `frontend/src/components/Navbar.vue` — add Achievements link

### Data sources (all existing, no new APIs)
- `useVillageGamification().questProgress.milestones` — 25 quest milestones with `{id, name, description, feature_unlocked, completed}`
- `useVillageGamification().ACHIEVEMENTS` — 10 E5 definitions with `{id, name, description, check}`
- `useVillageGamification().stats.achievements` — array of earned E5 achievement IDs

---

## H2: Agora Stage Badges — Social Proof

**Quest stage badge next to display names on Agora posts.**

### What it does
- Small colored chip: "Seeker" (grey) / "Adept" (blue) / "Opus" (purple) / "Azothic" (gold)
- Shows next to author display name on every post
- Only for quest-active users (classic tier shows nothing)
- Aspirational: other users see what stage someone reached

### Implementation
- **Modify**: `backend/app/api/v1/agora.py`
  - In feed/post queries: join `user_progressions` table via user relationship
  - Add `quest_stage` to post author serialization when `quest_active=true`
- **Modify**: `frontend/src/views/AgoraView.vue`
  - Render badge chip in post header next to author name
  - Color map: seeker=slate, adept=blue, opus=purple, azothic=amber/gold

### Backend detail
- `AgoraPost` already has `user_id` FK → join `UserProgression` on same user_id
- Only include `quest_stage` field — no detailed stats (privacy)
- No new models/migrations needed

---

## H3: Community Leaderboard — Hall of Fame

**Ranked list of top quest users on the Agora.**

### What it does
- New tab in AgoraView: "Feed" | "Leaderboard"
- Top 50 users ranked by milestones completed (tiebreaker: total_tasks)
- Columns: Rank, User, Stage Badge, Milestones, Tasks
- User's own rank highlighted (or shown below if outside top 50)
- **Privacy**: only users with `agora.enabled=true` AND `display_name_public=true`

### Implementation
- **Modify**: `backend/app/api/v1/agora.py`
  - New endpoint: `GET /agora/leaderboard` (30/min rate limit)
  - Query `user_progressions` where `quest_active=true`, order by milestones count desc
  - Filter by Agora privacy settings
  - Return: `{leaderboard: [{rank, display_name, quest_stage, milestones_completed, total_tasks}], user_rank}`
- **Modify**: `frontend/src/views/AgoraView.vue`
  - Add "Leaderboard" tab button
  - Table with styled rows, top 3 get medal icons
  - Own rank section at bottom

### Privacy
- Uses existing `get_agora_settings()` helper from `services/agora.py`
- Respects both `enabled` and `display_name_public` flags
- No new user-facing settings needed

---

## H4: Grand Prize Pedestal — The Village Shrine

**An evolving 3D object in Village Square that represents quest progress.**

### What it does
- Procedural 3D pedestal near Village Square center
- Evolves based on `questProgress.quest_stage`:
  - **No quest / Seeker**: Stone pedestal, faint white glow
  - **Adept**: Blue crystal shard appears, gentle pulse
  - **Opus**: Larger purple octahedron, orbiting particles, stronger glow
  - **Azothic**: Golden dodecahedron shrine, gold particle rain, "SensorHead Awaits" text sprite
- Click navigates to `/achievements`
- Classic users: pedestal hidden or shows decorative version

### Implementation
- **Modify**: `frontend/src/composables/useVillage3D.js`
  - New function `_createPedestal()` — CylinderGeometry base + stage-specific elements
  - New function `evolvePedestal(stage)` — swaps stage elements (crystal/octahedron/shrine)
  - Add pedestal rotation + particle emission in `_animate()` loop
  - Add pedestal to raycasting targets, emit `pedestal-click` event
  - Position: offset from fountain, e.g. `[3, 0, -3]` in Village Square area
- **Modify**: `frontend/src/components/village/Village3D.vue`
  - Expose `evolvePedestal` method
- **Modify**: `frontend/src/views/VillageGUIView.vue`
  - Call `evolvePedestal(questProgress.quest_stage)` in `applyQuestLockState()`
  - Handle pedestal click → `router.push('/achievements')`

### Three.js patterns (reuse existing)
- Procedural geometry like zone buildings
- PointLight for glow (like agent glow rings)
- ParticleSystem for orbiting effects
- Canvas texture for floating text (like speech bubbles)

---

## H5: Shareable Achievement Cards — Viral Moments

**Canvas-generated PNG cards for sharing achievements on social media.**

### What it does
- "Share" button on each unlocked achievement in AchievementsView
- Opens modal with canvas-rendered card preview (800x600)
- Card shows: achievement name, stage, description, unlock date, ApexAurum branding, gold border
- Actions: Download PNG, Copy to Clipboard
- Optional: "Post to Agora" creates an `achievement_share` content type post

### Implementation
- **Create**: `frontend/src/components/village/AchievementShareModal.vue` (~150 lines)
  - HTML5 Canvas rendering: dark gradient bg, gold border, text layout
  - `canvas.toDataURL()` for download, `canvas.toBlob()` + Clipboard API for copy
- **Modify**: `frontend/src/views/AchievementsView.vue`
  - Share button on unlocked cards, modal state
- **Modify**: `backend/app/api/v1/agora.py` (optional)
  - Add `achievement_share` to valid content types for Agora posting

---

## Execution Order

```
H1  Achievement Gallery          ← Foundation (trophy case)
H2  Agora Stage Badges           ← Quick win (social proof)
H3  Community Leaderboard        ← Competition (hall of fame)
H4  Grand Prize Pedestal         ← Visual anchor (3D shrine)
H5  Shareable Cards              ← Virality (share moments)
```

H1 first — it's the data backbone. H2+H3 are Agora enhancements (can be one commit). H4 is independent 3D work. H5 depends on H1 existing.

---

## Files Summary

### Create
| File | ~Lines | Purpose |
|------|--------|---------|
| `views/AchievementsView.vue` | ~250 | Trophy case grid |
| `components/village/AchievementShareModal.vue` | ~150 | Canvas card generator |

### Modify
| File | Sub-phase | Changes |
|------|-----------|---------|
| `router/index.js` | H1 | Add `/achievements` route |
| `components/Navbar.vue` | H1 | Add Achievements link (desktop + mobile) |
| `backend/app/api/v1/agora.py` | H2, H3, H5 | Stage badge in posts, leaderboard endpoint, achievement_share type |
| `frontend/src/views/AgoraView.vue` | H2, H3 | Badge chips, leaderboard tab |
| `frontend/src/composables/useVillage3D.js` | H4 | Pedestal creation + evolution |
| `frontend/src/components/village/Village3D.vue` | H4 | Expose evolvePedestal |
| `frontend/src/views/VillageGUIView.vue` | H4 | Wire pedestal to quest stage |

---

## Key Data Reference

### 25 Quest Milestones (from backend/app/services/progression.py)

**Seeker (8):** first_chat, meet_agents, zone_visit, web_search, file_upload, three_zones, council_first, seeker_mastery
**Adept (8):** music_gen, memory_store, bridge_connect, agent_level_3, opus_model, zone_master, council_expert, adept_mastery
**Opus (5):** dream_engine, nursery_train, all_zones, agent_level_7, full_opus
**Azothic (4):** all_agents_5, council_master, athanor_complete, sensorhead_earned

### 10 E5 Achievements (from useVillageGamification.js)

first_task, five_tasks, full_house, council_convened, zone_explorer, zone_master, agent_veteran, all_zones, streak_3, fifty_tasks

### Stage Symbols
- Seeker: ⚗ (grey)
- Adept: ⚡ (blue)
- Opus: ✦ (purple)
- Azothic: ∴ (gold)

---

## Verification

1. **H1**: Open `/achievements` — see 35 cards grouped by stage, locked/unlocked visuals, progress bar
2. **H2**: Open Agora — quest users' posts show colored stage badge next to name
3. **H3**: Agora Leaderboard tab — ranked list, own rank visible, privacy respected
4. **H4**: Village 3D — pedestal visible near square, evolves when quest stage changes, clickable
5. **H5**: Click Share on unlocked achievement — card renders, download works, clipboard works
6. `npm run build` passes after each sub-phase

---

*"Where every achievement becomes a trophy, and every trophy tells a story."*
