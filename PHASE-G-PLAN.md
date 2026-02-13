# Phase G: The Guided Path

> *"The difference between a feature list and an adventure is how it feels to unlock each one."*

## Context

Phase F built the Quest Engine — server-side milestones, feature gating, progression API. Phase G is the game design layer that makes all that data *feel* like a journey. This is the biggest UX phase: locked visuals, unlock ceremonies, progress tracking, tutorials, and stage transitions.

Sub-phased for incremental delivery. Each sub-phase is independently deployable and adds visible value.

---

## G1: Locked Village — The Visual Gate

**The foundation: quest users see a dim, locked Village that awakens as they progress.**

### What it does
- Quest tier users see zone buildings dimmed (opacity 0.4, desaturated)
- Padlock icon sprite above locked buildings
- Unlocked buildings at full brightness + color
- Classic tier users: no change (everything bright, no padlocks)
- Transition: when a feature unlocks, building goes from dim -> full (instant for now, G3 adds ceremony)

### Implementation
- `Village3D.vue`: Accept `lockedZones` prop (array of zone names)
- `useVillage3D.js`: New methods `setZoneLocked(zone, locked)` — adjusts building material emissive/opacity, adds/removes padlock sprite
- `VillageGUIView.vue`: Compute `lockedZones` from `questProgress.features_unlocked` + `FEATURE_REGISTRY` mapping
- Padlock sprite: Small canvas-drawn padlock icon (gold outline, ~16x20px) positioned above building

### Zone-to-feature mapping
| Zone | Feature gate | Milestone to unlock |
|------|-------------|-------------------|
| Workshop | `basic_chat` | `first_chat` |
| Library | `web_search` | `web_search` |
| DJ Booth | `music_gen` | `music_gen` |
| Memory Garden | `memory_system` | `memory_store` |
| File Shed | `file_vault` | `file_upload` |
| Bridge Portal | `external_integrations` | `bridge_connect` |
| Watchtower | `multi_agent` | `council_first` |
| Village Square | Always unlocked | — |

### Files
- Modify: `useVillage3D.js`, `Village3D.vue`, `VillageGUIView.vue`
- New: None (all within existing files)

---

## G2: Quest HUD — Progress at a Glance

**A compact heads-up display showing quest stage, milestone progress, and next objective.**

### What it does
- Floating panel (top-right or bottom-left of Village viewport)
- Shows: current stage badge (Seeker/Adept/Opus/Azothic), progress bar, next milestone name + description
- Milestone checklist: expandable list with checkmarks
- Compact by default (just stage + progress bar), expands on click
- Only visible for quest tier users (hidden for classic)
- Subtle glow pulse on the "next milestone" when user is close to completing it

### Layout concept
```
┌─────────────────────────┐
│ ⚗ SEEKER     ████░░ 3/8 │  <- compact view (always visible)
│                         │
│ ✓ First Steps           │  <- expanded checklist
│ ✓ Meet the Council      │
│ ✓ Village Explorer       │
│ → Knowledge Seeker       │  <- next milestone (highlighted)
│ ○ Archivist             │
│ ○ Pathfinder            │
│ ○ Council Convened      │
│ ○ Seeker Mastery        │
└─────────────────────────┘
```

### Implementation
- New component: `QuestHUD.vue` — self-contained, reads from `useVillageGamification().questProgress`
- Positioned absolute over the Village viewport
- Tailwind styling matching existing apex-dark theme
- Animated progress bar (CSS transition on width)
- Stage badge uses alchemical symbols: ⚗ Seeker, ⚡ Adept, ✦ Opus, ∴ Azothic

### Files
- Create: `frontend/src/components/village/QuestHUD.vue`
- Modify: `VillageGUIView.vue` (import + position QuestHUD)

---

## G3: Unlock Ceremonies — The Dopamine Moment

**When a milestone completes, the Village celebrates. Camera moves, particles rain, sound plays.**

### What it does
- On milestone completion (detected via `lastServerMilestones` watcher):
  1. Camera smoothly pans to the newly unlocked building (1.5s tween)
  2. Building transitions from dim -> full brightness (0.5s fade)
  3. Padlock sprite shatters (scale down + fade out)
  4. Gold particle shower above the building (60 particles, 3s duration)
  5. Achievement bubble appears: "Workshop Unlocked!" with milestone name
  6. Fanfare sound (reuse devModeActivate or new ascending arpeggio)
  7. Camera returns to previous position (1s tween)
- Queue system: if multiple milestones unlock at once, ceremonies play sequentially
- Skip button: click anywhere to skip current ceremony

### Implementation
- `useVillage3D.js`: New method `playUnlockCeremony(zoneName, callback)` — orchestrates camera tween, material fade, particle burst
- Camera tween: GSAP-style lerp (no new dependency, use existing animation loop)
- Particle shower: extend existing `ParticleSystem` with a "rain" pattern (particles fall from above)
- `VillageGUIView.vue`: Update `lastServerMilestones` watcher to trigger ceremonies instead of simple bursts

### Files
- Modify: `useVillage3D.js`, `VillageGUIView.vue`
- Potentially: `Village3D.vue` (expose ceremony method)

---

## G4: Tutorial Overlay — The First Steps

**A skippable step-by-step walkthrough for first-time Village visitors.**

### What it does
- Triggers on first Village visit (check localStorage flag `village_tutorial_complete`)
- 5-6 tooltip steps with spotlight effect (dim everything except the target)
- Each step: floating tooltip with arrow pointing at element, text explanation, "Next" / "Skip" buttons
- Steps:
  1. "Welcome to the Village!" — overview, pan camera around
  2. "These are the Zones" — highlight Workshop building
  3. "Click a zone to assign a task" — spotlight zone click area
  4. "Choose an agent" — show agent avatar, explain roles briefly
  5. "Complete tasks to unlock new zones" — show progress HUD
  6. "Your quest begins!" — dismiss, mark tutorial complete

### Implementation
- New component: `VillageTutorial.vue` — overlay with spotlight mask
- Spotlight: CSS clip-path or SVG mask that reveals a circular area around the target
- Step definitions: array of `{ target, position, title, text }` objects
- Camera control: tutorial can request camera focus on specific positions
- Persists completion to localStorage (not server — no quest tier required)
- Classic tier users get a shorter version (no mention of unlocking)

### Files
- Create: `frontend/src/components/village/VillageTutorial.vue`
- Modify: `VillageGUIView.vue` (mount tutorial, check localStorage flag)

---

## G5: Agent Unlock Progression — Earn Your Team

**Quest users start with AZOTH only. Other agents unlock through milestones.**

### What it does
- Quest users see 3 agents as silhouettes (greyed out, no glow, "?" nameplate)
- AZOTH is always available (the guide)
- `meet_agents` milestone unlocks all 4 agents — but the *visual reveal* is staged:
  - After first chat with a second agent, that agent's silhouette becomes full color
  - Achievement-style reveal animation per agent
- Agent popup for locked agents shows: "Complete [milestone] to unlock [agent name]"
- Classic tier users: all agents visible as normal

### Implementation
- `useVillage3D.js`: Modify agent material system — `setAgentLocked(agentId, locked)` desaturates material, hides glow ring
- `Village3D.vue`: Accept `lockedAgents` prop, agent popup shows lock state
- `VillageGUIView.vue`: Compute locked agents from quest features
- Silhouette effect: set agent mesh material to dark grey with low emissive, hide nameplate text (show "?" instead)

### Files
- Modify: `useVillage3D.js`, `Village3D.vue`, `VillageGUIView.vue`

---

## G6: Stage Transitions — The Grand Ceremonies

**When a user completes all milestones in a stage, a full-screen ceremony marks the ascension.**

### What it does
- Triggered when `stage_complete: true` comes back from server
- Full-screen overlay with alchemical theme:
  1. Screen dims, gold border glow appears
  2. Stage emblem fades in center: "SEEKER COMPLETE" / "ADEPT ACHIEVED" etc
  3. Particle constellation traces the stage symbol
  4. New stage name fades in: "You are now an Adept"
  5. Camera pulls back to show the full Village — newly unlocked zones illuminate sequentially
  6. "Continue" button dismisses overlay
- Sound: Dramatic ascending chord sequence (distinct from milestone jingle)
- Stores viewed ceremonies in localStorage (don't replay on refresh)

### Implementation
- New component: `StageTransition.vue` — full-screen overlay with CSS animations
- Canvas or SVG for the emblem/constellation effect
- Sequential zone illumination: call `setZoneLocked(zone, false)` with staggered delays
- `VillageGUIView.vue`: Watch for `questProgress.quest_stage` changes, trigger component

### Files
- Create: `frontend/src/components/village/StageTransition.vue`
- Modify: `VillageGUIView.vue`

---

## Execution Order

```
G1  Locked Village visuals          ← Foundation (see locked state)
G2  Quest HUD                       ← Progress tracking (see the path)
G3  Unlock Ceremonies               ← Reward feedback (feel the unlock)
G4  Tutorial Overlay                ← Onboarding (learn the system)
G5  Agent Unlock Progression        ← Depth (earn your team)
G6  Stage Transitions               ← Grand moments (celebrate ascension)
```

G1 + G2 form the **minimum viable quest experience** — users can see what's locked and track progress.
G3 adds the **game feel** — the dopamine loop.
G4 smooths the **onboarding** — nobody gets lost.
G5 + G6 add **depth and drama** — the full Athaverse experience.

Each sub-phase is independently deployable and adds visible value.

---

## Psychology Notes

The progression follows established game design patterns:
- **Variable ratio reinforcement**: Milestones vary in difficulty (easy wins early, harder later)
- **Loss aversion**: Dimmed buildings create desire to "fill in" the Village
- **Near-miss effect**: Progress bar at 7/8 milestones is more motivating than 1/8
- **Ceremony as reward**: The unlock animation is the reward, not just the feature access
- **Escalating commitment**: Each stage requires more investment, but the user has already invested
- **Social proof**: Stage badges visible in Agora posts (Phase H)
- **Endowed progress**: Starting with 1 unlocked zone (Workshop) gives users a head start feeling

---

*"The Guided Path: where every click brings the Village to life."*
