# Phase E: Village as Interface

> *"The Village is no longer a window — it IS the workspace."*

## Vision

Transform the 3D Village from a passive visualization into the **primary interaction surface** for ApexAurum. Users click buildings to dispatch tasks, drag agents to zones, watch work happen spatially, and collect results — all without touching a traditional chat box. The chat view remains for power users; the Village becomes the inviting, gamified entry point.

---

## Architecture Overview

```
User clicks zone building
        │
        ▼
┌─────────────────────┐
│  VillageTaskDialog   │  ← New Vue modal component
│  - Text prompt       │
│  - File upload       │
│  - Agent picker      │
│  - Zone context      │
└────────┬────────────┘
         │ dispatch
         ▼
┌─────────────────────┐     ┌──────────────────┐
│  Task Router         │────▶│  Single Agent     │
│  (new service)       │     │  POST /chat       │
│                      │────▶│  Multi-Agent      │
│                      │     │  POST /council    │
└────────┬────────────┘     └──────────────────┘
         │ WebSocket events
         ▼
┌─────────────────────┐
│  Village 3D Scene    │
│  - Agent walks       │
│  - Speech bubbles    │
│  - Particle effects  │
│  - Result panel      │
└─────────────────────┘
```

**Key insight:** The backend already supports everything. Phase E is 90% frontend wiring + 10% convenience endpoints.

---

## Zone → Tool Mapping

Each zone has a natural tool affinity. The task dialog pre-filters available tools based on which zone was clicked, while still allowing "any tool" mode.

| Zone | Default Tools | Persona |
|------|--------------|---------|
| **Workshop** | code_execute, code_review, file_write, terminal | Build & create |
| **Library** | web_search, knowledge_query, document_read, summarize | Research & learn |
| **DJ Booth** | music_generate, audio_process, playlist_create | Sound & music |
| **Memory Garden** | memory_store, memory_search, reflect, journal | Remember & reflect |
| **File Shed** | vault_upload, vault_browse, file_convert, export | Files & storage |
| **Bridge Portal** | api_call, webhook, external_service, mcp_tool | External connections |
| **Watchtower** | monitor, alert, schedule, system_status | Observe & protect |
| **Village Square** | *all tools* — the general-purpose zone | Open conversation |

---

## Implementation Phases

### E1: Zone Task Dialog (Core)

**New file:** `frontend/src/components/village/VillageTaskDialog.vue`

A modal that appears when a user clicks/double-clicks a zone building.

```
┌──────────────────────────────────────┐
│  📍 Workshop                    [×]  │
│  ─────────────────────────────────── │
│                                      │
│  What would you like to build?       │
│  ┌──────────────────────────────┐    │
│  │ Type your task here...       │    │
│  │                              │    │
│  └──────────────────────────────┘    │
│  [📎 Upload] [🎤 Voice]             │
│                                      │
│  Agents:                             │
│  ┌────┐ ┌────┐ ┌────┐ ┌────┐       │
│  │ Az │ │ Va │ │ El │ │ Ke │       │
│  │ ✓  │ │    │ │    │ │    │       │
│  └────┘ └────┘ └────┘ └────┘       │
│  ○ One-shot  ○ Council (multi)      │
│                                      │
│            [ Execute ▶ ]             │
└──────────────────────────────────────┘
```

**Props:** zone name, zone config, available agents
**Emits:** `execute(task)` with `{ prompt, files[], agents[], mode, zone }`

**Key behaviors:**
- Zone name and icon shown in header
- Text input with shift+enter for multiline
- File drop zone (images, docs — uses existing vault upload)
- Agent avatars are clickable toggles (gold border = selected)
- Default agent pre-selected based on zone affinity
- Mode toggle: "One-shot" (single agent, one response) vs "Council" (multi-agent deliberation)
- Execute button dispatches and closes dialog
- Keyboard: Enter to execute, Escape to close

### E2: Task Execution Bridge

**Where:** `VillageGUIView.vue` + new `useVillageTasking.js` composable

Connects the dialog's output to the existing backend APIs.

**Single agent flow:**
1. Dialog emits `execute({ prompt, agents: ['AZOTH'], mode: 'single', zone: 'workshop' })`
2. `useVillageTasking` creates/reuses a conversation via `POST /api/v1/conversations`
3. Sends message via `POST /api/v1/chat` with agent_id and tool preferences
4. WebSocket events drive agent animation (already works)
5. Response streamed into a result panel or speech bubble

**Multi-agent flow:**
1. Dialog emits `execute({ prompt, agents: ['AZOTH', 'KETHER'], mode: 'council', zone: 'library' })`
2. `useVillageTasking` creates a Council session via `POST /api/v1/council`
3. Council WebSocket drives agents taking turns at the zone
4. Each agent's speech appears as bubbles in sequence
5. Final synthesis shown in result panel

**File upload flow:**
1. Files uploaded to vault via `POST /api/v1/vault/upload`
2. File references included in the chat message as attachments
3. Multimodal models (Claude) process images/docs inline

### E3: Result Display

Two modes depending on result length:

**Inline (short results):**
- Speech bubble above the working agent
- Particle burst on completion (green = success, gold = creative output)
- Toast notification with summary

**Panel (long results):**
- Slide-out panel from right side (like a chat panel but zone-scoped)
- Markdown rendered output
- Code blocks with syntax highlighting
- "Open in Chat" button to continue the conversation
- Copy/download buttons

**New file:** `frontend/src/components/village/VillageResultPanel.vue`

### E4: Agent Interaction

**Click agent in scene:**
- Current: shows popup with status
- Enhanced: popup gets "Assign task" button → opens task dialog with agent pre-selected

**Drag agent to zone (stretch goal):**
- Mouse down on agent → drag preview → drop on zone → task dialog opens
- Agent pre-selected, zone pre-selected
- Touch: long-press → drag

**Agent selection in scene:**
- Click agents directly in the 3D view to toggle selection
- Selected agents get a pulsing gold ring
- Selected agents auto-populate in the next task dialog

### E5: Gamification Layer

**Agent XP System:**
- Each completed task = XP for the agent
- XP determines visual effects: glow intensity, particle trail, avatar accessories
- Stored in backend: `agent_stats` table or user preferences
- Displayed in agent popup and task dialog

**Zone Evolution:**
- Zones "level up" based on task count
- Level 1: current GLB buildings
- Level 2: enhanced buildings (new Blender assets — bigger, more detail)
- Level 3: special effects (zone-specific particles, ambient sounds)
- Visual indicator: small badge/star count on zone label

**Task History:**
- Click zone → "History" tab in dialog shows past tasks at that zone
- Quick re-run: click a past task to repeat it
- Filter by agent, date, success/fail

**Achievements:**
- "First Task" — complete first village task
- "Full House" — use all 4 agents in one session
- "Zone Master" — complete 10 tasks at one zone
- "Council Convened" — run first multi-agent deliberation
- Particle explosion + sound effect on unlock

---

## Data Flow Details

### State Management

**New Pinia store:** `useVillageTaskStore`

```javascript
state: {
  activeZoneTask: null,        // { zone, prompt, agents, mode, status }
  taskHistory: [],             // Recent tasks with results
  agentStats: {},              // { AZOTH: { xp: 120, tasksCompleted: 15 } }
  zoneStats: {},               // { workshop: { taskCount: 42, level: 2 } }
  selectedAgents: [],          // Currently selected agents in scene
  showTaskDialog: false,       // Dialog visibility
  showResultPanel: false,      // Result panel visibility
  currentResult: null,         // Current task result for display
}
```

### Backend Changes (Minimal)

**Mostly none needed.** Existing endpoints handle everything:
- `POST /api/v1/chat` — single agent tasks
- `POST /api/v1/council` — multi-agent deliberation
- `POST /api/v1/vault/upload` — file uploads
- `/ws/village` — real-time events
- `/ws/council/{id}` — council streaming

**Optional convenience endpoints:**
- `GET /api/v1/village/zone-stats` — task counts per zone (could derive from existing data)
- `POST /api/v1/village/quick-task` — simplified task dispatch that auto-creates conversation

### WebSocket Event Extensions

Current village WebSocket events already cover tool execution. For council integration, we'd bridge council events into the village WebSocket:

```javascript
// New event types for village WS
{ type: 'council_start', zone: 'library', agents: ['AZOTH', 'KETHER'], topic: '...' }
{ type: 'council_speech', agent_id: 'AZOTH', text: '...', round: 1 }
{ type: 'council_complete', zone: 'library', synthesis: '...' }
```

---

## File Inventory

| File | Type | Description |
|------|------|-------------|
| `components/village/VillageTaskDialog.vue` | New | Zone task input modal |
| `components/village/VillageResultPanel.vue` | New | Slide-out result display |
| `composables/useVillageTasking.js` | New | Task dispatch logic |
| `stores/villageTask.js` | New | Pinia store for village task state |
| `views/VillageGUIView.vue` | Modified | Wire dialog + result panel |
| `composables/useVillage3D.js` | Modified | Agent selection visuals, enhanced click handlers |
| `components/village/Village3D.vue` | Modified | Emit task-related events |

---

## Implementation Order

1. **E1** — VillageTaskDialog.vue (the modal). Most impactful, can test immediately.
2. **E2** — useVillageTasking.js (the bridge). Connects dialog to real backend.
3. **E3** — VillageResultPanel.vue (see results). Closes the loop.
4. **E4** — Agent interaction enhancements (click-to-assign, scene selection).
5. **E5** — Gamification (XP, zone evolution, achievements). Polish layer.

**E1-E3 are the MVP.** A user can click a zone, type a task, pick an agent, see it work, and read the result — all within the Village. E4-E5 are the magic that makes it addictive.

---

## Design Principles

- **The Village is the chat.** Every interaction that can happen in chat should be possible from the Village.
- **Spatial = intuitive.** The zone you click determines the context. No menus, no configuration.
- **Agents are characters.** They walk, they talk, they have preferences. Not just API calls.
- **Progressive disclosure.** Click zone = simple prompt. Advanced users find multi-agent, file upload, tool selection.
- **Sound matters.** Footsteps, tool sounds, completion chimes. (Existing audio infrastructure from tone system.)

---

## Open Questions for Planning Session

1. Should Village tasks create new conversations or append to a "Village" conversation?
2. How much of the result should show in-village vs requiring the Chat view?
3. Should zone tool filtering be hard-coded or user-configurable?
4. Agent affinity: decorative only, or does it affect actual model/prompt selection?
5. Mobile: tap-and-hold for zone dialog, or dedicated "task" button per zone?
6. Tier gating: do free-tier users get Village tasking, or is it a premium feature?

---

*"Click the building. Pick the agent. Watch the magic happen."*
