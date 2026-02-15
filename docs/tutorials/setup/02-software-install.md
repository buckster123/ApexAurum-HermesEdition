# Software Install

**Estimated time:** 15-30 minutes (depending on preset and internet speed; voice model downloads add ~10 minutes)

> This guide covers running the unified ApexAurum SensorHead installer. The installer is a single shell script that detects your hardware, installs all required software, configures system services, and verifies everything is working. It is safe to re-run at any time.

---

## Prerequisites

- A Raspberry Pi 5 running **Raspberry Pi OS 64-bit** (Bookworm or later)
- Hardware assembled per [01 - Full SensorHead Build](01-sensorhead-build.md) (or at minimum, a Pi with power and network)
- **Internet connection** (WiFi or Ethernet) -- the installer downloads packages and voice models
- **Terminal access** via one of:
  - Direct keyboard and monitor connected to the Pi
  - SSH from another computer: `ssh your-username@your-pi-hostname.local`
- Approximately 2GB of free disk space (more if installing voice models)

---

## Getting the Installer

**Option A -- Clone the repository (recommended):**

```bash
git clone <repository-url> ~/claude-root/SensorHead
cd ~/claude-root/SensorHead
```

**Option B -- Download just the installer:**

```bash
mkdir -p ~/claude-root/SensorHead
cd ~/claude-root/SensorHead
curl -O <repository-raw-url>/install.sh
```

Make it executable:

```bash
chmod +x install.sh
```

---

## Understanding Presets

The installer supports several presets that bundle modules together based on what hardware you have connected. Every preset includes the base modules (system setup, bridge, and memory). The difference is which sensor modules are added.

| Preset | What It Installs | Hardware Required | Est. Time |
|--------|-----------------|-------------------|-----------|
| `base` | System packages, SensorHead Bridge, CerebroCortex Memory | Pi only (no sensors) | ~5 min |
| `eye` | Base + camera drivers and detection | Pi + one or both cameras | ~6 min |
| `nose` | Base + BME688 air quality with BSEC2 SDK | Pi + BME688 breakout | ~7 min |
| `thermal` | Base + MLX90640 thermal camera driver | Pi + MLX90640 breakout | ~6 min |
| `full` | Everything: base + voice + cameras + BME688 + thermal | Pi + all sensors | ~15 min |
| `custom` | Interactive picker -- choose individual modules | Varies | Varies |

**Which preset should you use?**

- Just got a Pi with no sensors yet? Use `base`.
- Have the full hardware build from the previous guide? Use `full`.
- Want to add a sensor later? Re-run the installer with a different preset -- it detects what is already installed and skips those modules.

---

## Running the Installer

### With a Preset

```bash
sudo ./install.sh --preset full
```

Replace `full` with your chosen preset name. The installer will show a confirmation prompt listing which modules will be installed before proceeding.

### Interactive Mode

```bash
sudo ./install.sh
```

Without arguments, the installer displays a menu:

```
  Choose your SensorHead configuration:

  1) Base      -- Pi + Bridge + Cortex (no sensors)
  2) Eye       -- Base + cameras (visual + night)
  3) Nose      -- Base + BME688 air quality sensor
  4) Thermal   -- Base + MLX90640 thermal camera
  5) Full      -- Everything -- three-eyed SensorHead
  6) Custom    -- Pick individual modules
```

Choose a number to proceed. Option 6 (Custom) lets you select individual modules one by one.

### Getting Help

```bash
./install.sh --help
```

---

## What Each Module Does

### Module 0: System Base

**Always runs first.** Prepares the Pi's operating system for everything else.

- Updates the system package lists (`apt update`)
- Installs required system packages: `python3`, `python3-pip`, `python3-venv`, `git`, `build-essential`, `i2c-tools`, `curl`, `wget`
- On a Raspberry Pi, also installs `libcamera-tools`, `python3-libcamera`, and `python3-picamera2`
- Detects Python 3.11+ (required; the installer will stop if not found)
- Configures boot settings (`/boot/firmware/config.txt`):
  - Enables I2C interface (`dtparam=i2c_arm=on`)
  - Sets I2C bus speed to 400kHz (`dtparam=i2c_arm_baudrate=400000`) for the MLX90640
  - Enables camera auto-detection (`camera_auto_detect=1`)
- Adds the install user to hardware access groups: `i2c`, `video`, `gpio`
- Creates the project directory structure at `~/claude-root/`

> **Note:** If boot configuration changes are made (I2C, camera), the installer will warn that a reboot is needed. You can finish the install first and reboot at the end.

### Module 1: SensorHead Bridge

**Always runs.** This is the core service that connects your Pi to the ApexAurum cloud.

- Clones (or updates) the SensorHead repository
- Creates a Python virtual environment at `SensorHead/venv/`
- Installs Python dependencies from `pyproject.toml` (MCP framework, sensor libraries, numpy, etc.)
- Generates `config.json` with your cloud URL and device token (the installer will prompt you for a token, or you can configure it later)
- Installs a systemd service (`sensorhead-bridge.service`) that:
  - Starts the bridge automatically on boot
  - Restarts automatically if it crashes (10-second delay)
  - Runs as your user (not root)
- Starts the service and verifies it is running

The bridge maintains a persistent WebSocket connection to the ApexAurum backend. When you send a command from your phone ("read the temperature"), the cloud relays it through the WebSocket to the bridge, which executes it locally and sends the result back.

### Module 2: CerebroCortex Memory

**Included in all presets.** Installs the local memory system that agents use to remember things.

- Locates (or clones) the CerebroCortex source code
- Creates a Python virtual environment with ChromaDB (vector search), sentence-transformers (embedding model), and related packages
- Creates the data directory for memory storage
- Generates an MCP (Model Context Protocol) launcher script so Claude Code can connect to it
- On first run, the embedding model (`all-MiniLM-L6-v2`, ~88MB) downloads automatically

CerebroCortex stores memories in a local SQLite database with vector embeddings in ChromaDB. Memories are searchable by meaning (semantic search), not just keywords. The system also maintains a graph of relationships between memories.

### Module 3: Voice Server (Piper TTS + faster-whisper STT)

**Included in the `full` preset; optional in others.** Installs text-to-speech and speech-to-text locally on the Pi.

- Creates the VoiceServer directory and Python code
- Installs `piper-tts` (neural text-to-speech) and `faster-whisper` (speech recognition)
- Downloads five voice models from HuggingFace (one per agent + system voice):

| Voice Model | Agent | Size | Character |
|-------------|-------|------|-----------|
| `en_US-lessac-medium` | System | ~65MB | Neutral, clear |
| `en_US-ryan-high` | AZOTH | ~100MB | Deep, resonant |
| `en_US-amy-medium` | KETHER | ~65MB | Clear, authoritative |
| `en_US-danny-low` | VAJRA | ~30MB | Direct, clipped |
| `en_US-kusal-medium` | ELYSIAN | ~65MB | Warm, gentle |

Total download: approximately 361MB.

- Creates an MCP launcher script for Claude Code integration
- Optionally installs as a systemd service

> **Note:** The voice server uses approximately 700MB of RAM at peak (when all models are loaded). On a Pi 5 with 4GB RAM this is fine but tight alongside other services. 8GB is recommended for comfortable headroom.

### Module 4: Cameras

**Included in `eye` and `full` presets.** Configures and verifies the camera hardware.

- Verifies `libcamera-tools` is installed
- Runs `libcamera-hello --list-cameras` to detect connected cameras
- Checks specifically for the IMX500 (AI Camera) and IMX708 (Wide NoIR)
- Checks for IMX500 AI model files in `/usr/share/imx500-models/`
- Optionally takes a test photo to verify capture works

This module does not install additional drivers -- the Pi OS includes libcamera support for both cameras. It primarily verifies that the hardware is correctly connected and detected.

### Module 5: BME688 Air Quality (Nose)

**Included in `nose` and `full` presets.** Sets up the environmental sensor with Bosch's BSEC2 AI gas analysis.

- Scans the I2C bus for the BME688 at address `0x77` (or `0x76`)
- Checks for the BSEC2 SDK (Bosch Sensortec Environmental Cluster):
  - BSEC is Bosch's proprietary AI library that converts raw gas sensor resistance into meaningful air quality metrics (IAQ index, CO2 equivalent, breath VOC)
  - Due to Bosch's license, it cannot be redistributed -- you must download it from the Bosch website and place it in the expected directory
  - Without BSEC, the BME688 still works for basic readings (temperature, humidity, pressure, raw gas resistance) but cannot provide IAQ scores
- Builds the `bme68x` Python extension from source (compiles C code, takes ~30 seconds)
- Checks for existing BSEC calibration state (calibration improves over 48 hours of continuous operation)

> **Note:** The BSEC2 SDK build step is the most platform-sensitive part of the installer. It compiles native C code against the ARM64 BSEC library. If the build fails, check that `build-essential` is installed and that the BSEC SDK is in the correct directory.

### Module 6: MLX90640 Thermal Camera

**Included in `thermal` and `full` presets.** Installs the thermal camera driver.

- Scans the I2C bus for the MLX90640 at address `0x33`
- Installs `adafruit-circuitpython-mlx90640` in the SensorHead virtual environment
- Verifies I2C bus speed (400kHz is needed for usable frame rates; at 100kHz, each frame takes ~1.4 seconds instead of ~0.4 seconds)
- Optionally runs a test capture that reads a thermal frame and reports min/max/average temperatures

### Module 7: Pocket Sentinel

**Included in all presets (informational only).** Displays configuration information for the Sentinel security feature.

The Sentinel is built into the SensorHead Bridge software and does not require separate installation. It is activated and configured from the mobile app. This module explains the available detection modes (camera, thermal, sound) and presets (night watch, away mode, pet watch).

---

## Install Timing Estimates

These estimates assume a Pi 5 with a reasonable internet connection (~10 Mbps):

| Preset | Install Time | Download Size |
|--------|-------------|---------------|
| `base` | ~5 minutes | ~100MB (apt packages + Python packages) |
| `eye` | ~6 minutes | ~100MB |
| `nose` | ~7 minutes | ~120MB (includes BSEC build time) |
| `thermal` | ~6 minutes | ~110MB |
| `full` (no voice) | ~10 minutes | ~150MB |
| `full` (with voice) | ~15-25 minutes | ~500MB (voice models are the bulk) |

On a slower connection, voice model downloads dominate the install time. The five Piper voice models total approximately 361MB.

---

## Verifying the Install

After the installer finishes, it prints a summary and saves an install manifest. Here is how to manually verify each component.

### Check the Install Manifest

```bash
cat ~/claude-root/.install-manifest.json
```

This JSON file records what was installed, when, and where. Example:

```json
{
  "installer_version": "1.0.0",
  "install_date": "2026-02-15T14:30:00+00:00",
  "platform": "Raspberry Pi 5 Model B Rev 1.0",
  "python": "Python 3.11.2",
  "modules": ["system_base", "sensorhead_bridge", "cerebrocortex", "voice_server", "cameras", "bme688", "mlx90640", "sentinel_info"],
  "sensorhead_dir": "/home/hailo/claude-root/SensorHead",
  "cerebro_dir": "/home/hailo/claude-root/CerebroCore",
  "voice_dir": "/home/hailo/claude-root/VoiceServer"
}
```

### Check Service Status

```bash
# Bridge service (should show "active (running)")
systemctl status sensorhead-bridge

# Voice service (if installed as systemd)
systemctl status voice-server
```

### Check the I2C Bus

```bash
i2cdetect -y 1
```

Expect `33` (thermal) and `77` (environment) if those sensors are connected.

### Check Camera Detection

```bash
libcamera-hello --list-cameras
```

Expect two cameras listed (imx500 and imx708_wide_noir).

### Check Python Environments

```bash
# SensorHead venv
~/claude-root/SensorHead/venv/bin/python --version

# CerebroCortex venv
~/claude-root/CerebroCore/venv/bin/python --version

# Voice server venv (if installed)
~/claude-root/VoiceServer/venv/bin/python --version
```

### Check Bridge Logs

```bash
journalctl -u sensorhead-bridge -n 20 --no-pager
```

Look for "Bridge connected to cloud" or similar success messages. If you see repeated connection failures, your device token may not be configured yet -- see the next guide on cloud pairing.

---

## Re-running the Installer

The installer is designed to be idempotent -- it detects what is already installed and skips or upgrades as appropriate:

- **System packages:** skips already-installed packages
- **Git repositories:** pulls latest changes instead of re-cloning
- **Virtual environments:** reuses existing venvs
- **Config files:** does not overwrite existing configuration
- **Systemd services:** detects existing service files, does not recreate them
- **Voice models:** skips already-downloaded model files

You can safely re-run with a different preset to add new modules:

```bash
# Initially installed base:
sudo ./install.sh --preset base

# Later, added cameras:
sudo ./install.sh --preset eye

# Even later, went full:
sudo ./install.sh --preset full
```

Each run updates the install manifest with the current module list.

---

## Troubleshooting

### "Python 3.11+ required but not found"

The installer needs Python 3.11 or newer. Raspberry Pi OS Bookworm ships with Python 3.11. If you are on an older OS:

```bash
# Check your current Python version
python3 --version

# If below 3.11, upgrade your OS:
sudo apt update && sudo apt full-upgrade
```

Alternatively, install Python 3.11+ from source or a PPA, but upgrading the OS is strongly recommended.

### "apt update" fails

Check your internet connection:

```bash
ping -c 3 google.com
```

If DNS is not resolving, check `/etc/resolv.conf` or your WiFi configuration.

### BSEC2 SDK not found

The Bosch BSEC2 SDK cannot be redistributed due to licensing. Download it manually:

1. Go to [Bosch Sensortec Software Tools](https://www.bosch-sensortec.com/software-tools/software/bme688-software/)
2. Download BSEC 2.6.1.0 for Linux
3. Extract to `~/claude-root/SensorHead/BOSCH_SOFTWARE/`
4. Re-run the installer: `sudo ./install.sh --preset nose`

Without BSEC, the BME688 still provides temperature, humidity, pressure, and raw gas resistance. You lose the AI-processed IAQ index, CO2 estimates, and VOC classification.

### bme68x build fails

The bme68x Python extension compiles C code against the BSEC library. Common causes:

```bash
# Missing build tools
sudo apt install build-essential python3-dev

# Wrong BSEC platform binary
# Ensure you have the ARM64 (aarch64) version:
ls ~/claude-root/SensorHead/BOSCH_SOFTWARE/algo/bsec_IAQ_Sel/bin/RaspberryPi/PiFour_Armv8/
# Should contain libalgobsec.a
```

### Voice model download stalls

Large downloads can be interrupted on unreliable connections. Delete the partial file and re-run:

```bash
rm ~/claude-root/VoiceServer/data/voices/en_US-ryan-high.onnx
sudo ./install.sh --preset full
```

The installer checks for existing files by name, so removing a partial download lets it retry.

### Service fails to start

```bash
# Check detailed logs
journalctl -u sensorhead-bridge -n 50 --no-pager

# Common causes:
# - Missing config.json (no device token configured)
# - Python import errors (venv not fully installed)
# - Permission issues (wrong file ownership)

# Fix ownership if needed
sudo chown -R $USER:$USER ~/claude-root/SensorHead
```

### Install log location

Every run creates a timestamped log file:

```bash
ls /tmp/apexaurum-install-*.log

# View the most recent log
less /tmp/apexaurum-install-$(ls -t /tmp/apexaurum-install-*.log | head -1)
```

The log contains full output from every command the installer ran, including error details hidden from the terminal display.

---

## What's Next

- [03 - Cloud Pairing](03-cloud-pairing.md) -- Connect your SensorHead to the ApexAurum cloud backend
- [04 - Mobile App Setup](04-mobile-app.md) -- Install the ApexPocket companion app
- [05 - Voice Setup](05-voice-setup.md) -- Configure text-to-speech and speech-to-text in detail
