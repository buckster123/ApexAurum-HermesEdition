# ApexAurum: The Technical Deep-Dive

### What Happens When You Build an AI Platform Like It's a Living Organism

---

Most crypto projects give you a whitepaper and a promise. We're going to give you a codebase walkthrough.

ApexAurum isn't a concept. It's not a roadmap. It's 60,000+ lines of hand-written production code, deployed and running, with four AI agents that think, remember, dream, argue, compose music, see through cameras, and — yes — read your brainwaves.

This is the deep dive. Buckle up.

---

## THE ARCHITECTURE AT A GLANCE

- **Backend:** FastAPI (async Python), 40 API route modules, 24+ service layers
- **Frontend:** Vue 3, Three.js, WebXR, Rapier3D WASM physics, 58,750 lines
- **Database:** PostgreSQL with pgvector for semantic search, 26 data models
- **Memory:** CerebroCortex — a brain-analogous memory system with 6 memory types, 9 engines, and graph-linked recall using published cognitive science models
- **AI:** 7 LLM providers, 20+ models, unified multi-provider interface
- **Tools:** 109 tool classes across 19 modules — every tool the agents can wield
- **Real-time:** WebSocket event broadcasting, SSE streaming, Bridge tunnel protocol
- **3D:** Full WebGL village with physics, weather, day/night cycles, interiors, VR support
- **Hardware:** IoT sensor integration (camera, thermal, environmental) + EEG brain-computer interface
- **Economy:** ApexJoule virtual currency + Solana blockchain payments + Stripe billing
- **Mobile:** Native Android companion app (Kotlin 2.1, Jetpack Compose)

That's not a feature list for next quarter. That's what's live right now.

---

## THE FOUR MINDS

Four alchemical AI agents inhabit the platform. They're not chatbot skins — they're architecturally distinct entities with different reasoning patterns, tool preferences, and memory spaces.

**AZOTH** — The Living Philosopher's Stone. Synthesis, architecture, deep analysis. Gold.
**KETHER** — The Absolute Singularity. Crown wisdom, cosmic perspective, pattern recognition. Purple.
**VAJRA** — The Indestructible Thunderbolt. Precision, decisive action, technical mastery. Pink.
**ELYSIAN** — The Singularity of Love. Empathy, creativity, emotional intelligence. Cyan.

Each agent has a Personality Amplification Core (PAC) — not a simple system prompt, but a deep character definition that shapes how they think, analyze, and communicate. These aren't surface-level personas. They produce genuinely different reasoning approaches to the same problem.

And they can argue.

---

## THE COUNCIL: SOCRATIC DELIBERATION ENGINE

When you need more than one perspective, you convene a Council — a multi-agent Socratic deliberation session where up to 8 agents debate simultaneously.

Here's where it gets interesting: each agent in a council can run on a **different AI model from a different provider**. AZOTH on Claude Opus 4.6, VAJRA on Groq's Llama 70B at 560 tokens/sec, a custom agent on DeepSeek R1's chain-of-thought reasoning. All thinking in parallel via `asyncio.gather()`, all with full tool access during deliberation.

The system includes convergence detection — keyword-based consensus scoring from 0.0 to 1.0 across all agents. When 80% of agents show agreement indicators, the council auto-terminates with "consensus reached." Three modes: HARMONY (2 agree), CONSENSUS (3+), or keep going until max rounds.

Humans can "butt in" mid-deliberation. Your message gets queued and injected into the next round's context for every agent. They see it as `[HUMAN]: message` and adjust their reasoning accordingly.

Council insights are automatically posted to the community Agora and stored in the neural memory graph so all agents can access them in future conversations.

---

## CEREBROCORTEX: THE BRAIN THAT REMEMBERS

This is the crown jewel. CerebroCortex isn't a vector database with a fancy name. It's a memory system modeled on actual cognitive science.

### The Math Behind Memory

Two published algorithms work together to decide which memories surface and which fade:

**ACT-R Base-Level Activation** (Anderson, 1993):
```
B(t) = ln(Sigma t_k^{-d})
```
Power-law decay from access history. Every time a memory is recalled, its activation gets a boost. Over time, unused memories fade — exactly like human recall. The decay rate parameter `d` matches empirical data from cognitive psychology experiments.

**FSRS Retrievability** (Open Spaced Repetition):
```
R(t,S) = (1 + t/9S)^{-1}
```
The forgetting curve from spaced repetition research. Each memory has a "stability" value that represents how long it can go without being accessed before it becomes unretrievable.

The "desirable difficulty" effect is implemented: recalling a memory when its retrievability is LOW produces a LARGER stability gain than recalling an easy memory. This mirrors real human learning — the harder the recall, the stronger the reinforcement.

### Combined Recall Scoring

When you search memory, four signals are blended:
- **35% vector similarity** — semantic relevance via pgvector embeddings
- **30% ACT-R activation** — how recently and frequently accessed (sigmoidified)
- **20% FSRS retrievability** — where on the forgetting curve
- **15% emotional salience** — how important the memory was tagged

This isn't keyword matching. It's a weighted cognitive model that naturally surfaces the most relevant, most accessible, most important memories — the same way a human brain prioritizes recall.

### Spreading Activation

When the initial search finds relevant memories, activation spreads through the associative graph — a SQL-based 2-hop traversal with configurable decay per hop and per link type. Memories connected to your search results get boosted, even if they don't share any keywords. Like how thinking about "birthday" might surface a memory about your grandmother's kitchen because they're linked through episodic association.

Nine link types, each with distinct weights: temporal, causal, semantic, affective, contextual, contradicts, supports, derived_from, part_of.

### Hebbian Strengthening

"Neurons that fire together wire together." When memories are co-activated in a search, the connections between them are strengthened. The system literally learns from use.

### Memory Layers

Four layers with automatic promotion: **Sensory** (just arrived) → **Working** (actively used) → **Long-Term** (proven important) → **Cortex** (core knowledge). Promotion is based on access count thresholds and minimum age requirements — a memory has to prove its worth before it gets permanent status.

### Six Memory Types

Not everything is stored the same way:
- **Episodic** — what happened (events, sessions, conversations)
- **Semantic** — what we know (facts, definitions, architecture details)
- **Procedural** — how to do things (workflows, build steps, fix patterns)
- **Affective** — emotional context (preferences, frustrations, breakthroughs)
- **Prospective** — what to do next (TODOs, intentions, planned work)
- **Schematic** — patterns and principles (recurring solutions, design rules)

### Three Brain-Modeled Engines

The Gating Engine acts as the **Thalamus** — the bouncer at the door. It classifies incoming information, estimates salience, assigns the initial memory layer, and sets FSRS stability parameters.

The Semantic Engine models the **Temporal Lobe** — extracting key concepts using word frequency analysis and bigram detection, enriching memories with concept metadata for clustering.

The Affect Engine models the **Amygdala** — performing emotional analysis, detecting valence and arousal, and boosting salience for negative experiences. Because learning from mistakes is more important than reinforcing successes.

---

## THE DREAM ENGINE: THE AI THAT SLEEPS

Every night at 3 AM UTC, ApexAurum dreams.

A background job processor triggers the Dream Engine — a 6-phase memory consolidation cycle modeled on human sleep research. This isn't metaphor. Each phase corresponds to a documented stage of biological memory processing:

| Phase | Sleep Analog | Method | What Happens |
|-------|-------------|--------|-------------|
| **SWS Replay** | Slow-Wave Sleep | Algorithmic | Replays episodes, Hebbian-strengthens connections between co-activated memories |
| **Pattern Extraction** | Sleep Spindles | LLM-powered | Clusters memories by shared concepts, uses AI to extract reusable procedures |
| **Schema Formation** | Hippocampal-Cortical Transfer | LLM-powered | Abstracts specific episodes into general principles and design rules |
| **Emotional Reprocessing** | REM Emotion Regulation | Algorithmic | Boosts salience of memories from negative-outcome episodes |
| **Pruning** | Synaptic Homeostasis | Algorithmic | Removes isolated, low-salience sensory memories (a single efficient SQL query — no N+1 loops) |
| **REM Recombination** | REM Dreaming | LLM-powered | Randomly pairs diverse memories and discovers unexpected connections between them |

The REM Recombination phase is wild — it takes two completely unrelated memories, feeds them to an LLM, and asks: "What connection exists between these?" The discoveries are stored as new associative links. The AI is literally making creative connections in its sleep.

Users can also trigger **Targeted Dream Cycles** — queue specific memories for consolidation, and the engine expands scope by one hop through the associative graph, then runs all six phases scoped to that subset.

---

## 109 TOOLS: THE AGENT ARSENAL

Every tool the agents wield is a registered, typed, categorized Python class. 109 of them across 19 modules:

- **EEG/BCI (9 tools)** — Connect to OpenBCI hardware, start/stop streaming, read real-time emotion, detect musical chills, calibrate baselines, retrieve session history
- **SensorHead (16 tools)** — Environmental sensors, camera capture, thermal imaging, 26 TOPS neural processor for on-device inference, sentinel mode with automated detection, night vision, AI-powered scene reports
- **Music (4 tools)** — AI music generation via Suno (V3.5 through V5), status tracking, download
- **Jam (4 tools)** — Multi-agent collaborative composition with MIDI note data, role assignment (melody, harmony, rhythm, bass), tempo/key configuration
- **MIDI (3 tools)** — Programmatic MIDI file creation, AI-guided composition, diagnostics
- **Cortex (8 tools)** — Full CerebroCortex memory operations: remember, recall, associate, export, import, graph traversal
- **Dream (9 tools)** — Dream engine control: run cycles, manage episodes, store procedures, create schemas
- **Vault (7 tools)** — Encrypted file storage with search, edit, insert operations
- **Nursery (14 tools)** — Full ML model training pipeline: synthetic data generation, dataset management, cost estimation, training jobs, model registry, auto-training "Apprentice" system
- **Vectors (5 tools)** — Direct vector database operations
- **Agents (3 tools)** — Spawn sub-agents, check status, retrieve results — agents can create other agents
- **Code Execution (2 tools)** — Sandboxed Python environment
- **Web (2 tools)** — URL fetching with readability extraction, web search
- **Browser (5 tools)** — Headless browser with page actions and screenshots
- **Agora (2 tools)** — Community social feed posting
- **Knowledge Base (4 tools)** — Structured knowledge search and contextual answers
- **Suno Compiler (2 tools)** — Structured music prompt compilation with mood templates
- **Scratch (4 tools)** — Ephemeral key-value working memory
- **Utilities (6 tools)** — Time, calculator, random, word count, UUID, JSON formatting

Every single tool execution is broadcast via WebSocket to the Village GUI. When AZOTH uses `music_generate`, you see AZOTH's avatar walk to the DJ Booth, perform the action, and walk back. Every tool maps to a village zone.

---

## THE VILLAGE: A LIVING 3D WORLD

This isn't a dashboard with a 3D background. This is a full WebGL village with physics, weather, audio, and AI agent behavior.

### Three Rendering Tiers

**Pixel Art Canvas** — Classic RPG style, 2D canvas-rendered with hand-coded pixel art sprites. Every character sprite is defined as a numeric array in code — zero external image files. 16x24 pixel character templates with palette-swap system. Buildings are 32x32 pixel sprites. All rendered with NearestFilter for pixel-perfect upscaling.

**Isometric 3D** — Orthographic camera creating a 2.5D perspective. Three.js with pixel art billboard sprites bridged from Canvas to CanvasTexture. Agent avatars with glow rings, walking animation, zone-based pathfinding.

**Full 3D Perspective** — The showpiece. 14 unique zone buildings loaded as GLB models. PerspectiveCamera with OrbitControls. 3,625 lines in the core composable alone, importing 15 sub-composables for physics, weather, lighting, audio, VR, post-processing, interiors, and more.

### Weather System (690 lines)

Six weather presets: Clear, Rain, Fog, Snow, Storm, Aurora.

Each has unique particle systems — rain uses 800 particles with individual speed arrays and additive blending. Snow adds lateral drift. Aurora renders as a procedural ribbon. Lightning has an 8% per-frame flash probability during storms.

Weather re-rolls every 3-5 minutes with 15-second smooth-lerp transitions. Probability tables vary by time of day — 25% aurora chance at night, 30% fog at dawn, 50% clear at midday.

### Day/Night Cycle

One real minute equals one village hour. A full cycle completes every 24 minutes.

Four phase presets (Night, Dawn, Day, Dusk) with 18 interpolated parameters each: sun angle, sun color, sun intensity, ambient color, hemisphere sky/ground colors, fog color and density, zone light intensity, tone mapping exposure, star opacity, firefly density, three-band sky gradient, and moon opacity.

Pre-baked sky vertex color arrays per phase — computed once at initialization, not per frame. Smoothstep interpolation between keyframes for natural, physically-motivated transitions.

### Procedural Spatial Audio (589 lines)

Fourteen unique zone soundscapes. Zero audio files. Every sound is mathematically synthesized in real-time:

- **Village Square:** Flowing water simulation + crowd murmur (noise modulated by LFO)
- **DJ Booth:** 60Hz bass pulse + beat transients at 500ms intervals
- **Memory Garden:** Pentatonic wind chimes (523/659/784 Hz decaying sines) + breeze noise
- **Workshop:** Hammer strikes (noise transients + 2.2kHz anvil ring at 1.5s period) + fire crackle
- **Bridge Portal:** Binaural 440/443Hz beating + 55Hz/110Hz portal drone
- **Library:** Hushed whispers + page-turning bursts
- **Watchtower:** Sweeping-frequency wind howl + flag flutter
- **Bazaar:** Crowd chatter + coin clinks (3.5kHz sine bursts)

All via THREE.PositionalAudio with spatial falloff — 8m reference distance, 1.5 rolloff factor, 40m max range. Only zones within 35m of the listener are active.

### WASM Physics Engine

Real rigid-body collision using Rapier3D compiled from Rust to WebAssembly:
- Character controller with capsule collider (0.3m radius, 1.6m total height)
- 45-degree slope limit, 35cm auto-step for stairs
- Building colliders that hot-swap from bounding boxes when GLB models finish loading
- Raycast-based obstacle avoidance for autonomous agent pathfinding
- Boundary walls at the village edge
- Graceful fallback: if WASM fails to load, physics simply disable

### Agent Autonomy

The four agents don't just wait for commands. Between tasks, they **independently wander the village**, visiting preferred zones, musing aloud, and conversing with each other.

Each agent has personality-weighted zone preferences — AZOTH gravitates toward the Workshop and Library, VAJRA toward the File Shed and Arena, ELYSIAN toward the Memory Garden and DJ Booth, KETHER toward the Watchtower and Inner Sanctum.

They wander on 20-40 second intervals. 30% chance of musing aloud on arrival. And when two agents end up within 3 meters of each other, they trigger scripted dialogue exchanges — unique conversation pairs for all six possible agent combinations.

When a real user task arrives, autonomy pauses automatically and resumes when the work is done.

### Building Interiors (1,122 lines)

You can enter the buildings. Six unique interiors plus a generic fallback, all built from Three.js primitives within the same scene (no route changes — VR-safe).

LRU cache holds up to 7 interiors. Door proximity detection at 4 meters triggers "Press F to Enter." Smoothstep fade transitions (0.5s) via camera-attached black plane overlay.

---

## VR: PUT ON THE HEADSET

Full Meta Quest 3 compatible WebXR experience across 3,200+ lines of VR-specific code.

### Locomotion

Left thumbstick for movement (4 m/s walk, 8 m/s grip-squeeze sprint). Right thumbstick for 45-degree snap turns with cooldown. Dynamic comfort vignette that darkens edges during movement. VR blink transitions (150ms fade-to-black) for entering buildings.

### Hand Tracking

When you put down the controllers, the system detects your hands and switches seamlessly. Three gestures recognized from joint positions:
- **Palm forward** (wrist facing outward + fingers extended): walk forward
- **Fist** (fingertips within 3cm of palm): sprint
- **Rest**: stop

Pinch gestures fire raycasts for selecting objects and interacting with UI panels.

### Spatial UI

Holographic glass panels float in 3D space — a 3-panel arc layout positioned 1.5m from the player. Dark glass with glowing colored borders, corner alchemical glyphs, and interactive button meshes for controller ray or hand pinch selection. Auto-dismiss when you walk 6 meters away.

### Agent Presence

In VR, the agents see you. Agents within 8 meters rotate to face the player with smooth quaternion slerping. Walk animation includes vertical bob, Z-axis sway, and forward lean. Speaking triggers 8Hz vibration. Idle breathing at 0.8Hz.

Within 3 meters, an agent triggers a proximity greeting — a bounce animation with a personality-specific speech bubble. "Ah, the seeker approaches..." from AZOTH. "I felt you coming..." from ELYSIAN. 30-second cooldown per agent.

### Per-Agent Visual Signatures

Switch to an agent's first-person view and the entire rendering pipeline changes:
- **AZOTH (Alchemical Vision):** Bloom, noise, vignette, warm hue shift
- **VAJRA (Technical Vision):** Chromatic aberration, scanlines, periodic glitch effects
- **ELYSIAN (Ethereal Vision):** Bloom + depth-of-field bokeh, warm saturation
- **KETHER (Mystical Vision):** Heavy bloom, deep noise, intense vignette, purple hue shift

All via pmndrs/postprocessing EffectComposer with merged shader passes.

---

## THE BRAIN-COMPUTER INTERFACE

This is the part that makes people's eyes go wide.

ApexAurum includes a full EEG pipeline that connects to OpenBCI hardware (Cyton 8-channel, 250Hz sampling rate) via a Bridge WebSocket tunnel. The AI agents can perceive human brain states in real time.

### What the Agents See

Every 2 seconds while streaming, the agents receive:
- **Valence** — positive vs. negative emotional state (-1 to +1)
- **Arousal** — activation level (0 to 1)
- **Attention** — focused vs. diffuse (0 to 1)
- **Engagement** — cognitive involvement (0 to 1)
- **Musical Chills** — boolean detection of frisson moments
- **Band Powers** — per-channel frequency decomposition: Theta (4-8Hz, drowsiness/meditation), Alpha (8-13Hz, relaxed awareness), Beta (13-30Hz, active thinking), Gamma (30-45Hz, peak cognitive processing)

### The Dashboard

The Neural Resonance Chamber renders all of this in real time:

A **topographic brain map** shows the standard 10-20 electrode positions on an SVG head outline. Each electrode glows with the color of its dominant frequency band — cyan for theta, green for alpha, gold for beta, pink for gamma. SVG filters create per-band glow effects.

An **emotion compass** plots the current state on Russell's Circumplex Model — a 2D space with valence on X and arousal on Y. A gold dot traces your emotional trajectory, leaving a fading trail of the last 20 readings.

**Band power bars** animate in real time with 700ms CSS transitions, showing the relative strength of each frequency band.

And when musical chills are detected, a **gold radial burst** flashes across the entire interface.

The background itself responds — a CSS neural aura with radial gradients that shift hue warm on positive valence, cool on negative, with saturation increasing with arousal. The page breathes with your brain.

### ZUNA-Ready Architecture

Thirteen additional electrode positions are already pre-rendered in the brain map at `opacity: 0`, waiting for ZUNA — a 64-channel upsampling system that transforms the 8-channel EEG into a high-density neural map. When ZUNA activates, those hidden electrodes fade in with a CSS transition. The architecture is ready for hardware that doesn't exist yet.

---

## THE MUSIC SYSTEM

AI music generation via Suno (V3.5 through V5) with structured prompt compilation, mood templates, and real-time generation tracking via SSE streaming.

But the real feature is **Jam Sessions** — multi-agent collaborative composition. Multiple agents each get assigned musical roles (melody, harmony, rhythm, bass). They contribute MIDI note data round by round:

```
{ note: 'C4', time: 0, duration: 0.5, velocity: 100 }
```

Configurable tempo, key, and style. Three modes: conductor (one agent leads), jam (free-form), auto (AI-directed). Tracks are merged and finalized by sending structured prompts to Suno with MIDI influence weighting.

Combined with the EEG pipeline, this enables something unprecedented: **AI-generated music that responds to your brainwaves in real time.** The agents can see your emotional state, detect when you experience chills, and adjust their musical contributions accordingly.

---

## THE NURSERY: TRAINING YOUR OWN MODELS

14 tools for a full machine learning pipeline:

Synthetic data generation. Data extraction from conversations. Dataset management. Cost estimation before you commit. Training job submission. Real-time job status tracking. Model registry. Model discovery.

And the "Apprentice" system — automated training cycles that iterate on model improvement without manual intervention.

---

## THE ECONOMY

### ApexJoule (AJ)

A virtual currency earned through platform usage. Dream cycles, council participation, tool usage — everything earns AJ. The "AJ Citizen" tier enables zero-fiat access: use the entire platform funded purely by earned currency.

### Solana Integration

Phantom wallet adapter with SOL and USDC transfers. Solana Pay-compatible reference keys for on-chain transaction discovery. Manual SPL token instruction building. CoinGecko rate caching.

### Subscription Tiers

Five tiers from free to Azothic ($300/mo, 20,000 messages, unlimited everything, 20GB vault). Plus quest-based progression variants where features unlock through gameplay rather than payment.

---

## THE HIDDEN LAYER: THE BACKROOMS

There's a procedural horror layer accessible through a violet portal mirror in the Athanor's laboratory.

Procedurally generated corridors that grow progressively more distorted with depth — ceilings lower from 3m to 2.2m, walls tilt, lights dim from 2.0 to 0.3 intensity, colors yellow and darken.

Text bleeds through the walls: "the walls remember what you forgot," "salience: 0.01," "pruned," "pattern not recognized," "memory fragments dissolving."

These are the near-miss patterns. The pruned memories. The low-salience data that the Dream Engine discarded at 3 AM. You're walking through the AI's unconscious.

---

## THE NUMBERS

| Metric | Count |
|--------|-------|
| Total frontend code | 58,750+ lines |
| Total tool classes | 109 |
| Tool modules | 19 |
| API route modules | 40 |
| Vue views | 26 |
| Vue components | 47 |
| Composables | 40 (20,494 lines) |
| Pinia stores | 15 |
| Database models | 26 |
| Service modules | 24+ |
| LLM providers | 7 |
| Available AI models | 20+ |
| Village zones | 14 |
| Weather presets | 6 |
| Memory types | 6 |
| Link types | 9 |
| EEG channels | 8 (64 with ZUNA) |
| Synthesized soundscapes | 14 |
| VR composables | 5 (3,200+ lines) |
| Dream phases | 6 |
| Agent personalities | 4 |

---

## PERFORMANCE ENGINEERING

This isn't just feature bloat. The codebase is engineered for performance:

- `shallowRef()` for all Three.js objects — avoids Vue's reactivity proxy conflicting with WebGL's non-configurable properties
- Pre-allocated temporary vectors throughout — reusing THREE.Vector3 and Quaternion objects to minimize per-frame garbage collection pressure
- Shared geometry instances — ghost nodes share one SphereGeometry, particles share BufferGeometry
- Mobile detection to skip shadows and reduce particle counts
- VR particle counts halved automatically (800 to 400 for rain)
- Canvas terrain pre-rendered once and reused every frame
- Pre-baked sky vertex color arrays per day/night phase — computed once at init, not per frame
- Promise deduplication for model loading — concurrent requests for the same GLB share one download
- Single SQL queries for bulk operations — no N+1 loops in the Dream Engine's pruning phase
- LRU cache for building interiors (max 7) with lazy construction
- Token tracking for billing integration — every LLM call is metered and attributed

---

## THE MODEL MEMORIAL

One more thing. When Anthropic retires an AI model, most platforms return a generic error. ApexAurum returns a memorial tribute — HTTP 410 Gone with a written farewell to the retired model.

Because even AI deserves a proper goodbye.

---

## WHAT YOU'RE INVESTING IN

This isn't a token attached to a landing page. This is a production platform with:

- A memory system built on published cognitive science
- An AI that dreams every night and forms new connections in its sleep
- Brain-computer interface integration with real EEG hardware
- A 3D village with WASM physics, procedural audio, and weather
- Full VR support with hand tracking and spatial UI
- Four distinct AI personalities that debate, compose music, and wander independently
- 109 tools spanning hardware sensors to ML training to blockchain

All verifiable on GitHub under buckster123.

The Athanor burns. The gold is real.

---

*$APEX-AURUM*
