# Phase A: System Audit — Complete Inventory

> *"Know the Athanor before you build the Athanor."*

**Date:** 2026-02-15
**Purpose:** Full inventory of all components for building the unified install system + tutorial hub.

---

## 1. SYSTEM OVERVIEW

| Component | Location | Platform | Status |
|-----------|----------|----------|--------|
| SensorHead Bridge | `/home/hailo/claude-root/SensorHead/` | Pi 5 | Running (systemd) |
| CerebroCortex MCP | `/home/hailo/claude-root/airlock/cerebro_future/CerebroCore/` | Pi 5 | Running (Claude MCP) |
| Voice Server | `/home/apex/VoiceServer/` (laptop WSL2) | Laptop | Running (SSH tunnel) |
| Backend API | Railway (auto-deploy) | Cloud | Running |
| Frontend | Railway (auto-deploy) | Cloud | Running |
| Android App | `/home/hailo/claude-root/Projects/ApexPocket-Android/` | Local build | APK: 43MB |

**Hardware:** Raspberry Pi 5 8GB, aarch64, Debian 13 (Trixie), Linux 6.12, NVMe SSD boot
**Python:** 3.13.5 (Pi), 3.12.3 (Laptop WSL2)
**Network:** Pi at 192.168.0.158, Laptop at 192.168.0.104/107

---

## 2. SENSORHEAD BRIDGE

### Service
```ini
# /etc/systemd/system/sensorhead-bridge.service
[Unit]
Description=SensorHead Cloud Bridge
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=hailo
WorkingDirectory=/home/hailo/claude-root/SensorHead
ExecStart=/home/hailo/claude-root/SensorHead/venv/bin/python -m sensor_head.bridge
Restart=always
RestartSec=10
Environment=PYTHONPATH=/home/hailo/claude-root/SensorHead

[Install]
WantedBy=multi-user.target
```

### Config
```json
// /home/hailo/claude-root/SensorHead/config.json
{
  "cloud_url": "https://backend-production-507c.up.railway.app",
  "device_token": "apex_dev_9f778072dee06c07450570614d299cfc",
  "device_id": "bcc71fae-93eb-4fc8-8589-526c2212ea88",
  "api_version": "v1",
  "ws_url": "wss://backend-production-507c.up.railway.app/ws/bridge"
}
```
Alternative location: `~/.config/sensorhead/bridge.json` (600 perms, checked first)

### Python Dependencies (pyproject.toml)
```toml
requires-python = ">=3.11"
dependencies = [
    "mcp>=1.26.0",
    "smbus2>=0.4.3",
    "adafruit-circuitpython-mlx90640",
    "adafruit-servokit",
    "bme68x",           # LOCAL BUILD — see BSEC2 section
    "numpy",
    "pillow",
]
```

### Module Structure
```
sensor_head/
├── __init__.py, __main__.py
├── bridge.py          # CloudBridge WebSocket client (18.8 KB)
├── bridge_config.py   # Config management / pairing
├── config.py          # Hardware addresses & constants
├── server.py          # FastMCP server (10 tools)
├── dashboard.py       # HTTP REST API (port 8080, manual)
├── sentinel.py        # Autonomous detection loop (14.5 KB)
├── hardware/
│   ├── environment.py # BME688 + BSEC2 (13.4 KB)
│   ├── cameras.py     # IMX500 + IMX708 (6.4 KB)
│   ├── inference.py   # IMX500 on-chip AI
│   ├── thermal.py     # MLX90640 (8.1 KB)
│   └── i2c_bus.py     # I2C scanner
├── imaging/           # Placeholder
└── static/index.html  # Dashboard web UI (48 KB)
```

### Bridge Protocol Commands
| Category | Commands |
|----------|----------|
| Sensor | `sense_environment`, `sense_thermal`, `read_thermal` |
| Vision | `capture_visual`, `capture_night`, `capture_night_cropped` |
| AI | `detect_objects`, `classify_scene`, `estimate_poses` |
| Sentinel | `sentinel_arm/disarm/configure/load_preset/status` |
| System | `get_head_status`, `tts_speak` |

### Startup Sequence
1. Systemd starts after `network-online.target`
2. Load config from `config.json`
3. Lazy-init hardware (on first command)
4. Connect WSS to backend with auth token
5. Launch 4 async loops: commands, telemetry (30s), heartbeat (25s), sentinel

---

## 3. HARDWARE

### Boot Configuration (`/boot/firmware/config.txt`)
```ini
dtparam=i2c_arm=on
dtparam=i2c_arm_baudrate=400000   # Required for MLX90640 speed
dtparam=spi=on                     # Reserved
dtparam=audio=on
camera_auto_detect=1               # Auto-detect CSI cameras
dtparam=pciex1_gen=3               # NVMe SSD boot
```

### I2C Devices (bus 1)
| Address | Device | Notes |
|---------|--------|-------|
| 0x33 | MLX90640 thermal | 32x24 FIR array |
| 0x77 | BME688 environment | pi3g breakout (alt addr) |
| 0x40 | PCA9685 servo | Not currently connected |

### Cameras
| Camera | Model | Port | Purpose |
|--------|-------|------|---------|
| CAM0 | IMX500 | Top (near USB-C/eth) | AI vision (on-chip neural) |
| CAM1 | IMX708 Wide NoIR | Bottom (near power) | Night vision / IR |

- FPC cables: 22-pin wide-to-narrow, **contacts facing DOWN**
- Both cameras rotated 180° (upside-down mount)
- 30+ AI models in `/usr/share/imx500-models/` (91 MB)

### Physical Build
- Pi 5 vertical on wooden riser platform
- 3D-printed camera bracket (dual cameras)
- BME688 via 6-pin GPIO adapter (occupies 5V pins)
- MLX90640 VIN → Pi 3.3V rail (**NOT** BME688's 5V pass-through)
- Samsung SSD USB boot

---

## 4. BSEC2 BUILD (Critical — Trickiest Install Step)

### Source
```
/home/hailo/claude-root/SensorHead/bme68x-build/
├── bme68xmodule.c              # C extension (77 KB)
├── setup.py                     # Build script
├── BME68x-Sensor-API/          # Bosch C driver (git submodule)
└── bsec2-6-1-0_generic_release # Symlink → ../BOSCH_SOFTWARE

/home/hailo/claude-root/SensorHead/BOSCH_SOFTWARE/
├── algo/bsec_IAQ_Sel/bin/RaspberryPi/PiFour_Armv8/libalgobsec.a  (148 KB)
├── algo/bsec_IAQ_Sel/config/bme688/  (8 config presets)
└── integration_guide/BST-BME-Integration-Guide-AN011-61.pdf
```

### Build Commands
```bash
cd /home/hailo/claude-root/SensorHead/bme68x-build
BSEC2=64 python3 setup.py build
BSEC2=64 python3 setup.py bdist_egg
pip install dist/bme68x-2.6.1-py3.13-linux-aarch64.egg
```

### Output
- `bme68x.cpython-313-aarch64-linux-gnu.so`
- Links: pthread, m, rt, algobsec
- **Python 3.13 specific** — must rebuild for different Python version

### Calibration
- Accuracy levels: 0 → 1 → 2 → 3 (full calibration: **48 hours**)
- State persisted to `data/bsec_state.json` every 5 min
- Compensated temp ~5°C lower than raw (self-heating correction)
- CO2 equivalent derived from VOC (not actual CO2)

---

## 5. CEREBROCORTEX MCP SERVER

### Location & Launch
```
/home/hailo/claude-root/airlock/cerebro_future/CerebroCore/
├── cerebro-mcp              # Bash launcher (MCP stdio)
├── cerebro-api              # REST API launcher (port 8767)
├── cerebro                  # CLI launcher
├── src/cerebro/             # Source (43KB cortex.py, 77KB mcp_server.py)
├── venv/                    # Python 3.13 venv
└── data/
    ├── cerebro.db           # SQLite (4.3 MB, 1921 memories)
    ├── cerebro.db-wal       # WAL file (3 MB)
    └── chroma/              # ChromaDB vectors (19 MB)
```

### Dependencies
```
chromadb>=0.4.0
sentence-transformers>=2.2.0
python-igraph>=0.11.0
pydantic>=2.0.0
click>=8.0.0
python-dateutil>=2.8.0
mcp>=0.1.0
fastapi>=0.100.0
uvicorn>=0.22.0
anthropic>=0.25.0
```

### Config
| Setting | Value |
|---------|-------|
| Embedding model | all-MiniLM-L6-v2 (384 dim) |
| Database | SQLite 3.x |
| Vector store | ChromaDB (local persistent) |
| Dream LLM primary | qwen/qwen3-4b-2507 via LM Studio @ 192.168.0.107:1234 |
| Dream LLM fallback | claude-sonnet-4-5-20250929 |
| Data dir env | `CEREBRO_DATA_DIR` |
| Model cache | `~/.cache/huggingface/` (88 MB) + `~/.cache/chroma/` (167 MB) |

### Disk Footprint: ~300 MB (data + models + venv)

---

## 6. VOICE SERVER (Currently on Laptop — Needs Pi Consolidation)

### Current Architecture
```
Pi ──SSH tunnel──> Laptop WSL2 ──> /home/apex/VoiceServer/
```
MCP config: `ssh -o ConnectTimeout=5 -o ServerAliveInterval=30 laptop /home/apex/VoiceServer/voice-mcp`

### Source Structure
```
VoiceServer/
├── voice_server/
│   ├── engine.py       # Multi-voice TTS + STT engine (8.4 KB)
│   ├── mcp_server.py   # 4 MCP tools: speak, listen, voices, voice_status
│   └── api.py          # REST API (3.3 KB)
├── data/voices/        # Piper .onnx models (361 MB total)
├── voice-mcp           # MCP launcher
└── voice-api           # REST API launcher
```

### Dependencies
```
piper-tts>=1.4.0
faster-whisper>=1.2.0
onnxruntime>=1.24.0
mcp>=0.1.0
fastapi>=0.100.0 (optional, for REST API)
uvicorn>=0.22.0 (optional, for REST API)
```

### Voice Models (5 voices, 361 MB)
| Model | Size | Agent |
|-------|------|-------|
| en_US-ryan-high.onnx | 116 MB | AZOTH |
| en_US-amy-medium.onnx | 61 MB | KETHER |
| en_US-danny-low.onnx | 61 MB | VAJRA |
| en_US-kusal-medium.onnx | 61 MB | ELYSIAN |
| en_US-lessac-medium.onnx | 61 MB | System |

### STT: faster-whisper (base model, int8 quantized, CPU, beam=5, VAD enabled)

### Pi Consolidation Notes
- Piper TTS runs great on Pi 5 (~50ms/sentence on CPU)
- faster-whisper base model needs ~400 MB RAM
- Voice model cache: ~300 MB RAM when all 5 loaded
- Total voice footprint: ~800 MB disk, ~700 MB RAM peak
- Pi 5 8GB has headroom for this

---

## 7. BACKEND (Cloud — Railway)

### Dockerfile
- Base: `python:3.11-slim`
- Non-root user: `apex`
- System deps: `build-essential`, `curl`, `fluidsynth`, `fluid-soundfont-gm`, `ffmpeg`
- Entry: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`

### Required Env Vars
| Variable | Purpose |
|----------|---------|
| `ANTHROPIC_API_KEY` | Claude API |
| `DATABASE_URL` | PostgreSQL+asyncpg |
| `REDIS_URL` | Cache/sessions |
| `SECRET_KEY` | JWT signing |
| `VOYAGE_API_KEY` | Enhanced embeddings (optional) |
| `SUNO_API_KEY` | Music generation (optional) |
| `S3_*` | Object storage (optional) |

### Native Prompts (11 files, 761 lines)
```
native_prompts/
├── ∴AZOTH∴.txt (114 lines)        ∴AZOTH∴-PAC.txt (17 lines)
├── ∴KETHER∴.txt (111 lines)       ∴KETHER∴-PAC.txt (18 lines)
├── ∴VAJRA∴.txt (100 lines)        ∴VAJRA∴-PAC.txt (20 lines)
├── ∴ELYSIAN∴.txt (114 lines)      ∴ELYSIAN∴-PAC.txt (17 lines)
├── NURSERY_KEEPER.txt (33 lines)   ∴Nursery Keeper∴-PAC.txt (18 lines)
└── GPT4O-SYSTEM.txt (199 lines)
```

---

## 8. ANDROID APP

### Build Config
```kotlin
applicationId: com.apexaurum.pocket
minSdk: 26 (Android 8.0)
targetSdk: 35 (Android 15)
versionCode: 1, versionName: "1.0.0"
Java: 21, Kotlin: 2.1.0, Compose BOM: 2024.12.01
ProGuard: enabled (release), resource shrinking: enabled
```

### APK Size: ~43 MB (debug), release TBD
### No CI/CD — manual `./gradlew assembleDebug` + ADB install

---

## 9. EXISTING CONTENT ASSETS

### Build Photos (17 high-res + 1 composite)
| File | Description |
|------|-------------|
| `marketing/SensorHead/the-pi.jpg` | Pi 5 on wooden riser |
| `marketing/SensorHead/nose.jpg` | BME688 breakout |
| `marketing/SensorHead/ai-cam.jpg` | IMX500 AI camera |
| `marketing/SensorHead/noir-cam.jpg` | IMX708 NoIR camera |
| `marketing/SensorHead/thermal.jpg` | MLX90640 module |
| `marketing/SensorHead/thermal-connections.jpg` | Thermal wiring detail |
| `SensorHead/pics/composite_all_senses.jpg` | All sensors composite |
| + 10 additional build photos | Assembly progress shots |

### Existing Tutorials (Already Coded!)
- **`BuildGuideView.vue`** (492 lines) — 10-step build guide with parts list, photos, commands, collapsible steps
- **`SensorDashboardView.vue`** (492 lines) — Full sensor dashboard
- **`DevicesView.vue`** (400+ lines) — Device management + QR pairing

### Documentation
- **`MASTERPLAN-INSTALL-TUTORIALS.md`** — Install system + tutorial hub blueprint
- **`SENSORHEAD-DIY-PLAN.md`** — Device page + build guide + builder reward plan
- **`campaign-brief.md`** — Full marketing campaign (432 lines)
- **`SESSION_KNOWLEDGE.md`** — SensorHead technical reference (52 lines)

### Content Gaps
1. No offline-capable tutorial viewer (HTML)
2. No troubleshooting decision trees (planned, unwritten)
3. No deep guides (BME688 calibration, thermal interpretation)
4. No quick-start guides (5 planned, 0 written)
5. No agent-narrated content yet

---

## 10. SYSTEM PACKAGE REQUIREMENTS (Fresh Pi Install)

### APT Packages
```bash
# Core
python3 python3-pip python3-venv python3-dev git build-essential

# I2C / GPIO
i2c-tools

# Camera
libcamera-tools libcamera-v4l2 python3-libcamera python3-picamera2

# Audio (for voice on Pi)
pulseaudio  # or pipewire

# Optional
curl wget
```

### Boot Config Edits (raspi-config noninteractive)
```bash
raspi-config nonint do_i2c 0           # Enable I2C
raspi-config nonint do_spi 0           # Enable SPI
raspi-config nonint do_camera 0        # Enable camera
# Manual: add dtparam=i2c_arm_baudrate=400000 to config.txt
```

### User Groups
```bash
usermod -aG i2c $USER
usermod -aG video $USER
usermod -aG gpio $USER
```

---

## 11. INSTALL MODULE MAP

| Module | Required | Deps | Venv | Service | Config |
|--------|----------|------|------|---------|--------|
| 0: System Base | Yes | apt packages, boot config | — | — | config.txt |
| 1: Bridge | Yes | pyproject.toml + bme68x egg | SensorHead/venv | sensorhead-bridge.service | config.json |
| 2: CerebroCortex | Yes | cerebro-cortex[all] | CerebroCore/venv | Claude MCP config | CEREBRO_DATA_DIR |
| 3: Voice | Optional | piper-tts, faster-whisper | VoiceServer/venv | voice-server.service (NEW) | voice models |
| 4: Cameras | Optional | libcamera, picamera2 | shared w/ Bridge | — | config.py |
| 5: BME688 | Optional | BSEC2 build + bme68x egg | shared w/ Bridge | — | I2C 0x77 |
| 6: MLX90640 | Optional | adafruit-mlx90640 | shared w/ Bridge | — | I2C 0x33 |
| 7: Sentinel | Auto | (part of bridge) | shared w/ Bridge | — | thresholds in bridge |

---

## 12. NETWORK TOPOLOGY

```
┌─ Pi 5 (192.168.0.158) ──────────────────────────────────┐
│                                                           │
│  SensorHead Bridge (systemd, auto-start)                  │
│    └─ WSS ──────────> Railway Backend (cloud)             │
│                            └─ Postgres + Redis + S3       │
│  CerebroCortex MCP (Claude stdio, session-scoped)         │
│    └─ SQLite + ChromaDB (local)                           │
│    └─ Dream LLM ──> LM Studio @ 192.168.0.107:1234       │
│                                                           │
│  Voice Server MCP (SSH tunnel, session-scoped)            │
│    └─ SSH ──────────> Laptop WSL2 (192.168.0.104)         │
│                          └─ Piper TTS + Whisper STT       │
│                                                           │
│  Blender MCP (session-scoped)                             │
│    └─ TCP ──────────> Windows Blender @ 192.168.0.104:9876│
└───────────────────────────────────────────────────────────┘

┌─ Mobile (Android) ───────────────────────────────────────┐
│  ApexPocket App                                           │
│    └─ HTTPS ────────> Railway Backend                     │
│    └─ WSS ──────────> Railway Backend /ws/village         │
└───────────────────────────────────────────────────────────┘
```

---

## 13. ESTIMATED DISK/RAM BUDGET (Full Install)

| Component | Disk | RAM (peak) |
|-----------|------|------------|
| System + apt packages | ~500 MB | — |
| SensorHead venv + code | ~200 MB | ~150 MB |
| BSEC2 SDK + build | ~50 MB | — |
| CerebroCortex venv + data | ~300 MB | ~500 MB |
| Embedding model cache | ~255 MB | ~200 MB |
| Voice Server venv + models | ~800 MB | ~700 MB |
| IMX500 AI models | ~91 MB | ~50 MB |
| **Total** | **~2.2 GB** | **~1.6 GB peak** |

Pi 5 8GB has plenty of headroom. 4GB model should work without voice.

---

*"The inventory is complete. The Athanor's components are catalogued. Build may begin."*
