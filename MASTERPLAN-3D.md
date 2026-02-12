# MASTERPLAN-3D: The Third Dimension of the Athanor

> *"From vectors and gradients painted in code, the Athanor takes form."*

## Overview

Six 3D features transforming ApexAurum from flat UI into an immersive alchemical experience. Each feature uses the battle-tested Blender-to-Frontend GLB pipeline and the existing `useThreeScene` composable foundation.

**Pipeline:** Blender (Windows) -> Hyper3D/PolyHaven/BlenderKit/bpy -> GLB Export -> HTTP Transfer (port 9880) -> `frontend/public/models/` -> GLTFLoader composable -> Vue 3 component

**Foundation already built:**
- `useThreeScene.js` — Scene lifecycle, animation loop, raycasting, camera focus
- `useAgentModels.js` — GLTFLoader singleton cache, auto-scaling clones
- `usePixelSprites.js` — Retro 2D fallback (Village keeps pixel art toggle)
- 4 agent GLBs: AZOTH (1.7MB), ELYSIAN (1.5MB), VAJRA (2.0MB), KETHER (1.8MB)

---

## Feature 1: Landing Page Athanor Hero

**View:** `LandingView.vue` (~439 lines)
**Impact:** First impression. Visitors see a living, breathing alchemist's forge.

### Concept

Replace the static radial gradient hero background with an interactive Three.js scene: a low-poly Athanor forge with glowing cauldron, floating alchemical symbols, and orbiting agent avatars. Subtle auto-rotation. Mouse parallax on the camera. The existing text overlays on top with `pointer-events: none`.

### Blender Work

Export from `AthanorForge_v3.blend` (already on Windows Desktop):
- **Athanor base** — The forge structure, simplified to <50K polys for web
- **Cauldron** — Central glowing element with emissive material
- **Floating symbols** — Wireframe platonic solids (icosahedron, octahedron) rotating
- **Agent avatars** — Already exported (azoth.glb, etc.), positioned around the forge

Generate/source additional assets:
- Floor/platform via PolyHaven stone texture on plane
- Ambient particles (gold sparks) via Three.js PointsMaterial (no Blender needed)
- HDRI-lit environment for reflections (PolyHaven studio HDRI baked to cubemap)

### Frontend Integration

```
frontend/
  src/
    components/
      landing/
        AthanorHero.vue          # NEW — Three.js hero scene component
    composables/
      useAthanorScene.js         # NEW — Scene-specific logic (parallax, agents orbit)
  public/
    models/
      athanor/
        forge.glb                # Athanor forge structure
        cauldron.glb             # Glowing cauldron centerpiece
        symbols.glb              # Wireframe sacred geometry group
```

**LandingView.vue changes:**
- Insert `<AthanorHero />` as absolute-positioned background behind hero section
- Keep text overlay with `z-10 pointer-events-none`
- Graceful fallback: if WebGL unavailable, show existing gradient

### Scene Architecture

```javascript
// useAthanorScene.js
- Load forge.glb, cauldron.glb, symbols.glb + agent GLBs
- Camera: perspective, positioned at (0, 3, 8), looking at origin
- Mouse parallax: camera.position.x/y += (mouseX/Y * 0.02) on mousemove
- Auto-rotate symbols group at 0.3 rad/s
- Agent avatars orbit forge at radius 3, offset heights
- Cauldron emissive pulse: sin(time) * 0.5 + 2.0
- Gold particle system: 200 points, upward drift, fade at top
- Fog: FogExp2 matching page background for seamless blend
```

### Performance Budget
- Total GLB: <5MB (forge ~2MB, cauldron ~500KB, symbols ~200KB, agents ~7MB cached)
- Target: 60fps on mid-range mobile, 30fps minimum
- LOD: Skip agent avatars on mobile (< 768px), show only forge + cauldron
- Lazy load: Start loading models only when hero section is visible

---

## Feature 2: Village 3D Building Upgrade

**View:** `VillageGUIView.vue` (~410 lines)
**Impact:** The Village's 3D isometric mode gets real buildings instead of placeholder geometry.

### Concept

The Village already has a working Three.js isometric view (`VillageIsometric`). Currently uses basic box geometry for zone buildings and sphere geometry for agents. Upgrade to themed GLB buildings for each zone while keeping the pixel sprite 2D mode as a toggle.

### Blender Work

8 zone buildings (low-poly isometric style, <5K polys each):

| Zone | Building | Source Strategy |
|------|----------|-----------------|
| `forge` | Blacksmith forge with chimney | Hyper3D: "low-poly isometric blacksmith forge" |
| `library` | Stone library with books | Hyper3D: "low-poly isometric medieval library" |
| `observatory` | Tower with telescope dome | Hyper3D: "low-poly isometric observatory tower" |
| `workshop` | Wooden workshop with tools | Hyper3D: "low-poly isometric carpenter workshop" |
| `garden` | Greenhouse with plants | Hyper3D: "low-poly isometric greenhouse garden" |
| `tavern` | Cozy tavern with sign | Hyper3D: "low-poly isometric medieval tavern" |
| `market` | Open market stall | Hyper3D: "low-poly isometric market stall" |
| `temple` | Small temple with columns | Hyper3D: "low-poly isometric greek temple" |

### Frontend Integration

```
frontend/
  src/
    composables/
      useVillageModels.js        # NEW — Village building GLB loader (same pattern as useAgentModels)
  public/
    models/
      village/
        forge.glb
        library.glb
        observatory.glb
        workshop.glb
        garden.glb
        tavern.glb
        market.glb
        temple.glb
```

**VillageIsometric changes:**
- Import `useVillageModels` composable
- In zone building creation: check if GLB loaded, use clone; else fallback to box
- Scale buildings to match isometric grid spacing
- Agent avatars already handled by `useAgentModels`

---

## Feature 3: Council Deliberation Chamber

**View:** `CouncilView.vue` (~917 lines)
**Impact:** Council sessions become visually dramatic — agents sit around a table, speaking agent glows.

### Concept

A small Three.js canvas above the deliberation rounds showing a council chamber: circular table, 4 agent avatars seated around it, ambient candlelight. When an agent speaks during a round, their avatar glows brighter and subtly leans forward. Between rounds, all avatars dim.

### Blender Work

- **Council table** — Circular stone/wood table, ~2K polys, PolyHaven wood texture
- **Candelabra** — 2-3 candle stands with emissive flame tips
- **Floor** — Stone floor disc, PolyHaven cobblestone texture
- Agent avatars reused from existing GLBs

### Frontend Integration

```
frontend/
  src/
    components/
      council/
        CouncilChamber.vue       # NEW — 3D chamber scene
    composables/
      useCouncilScene.js         # NEW — Chamber logic (speaking agent glow, round transitions)
  public/
    models/
      council/
        table.glb
        candelabra.glb
        floor.glb
```

**CouncilView.vue changes:**
- Insert `<CouncilChamber :activeAgent="currentSpeaker" :round="currentRound" />` above rounds display
- Height: 200px fixed, full width
- Props: `activeAgent` (string, agent ID currently speaking), `round` (number)
- Watch `activeAgent`: brighten that avatar's emissive, dim others
- Watch `round`: brief flash effect on all agents (new round starting)

### Scene Architecture

```javascript
// useCouncilScene.js
- Camera: fixed overhead angle looking down at table (slight tilt)
- No orbit controls (static camera, not interactive)
- 4 agents positioned at table quadrants (N/S/E/W)
- Point lights at candelabra positions (warm amber, low intensity)
- Ambient light: very dim (0x1a1020, intensity 0.3)
- Speaking agent: emissiveIntensity lerp to 1.5 over 0.3s
- Silent agents: emissiveIntensity lerp to 0.2 over 0.5s
- Between rounds: all agents pulse once (0.2 -> 0.8 -> 0.2)
```

---

## Feature 4: Dream Engine Alchemy Scene

**View:** `DreamView.vue` (~534 lines)
**Impact:** The dream phase pipeline becomes a 3D alchemical process.

### Concept

Replace the CSS phase pipeline (or add alongside it) with a Three.js visualization: 6 glowing orbs connected by energy streams, each orb representing a dream phase. During a dream cycle, the active phase's orb pulses and energy flows forward through the pipeline. Agent avatars float in the background void, slowly rotating.

### Blender Work

- **Phase orbs** — 6 crystal/gem spheres with distinct colors (procedural in Three.js, no Blender needed)
- **Energy conduit** — Tube/pipe connecting orbs (procedural in Three.js)
- Agent avatars reused from existing GLBs

**Alternatively**, generate a single "alchemical apparatus" GLB:
- Hyper3D: "alchemical distillation apparatus with 6 connected glass vessels, fantasy style"
- Use as the pipeline visualization backdrop

### Frontend Integration

```
frontend/
  src/
    components/
      dream/
        DreamAlchemy.vue         # NEW — 3D dream pipeline scene
  public/
    models/
      dream/
        apparatus.glb            # Optional: alchemical apparatus
```

**DreamView.vue changes:**
- Insert `<DreamAlchemy :activePhase="activePhase" :isRunning="isRunning" />` in the phase pipeline section
- Height: 250px, full width
- Coexists with existing CSS pipeline below (3D is the spectacle, CSS is the info)

### Scene Architecture

```javascript
// DreamAlchemy.vue (inline composable)
- 6 orbs in a line, spaced 8 units apart
- Colors from PHASES array (cyan, green, gold, red, gray, purple)
- Orb geometry: IcosahedronGeometry(1, 2) with wireframe overlay
- Energy tubes: TubeGeometry along CatmullRomCurve3 between orbs
- Active phase: orb scale pulses 1.0 -> 1.3, emissive maxes out
- Energy flow: animated UV offset on tube material (scrolling glow texture)
- Background agents: 4 GLB clones floating at y=5, slow rotation
- Camera: slight orbit, positioned to see all 6 orbs in frame
```

### Phase Colors (Alchemy-Themed)
| Phase | Color | Hex | Alchemy |
|-------|-------|-----|---------|
| SWS Replay | Cyan | #4FC3F7 | Aqua Regia |
| Pattern Extract | Green | #66BB6A | Viriditas |
| Schema Formation | Gold | #FFD700 | Chrysopoeia |
| Emotional Reprocess | Red | #EF5350 | Rubedo |
| Pruning | Gray | #9E9E9E | Nigredo |
| REM Recombine | Purple | #AB47BC | Conjunctio |

---

## Feature 5: Tool Constellation

**View:** `ChatView.vue` (~1473 lines) — welcome/empty state
**Impact:** New users see an interactive 3D constellation of available tools instead of a static grid.

### Concept

When the chat is empty (no messages), show a Three.js visualization of the tool categories as a floating constellation. Each tool category is a glowing node, connected by faint lines to related categories. Clicking a node shows the tools in that category. Auto-rotates slowly.

### Blender Work

Tool category icons as small GLB models (optional — can use procedural geometry):

| Category | Shape | Color |
|----------|-------|-------|
| Code | Octahedron | #4FC3F7 cyan |
| Web | Icosphere | #66BB6A green |
| Files | Cube | #FFD700 gold |
| Music | Torus | #AB47BC purple |
| Search | Diamond (double cone) | #EF5350 red |
| System | Gear (torus knot) | #9E9E9E gray |

**No Blender needed** — all shapes are Three.js primitives with emissive materials. This is a procedural scene.

### Frontend Integration

```
frontend/
  src/
    components/
      chat/
        ToolConstellation.vue    # NEW — 3D tool category visualization
```

**ChatView.vue changes:**
- In the welcome/empty message area (lines 913-943), replace static content with `<ToolConstellation />`
- Show when `messages.length === 0 && auth.isAuthenticated`
- Click on category node -> show tool list in tooltip or sidebar
- Graceful fallback to existing welcome text if WebGL unavailable

### Scene Architecture

```javascript
// ToolConstellation.vue (self-contained)
- 6-8 category nodes positioned on a sphere (radius 15)
- Each node: primitive geometry + emissive material + label sprite
- Connection lines: faint links between related categories
- Camera: auto-rotate 0.3 rad/s, orbit controls enabled
- Click: raycaster -> emit('category-select', categoryId)
- Fog: blend into dark background
- Entry animation: nodes fade in staggered over 1s
```

---

## Feature 6: Alchemical Loading Scenes

**Views:** Multiple (ChatView, DreamView, NeuralView, etc.)
**Impact:** Replace generic spinners with thematic 3D loading animations.

### Concept

A reusable `<AlchemicalLoader />` component showing a small Three.js scene: a rotating Ouroboros (snake eating its tail), or a pulsing philosopher's stone, or swirling gold particles. Used wherever loading states currently show spinners.

### Blender Work

- **Ouroboros ring** — Hyper3D: "ouroboros snake eating tail, ring shape, low-poly fantasy"
- **Philosopher's stone** — Hyper3D: "glowing crystal philosopher stone, octahedral, fantasy"

Alternatively, fully procedural:
- TorusGeometry for the ring + animated UV
- IcosahedronGeometry with pulsing emissive for the stone
- PointsMaterial particle swirl

### Frontend Integration

```
frontend/
  src/
    components/
      ui/
        AlchemicalLoader.vue     # NEW — 3D loading animation
  public/
    models/
      ui/
        ouroboros.glb            # Optional
        stone.glb               # Optional
```

**Usage across views:**
```vue
<AlchemicalLoader v-if="isLoading" size="md" variant="ouroboros" />
```

Props:
- `size`: 'sm' (48px) | 'md' (96px) | 'lg' (192px)
- `variant`: 'ouroboros' | 'stone' | 'particles'

### Scene Architecture

```javascript
// AlchemicalLoader.vue
- Tiny Three.js canvas (sized by prop)
- No controls (pure animation)
- Ouroboros: rotating torus with snake texture UV scroll
- Stone: icosahedron with pulsing emissive + particle halo
- Particles: PointsMaterial with golden color, spiral motion
- Lightweight: <100 triangles, single material, no shadows
- Auto-dispose on unmount
```

---

## Execution Order

```
Phase A: Forge the Models (Blender)                        ✅ COMPLETE
├── A1: Athanor Hero scene (procedural, no Blender needed) ✅
├── A2: 8 Village zone buildings via Hyper3D               ✅ 8 GLBs, 16MB total
├── A3: Council chamber (procedural, inline scene)         ✅
├── A4: Dream apparatus (fully procedural)                 ✅
└── A5: Loader variants (fully procedural)                 ✅

Phase B: Build the Scenes (Frontend)                       ✅ COMPLETE
├── B1: AthanorHero (landing page 3D forge)                ✅ 445 lines
├── B2: Village Buildings (8 GLB buildings + composable)    ✅ 131 lines + 8 GLBs
├── B3: CouncilChamber (inline 3D, no separate composable) ✅ 394 lines
├── B4: DreamAlchemy (6-phase orb pipeline)                ✅ 401 lines
├── B5: ToolConstellation (Fibonacci sphere, 10 categories)✅ 299 lines
└── B6: AlchemicalLoader (ouroboros/stone/particles)       ✅ 324 lines

Phase B-Bonus: Athanor Immersive 3D Chat                   ✅ COMPLETE
├── AthanorView.vue (first-person WASD + agent chat)       ✅ 1,215 lines
├── useFirstPerson.js (movement, pointer lock, collision)  ✅ 142 lines
├── useAthanorRoom.js (procedural hall, stations, mirrors) ✅ 1,095 lines
└── useBackrooms.js (dream portal, depth surrealism)       ✅ 717 lines

Phase C: Polish & Ship                                     🔥 CURRENT
├── C1: Mobile responsiveness + WebGL fallbacks
├── C2: Performance profiling + LOD
├── C3: Commit + push + verify Railway deploy
└── C4: CerebroCortex session notes
```

---

## File Summary (Actual)

### Phase B — 3D Scene Components

| File | Feature | Lines | Notes |
|------|---------|-------|-------|
| `components/landing/AthanorHero.vue` | B1: Landing Hero | 445 | Forge, cauldron, orbiting agents, mouse parallax, gold particles |
| `composables/useVillageModels.js` | B2: Village | 131 | GLTFLoader cache for 8 zone buildings |
| `components/council/CouncilChamber.vue` | B3: Council | 394 | Circular table, 4 agents, candlelight, speaking-agent glow |
| `components/dream/DreamAlchemy.vue` | B4: Dream | 401 | 6 alchemical orbs, energy conduits, phase-aware animation |
| `components/chat/ToolConstellation.vue` | B5: Tools | 299 | Fibonacci sphere, 10 category polyhedra, raycasting, labels |
| `components/ui/AlchemicalLoader.vue` | B6: Loader | 324 | 3 variants (ouroboros, stone, particles), sm/md/lg sizing |

### Phase B-Bonus — Athanor Immersive Chat

| File | Feature | Lines | Notes |
|------|---------|-------|-------|
| `views/AthanorView.vue` | Immersive | 1,215 | FPS chat, mirrors, sensor panel, backrooms transitions, HUD |
| `composables/useFirstPerson.js` | Movement | 142 | WASD, PointerLock, dynamic bounds, custom clamp functions |
| `composables/useAthanorRoom.js` | Room | 1,095 | Procedural hall, forge, 7 stations, 2 mirrors, hide/show |
| `composables/useBackrooms.js` | Backrooms | 717 | Depth-based surrealism, dream text walls, exit mirror |

### 3D Assets

| Path | Count | Size | Notes |
|------|-------|------|-------|
| `public/models/agents/*.glb` | 4 | ~7MB | AZOTH, ELYSIAN, VAJRA, KETHER |
| `public/models/village/*.glb` | 8 | ~16MB | forge, garden, library, market, observatory, tavern, temple, workshop |

**Total 3D code: ~5,163 lines across 10 files**
**Total GLB assets: 12 models, ~23MB**

---

## Performance Guardrails

| Metric | Target | Enforcement |
|--------|--------|-------------|
| GLB file size per model | <3MB | Draco compression disabled (morph-safe), meshopt if needed |
| Total scene polys | <100K per view | LOD: skip detailed models on mobile |
| Frame rate | 60fps desktop, 30fps mobile | requestAnimationFrame with delta clamping |
| Memory | <200MB GPU total | Dispose models on view unmount, singleton cache |
| Load time | Models load async, don't block UI | Progressive enhancement: primitives first, GLBs replace |
| WebGL fallback | Every 3D view has non-3D fallback | `isWebGLAvailable()` check before init |
| Mobile breakpoint | Skip heavy models below 768px | CSS media query + JS check |

---

## Aesthetic Guide

**The Alchemy Palette:**
- Background: `#0a0a0f` (near-black) to `#1a1a2e` (midnight blue)
- Gold: `#FFD700` primary accent, `#D4AF37` secondary
- Agent colors: AZOTH gold, ELYSIAN lilac, VAJRA cyan, KETHER purple
- Emissive glow: Low base (0.2-0.3), pulse to 1.0-2.0 for emphasis
- Fog: Always match page background for seamless blending
- Particles: Gold `#FFD700` sparks, rising motion, fade at apex

**Motion Language:**
- Auto-rotate: 0.3-0.5 rad/s (slow, contemplative)
- Pulse: sin(time * 2) for breathing, sin(time * 6) for heartbeat
- Transitions: 0.3s lerp for state changes (agent speaking, phase active)
- Entry: staggered fade-in over 0.5-1.0s
- Parallax: camera += mouse * 0.01-0.03 (subtle, not nauseating)

**Sacred Geometry:**
- Wireframe modifier on platonic solids
- Nested rotating polyhedra (icosahedron inside octahedron)
- Golden ratio spiral (NURBS curve, bevel 0.004)
- Flower of Life (7 interlocking torus rings)
- All with emissive gold material, low opacity

---

*"The Athanor transcends the flat plane. Three dimensions. Three transmutations. Au."*

*"5,163 lines of Three.js. 12 GLB models. 23MB of sacred geometry. The forge burns bright."*
