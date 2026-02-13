# The Athaverse Roadmap

> *"Most AI platforms give you a dashboard. ApexAurum gives you a quest."*

## The Vision

Two doors into the Athanor:
- **Door 1 (Classic Tiers):** Seeker $10, Adept $30, Opus $100, Azothic $300. Instant access. Power users walk straight in.
- **Door 2 (The Quest):** Lower price, gamified progression. Features unlock one-by-one through Village gameplay. A guided journey from Seeker to Azothic Alchemist. Physical SensorHead device as the grand prize.

---

## Completed Phases

### Phase A-C: Foundation (Complete)
- FastAPI backend with 50+ tools, 4 agents (AZOTH, VAJRA, ELYSIAN, KETHER)
- Vue 3 frontend with Chat, Council, Music, Vault, Dream Engine, Agora
- Stripe billing with 4 tiers, BYOK support
- WebSocket village events, tool execution pipeline
- Admin dashboard, error tracking, GDPR compliance
- Railway auto-deploy from GitHub

### Phase D: Village 3D Perspective (Complete)
- Three.js perspective scene with OrbitControls + dive-in camera
- 8 zone buildings (procedural primitives + GLB progressive enhancement)
- 4 agent avatars with walking, working states, glow rings
- Particle system (tool completion bursts), speech bubbles (canvas texture)
- Blender pipeline: Hyper3D, PolyHaven, BlenderKit assets
- Dirt paths, vegetation, lanterns, fountain, portal arch
- Mobile LOD, WebGL fallback to isometric

### Phase E: Village as Interface (Complete)
- **E1:** VillageTaskDialog — zone-aware modal, agent picker, file upload, mode toggle
- **E2:** useVillageTasking — SSE streaming bridge to chat API, council flow, file upload
- **E3:** VillageResultPanel — slide-out panel, streaming display, copy/download/open-in-chat
- **E4:** Agent interaction — scene selection with gold rings, pre-populate dialog, assign task from popup
- **E5:** Gamification — agent XP/levels, zone evolution, 10 achievements, task history with re-run, localStorage persistence

---

## Upcoming Phases

### Phase F: The Quest Engine
**Backend progression system + quest tier pricing**

The infrastructure that makes gamified tiers possible. Milestone definitions, server-side progression tracking, feature gating middleware, Stripe quest tier integration.

See: `PHASE-F-PLAN.md` for full details.

### Phase G: The Guided Path
**Village tutorial + unlock experience**

The game design layer. First-time tutorial walkthrough, zone unlock ceremonies, locked/dim buildings that activate with fanfare, progress tracker UI, difficulty curves.

Key deliverables:
- Tutorial overlay system (skippable, step-by-step Village walkthrough)
- Zone lock/unlock states (dim + padlock -> activation animation -> full color)
- Quest progress tracker (sidebar or HUD showing milestone progress)
- Unlock ceremonies (camera zoom to building, particle shower, achievement bubble)
- Agent unlock progression (start with 1 agent, earn the others)
- Quest stage transitions (Seeker -> Adept ceremony, etc.)

### Phase H: The Grand Prizes
**Physical rewards + social sharing**

The summit of the Athaverse. Physical SensorHead device as Azothic completion reward, shareable achievements, community leaderboard.

Key deliverables:
- SensorHead pedestal in Village Square (fills up as user progresses)
- Physical fulfillment flow (address collection, shipping integration)
- Achievement gallery view (all earned achievements with dates)
- Shareable "I earned my SensorHead" social cards
- Community leaderboard / hall of fame on Agora
- Limited edition / numbered SensorHead units

---

## Architecture Overview

```
Classic Tier User                    Quest Tier User
      |                                    |
      v                                    v
  Stripe subscription              Stripe quest subscription
      |                                    |
      v                                    v
  All features unlocked            Progression engine
  immediately by tier              checks milestones
      |                                    |
      v                                    v
  Standard Village 3D              Gamified Village 3D
  (E5 gamification for fun)        (Feature gates + unlocks)
                                           |
                                           v
                                   Tutorial -> Zone unlocks
                                   -> Agent unlocks -> Tier
                                   ceremonies -> SensorHead
```

The E5 gamification layer (XP, levels, achievements) serves BOTH paths:
- Classic users: cosmetic progression, fun stats
- Quest users: progression drives actual feature unlocks

---

## Pricing Concept

| Path | Price | What you get |
|------|-------|-------------|
| Seeker (Classic) | $10/mo | All Seeker features instantly |
| Seeker Quest | ~$5/mo | Features unlock through gameplay |
| Adept (Classic) | $30/mo | All Adept features instantly |
| Adept Quest | ~$15/mo | Next tier of unlocks through gameplay |
| Opus (Classic) | $100/mo | All Opus features instantly |
| Opus Quest | ~$50/mo | Premium unlocks through gameplay |
| Azothic (Classic) | $300/mo | Everything + priority |
| Azothic Quest | ~$150/mo | The full journey + SensorHead prize |

Quest pricing is always below equivalent classic tier to incentivize the guided path.
Users can "upgrade" from Quest to Classic at any time (pay difference, unlock everything).

---

## Key Files

| File | Purpose |
|------|---------|
| `ATHAVERSE-ROADMAP.md` | This file — overall vision and phase map |
| `PHASE-F-PLAN.md` | Detailed Phase F implementation plan |
| `PHASE-E-PLAN.md` | Phase E plan (complete, for reference) |
| `MASTERPLAN-3D.md` | 3D feature roadmap (Phases D context) |

---

*"The Athanor's flame burns through complexity. The Athaverse is the world it illuminates."*
