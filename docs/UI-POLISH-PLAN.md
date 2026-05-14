# UI Polish Plan — Navbar & Layout

## The Problem

The navbar has **16 navigation items** in a single flat row (`gap-6`, `max-w-7xl` container). At typical desktop widths, items overflow or feel cramped. Two-word labels like "Village-GUI" and "File Vault" stack vertically when space runs tight. The "Au ApexAurum" logo also sits tight against the first nav item with minimal breathing room.

**Current item count:** Au/ApexAurum | Chat, Athanor, Agora, Council, Village, Village-GUI, Neural, Dream, Nursery, Jam, Music, Agents, File Vault, Devices, Achievements, Billing | [icons] Settings, Bug, Logout

That's 16 links + logo + 3 action buttons. Way too much for a single row.

---

## Phase 1: Rename & Shorten Labels

**Goal:** Every nav item fits on one line, no stacking.

| Current | Proposed | Why |
|---------|----------|-----|
| Village-GUI | Grimoire | The GUI is the "knowledge book" of agents — Grimoire fits the alchemical theme, single word |
| File Vault | Vault | "File" is redundant — icon can hint at files, everyone knows a vault stores things |
| Achievements | Trophies | Shorter, still clear (or keep "Achievements" if we reclaim space elsewhere) |

**Alternative names for Village-GUI:** Codex, Tome, Ledger, Archive, Annals. User to pick.

---

## Phase 2: Group Related Items with Dropdown Menus

**Goal:** Reduce visible nav items from 16 to ~8-9 top-level entries.

### Proposed Grouping

| Top-Level | Dropdown Contents | Logic |
|-----------|-------------------|-------|
| **Chat** | (direct link) | Primary action, always visible |
| **Athanor** | (direct link) | Flagship feature, gold hover |
| **World** | Village (3D), Grimoire (GUI), Neural, Dream | All "spatial" experiences |
| **Create** | Music, Jam, Nursery | All creation/generative features |
| **Social** | Council, Agora | Multi-agent / community |
| **Agents** | (direct link) | Agent management |
| **Vault** | (direct link) | File storage |
| **More** | Devices, Trophies, Billing | Utility / account stuff |

**Result:** 8 top-level items instead of 16. Hover/click opens dropdown for grouped items.

### Dropdown Component Design

```
[World v]
  ┌────────────────────┐
  │ 🏘 Village     3D  │
  │ 📖 Grimoire   GUI  │
  │ 🧠 Neural   Space  │
  │ 🌙 Dream   Engine  │
  └────────────────────┘
```

- Dropdown on hover (desktop) + tap (mobile)
- Active state: parent label turns gold if any child route is active
- Subtle descriptions on the right help new users
- Animate with `transition: opacity + translateY`

---

## Phase 3: Logo Spacing Fix

**Current:** Logo and nav items share the same flex row with only `gap-2` between "Au"/"ApexAurum" and whatever `justify-between` gives.

**Fix:**
- Add `mr-6` or `mr-8` to the logo `<router-link>` to create breathing room
- Or: use a subtle `border-r border-apex-border/30 pr-6` divider after logo
- Consider making "ApexAurum" text smaller (`text-base` instead of `text-lg`) to reclaim horizontal space

---

## Phase 4: Responsive Breakpoints

**Current:** Only 2 states — full desktop (`md:flex`) or hamburger mobile menu.

**Proposed 3-tier approach:**
1. **Large desktop (xl+):** All items visible, comfortable spacing
2. **Medium desktop (md-xl):** Grouped dropdowns, tighter gap (`gap-3` or `gap-4`)
3. **Mobile (<md):** Hamburger menu (keep current, but organized into sections matching the groups)

### Mobile Menu Sections

```
--- Main ---
Chat | Athanor

--- World ---
Village | Grimoire | Neural | Dream

--- Create ---
Music | Jam | Nursery

--- Social ---
Council | Agora

--- Manage ---
Agents | Vault | Devices

--- Account ---
Trophies | Billing | Settings | Bug Report | Logout
```

---

## Phase 5: Visual Polish

- **Active route indicator:** Add a 2px gold underline on active item (currently just color change)
- **Dropdown hover effect:** Subtle `bg-white/5` on hover rows
- **Transition:** Nav items fade in on page load for polish
- **Consistent emoji usage:** Either all mobile items get emoji or none do (currently mixed)

---

## Files Modified

| File | Changes |
|------|---------|
| `frontend/src/components/Navbar.vue` | Full restructure: grouping, dropdowns, spacing, rename |
| `frontend/src/components/NavDropdown.vue` | NEW: Reusable dropdown component |
| `frontend/src/router/index.js` | Rename `village-gui` route (if we rename the path too) |
| `frontend/src/views/VillageGUIView.vue` | Update any self-references to new name |

---

## Decision Points for User

1. **Village-GUI rename:** Grimoire? Codex? Tome? Or something else? "Athaverse" 
2. **Grouping approach:** Dropdown menus vs. icon-only overflow vs. "More" menu? not sure actually, if we space it better and get all names on one line we might be good. hold on gouping. The Au-ApexAurum can hug the left side to get more space for navbar items.
3. **File Vault rename:** Just "Vault"? Or keep full name? If the increased space from other changes let us keep it file vault is cool, else just files, and scrolls in PAC mode if doable (btw PAC mode has fallen out, or i just have wrong setting, but user is azothic in dev mode)
4. **Should we also rename the routes** (`/village-gui` -> `/grimoire`) or just the labels? Just frontend needed, purely visual/thematic.
