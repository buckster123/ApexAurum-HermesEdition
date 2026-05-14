# MASTERPLAN: Unified Install System + Tutorial Hub

> *"The Athanor must be built before the Great Work can begin."*

## Vision

A single, unified system that takes someone from "I just got a Raspberry Pi and some sensors" to a fully operational ApexAurum SensorHead + mobile companion — with offline-capable tutorials, troubleshooting, and quick-start guides.

---

## Part 1: Unified Install System (`install.sh`)

### Design Principles
- **One entry point**: `./install.sh` — interactive menu OR `--preset` flags
- **Modular**: each component installs independently, skips gracefully if hardware absent
- **Idempotent**: safe to re-run (detects existing installs, offers upgrade)
- **Offline-friendly**: downloads can be pre-cached for air-gapped setup

### Hardware Presets

| Preset | Components | Sensors |
|--------|-----------|---------|
| `--preset base` | Pi + Bridge + Cortex + Voice | None |
| `--preset eye` | Base + 1 camera (Pi or USB) | Camera |
| `--preset nose` | Base + BME688 air quality | BME688 + BSEC |
| `--preset thermal` | Base + MLX90640 thermal | MLX90640 |
| `--preset full` | All of the above ("three-eyed") | All sensors |
| `--preset custom` | Interactive picker | User chooses |

### Install Modules (execution order)

#### Module 0: System Base
- Update apt packages
- Install system deps: python3.11+, pip, venv, git, i2c-tools, libcamera
- Enable I2C, SPI, camera interfaces via raspi-config noninteractive
- Create project directory structure (`/home/$USER/claude-root/`)

#### Module 1: SensorHead Bridge (REQUIRED)
- **Source**: Clone ApexAurum-SensorHead repo (or extract from bundle)
- **Venv**: Create `/SensorHead/venv/`, install from `pyproject.toml`
- **Config**: Generate `config.json` from template (asks for cloud token)
  - `cloud_url`: wss://backend-production-507c.up.railway.app/ws/bridge
  - `device_token`: from pairing flow
  - `device_name`: user-chosen name
- **Service**: Install `sensorhead-bridge.service` to `/etc/systemd/system/`
- **Verify**: Start service, check logs for "Bridge connected to cloud"

#### Module 2: CerebroCortex MCP Server
- **Source**: CerebroCortex server code
- **Venv**: Separate venv or shared with SensorHead
- **Config**: Database path, embedding model, memory limits
- **Claude Code integration**: Add to `~/.claude/settings.json` MCP servers
- **Verify**: Test memory store/recall

#### Module 3: Voice Server (TTS/STT)
- **Current state**: Runs on laptop (WSL2) — NEEDS CONSOLIDATION TO PI
- **Target**: Piper TTS + Whisper STT running natively on Pi 5
- **Models**: Download voice models (per agent: azoth, kether, vajra, elysian)
- **Service**: `voice-server.service` systemd unit
- **Config**: Port, model paths, agent voice mappings
- **Verify**: Test speak/listen endpoints

#### Module 4: Camera(s) — Optional
- **Pi Camera**: libcamera setup, test with `libcamera-still`
- **USB Camera**: detect via `v4l2-ctl --list-devices`
- **Config**: Resolution, rotation, capture paths in SensorHead config
- **Verify**: Test capture via bridge command

#### Module 5: BME688 Air Quality (Nose) — Optional
- **Hardware**: I2C address 0x77 (or 0x76), detect via `i2cdetect -y 1`
- **BSEC SDK**: Install Bosch BSEC 2.6.1.0 from `BOSCH_SOFTWARE/`
  - This is the trickiest part — binary SDK, platform-specific
  - Build bme68x Python bindings from `bme68x-build/`
- **Calibration**: BSEC state file, accuracy levels (0-3), auto-save
- **Config**: I2C address, sample rate, BSEC config profile
- **Verify**: Read temperature, humidity, IAQ, gas resistance

#### Module 6: MLX90640 Thermal Camera — Optional
- **Hardware**: I2C address 0x33, detect via `i2cdetect -y 1`
- **Dependencies**: `adafruit-circuitpython-mlx90640`
- **Config**: Refresh rate (4Hz default), I2C frequency
- **Warmup**: 2 frames discarded on startup
- **Verify**: Capture thermal frame, check min/max temps

#### Module 7: Pocket Sentinel (Software)
- **Always installed** with bridge, but configurable
- **Config**: Detection modes (camera/sound/motion), thresholds
  - Camera change threshold, min pixels
  - Sound dB threshold
  - Motion G threshold
  - Cooldown between events
- **Presets**: Home/Away/Sleep/Custom

### Post-Install
- Print summary of what's installed and running
- Generate QR code for mobile app pairing
- Offer to run system test (all sensors, bridge connection, voice)
- Save install manifest for future updates

---

## Part 2: Tutorial Hub (Web)

### Architecture
- **Offline mode**: Single `index.html` + embedded CSS/JS + base64 images
  - Runs from `file://` — works before wifi is configured
  - Bundle size target: <5MB
- **Online mode**: Served from main site (`/docs` or `/setup`)
  - Enhanced: video embeds, live API checks, remote diagnostics
  - Better styling, search, print-friendly
- **Shared content**: Markdown source compiled to both targets

### Content Structure

#### Quick Start Guides (5-10 min each)
1. **First Boot** — Flash SD, boot Pi, connect to wifi
2. **Pair Your Phone** — Install APK, scan QR, first chat
3. **Meet the Agents** — AZOTH, ELYSIAN, VAJRA, KETHER intros
4. **Your First Memory** — Save and recall a cortex memory
5. **SensorHead Basics** — Read environment, take a photo

#### Setup Guides (30-60 min each)
1. **Full SensorHead Build** — Hardware assembly with photos
   - Parts list with purchase links
   - Step-by-step assembly (camera mount, I2C wiring, thermal placement)
   - Case/enclosure options
2. **Software Install** — Running the install system
3. **Cloud Pairing** — Account creation, device registration, token setup
4. **Mobile App Setup** — APK install, permissions, notification config
5. **Voice Setup** — TTS/STT configuration, agent voice selection

#### Deep Guides
1. **Sentinel Configuration** — Tuning detection thresholds, presets, alert routing
2. **BME688 Air Quality** — Understanding IAQ, BSEC calibration, gas scanning
3. **Thermal Imaging** — MLX90640 interpretation, heat mapping, anomaly detection
4. **CerebroCortex** — Memory types, graph navigation, dream cycles
5. **Council Deliberation** — Multi-agent debate setup, question framing
6. **Music Generation** — How the music engine works, library management
7. **Agent Personalities** — Prompt depth, PAC mode, personality tuning

#### Troubleshooting Trees
- **"SensorHead offline"** → Check service → Check bridge → Check wifi → Check token
- **"Camera not working"** → Check interface enabled → Check permissions → Check libcamera
- **"BME688 not detected"** → Check I2C enabled → Check wiring → Check address → Check BSEC
- **"App won't connect"** → Check internet → Check token → Check backend health
- **"Voice not working"** → Check service → Check models → Check audio output

### Agent-Narrated Content (Marketing Crossover)
- AZOTH: *"The Alchemical Build Guide"* — narrates the hardware assembly as transmutation
- ELYSIAN: *"Feeling Your Space"* — emotional framing of sensor capabilities
- VAJRA: *"No Wasted Motion"* — direct, efficient troubleshooting
- KETHER: *"The Unified Field"* — how all components synthesize into one system

---

## Part 3: APK Distribution

### Download Page (`/download` or `/pocket`)
- APK direct download link (latest release)
- QR code for easy phone scanning
- Version info, changelog
- Minimum Android version, permissions explained
- Screenshots/preview gallery

### Update Mechanism
- In-app update check against backend version endpoint
- Backend serves APK from S3/MinIO or static hosting
- Version pinning per subscription tier (if needed)

---

## Part 4: Implementation Phases

### Phase A: Audit & Gather (1 session)
- [ ] Inventory all systemd services, configs, ports, venvs
- [ ] Document all hardware I2C addresses, GPIO pins, interfaces
- [ ] Catalog all Python dependencies across all venvs
- [ ] Map the voice server architecture (current laptop → target Pi)
- [ ] Collect all existing photos/media from marketing/SensorHead/

### Phase B: Install System (2-3 sessions)
- [ ] Create `install.sh` framework with module system
- [ ] Implement Module 0-2 (base, bridge, cortex)
- [ ] Implement Module 3 (voice consolidation to Pi)
- [ ] Implement Module 4-6 (camera, BME688, thermal)
- [ ] Test full install on fresh Pi image
- [ ] Create pre-built SD card image for "instant" option

### Phase C: Tutorial Content (2-3 sessions)
- [ ] Write quick-start guides (markdown source)
- [ ] Write setup guides with photo integration
- [ ] Write deep guides for complex features
- [ ] Build troubleshooting decision trees
- [ ] Agent-narrated versions for marketing flavor

### Phase D: Tutorial Web App (1-2 sessions)
- [ ] Build offline-capable single-page tutorial viewer
- [ ] Compile markdown → embedded HTML
- [ ] Add search, navigation, print styling
- [ ] Build online version with enhanced features
- [ ] Integrate into main site or serve standalone

### Phase E: APK Distribution (1 session)
- [ ] Add download page to frontend
- [ ] Backend endpoint to serve APK + version info
- [ ] In-app update check
- [ ] QR code generation for pairing flow

---

## Key Files & Locations

| Component | Location | Notes |
|-----------|----------|-------|
| SensorHead Bridge | `/home/hailo/claude-root/SensorHead/` | Python, systemd service |
| SensorHead Config | `SensorHead/config.json` | Cloud URL, token, device name |
| Bridge Service | `/etc/systemd/system/sensorhead-bridge.service` | Auto-restart enabled |
| BSEC SDK | `SensorHead/BOSCH_SOFTWARE/` | Binary, platform-specific |
| BME68x Build | `SensorHead/bme68x-build/` | Python bindings |
| Sensor MCP | `SensorHead/sensor-mcp/` | MCP server for sensors |
| Voice Server | TBD (consolidate from laptop) | Piper TTS + Whisper STT |
| CerebroCortex | TBD (document location) | MCP server for memory |
| Backend | `Projects/ApexAurum-Cloud/backend/` | FastAPI on Railway |
| Frontend | `Projects/ApexAurum-Cloud/frontend/` | Vue 3 on Railway |
| Android App | `Projects/ApexPocket-Android/` | Kotlin Compose |
| Build photos | `Projects/ApexAurum-Cloud/marketing/SensorHead/` | Assembly reference |

---

## Hardware Bill of Materials

| Part | Required | Est. Cost | Notes |
|------|----------|-----------|-------|
| Raspberry Pi 5 (4GB+) | Yes | $60-80 | 8GB recommended for voice |
| MicroSD Card (32GB+) | Yes | $10 | A2 speed class recommended |
| USB-C Power Supply (27W) | Yes | $15 | Official Pi 5 PSU |
| Pi Camera Module 3 | Optional | $25 | Or compatible USB webcam |
| BME688 Breakout | Optional | $20-30 | Adafruit or Pimoroni |
| MLX90640 Thermal | Optional | $50-70 | 32x24 pixel thermal array |
| I2C Cables/Jumpers | If sensors | $5 | Qwiic/STEMMA QT recommended |
| Case/Enclosure | Optional | $10-30 | 3D printed or commercial |
| USB Microphone | For voice | $15 | Any USB mic works |
| Speaker/DAC | For voice | $10-30 | I2S DAC or USB audio |

**Minimum viable: Pi 5 + SD + PSU = ~$85**
**Full three-eyed SensorHead: ~$250-300**

---

*"Build the Athanor. Light the flame. The Work begins."*
