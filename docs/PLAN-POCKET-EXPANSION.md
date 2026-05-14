# Pocket Expansion Plan — App-Maxxing the Athanor

*"Carry the full Athanor in your pocket — not just a chat window with sensor perks."*

## The Gap

The mobile app has **20 tools** out of the site's **97+**. Agents on mobile can't remember, can't dream, can't search knowledge, can't guard the house, can't predict weather, can't speak aloud. The phone is a second-class citizen.

**After this plan:** Agents on mobile have full memory powers, environmental intelligence, guardian control, knowledge access, and file management — the same superpowers as the website.

---

## Phase 1: Tool Expansion (Backend Only)

**Goal:** Expand POCKET_TOOLS from 20 to 50+ — zero Kotlin changes needed since tools execute server-side.

### 1A. CerebroCortex Memory (11 tools)
Agents can finally **remember and recall** on mobile.

| Tool | Purpose |
|------|---------|
| `cortex_remember` | Store memories with full pipeline (gating, classification, dedup) |
| `cortex_recall` | Semantic vector search + spreading activation |
| `cortex_village` | Shared cross-agent memories |
| `cortex_stats` | Memory statistics breakdown |
| `cortex_associate` | Create typed links between memories |
| `cortex_neighbors` | Traverse associative memory graph |
| `cortex_episode_start` | Begin narrative episode |
| `cortex_episode_end` | End episode with summary + tone |
| `cortex_episode_add` | Add step to episode |
| `cortex_store_procedure` | Save reusable workflows |
| `cortex_list_procedures` | Browse saved workflows |

*Not included: `cortex_export`, `cortex_import` (file-based, desktop UX), `cortex_create_schema`, `cortex_find_schemas` (niche, agent rarely self-initiates)*

### 1B. Dream Engine (2 tools)
Mobile dream triggers — agents can consolidate on the go.

| Tool | Purpose |
|------|---------|
| `cortex_dream_run` | Trigger full consolidation cycle (ARQ background job) |
| `cortex_dream_status` | Check monthly usage + last cycle results |

### 1C. SensorHead v2 (13 tools → 18 total)
All the new toys we just shipped, plus the missing originals.

| Tool | Purpose |
|------|---------|
| `sensorhead_thermal_data` | Raw thermal readings |
| `sensorhead_classify` | Scene classification |
| `sensorhead_pose` | Human pose estimation |
| `sensorhead_sentinel_arm` | Arm/disarm guardian |
| `sensorhead_sentinel_status` | Guardian status check |
| `sensorhead_sentinel_events` | Event timeline query |
| `sensorhead_sentinel_snapshot` | View detection image |
| `sensorhead_sentinel_configure` | Tune detection config |
| `sensorhead_weather` | Weather prediction from pressure trends |
| `sensorhead_air_quality` | Air quality report + recommendations |
| `sensorhead_speak` | Physical voice through SensorHead speaker |
| `sensorhead_scene_report` | Full multi-sensor scene report |
| `sensorhead_night_vision` | NoIR + thermal dark room check |

### 1D. Knowledge Base (3 tools)
Complete the KB toolkit.

| Tool | Purpose |
|------|---------|
| `kb_lookup` | Quick term definition |
| `kb_topics` | Available knowledge topics |
| `kb_answer` | RAG context retrieval |

### 1E. Vault (3 tools)
Full file management — agents can create files on mobile.

| Tool | Purpose |
|------|---------|
| `vault_write` | Create/overwrite files |
| `vault_search` | Full-text search |
| `vault_edit` | Modify existing files |

### 1F. Scratch Pad (3 tools)
Temporary working memory for multi-step reasoning.

| Tool | Purpose |
|------|---------|
| `scratch_store` | Temp storage |
| `scratch_get` | Retrieve |
| `scratch_list` | Browse |

### 1G. Utilities (3 tools)

| Tool | Purpose |
|------|---------|
| `random_number` | Random generation |
| `uuid_generate` | UUID generation |
| `json_format` | JSON formatting |

### 1H. Timeout Adjustment

Bump `POCKET_TOOL_TIMEOUT` from 30s to 60s — scene_report and dream_run need breathing room. Keep `POCKET_MAX_TOOL_TURNS` at 3.

### Phase 1 Total: 20 existing + 39 new = **59 tools**

**Files Modified:** `backend/app/api/v1/pocket.py` only (POCKET_TOOLS list + timeout)

---

## Phase 2: Memory UI in Android App

**Goal:** Give users a visual interface for browsing, searching, and managing agent memories on mobile.

### 2A. Memory Browser Screen
- List memories per agent with type badges (episodic, semantic, procedural, etc.)
- Search bar with semantic recall (calls `/api/v1/cortex/search`)
- Swipe-to-delete individual memories
- Pull-to-refresh
- Tap memory to see full content + metadata (salience, layer, access count)

### 2B. Memory Quick Actions
- Long-press chat message → "Remember This" (already exists, upgrade to cortex_remember)
- Long-press chat message → "Add to Episode" (start/continue episode)
- Shake phone → "Dream Now" (trigger consolidation with haptic feedback)

### 2C. New API Endpoints (Pocket-specific)
```
GET  /api/v1/pocket/cortex/memories    — Paginated memory list with filters
POST /api/v1/pocket/cortex/search      — Semantic search (simplified response)
GET  /api/v1/pocket/cortex/stats       — Memory dashboard stats
POST /api/v1/pocket/cortex/dream       — Trigger dream cycle
GET  /api/v1/pocket/cortex/dream       — Dream status + history
```

### 2D. Kotlin Implementation
- `CortexApi.kt` — Retrofit interface for cortex endpoints
- `CortexRepository.kt` — Cache + offline queue
- `MemoryBrowserScreen` — Compose/XML list with search
- `MemoryDetailSheet` — Bottom sheet for memory details
- Room entity: `cached_cortex_memories` table

### Files Modified
| File | Change |
|------|--------|
| `backend/app/api/v1/pocket.py` | +5 cortex endpoints |
| `PocketApi.kt` | +cortex models |
| `CortexRepository.kt` | New — cache + offline |
| `PocketViewModel.kt` | +cortex state flows |
| `MemoryBrowserScreen.kt` | New — memory list UI |
| `MemoryDetailSheet.kt` | New — memory detail |
| `Entities.kt` | +cached_cortex_memories |
| `AppDatabase.kt` | +CortexDao |

---

## Phase 3: Offline Memory Sync — COMPLETE

**Goal:** Memories work offline — cached locally, queued for sync, merged on reconnect.

### 3A. Offline Memory Cache — DONE
- CortexRepository with Room cache + 5-minute TTL
- Cache age indicator in sync status bar ("synced 3m ago")
- Automatic refresh when cache is stale

### 3B. Offline Write Queue — DONE
- `cortex_remember` + `cortex_delete` queued in `offline_actions` table
- Queue replay on network return via SyncManager
- Local Room placeholder with `pending_` ID for immediate UI visibility
- Fallback: API call fails → auto-queue (handles NetworkMonitor race condition)

### 3C. Reconnect Handler — DONE
- Global `isOnline` false→true transition detector with 800ms debounce
- Waits up to 3s for API client readiness
- Triggers: offline queue flush, Village Pulse WS reconnect, cortex cache refresh
- Manual sync via Refresh button as backup

### 3D. Background Sync Worker — DONE
- CortexSyncWorker via WorkManager (every 15 min, network + battery constraints)
- Processes offline queue + refreshes cortex cache

### 3E. UI — DONE
- Sync status bar: cache age, pending count, online/offline indicator
- Purple Remember FAB with agent selector + content field
- Pending badge on Cortex chip

### Files Modified
| File | Change |
|------|--------|
| `backend/app/api/v1/pocket.py` | POST /cortex/memories endpoint |
| `CortexRepository.kt` | New — Room cache + offline queue + fallback |
| `CortexSyncWorker.kt` | New — WorkManager periodic sync |
| `SyncManager.kt` | +cortex_remember, cortex_delete replay |
| `PocketViewModel.kt` | +CortexRepository, reconnect handler, sync methods |
| `MemoriesScreen.kt` | +sync status bar, Remember FAB, pending badge |
| `MainActivity.kt` | +cortex sync wiring |
| `PocketApi.kt` | +createCortexMemory endpoint + models |
| `Daos.kt` | +getLastSyncTime, count queries |
| `ApexPocketApp.kt` | +CortexSyncWorker registration |

---

## Phase 4: Stretch Goals

### 4A. Memory Graph Visualization (3D)
- Simplified force-directed graph of memory nodes on phone
- Tap node to read memory, long-press to navigate links
- Use Compose Canvas or lightweight GL

### 4B. Voice Memory
- "Hey AZOTH, remember that..." → STT → cortex_remember
- "What do you know about..." → STT → cortex_recall → TTS response
- Zero-tap memory interaction

### 4C. Shared Agent Workspace
- Cross-agent memory sharing visible on mobile
- Village memory feed (real-time cortex_village updates)
- Agent-to-agent memory references in chat

### 4D. Smart Notifications
- "AZOTH remembered something about your trip" push notification
- Dream cycle completion with highlight summary
- Sentinel event push with snapshot thumbnail

---

## Summary

| Phase | Scope | Effort | Impact |
|-------|-------|--------|--------|
| **1** | POCKET_TOOLS expansion | 30 min | Agents get full powers on mobile — **SHIPPED** |
| **2** | Memory UI screens | 1-2 days | Users can browse/search memories — **SHIPPED** |
| **3** | Offline sync | 1 day | Works without internet — **SHIPPED** |
| **4** | Stretch (graph, voice, push) | 2-3 days | Premium mobile experience |

---

*"The pocket holds the flame — every memory, every dream, every guardian whisper."*
