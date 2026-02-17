# Athaverse — Current Plan

> Updated: 2026-02-17
> **Phases 13, 14, 16 SHIPPED** — Building Interiors, Physics, Weather

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
| 9 | FPV Agent Mode — per-agent vision, PointerLock WASD, post-processing profiles | Shipped (b3a591c) |
| 10 | FPV Agent Interaction — proximity prompt, E-key chat, streaming bubbles | Shipped (7dd6d27) |
| 11 | Spatial Audio — zone ambients, TTS agent voices, FPV footsteps, volume control | Shipped |
| 12 | Day/Night Cycle — dynamic lighting, sky gradient, firefly/star modulation | Shipped (166deec) |
| 13 | Building Interiors — procedural rooms, exit portals, 7 unique interiors, LRU cache | Shipped |
| 14 | Physics & Collision — Rapier3D WASM, character controller, building colliders, agent raycasting | Shipped |
| 15 | Agent Autonomy — wandering, zone preferences, musings, agent-to-agent dialogue | Shipped |
| 16 | Weather & Atmosphere — rain, snow, fog, storm, aurora, lightning, probability schedule | Shipped |
| 17 | WebXR VR Mode — Quest 3 immersive VR, thumbstick locomotion, comfort vignette | Shipped |

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

- **Phase 18: Hand Tracking** — Meta Quest hand input, gesture-based interactions
- **Phase 19: VR UI Panels** — Floating spatial panels for chat, task dialog, settings in VR
- **Phase 20: Agent Avatars in VR** — Full-body IK, eye tracking, lip sync
- **WebGPU + TSL** — Three.js v0.171+ for compute shaders, node-based materials
- **realism-effects** — SSGI, SSR, motion blur for near-photorealistic rendering
- **Gaussian Splatting** — photogrammetry environments in browser

---

*"See through the eyes of the Athanor's agents. Each perspective a new alchemy."*
