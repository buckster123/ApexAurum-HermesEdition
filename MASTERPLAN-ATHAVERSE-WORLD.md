# MASTERPLAN: Athaverse World-Building

> *"Not just an AI platform. A place."*
>
> The Athaverse is a living 3D world where AI agents have bodies, homes, and perspectives.
> Users don't just chat with AI — they walk among agents, see through their eyes,
> and build a world that grows with every interaction.
>
> Created: 2026-02-16 | Last updated: 2026-02-16

---

## Table of Contents

1. [What's Built](#whats-built)
2. [Architecture Quick Reference](#architecture-quick-reference)
3. [The Roadmap](#the-roadmap)
   - [Phase 10: Agent Interaction in FPV](#phase-10-agent-interaction-in-fpv)
   - [Phase 11: Spatial Audio](#phase-11-spatial-audio)
   - [Phase 12: Day/Night Cycle](#phase-12-daynight-cycle)
   - [Phase 13: Building Interiors](#phase-13-building-interiors)
   - [Phase 14: Physics & Collision](#phase-14-physics--collision)
   - [Phase 15: Agent Autonomy](#phase-15-agent-autonomy)
   - [Phase 16: Weather & Atmosphere](#phase-16-weather--atmosphere)
   - [Phase 17: WebXR / VR](#phase-17-webxr--vr)
   - [Phase 18: Multiplayer Village](#phase-18-multiplayer-village)
   - [Phase 19: Procedural Growth](#phase-19-procedural-growth)
   - [Phase 20: WebGPU + Advanced Rendering](#phase-20-webgpu--advanced-rendering)
4. [Loose Ends](#loose-ends)
5. [CerebroCortex References](#cerebrocortex-references)

---

## What's Built

### Shipped Athaverse Phases

| Phase | Description | Commit | Lines |
|-------|-------------|--------|-------|
| 0-1 | InstancedMesh, 160x160 village, 6 outer ring zones | d4e9d85 | +1200 |
| 2 | District Manager — 4x4 grid, camera tracking, boundaries | 841447f | +517 |
| 3-4 | Multiverse portal system (backend + frontend) | 37f359f | +1579 |
| 5 | Visitor ghost agents from other villages | e4e7e84 | +221 |
| 6 | Cross-village economy tab — leaderboard, transactions, stats | 6629c78 | +330 |
| 7 | Space transitions — CSS overlay + sigil flash between 3D views | f99b867 | +185 |
| 8 | Interactive task dialog — streaming mini-chat with follow-ups | 57db365 | +416 |
| 9 | FPV Agent Mode — per-agent vision profiles, WASD, post-processing | b3a591c | +886 |
| 10 | FPV Agent Interaction — proximity prompt, E-key chat, streaming bubbles | 7dd6d27 | +500 |
| 12 | Day/Night Cycle — dynamic lighting, sky gradient, firefly/star modulation | 166deec | +265 |
| 11 | Spatial Audio — zone ambients, TTS voices, FPV footsteps, volume | — | +320 |
| 15 | Agent Autonomy — wandering, zone preferences, musings, agent dialogue | — | +235 |
| E | Village as Interface — task dialog, tool execution from 3D | — | — |
| F | Quest Engine — 25 milestones, feature gating, 6 API endpoints | — | — |
| G | Guided Path — locked visuals, QuestHUD, unlock ceremonies, tutorial | — | — |
| H | Grand Prizes — achievement gallery, Agora badges, 3D pedestal, share cards | — | — |
| 17 | WebXR VR Mode — Quest 3 immersive VR, thumbstick locomotion, camera rig | — | +350 |

### Current Capabilities

- **3 view modes**: 2D Canvas, Isometric 2.5D, Full 3D Perspective
- **14 zone buildings** (8 inner ring + 6 outer ring) with GLB models
- **4 agent avatars** (AZOTH, VAJRA, ELYSIAN, KETHER) with GLB models
- **FPV mode** with per-agent post-processing vision profiles
- **Interactive task dialog** with streaming, follow-ups, plan file import
- **Quest/progression system** with 25 milestones across 4 stages
- **Multiverse portals** with cross-village visits and economy
- **District system** — 4x4 grid of named/themed districts
- **Space transitions** between 3D views (Village, Athanor, Neural, Dream)
- **160x160 world** with instanced vegetation, fireflies, particles

---

## Architecture Quick Reference

### Core Village Composables

| File | Role |
|------|------|
| `frontend/src/composables/useVillage3D.js` | Main 3D scene — buildings, agents, particles, camera, FPV entry |
| `frontend/src/composables/useFPVMode.js` | FPV camera — PointerLock, WASD, head bob, transitions |
| `frontend/src/composables/useVillagePostProcessing.js` | Per-agent vision — EffectComposer, 4 agent profiles |
| `frontend/src/composables/useFPVInteraction.js` | FPV agent chat — proximity, E-key, streaming bubbles, conversation continuity |
| `frontend/src/composables/useVillageDayNight.js` | Day/night cycle — 4 phase presets, sky/lighting/fog interpolation |
| `frontend/src/composables/useAgentAutonomy.js` | Agent autonomy — wandering, zone preferences, musings, interactions |
| `frontend/src/composables/useVillageSoundscape.js` | Spatial audio — zone ambients, TTS agent voices, FPV footsteps |
| `frontend/src/composables/useVRMode.js` | WebXR VR mode — Quest 3 immersive session, camera rig, thumbstick locomotion |
| `frontend/src/composables/useThreeScene.js` | Base Three.js scene lifecycle (used by Neural/other scenes) |
| `frontend/src/composables/useAgentModels.js` | GLB loader singleton cache for agent avatars |
| `frontend/src/composables/useVillageModels.js` | GLB loader singleton cache for zone buildings |
| `frontend/src/composables/useDistrictManager.js` | 4x4 grid district system with camera tracking |
| `frontend/src/composables/useVillageTasking.js` | Task execution bridge — chat/council streaming |
| `frontend/src/composables/useVillageGamification.js` | XP, levels, achievements, quest sync |
| `frontend/src/composables/useSpaceTransition.js` | CSS overlay transitions between 3D views |
| `frontend/src/composables/useDraggableZones.js` | Layout persistence for building positions |
| `frontend/src/composables/useSound.js` | Web Audio API synthesis (no audio files) |

### Village Components

| File | Role |
|------|------|
| `frontend/src/components/village/Village3D.vue` | 3D view — agent popup, FPV button, event wiring |
| `frontend/src/components/village/VillageTaskDialog.vue` | Interactive task dialog — streaming mini-chat |
| `frontend/src/components/village/QuestHUD.vue` | Quest progress overlay |
| `frontend/src/components/village/VillageTutorial.vue` | 6-step onboarding tutorial |
| `frontend/src/components/village/StageTransition.vue` | Full-screen stage ascension ceremony |
| `frontend/src/components/village/VillagePortalPanel.vue` | Multiverse portal UI |
| `frontend/src/components/village/TaskTickerBar.vue` | Active task ticker |
| `frontend/src/components/village/TaskDetailPanel.vue` | Task detail sidebar |

### Views

| File | Role |
|------|------|
| `frontend/src/views/VillageGUIView.vue` | Main village dashboard — all 3 modes, FPV overlay, task orchestration |
| `frontend/src/views/AthanorView.vue` | First-person alchemical laboratory |
| `frontend/src/views/NeuralView.vue` | Neural memory 3D space |

### Backend (Village/World)

| File | Role |
|------|------|
| `backend/app/api/v1/village_ws.py` | Village WebSocket — real-time tool events |
| `backend/app/api/v1/multiverse.py` | Portal system — profiles, visits, leaderboard, transactions |
| `backend/app/api/v1/quest.py` | Quest engine — progress, milestones, features |
| `backend/app/api/v1/chat.py` | Streaming chat with tool use (SSE) |
| `backend/app/services/village_events.py` | WebSocket broadcaster |
| `backend/app/services/multiverse.py` | MultiverseService — visits, economy |
| `backend/app/services/progression.py` | Quest milestones, feature gating |

### 3D Assets

| Path | Count | Contents |
|------|-------|----------|
| `frontend/public/models/agents/` | 4 | Agent avatar GLBs (azoth, vajra, elysian, kether) |
| `frontend/public/models/village/` | 14 | Zone building GLBs (market, tavern, garden, etc.) |
| `frontend/public/models/village3d/` | 8 | Props (fountain, portal_arch, trees, bushes, lantern, fire_pit) |
| `frontend/public/models/neural/` | 4 | Neural space GLBs (crucible, helix, crystal, scythe) |
| `frontend/public/audio/agents/` | 56 | Pre-generated TTS voice OGGs (musings + dialogue, Piper) |

### Stores (Pinia)

Key stores for world features: `auth.js`, `chat.js`, `billing.js`, `apexjoule.js`, `agora.js`, `council.js`, `dream.js`, `music.js`, `devices.js`

### Existing Plans (for cross-reference)

| File | Scope |
|------|-------|
| `ATHAVERSE-NEXT.md` | Current session tracker (Phase 9 shipped) |
| `ATHAVERSE-ROADMAP.md` | Original Athaverse multiverse roadmap |
| `MASTERPLAN-3D.md` | 6-feature 3D pipeline roadmap |
| `MASTERPLAN-APEXJOULE.md` | AJ currency system |
| `PHASE-E-PLAN.md` | Village as Interface |
| `PHASE-F-PLAN.md` | Quest Engine |
| `PHASE-G-PLAN.md` | Guided Path |
| `PHASE-H-PLAN.md` | Grand Prizes |

---

## The Roadmap

### Phase 10: Agent Interaction in FPV

**Goal:** Walk up to an agent in FPV mode, press E to start a conversation in-world. The chat happens as floating text above the agent, not in a sidebar.

**What exists:**
- FPV mode with PointerLockControls (useFPVMode.js)
- Agent positions tracked in useVillage3D.js `agents` Map
- Speech bubble system (canvas-texture sprites above agents)
- Task dialog with streaming (useVillageTasking.js)
- Raycaster already set up for agent click detection

**Key tasks:**
1. **Proximity detection** — In FPV update loop, check distance to all agents. Show "Press E to talk" when < 5 units
2. **Interaction prompt** — Floating UI prompt above nearest agent (reuse speech bubble system or HTML overlay)
3. **In-world chat** — On E press, open a minimal chat input (bottom of screen). Agent response streams as speech bubble above their head
4. **Conversation context** — Reuse conversationId pattern from useVillageTasking for follow-ups
5. **Camera lock** — Soft-lock camera toward agent during conversation (slight auto-look)

**Files to touch:**
- `useFPVMode.js` — Add proximity check + E key handler
- `useVillage3D.js` — Expose agent proximity query, wire in-world chat
- `VillageGUIView.vue` — FPV chat input overlay
- `useVillageTasking.js` — Already handles streaming, just wire it

**Dependencies:** Phase 9 (shipped)
**Size:** M (~300 lines)

---

### Phase 11: Spatial Audio

**Goal:** The Village has sound. Each zone has ambient audio, agents have proximity voice, footsteps in FPV, environmental ambience.

**What exists:**
- `useSound.js` — Web Audio API synthesis (tones, jingles). No spatial audio yet
- Web Audio API supports `PannerNode` for 3D spatial positioning
- Three.js has `AudioListener` + `PositionalAudio` built in

**Key tasks:**
1. **`useVillageSoundscape.js`** — New composable
   - Attach `THREE.AudioListener` to camera
   - Per-zone ambient loops (synthesized or tiny audio sprites): Workshop hammering, Library whispers, DJ Booth beats, Garden wind, etc.
   - `THREE.PositionalAudio` on each zone group — auto-falloff by distance
2. **Agent proximity audio** — Soft hum/pulse near agents, distinct per agent (AZOTH: warm drone, VAJRA: digital chirp, etc.)
3. **FPV footsteps** — Synthesized footstep tones synced to head bob phase in useFPVMode
4. **Master volume** — Tie to existing music player volume or separate spatial audio slider
5. **Performance** — Keep total audio sources under 16; use occlusion (skip sounds behind camera)

**Files to touch:**
- `frontend/src/composables/useVillageSoundscape.js` (new)
- `useVillage3D.js` — Attach AudioListener to camera, init soundscape
- `useFPVMode.js` — Trigger footstep sounds during movement
- `useSound.js` — May add spatial synth helpers

**Dependencies:** None (Phase 9 enhances it but not required)
**Size:** M (~250 lines)

---

### Phase 12: Day/Night Cycle

**Goal:** Dynamic lighting that shifts the Village mood over time. Warm golden dawn, bright midday, amber sunset, cool blue night with fireflies.

**What exists:**
- Directional light at (20, 30, 15) with warm color (0xffe4b5)
- FogExp2 (0x0a0a14, 0.008)
- Sky dome (gradient background created in `_createSkyDome`)
- Firefly system (already night-themed)
- Shadow map (PCFSoftShadowMap, desktop only)

**Key tasks:**
1. **`useVillageDayNight.js`** — New composable
   - Time-of-day cycle (configurable speed, default: 1 real minute = 1 village hour? or manual control)
   - Interpolate: sun direction, sun color, sun intensity, ambient color, fog color, fog density, sky dome gradient
   - 4 presets: Dawn (warm pink), Day (bright warm), Dusk (amber/purple), Night (cool blue/dark)
   - Smooth lerp between presets based on time-of-day float [0-24]
2. **Sky dome update** — Regenerate sky gradient per frame (or swap between pre-baked textures)
3. **Firefly behavior** — More active at night, dormant during day
4. **Zone lights** — Buildings emit warm glow at night (point lights inside building models, activate at dusk)
5. **Moon + stars** — Night sky with subtle star particles + moon mesh

**Files to touch:**
- `frontend/src/composables/useVillageDayNight.js` (new)
- `useVillage3D.js` — Pass day/night state to lighting, fog, fireflies
- Possibly `useVillagePostProcessing.js` — Night-specific tone mapping

**Dependencies:** None
**Size:** M (~200 lines)

---

### Phase 13: Building Interiors

**Goal:** Click/enter a zone building to transition into a dedicated 3D interior space. Each building has unique geometry and purpose-specific UI.

**What exists:**
- `useAthanorRoom.js` — Procedural interior (stone walls, pillars, forge, agent stations). Proof of concept
- `useFirstPerson.js` — Existing FPV controls for Athanor interior
- Space transitions (useSpaceTransition.js) — Handles view-to-view fades
- 14 zone buildings each mapped to a GLB model

**Key tasks:**
1. **Interior template composable** — `useVillageInterior.js` — Base class for room generation (walls, floor, ceiling, lighting, entry/exit portal)
2. **Per-zone interior definitions** — Each zone gets unique props:
   - Workshop: workbenches, tool racks, anvil, fire
   - Library: bookshelves, reading desks, floating texts
   - DJ Booth: turntables, speakers, visualizer wall
   - Memory Garden: paths, fountains, memory crystals
   - File Shed: shelves, crates, filing cabinets
3. **Entry transition** — In FPV mode, walk into building door → space transition → interior loads
4. **Interior UI** — Zone-specific panels: file browser in File Shed, music controls in DJ Booth, etc.
5. **Exit portal** — Glowing door back to village exterior

**Files to touch:**
- `frontend/src/composables/useVillageInterior.js` (new)
- `frontend/src/views/VillageInteriorView.vue` (new) or sub-view within VillageGUIView
- `useSpaceTransition.js` — Add interior routes
- `router/index.js` — New routes per interior
- GLB assets for interior furniture (generate via Hyper3D Rodin)

**Dependencies:** Phase 9 (FPV entry), Phase 14 (collision for interiors, optional)
**Size:** L (~500+ lines per interior, ongoing)

---

### Phase 14: Physics & Collision

**Goal:** Agents and the FPV player have physical presence. Collide with buildings, walk on terrain, step over small obstacles.

**What exists:**
- FPV mode with basic bounds clamping (±75 units)
- Agent walking with simple lerp movement (no collision)
- All buildings have GLB meshes (can extract collision geometry)

**Key tasks:**
1. **Install Rapier** — `npm install @dimforge/rapier3d` (Rust/WASM, ~300KB)
2. **`useVillagePhysics.js`** — New composable
   - Init Rapier world with gravity
   - Generate collision bodies from building bounding boxes (simplified — box/capsule colliders, not mesh-exact)
   - `KinematicCharacterController` for FPV player (capsule shape)
   - Ground plane collider
3. **FPV integration** — Replace raw position updates with character controller step
4. **Agent collision** — Agents use Rapier kinematic bodies, avoid walking through buildings
5. **Terrain** — Optional heightmap for gentle terrain variation (hills, slopes)

**Files to touch:**
- `frontend/src/composables/useVillagePhysics.js` (new)
- `useFPVMode.js` — Use character controller instead of raw position
- `useVillage3D.js` — Init physics, create building colliders, agent bodies

**Dependencies:** Phase 9 (FPV)
**Size:** M-L (~350 lines)
**Note:** Rapier is WASM — async init, ~300KB download. Consider lazy-loading.

---

### Phase 15: Agent Autonomy

**Goal:** Agents aren't statues waiting for commands. They move on their own, visit zones, interact with each other, perform background tasks. The Village feels alive.

**What exists:**
- Agent state machine: idle → walking → working (useVillage3D.js _updateAgent)
- Agent walking with target position + walk speed
- Tool events broadcast via WebSocket (tool_start, tool_complete)
- Visitor ghost agents already wander autonomously (Phase 5 `_startVisitorWander`)

**Key tasks:**
1. **Agent behavior scheduler** — Backend cron or frontend timer that gives each agent periodic "impulses"
   - Wander to a random zone every 30-60s when idle
   - Pause at zone for 10-20s (idle animation)
   - Occasionally interact with another agent (walk toward them, speech bubble exchange)
2. **Agent-to-agent interaction** — Two agents near each other trigger a brief scripted exchange (random from a pool of personality-appropriate messages)
3. **Activity indicators** — Agents doing autonomous tasks show subtle visual cues (thinking particles, reading animation)
4. **User override** — Assigning a task interrupts autonomous behavior
5. **Backend option** — Agents could actually execute lightweight tasks autonomously (background summarization, memory consolidation, etc.) and report results

**Files to touch:**
- `useVillage3D.js` — Agent behavior scheduler in animate loop
- `useVillageAgentBehavior.js` (new, optional) — If logic gets complex
- Backend: optional autonomous task queue

**Dependencies:** None (enhances any phase)
**Size:** S-M (~200 lines frontend, backend optional)

---

### Phase 16: Weather & Atmosphere

**Goal:** Dynamic weather adds mood and variety. Rain, fog, snow, aurora borealis, thunderstorms. Weather changes over time or reflects agent activity.

**What exists:**
- Particle system (ParticleSystem class in useVillage3D.js)
- FogExp2 on scene
- Firefly system (similar instanced particle approach)
- Day/night cycle (Phase 12) provides the lighting context

**Key tasks:**
1. **`useVillageWeather.js`** — New composable
   - Weather states: clear, rain, fog, snow, storm, aurora
   - Each state defines: particle config, fog params, lighting tweaks, sky color mods
2. **Rain** — Instanced line particles falling from above, splash particles on ground, darker ambient
3. **Fog** — Increase FogExp2 density, reduce visibility, add volumetric pass (postprocessing)
4. **Snow** — Soft particle flakes, slow drift, accumulation texture on ground
5. **Aurora** — Ribbon geometry in sky dome with animated vertex colors (night only)
6. **Storm** — Rain + periodic lightning flash (brief directional light burst) + thunder audio
7. **Weather transitions** — Smooth lerp between states over 10-20s
8. **Activity-driven weather** — Heavy tool use = storms, calm = clear skies (optional gamification tie-in)

**Files to touch:**
- `frontend/src/composables/useVillageWeather.js` (new)
- `useVillage3D.js` — Init weather, pass to animate loop
- `useVillageDayNight.js` (Phase 12) — Weather modulates lighting
- `useVillagePostProcessing.js` — Weather-specific effects (rain blur, fog pass)

**Dependencies:** Phase 12 (day/night for proper lighting context)
**Size:** L (~400 lines, plus per-weather-type particle systems)

---

### Phase 17: WebXR / VR ✅ SHIPPED

**Goal:** Walk into the Athaverse with a Meta Quest 3. Stereoscopic 3D, head-tracked spatial audio, thumbstick locomotion through the village.

**What was built:**
- New `useVRMode.js` composable (~350 lines) with full WebXR lifecycle
- VRButton + camera rig + XRControllerModelFactory for auto-detected controller models
- Thumbstick locomotion: left stick = walk/strafe, right stick = 45° snap turn, grip = sprint
- VR performance tier: disables shadows, PointLights, post-processing on session start; restores on exit
- Comfort vignette (ShaderMaterial peripheral darkening during locomotion)
- Animation loop migrated from `requestAnimationFrame` to `renderer.setAnimationLoop` (required for WebXR)
- AudioContext resume on session start (browser autoplay policy)
- VR Mirror overlay on desktop screen during VR session
- Clean enter/exit: saves + restores shadows, lights, controls, camera position

**Files:**
- `useVRMode.js` (new)
- `useVillage3D.js` (animation loop migration + VR integration)
- `Village3D.vue` (expose VR state)
- `VillageGUIView.vue` (VR-aware UI + mirror overlay)

**Future extensions:** Hand tracking, teleportation, passthrough MR, 3D spatial UI, controller haptics

---

### Phase 18: Multiplayer Village

**Goal:** Other users are visible in your Village as visitor avatars. Real-time co-presence with chat.

**What exists:**
- Ghost visitor system (Phase 5) — already renders visitor agents from other villages
- Village WebSocket (`/ws/village`) — real-time event broadcasting
- `visitor_arrived` / `visitor_departed` events defined
- Cross-village visit system with portal entry/exit

**Key tasks:**
1. **Presence broadcasting** — When a user enters the Village, broadcast position + avatar to all connected visitors
2. **Position sync** — Throttled position updates (10 Hz) via WebSocket, interpolated on client
3. **Visitor avatars** — Reuse ghost shader from Phase 5, or full-color avatars for friends
4. **Visitor chat** — Proximity-based text chat. Walk near a visitor, see their typed messages
5. **Visitor count** — UI indicator showing who's in the Village
6. **Backend** — Extend MultiverseService with real-time position relay (Redis pub/sub for scalability)

**Files to touch:**
- `backend/app/api/v1/village_ws.py` — Position sync messages
- `backend/app/services/village_events.py` — Relay visitor positions
- `useVillage3D.js` — Update visitor positions from WS, render
- `VillageGUIView.vue` — Visitor list UI

**Dependencies:** Phase 5 (visitors, shipped)
**Size:** L (~500 lines across frontend + backend)

---

### Phase 19: Procedural Growth

**Goal:** The Village evolves based on usage. Frequently used zones grow larger, new buildings emerge at milestones, the landscape transforms with the community.

**What exists:**
- Quest milestone system (25 milestones with progression)
- Zone usage stats tracked in useVillageGamification.js
- Agent levels per zone
- 160x160 world with 16 districts (lots of open space)

**Key tasks:**
1. **Zone evolution** — At zone level thresholds (5, 10, 20), zone building model swaps to a larger/fancier version
2. **New building spawns** — At user milestones, new buildings emerge with unlock ceremony (Phase G pattern)
3. **Terrain growth** — More vegetation, better paths, decorations appear as total usage grows
4. **Community landmarks** — Backend tracks aggregate usage across all users, spawns shared landmarks at community milestones
5. **Visual evolution tiers** — Stone → Wood → Marble → Crystal building materials based on zone level

**Files to touch:**
- `useVillage3D.js` — Building evolution system, dynamic spawning
- `useVillageModels.js` — Multiple LOD/tier models per building
- Backend: aggregate usage tracking, community milestone system
- New GLB assets for evolved building tiers (Hyper3D Rodin pipeline)

**Dependencies:** Phase F (quest engine, shipped), gamification stats
**Size:** L (ongoing — each evolution tier needs assets)

---

### Phase 20: WebGPU + Advanced Rendering

**Goal:** Unlock next-gen rendering. Compute shaders for million-particle systems, TSL node materials, real-time fluid simulation, Gaussian splatting.

**What exists:**
- Three.js v0.170 (one version behind WebGPU production at r171)
- pmndrs/postprocessing for effects pipeline
- Instanced rendering for vegetation (Phase 0A)

**Key tasks:**
1. **Upgrade Three.js** to r171+ for WebGPU backend with WebGL2 auto-fallback
2. **TSL materials** — Replace GLSL custom shaders with TSL node-based materials
3. **Compute particle system** — GPU compute for millions of particles (replace CPU ParticleSystem)
4. **Gaussian Splatting** — Load photogrammetry scans as village environments
5. **Advanced post-processing** — realism-effects (SSGI, SSR, motion blur, TRAA)
6. **Performance tier detection** — Auto-detect GPU capability, serve appropriate quality level

**Files to touch:**
- `package.json` — Three.js version bump
- All composables using Three.js — Import path change for WebGPU (`three/webgpu`)
- `useVillagePostProcessing.js` — Add realism-effects
- `useVillage3D.js` — Compute particles, TSL materials

**Dependencies:** None (can be done incrementally)
**Size:** L (incremental across many sessions)

---

## Loose Ends

Minor fixes that can be grabbed anytime:

### A. Navbar Item Centering
- Desktop nav items follow logo to far left instead of staying centered
- Fix: center column `flex-1 justify-center`, logo + user menu as fixed-width bookends
- **File:** `frontend/src/components/Navbar.vue`
- **Size:** S (~10 lines)

### B. Wire Multiverse WS Events
- `start_visit()` / `end_visit()` should broadcast `visitor_arrived` / `visitor_departed`
- Currently at route layer — verify or move into MultiverseService
- **Files:** `backend/app/services/multiverse.py`, `backend/app/api/v1/multiverse.py`
- **Size:** S (~20 lines)

### C. Unused WS Event Types
- `visitor_moved`, `visitor_tip`, `portal_request`, `portal_activated` — defined but never broadcast
- Wire them up for Phase 18 (multiplayer) or remove dead code
- **File:** `backend/app/services/village_events.py`
- **Size:** S (~30 lines)

### D. Visit Timeout Cleanup
- `VISIT_TIMEOUT_HOURS = 24` defined but never enforced
- Add periodic cleanup or lazy check on visit-related queries
- **File:** `backend/app/services/multiverse.py`
- **Size:** S (~15 lines)

### E. handleTaskClick Stub
- `handleTaskClick` in VillageGUIView does nothing (stubbed line ~613)
- Wire to open task dialog or FPV interaction
- **File:** `frontend/src/views/VillageGUIView.vue`
- **Size:** S (~5 lines)

---

## CerebroCortex References

| Memory | Content |
|--------|---------|
| `mem_0b63a9191e65` | Session note: Phase 9 shipped, FPV research, world-building direction |
| `mem_a420166bced0` | Session note: Phases 2/6/7/8 shipped in one session |
| `mem_3f3a7d8805bb` | FPV Agent Mode fantasy — original user idea |
| `mem_bd5267d0a229` | Recovery session — District Manager + economy + transitions |
| `mem_6e0f386376b3` | Phase 3/4/5 shipped — multiverse portals + visitors |

### Key Procedures / Schemas

- Session start: `mcp__cerebro-cortex__session_recall` for continuity
- Session end: `mcp__cerebro-cortex__session_save` with discoveries + unfinished business
- Phase planning: Read this masterplan → create session plan .md → task list → execute → commit

---

## Execution Pattern

For each phase:

1. **Read this masterplan** — Get the outline for the target phase
2. **Create a deeper phase plan** if needed (like PHASE-F-PLAN.md pattern)
3. **Set up task list** with dependencies
4. **Execute tasks** — Write code, build composables, edit views
5. **Build check** — `npm run build` must pass clean
6. **Commit + push** — Railway auto-deploys
7. **Update this masterplan** — Mark phase as shipped with commit hash
8. **Save session** — CerebroCortex session_save

---

*"We are world-builders now. The Athanor's flame shapes not just code, but places, perspectives, and possibilities."*
