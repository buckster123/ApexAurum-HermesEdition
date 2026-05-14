# Settings Page Combover Plan

## The Problem

The Settings page (`SettingsView.vue`, ~1800 lines) has several issues:
1. **Disconnected data:** Memory tab counters and Advanced tab stats don't always connect to real backend data
2. **Model selection fragmented:** Model is set in Settings (Advanced tab) but also in ChatView, and they may not sync
3. **Dev Mode gating:** Most useful settings are hidden behind Dev Mode (Opus+ tier), making the standard settings page feel empty
4. **Stale model list:** Hardcoded model array that needs to stay in sync with backend tier config

---

## Phase 1: Global Model Selection

### Current State
- **SettingsView.vue** (Advanced tab, line 1385-1412): Model dropdown with 4 hardcoded models, saves to `chatStore.defaultModel`
- **ChatView.vue**: Has its own model selector in the chat header, writes to same `chatStore.defaultModel`
- **Problem:** Two places to change the same thing, but user might not realize they're connected

### Solution: Unified Model Setting

**a) Single source of truth:** `chatStore.defaultModel` (already exists)

**b) Remove duplicate:** Keep model selector in ChatView header (it's contextual and convenient), but remove the standalone model dropdown from Settings Advanced tab. Instead, show a read-only "Current model: Sonnet 4.5" with a "Change in Chat" link.

**c) Global model setting in Profile tab:** Add a small "Default Model" section to the Profile tab (visible to all users, not just Dev Mode). This makes it accessible without Dev Mode.

**d) Sync guarantee:** Both ChatView selector and Settings Profile selector write to `chatStore.defaultModel`. When either changes, the other reflects it immediately (Pinia reactivity handles this).

**e) Model list from backend:** Replace hardcoded model list with `billing.allowedModels` filtered list. Backend already returns allowed models in `BillingStatusResponse.features.models`. Frontend can maintain display names in a lookup map.

---

## Phase 2: Fix Memory Tab Data

### Current State (Memory Tab, Lines 1139-1291)
- Shows "memory stats by agent" — agent name + message count
- Memory toggle (enable/disable)
- Agent memory list with expand/collapse
- Export/Clear controls

### Issues to Investigate
- Does the memory toggle actually persist? Check what API it calls
- Are memory counts accurate? Cross-reference with backend memory endpoints
- Does "Clear" actually clear server-side data or just local?

### Fix Plan
- Verify each memory action maps to a real API endpoint:
  - Toggle: `PATCH /api/v1/memory/settings` or similar
  - List: `GET /api/v1/memory/agents`
  - Export: `GET /api/v1/memory/export`
  - Clear: `DELETE /api/v1/memory/agents/{agent_id}`
- If endpoints are missing, either create them or remove the dead UI
- Add loading states and error handling for memory operations

---

## Phase 3: Fix Advanced Tab Counters

### Current State (Advanced Tab, Lines 1574-1612)
Usage stats section showing: messages, music_generated, tokens, cost estimates

### Issues
- Where does this data come from? Likely `billing.usageSummary` or a stats endpoint
- Are counters live or stale?
- Some may be frontend-only counts that reset on page refresh

### Fix Plan
- Map each counter to its backend source:
  - `messages`: from `billing.status.messages_used` (reliable)
  - `music_generated`: from `billing.usageSummary.resources` (if fetched)
  - `tokens`: may not have a backend source — if not, either add endpoint or remove
  - `cost`: if estimated from tokens, clarify it's an estimate
- Add "Last updated" timestamp
- Auto-refresh on tab activation

---

## Phase 4: Promote Useful Settings Out of Dev Mode

### Current Gating
- **Profile tab:** Always visible (good)
- **Agents, Memory, Import, Advanced, API:** Dev Mode only (Opus+ tier, or Easter egg)

### Problem
Seeker and Adept users have no access to:
- Agora settings (these ARE in Profile, good)
- Model selection (stuck on default)
- Sound/haptic toggles
- Temperature slider

### Proposed Restructure

**All Users (no Dev Mode required):**
| Section | Contents |
|---------|----------|
| Profile | Email, display name (existing) |
| Preferences | Default model, default agent, theme, streaming toggle (merge from existing) |
| Sound & UX | Sound effects, haptic (move from Advanced) |
| Response | Max tokens slider, temperature (move from Advanced) |
| Agora | Existing agora settings |
| Usage | Message count, period info (from billing) |

**Dev Mode Only (keep gated):**
| Section | Contents |
|---------|----------|
| Agents | Native + custom agent management |
| Memory | Agent memory management |
| Import | Conversation/memory import |
| API / BYOK | Multi-provider key management |
| Advanced | Cache strategy, context strategy, debug tools |

**Result:** Regular users get a useful settings page. Power users still get everything via Dev Mode.

---

## Phase 5: Temperature & Model Interaction

### Current
- Temperature slider in Advanced tab (Dev Mode only)
- No guidance on what temperature values mean for different models

### Fix
- Move temperature to the "Response" section (all users)
- Add descriptive labels: 0.0 = "Precise", 0.5 = "Balanced", 1.0 = "Creative"
- Persist temperature globally via `chatStore`

---

## Files Modified

| File | Changes |
|------|---------|
| `frontend/src/views/SettingsView.vue` | Restructure tabs, fix data connections, promote settings |
| `frontend/src/stores/chat.js` | Ensure model/temperature are persisted and reactive |
| `frontend/src/views/ChatView.vue` | Minor — ensure model selector reads from same store |
| Backend endpoints | TBD — may need memory management endpoints if missing |

---

## Decision Points for User

1. **Model selector in Settings:** Keep in Advanced (Dev Mode) or promote to Profile (all users)? All users, just limited byt whatever tier user is on.
2. **Sound/temperature:** Promote to all users or keep Dev Mode gated? All users, key for gamified mode/quest teases.
3. **Dead counters:** Remove them or build backend endpoints to support them? 86 them
4. **Memory tab:** Full audit + fix, or remove if barely used? We have neural now, could improve/add insights input there if needed.
