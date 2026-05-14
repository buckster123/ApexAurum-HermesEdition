# SensorHead DIY Build Guide & Device Page Plan

## Vision

SensorHead is the physical crown jewel of ApexAurum — a Raspberry Pi-powered sensor companion that gives AI agents real-world perception. Currently it's a working prototype (BME688 environment, MLX90640 thermal, IMX500 AI camera, IMX708 NoIR night camera) with full cloud integration already shipped.

The plan: create a **DIY build guide** for tinkerers, a polished **Devices page**, and a **reward system** that gives builders access regardless of tier.

---

## Part 1: Devices Page Streamline

### Current State
- `DevicesView.vue` (400 lines): Lists devices as cards, supports ApexPocket + SensorHead types
- `SensorDashboardView.vue` (492 lines): Full sensor dashboard (env, thermal, 3 cameras)
- Route: `/devices` (list) and `/devices/:id/sensors` (dashboard)
- Navbar: "Devices" link already exists

### Proposed Changes

**a) Device Page Sections**

```
┌─────────────────────────────────────────────┐
│  📱 My Devices                    [+ Add]   │
│                                              │
│  ┌──── SensorHead ────┐  ┌── ApexPocket ──┐ │
│  │ 🟢 Pi-Sentinel     │  │ 🔴 My Phone    │ │
│  │ Sensors | Dashboard │  │ Reconnect      │ │
│  └────────────────────┘  └────────────────┘ │
│                                              │
│  ─────────────────────────────────────────── │
│                                              │
│  🔧 Build Your Own SensorHead               │
│  [Hero image of completed build]             │
│  Step-by-step guide to build your own AI     │
│  companion device. All tiers welcome.        │
│  [Start Building →]                          │
│                                              │
│  ─────────────────────────────────────────── │
│                                              │
│  📊 What SensorHead Can Do                   │
│  • Environment: temp, humidity, air quality  │
│  • Thermal imaging: heat maps, temp alerts   │
│  • AI Vision: object detection, pose, scene  │
│  • Night vision: IR-sensitive wide angle     │
│  • All accessible to your AI agents          │
│                                              │
└─────────────────────────────────────────────┘
```

**b) Build Guide CTA Card**
- Prominent card below device list
- Hero image of completed SensorHead
- Links to `/devices/build-guide` (new route)
- "Free for all tiers" badge

**c) Capability Showcase**
- Below the build guide CTA
- Visual grid showing the 4 sensor types with sample output images
- "Available to your agents in chat" callout

---

## Part 2: DIY Build Guide Page

### New Route: `/devices/build-guide`

### Page Structure

```
┌─────────────────────────────────────────────┐
│  🔧 Build Your Own SensorHead               │
│  "Give your AI agents real-world senses"     │
│                                              │
│  ┌──────────────────────────────────────┐   │
│  │  [Hero photo: completed SensorHead]   │   │
│  └──────────────────────────────────────┘   │
│                                              │
│  ═══ What You'll Need ═══                    │
│  [Parts list with photos + buy links]        │
│                                              │
│  ═══ Build Steps ═══                         │
│  Step 1: Prepare the Pi .............. [img] │
│  Step 2: Connect BME688 sensor ....... [img] │
│  Step 3: Mount thermal camera ........ [img] │
│  Step 4: Install AI camera .......... [img]  │
│  Step 5: Wire NoIR camera ........... [img]  │
│  Step 6: Assemble enclosure ......... [img]  │
│  Step 7: Flash firmware ............. [img]  │
│  Step 8: Connect to ApexAurum ....... [img]  │
│                                              │
│  ═══ Claim Your Builder Reward ═══           │
│  [Verification + tier gift flow]             │
│                                              │
└─────────────────────────────────────────────┘
```

### Parts List (Bill of Materials)

| Component | Purpose | Est. Cost |
|-----------|---------|-----------|
| Raspberry Pi 5 (4GB+) | Brain | ~$60 |
| BME688 breakout | Environment (temp, humidity, pressure, IAQ) | ~$20 |
| MLX90640 breakout | Thermal imaging (32x24 IR) | ~$55 |
| IMX500 AI camera module | Object detection, classification, pose | ~$70 |
| IMX708 NoIR wide-angle | Night vision camera | ~$30 |
| Jumper wires + headers | Connections | ~$5 |
| MicroSD card (32GB+) | OS + firmware | ~$10 |
| USB-C power supply | Power | ~$15 |
| Enclosure (3D printed or DIY) | Housing | ~$5-15 |
| **Total** | | **~$270-280** |

### Build Steps (High Level)

1. **Prepare the Pi** — Flash Raspberry Pi OS, enable I2C, SPI, camera interfaces
2. **Connect BME688** — I2C wiring (SDA/SCL/3.3V/GND), verify with `i2cdetect`
3. **Mount MLX90640** — I2C (same bus or secondary), verify thermal reads
4. **Install IMX500** — CSI ribbon cable, `libcamera` setup, AI model deployment
5. **Install IMX708 NoIR** — Second CSI port, configure dual-camera
6. **Enclosure assembly** — 3D print files provided (STL) or DIY box guide
7. **Flash SensorHead firmware** — Install bridge client software, configure cloud endpoint
8. **Register with ApexAurum** — Create device in Devices page, pair with token

### Photo Requirements

User (Hailo) has build photos and can recreate any missing ones. Need:
- Each major step (wiring close-ups, board orientation)
- Completed unit from multiple angles
- Screen captures of verification steps
- Before/after of enclosure assembly

### Content Format
- Static Vue page with embedded markdown-style content
- Images stored in `frontend/public/images/build-guide/`
- Collapsible step sections (click to expand details)
- "Copy" buttons for terminal commands
- Print-friendly CSS for offline reference

---

## Part 3: Builder Reward System

### Concept
Anyone who builds a SensorHead and connects it gets rewarded, **regardless of tier** (even free trial).

### Reward Options (User to decide)

| Option | Description | Complexity |
|--------|-------------|------------|
| **A) Tier bump** | Free upgrade to Seeker tier for 30 days | Medium — needs coupon/billing integration |
| **B) Quest shortcut** | Auto-unlock "SensorHead Builder" achievement + bonus quest XP | Low — existing achievement system |
| **C) Permanent perk** | "Builder" badge + SensorHead access on any tier forever | Medium — needs new feature flag |
| **D) Credit grant** | $10 credit bonus on first sensor reading | Low — existing credit system |
| **E) Combo** | Achievement + credit grant + "Builder" badge | Medium |

### Verification Flow

How do we know someone actually built it (vs. just claiming)?

**Option 1: First Sensor Reading (Recommended)**
- Device registered + first successful `sensorhead_environment` reading = verified
- Backend checks: device exists, type=sensor_head, has telemetry data
- Automatic reward trigger via webhook/event

**Option 2: Photo Submission**
- User uploads build photos → admin review → manual approval
- More human touch but doesn't scale

**Option 3: Unique Device Fingerprint**
- BME688 has a unique sensor ID, MLX90640 has serial numbers
- First-time registration of a unique sensor = verified
- Prevents token sharing

### Implementation

```
User builds SensorHead
  → Registers device on Devices page
  → Device connects via WebSocket bridge
  → First environment read succeeds
  → Backend fires "sensorhead_first_read" event
  → Achievement system grants "Builder" milestone
  → Reward applied (tier bump / credits / badge)
  → Celebration animation on Devices page
```

---

## Part 4: SensorHead Access for All Tiers

### Current State
- SensorHead tools are in `ToolCategory.SENSORHEAD`
- Tool access is tier-gated in `services/usage.py`
- Currently unclear what tier is required

### Proposed Change
- **If user has a verified SensorHead device:** All SensorHead tools unlocked regardless of tier
- **If no device:** Tools hidden (can't use them anyway)
- Implementation: Check `device_type='sensor_head'` + `status='active'` in tool permission check
- This is already partially natural — you need a physical device to use the tools, so gating by tier is pointless

### Backend Change
In `tool_permission_check()` (or wherever tools are gated):
```python
# SensorHead tools: require active device, not tier
if tool.category == ToolCategory.SENSORHEAD:
    has_device = await check_user_has_active_sensorhead(user_id, db)
    return has_device  # Tier doesn't matter
```

---

## Part 5: Enclosure Design

### Option A: 3D Printed (for makers with printers)
- Provide STL files in the build guide
- Snap-fit design, no screws
- Ventilation slots for BME688 airflow
- Camera port cutouts
- Pi mounting standoffs

### Option B: DIY Box (for everyone else)
- Guide using a small project box from electronics store
- Drill template PDF for camera holes
- Hot glue mounting instructions

### Option C: Premium Oak Edition (future)
- CNC-milled oak enclosure
- Brass accent fittings
- Pan-tilt servo mount (per SensorHead Vision Roadmap)
- Could be the "Azothic Grand Prize" physical reward

---

## Files Created / Modified

| File | Type | Description |
|------|------|-------------|
| `frontend/src/views/BuildGuideView.vue` | NEW | Step-by-step build guide page |
| `frontend/src/views/DevicesView.vue` | EDIT | Add build guide CTA, capability showcase |
| `frontend/src/router/index.js` | EDIT | Add `/devices/build-guide` route |
| `frontend/public/images/build-guide/` | NEW | Build step photos (from user) |
| `frontend/public/models/build-guide/` | NEW | Optional: 3D STL preview |
| `backend/app/services/usage.py` | EDIT | SensorHead tool access for all tiers |
| `backend/app/api/v1/devices.py` | EDIT | Builder verification endpoint |

---

## Phased Delivery

| Phase | What | Effort |
|-------|------|--------|
| **S1** | Build guide page (text + placeholder images) | 1 session |
| **S2** | Devices page streamline + build guide CTA | 1 session |
| **S3** | Builder reward system (achievement + credits) | 1 session |
| **S4** | SensorHead tool access for all tiers | Quick fix |
| **S5** | Real photos from user + polish | User provides photos |
| **S6** | 3D printable enclosure STLs (if user designs them) | User-driven |

---

## Decision Points for User

1. **Reward type:** Tier bump? Credits? Achievement? Combo? Tier bump+some credits. Max bump to opus.
2. **Verification method:** First sensor reading (automatic) or photo submission (manual)? Both, need fairly good verification in case high tiers (vs cost/loss/gain).
3. **Enclosure:** Provide 3D print files, DIY box guide, or both? Both, i have the simplest "some wood and some nails build prototype ready, and we can make or generate what images and assests we don´t have (online or in local blender-mcp+blenderkit+ai-gen-api´s.
4. **Guide depth:** Quick-start (assumes Pi experience) or beginner-friendly (from zero)? Pi tinkering pre-experience is recommended, but anybody could build this if they buy the thermal with a soldered header, most connections are no-solder ones.
5. **Photos:** Which steps can you photograph? Do we need to recreate any? We have some and it is built so i can easily create any we need now
6. **Route:** `/devices/build-guide` or `/build` or `/sensorhead`? i think sensorhead exists for the actual sensorhead, this already works with my protoype on the site on the one admin account i test with. It has a "sensor" button that leads to the ui for it, but could be brough more into the spotlight on the main devices page.
