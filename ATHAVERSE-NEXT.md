# Athaverse — Current Plan

> Updated: 2026-02-16
> **Active: Phase 9 — FPV Agent Mode**

---

## Shipped Phases (Complete)

| Phase | Description | Status |
|-------|-------------|--------|
| 0-1 | InstancedMesh, 160x160 village, 6 outer ring zones | Shipped |
| 2 | District Manager — 4x4 grid, camera tracking, boundaries | Shipped (841447f) |
| 3-4 | Multiverse portal system (backend + frontend) | Shipped (37f359f) |
| 5 | Visitor ghost agents from other villages | Shipped (e4e7e84) |
| 6 | Cross-village economy tab — leaderboard, transactions, stats | Shipped (6629c78) |
| 7 | Space transitions — CSS overlay + sigil flash between 3D views | Shipped (f99b867) |
| 8 | Interactive task dialog — streaming mini-chat with follow-ups | Shipped (57db365) |
| F | Quest Engine — 25 milestones, feature gating, 6 API endpoints | Shipped |
| G | Guided Path — locked visuals, QuestHUD, unlock ceremonies, tutorial | Shipped |
| H | Grand Prizes — achievement gallery, Agora badges, 3D pedestal, share cards | Shipped |

---

## Phase 9: FPV Agent Mode

**Goal:** Click an agent in the Village 3D view, enter First Person View through that agent's eyes. Each agent has a unique visual signature — different post-processing, color grading, and effects that reflect their personality.

### 9.1 — Post-Processing Foundation

**New composable:** `useVillagePostProcessing.js` (~150 lines)

Install `postprocessing` (pmndrs) — merged-pass EffectComposer for performance.

- Create `EffectComposer` that wraps the existing renderer
- Define per-agent effect profiles (see table below)
- `activateProfile(agentId)` / `deactivateProfile()` to swap effects
- Hook into existing render loop via `addAnimationCallback()`

**Per-Agent Vision Profiles:**

| Agent | Color Grade | Signature Effects | Mood |
|-------|-------------|------------------|------|
| AZOTH | Warm gold tones | Bloom + film grain + subtle lens flare | Alchemical, ancient |
| VAJRA | Cool blue shift | Chromatic aberration + scan lines + glitch | Technical, precise |
| ELYSIAN | Soft pink/rose | Heavy depth of field + vignette + dream blur | Ethereal, emotional |
| KETHER | Deep purple | God rays + noise + volumetric fog | Mystical, transcendent |

**Package:** `npm install postprocessing`

### 9.2 — FPV Camera & Movement

**New composable:** `useFPVMode.js` (~200 lines)

- `PointerLockControls` from `three/addons` — FPS mouse look
- WASD movement with configurable speed
- Head bob (sinusoidal Y offset tied to movement speed, ~15 lines)
- Camera positioned at agent eye height
- Smooth transition animation: OrbitControls -> FPV (dolly + rotate blend)
- ESC to exit FPV, return to orbit view
- `enterFPV(agentId, position, rotation)` / `exitFPV()`
- Expose `isFPV` ref for UI to react (hide HUD elements, show FPV overlay)

### 9.3 — Village3D Integration

Wire FPV into existing click flow:

- Agent click currently opens task dialog or navigates to chat
- Add FPV option: hold click / long press / dedicated button in agent popup
- On FPV enter: disable OrbitControls, activate PointerLock, apply agent post-processing
- On FPV exit: restore OrbitControls, remove post-processing, return camera
- Pause district tracking / HUD while in FPV

### 9.4 — FPV UI Overlay

Minimal HUD while in first-person:

- Agent name + identity badge (top-left)
- "Press ESC to exit" hint (bottom-center, fades after 3s)
- Optional: agent-themed crosshair or reticle
- Optional: interact prompt when looking at other agents / buildings

### 9.5 — Physics & Collision (Optional Enhancement)

**Package:** `npm install @dimforge/rapier3d` (Rust/WASM)

- `KinematicCharacterController` for proper collision response
- Step-over for low obstacles, slope limits
- Boundary enforcement (stay within village 160x160)
- Only add if movement without collision feels too floaty

**Files:**
- `frontend/src/composables/useFPVMode.js` (new)
- `frontend/src/composables/useVillagePostProcessing.js` (new)
- `frontend/src/composables/useVillage3D.js` (wire FPV entry/exit)
- `frontend/src/components/village/Village3D.vue` (FPV toggle in agent interaction)
- `frontend/src/views/VillageGUIView.vue` (FPV UI overlay)

---

## Loose Ends (Minor Priority)

### A. Wire Multiverse WS Events
- `start_visit()` / `end_visit()` should broadcast `visitor_arrived` / `visitor_departed`
- Currently at route layer — verify sufficiency or move into MultiverseService

### B. Navbar Item Centering
- Desktop nav items follow logo to far left instead of staying centered
- Fix: center column `flex-1 justify-center`, logo + user menu as fixed-width bookends

### C. Unused WS Event Types
- `visitor_moved`, `visitor_tip`, `portal_request`, `portal_activated` — defined but never broadcast
- Wire them up for future use or remove dead code

### D. Visit Timeout Cleanup
- `VISIT_TIMEOUT_HOURS = 24` defined but never enforced
- Add periodic cleanup or lazy check on visit-related queries

---

## Future Horizons

- **WebGPU + TSL** — Three.js v0.171+ for compute shaders, node-based materials
- **Rapier physics** — full collision world for village navigation
- **WebXR extension** — FPV mode naturally extends to VR headsets via Three.js WebXRManager
- **realism-effects** — SSGI, SSR, motion blur for near-photorealistic rendering
- **Gaussian Splatting** — photogrammetry environments in browser

---

*"See through the eyes of the Athanor's agents. Each perspective a new alchemy."*
