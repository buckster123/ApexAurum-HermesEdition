#!/usr/bin/env bash
# ══════════════════════════════════════════════════════════════════════
#  ApexAurum SensorHead — Unified Installer
#  "Build the Athanor. Light the flame. The Work begins."
#
#  Usage:
#    ./install.sh                    # Interactive menu
#    ./install.sh --preset base      # Pi + Bridge + Cortex
#    ./install.sh --preset eye       # Base + cameras
#    ./install.sh --preset nose      # Base + BME688 air quality
#    ./install.sh --preset thermal   # Base + MLX90640 thermal
#    ./install.sh --preset full      # Everything ("three-eyed")
#    ./install.sh --preset custom    # Interactive picker
#    ./install.sh --help             # Show this help
#
#  Safe to re-run — detects existing installs, skips or upgrades.
# ══════════════════════════════════════════════════════════════════════
set -euo pipefail

# ── Version ──────────────────────────────────────────────────────────
INSTALLER_VERSION="1.0.0"

# ── Paths ────────────────────────────────────────────────────────────
INSTALL_USER="${SUDO_USER:-$USER}"
INSTALL_HOME=$(eval echo "~$INSTALL_USER")
PROJECT_ROOT="${INSTALL_HOME}/claude-root"
SENSORHEAD_DIR="${PROJECT_ROOT}/SensorHead"
CEREBRO_DIR="${PROJECT_ROOT}/CerebroCore"
VOICE_DIR="${PROJECT_ROOT}/VoiceServer"
DATA_DIR="${SENSORHEAD_DIR}/data"
MANIFEST_FILE="${PROJECT_ROOT}/.install-manifest.json"
LOG_FILE="/tmp/apexaurum-install-$(date +%Y%m%d-%H%M%S).log"

# ── Git Repos ────────────────────────────────────────────────────────
SENSORHEAD_REPO="git@github.com:buckster123/SensorHead.git"
CEREBRO_REPO=""  # TODO: set when published
VOICE_REPO=""    # TODO: set when published

# ── Cloud Defaults ───────────────────────────────────────────────────
CLOUD_URL="https://backend-production-507c.up.railway.app"
WS_URL="wss://backend-production-507c.up.railway.app/ws/bridge"
API_VERSION="v1"

# ── Colors ───────────────────────────────────────────────────────────
GOLD='\033[38;5;220m'
AMBER='\033[38;5;214m'
RED='\033[38;5;196m'
GREEN='\033[38;5;82m'
BLUE='\033[38;5;111m'
VIOLET='\033[38;5;183m'
WHITE='\033[38;5;255m'
DIM='\033[38;5;242m'
BOLD='\033[1m'
RESET='\033[0m'

# ── State ────────────────────────────────────────────────────────────
MODULES_TO_RUN=()
INSTALLED_MODULES=()
PYTHON_CMD=""
ERRORS=()

# ══════════════════════════════════════════════════════════════════════
#  UTILITY FUNCTIONS
# ══════════════════════════════════════════════════════════════════════

banner() {
    echo ""
    echo -e "${GOLD}${BOLD}"
    echo "  ╔══════════════════════════════════════════════════════╗"
    echo "  ║                                                      ║"
    echo "  ║     ∴ ApexAurum SensorHead Installer ∴              ║"
    echo "  ║                                                      ║"
    echo "  ║     \"Build the Athanor. Light the flame.\"           ║"
    echo "  ║                                                      ║"
    echo "  ╚══════════════════════════════════════════════════════╝"
    echo -e "${RESET}"
    echo -e "${DIM}  Installer v${INSTALLER_VERSION} — $(date '+%Y-%m-%d %H:%M')${RESET}"
    echo ""
}

log() {
    echo "[$(date '+%H:%M:%S')] $*" >> "$LOG_FILE"
}

info() {
    echo -e "  ${GOLD}▸${RESET} $*"
    log "INFO: $*"
}

success() {
    echo -e "  ${GREEN}✓${RESET} $*"
    log "OK: $*"
}

warn() {
    echo -e "  ${AMBER}⚠${RESET} $*"
    log "WARN: $*"
}

error() {
    echo -e "  ${RED}✗${RESET} $*"
    log "ERROR: $*"
    ERRORS+=("$*")
}

section() {
    echo ""
    echo -e "${GOLD}${BOLD}  ── $* ──${RESET}"
    echo ""
    log "=== SECTION: $* ==="
}

subsection() {
    echo -e "  ${DIM}─ $* ─${RESET}"
    log "--- $* ---"
}

prompt_yn() {
    local prompt="$1"
    local default="${2:-y}"
    local yn_hint
    if [[ "$default" == "y" ]]; then
        yn_hint="[Y/n]"
    else
        yn_hint="[y/N]"
    fi
    echo -en "  ${GOLD}?${RESET} ${prompt} ${DIM}${yn_hint}${RESET} "
    read -r answer
    answer="${answer:-$default}"
    [[ "${answer,,}" == "y" || "${answer,,}" == "yes" ]]
}

prompt_input() {
    local prompt="$1"
    local default="${2:-}"
    if [[ -n "$default" ]]; then
        echo -en "  ${GOLD}?${RESET} ${prompt} ${DIM}[${default}]${RESET} "
    else
        echo -en "  ${GOLD}?${RESET} ${prompt} "
    fi
    read -r answer
    echo "${answer:-$default}"
}

spinner() {
    local pid=$1
    local msg="${2:-Working...}"
    local chars='⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏'
    local i=0
    while kill -0 "$pid" 2>/dev/null; do
        echo -en "\r  ${GOLD}${chars:i%${#chars}:1}${RESET} ${msg}"
        i=$((i + 1))
        sleep 0.1
    done
    echo -en "\r"
}

run_quiet() {
    local msg="$1"
    shift
    log "RUN: $*"
    if "$@" >> "$LOG_FILE" 2>&1; then
        success "$msg"
        return 0
    else
        error "$msg — failed (check $LOG_FILE)"
        return 1
    fi
}

run_sudo() {
    local msg="$1"
    shift
    log "SUDO: $*"
    if sudo "$@" >> "$LOG_FILE" 2>&1; then
        success "$msg"
        return 0
    else
        error "$msg — failed (check $LOG_FILE)"
        return 1
    fi
}

check_root() {
    if [[ $EUID -eq 0 && -z "${SUDO_USER:-}" ]]; then
        error "Don't run as root directly. Use: sudo ./install.sh"
        exit 1
    fi
}

detect_python() {
    for cmd in python3.13 python3.12 python3.11 python3; do
        if command -v "$cmd" &>/dev/null; then
            local ver
            ver=$("$cmd" --version 2>&1 | grep -oP '\d+\.\d+')
            local major minor
            major=$(echo "$ver" | cut -d. -f1)
            minor=$(echo "$ver" | cut -d. -f2)
            if [[ "$major" -ge 3 && "$minor" -ge 11 ]]; then
                PYTHON_CMD="$cmd"
                success "Python: $($cmd --version) ($cmd)"
                return 0
            fi
        fi
    done
    error "Python 3.11+ required but not found"
    return 1
}

is_pi() {
    [[ -f /proc/device-tree/model ]] && grep -qi "raspberry" /proc/device-tree/model 2>/dev/null
}

pi_model() {
    if is_pi; then
        tr -d '\0' < /proc/device-tree/model
    else
        echo "Not a Raspberry Pi"
    fi
}

check_i2c_device() {
    local addr="$1"
    if command -v i2cdetect &>/dev/null; then
        i2cdetect -y 1 2>/dev/null | grep -q "$addr"
    else
        return 1
    fi
}

check_service_active() {
    systemctl is-active --quiet "$1" 2>/dev/null
}

check_service_exists() {
    systemctl list-unit-files "$1" &>/dev/null 2>&1 && \
        systemctl list-unit-files "$1" 2>/dev/null | grep -q "$1"
}

create_venv() {
    local dir="$1"
    local name="$2"
    if [[ -d "${dir}/venv" ]]; then
        info "Venv already exists: ${name}"
        return 0
    fi
    run_quiet "Creating venv: ${name}" \
        sudo -u "$INSTALL_USER" "$PYTHON_CMD" -m venv "${dir}/venv"
}

pip_install() {
    local venv_dir="$1"
    shift
    "${venv_dir}/venv/bin/pip" install --quiet --upgrade "$@" >> "$LOG_FILE" 2>&1
}

as_user() {
    sudo -u "$INSTALL_USER" "$@"
}

# ══════════════════════════════════════════════════════════════════════
#  MODULE 0: SYSTEM BASE
# ══════════════════════════════════════════════════════════════════════

module_0_system_base() {
    section "MODULE 0: System Base"

    # ── Check platform ──
    if is_pi; then
        success "Platform: $(pi_model)"
    else
        warn "Not a Raspberry Pi — some hardware features may not work"
        if ! prompt_yn "Continue anyway?"; then
            error "Aborted by user"
            exit 1
        fi
    fi

    # ── System packages ──
    subsection "System Packages"

    local packages=(
        python3 python3-pip python3-venv python3-dev
        git build-essential
        i2c-tools
        curl wget
    )

    # Camera packages (Pi-specific)
    if is_pi; then
        packages+=(
            libcamera-tools
            python3-libcamera
            python3-picamera2
        )
    fi

    info "Updating package lists..."
    run_sudo "apt update" apt-get update -qq

    local to_install=()
    for pkg in "${packages[@]}"; do
        if dpkg -l "$pkg" &>/dev/null 2>&1; then
            log "Already installed: $pkg"
        else
            to_install+=("$pkg")
        fi
    done

    if [[ ${#to_install[@]} -gt 0 ]]; then
        info "Installing: ${to_install[*]}"
        run_sudo "Install system packages" \
            apt-get install -y -qq "${to_install[@]}"
    else
        success "All system packages already installed"
    fi

    # ── Python ──
    subsection "Python"
    detect_python || {
        error "Cannot continue without Python 3.11+"
        exit 1
    }

    # ── Boot config (Pi only) ──
    if is_pi; then
        subsection "Boot Configuration"

        local config_file="/boot/firmware/config.txt"
        [[ -f "$config_file" ]] || config_file="/boot/config.txt"

        if [[ -f "$config_file" ]]; then
            local changed=false

            # I2C
            if ! grep -q "^dtparam=i2c_arm=on" "$config_file"; then
                echo "dtparam=i2c_arm=on" | sudo tee -a "$config_file" > /dev/null
                success "Enabled I2C"
                changed=true
            else
                success "I2C already enabled"
            fi

            # I2C fast mode (400kHz for MLX90640)
            if ! grep -q "i2c_arm_baudrate=400000" "$config_file"; then
                echo "dtparam=i2c_arm_baudrate=400000" | sudo tee -a "$config_file" > /dev/null
                success "Set I2C baudrate to 400kHz"
                changed=true
            else
                success "I2C 400kHz already set"
            fi

            # Camera
            if ! grep -q "^camera_auto_detect=1" "$config_file"; then
                echo "camera_auto_detect=1" | sudo tee -a "$config_file" > /dev/null
                success "Enabled camera auto-detect"
                changed=true
            else
                success "Camera auto-detect already enabled"
            fi

            if $changed; then
                warn "Boot config changed — reboot required for hardware changes"
            fi
        else
            warn "Boot config not found at expected location"
        fi

        # ── User groups ──
        subsection "User Groups"
        for group in i2c video gpio; do
            if id -nG "$INSTALL_USER" | grep -qw "$group"; then
                success "${INSTALL_USER} in group: ${group}"
            else
                run_sudo "Add ${INSTALL_USER} to ${group}" \
                    usermod -aG "$group" "$INSTALL_USER"
            fi
        done
    fi

    # ── Directory structure ──
    subsection "Directory Structure"

    local dirs=(
        "$PROJECT_ROOT"
        "$DATA_DIR"
    )
    for dir in "${dirs[@]}"; do
        if [[ -d "$dir" ]]; then
            success "Exists: ${dir/$INSTALL_HOME/~}"
        else
            mkdir -p "$dir"
            chown "$INSTALL_USER:$INSTALL_USER" "$dir"
            success "Created: ${dir/$INSTALL_HOME/~}"
        fi
    done

    INSTALLED_MODULES+=("system_base")
    success "Module 0 complete"
}

# ══════════════════════════════════════════════════════════════════════
#  MODULE 1: SENSORHEAD BRIDGE
# ══════════════════════════════════════════════════════════════════════

module_1_sensorhead_bridge() {
    section "MODULE 1: SensorHead Bridge"

    # ── Clone or update repo ──
    subsection "Source Code"
    if [[ -d "${SENSORHEAD_DIR}/.git" ]]; then
        info "SensorHead repo exists — pulling latest"
        (cd "$SENSORHEAD_DIR" && as_user git pull --ff-only 2>/dev/null) || \
            warn "Git pull failed — using existing code"
        success "SensorHead: ${SENSORHEAD_DIR/$INSTALL_HOME/~}"
    elif [[ -d "$SENSORHEAD_DIR" ]]; then
        success "SensorHead directory exists (not a git repo)"
    else
        if [[ -n "$SENSORHEAD_REPO" ]]; then
            info "Cloning SensorHead..."
            run_quiet "Clone SensorHead" \
                as_user git clone "$SENSORHEAD_REPO" "$SENSORHEAD_DIR"
        else
            error "SensorHead repo not configured and directory doesn't exist"
            return 1
        fi
    fi

    # ── Virtual environment ──
    subsection "Python Environment"
    create_venv "$SENSORHEAD_DIR" "SensorHead"

    # Install dependencies from pyproject.toml
    if [[ -f "${SENSORHEAD_DIR}/pyproject.toml" ]]; then
        info "Installing SensorHead dependencies..."
        (cd "$SENSORHEAD_DIR" && as_user ./venv/bin/pip install --quiet --upgrade -e .) >> "$LOG_FILE" 2>&1 && \
            success "Dependencies installed" || \
            warn "Some dependencies failed — check $LOG_FILE"
    else
        warn "No pyproject.toml found — installing core packages"
        as_user "${SENSORHEAD_DIR}/venv/bin/pip" install --quiet \
            "mcp>=1.26.0" "smbus2>=0.4.3" "numpy" "pillow" \
            "adafruit-circuitpython-mlx90640" "adafruit-servokit" \
            >> "$LOG_FILE" 2>&1
        success "Core packages installed"
    fi

    # ── Bridge config ──
    subsection "Bridge Configuration"

    local config_path="${SENSORHEAD_DIR}/config.json"
    local alt_config="${INSTALL_HOME}/.config/sensorhead/bridge.json"

    if [[ -f "$config_path" || -f "$alt_config" ]]; then
        success "Bridge config exists"
        if [[ -f "$alt_config" ]]; then
            info "Using: ~/.config/sensorhead/bridge.json"
        else
            info "Using: SensorHead/config.json"
        fi
    else
        info "No bridge config found — creating one"
        echo ""
        echo -e "  ${GOLD}Cloud Pairing${RESET}"
        echo -e "  ${DIM}You need a device token from the ApexAurum dashboard.${RESET}"
        echo -e "  ${DIM}Go to: ${WHITE}${CLOUD_URL}${DIM} → Devices → Add Device${RESET}"
        echo ""

        local device_token
        device_token=$(prompt_input "Device token (apex_dev_...):")

        if [[ -z "$device_token" ]]; then
            warn "No token provided — you'll need to configure manually"
            warn "Edit: ${config_path/$INSTALL_HOME/~}"
            cat > "$config_path" <<EOF
{
  "cloud_url": "${CLOUD_URL}",
  "device_token": "YOUR_TOKEN_HERE",
  "device_id": "",
  "api_version": "${API_VERSION}",
  "ws_url": "${WS_URL}"
}
EOF
        else
            local device_name
            device_name=$(prompt_input "Device name:" "SensorHead-$(hostname)")
            local device_id
            device_id=$(python3 -c "import uuid; print(uuid.uuid4())")

            cat > "$config_path" <<EOF
{
  "cloud_url": "${CLOUD_URL}",
  "device_token": "${device_token}",
  "device_id": "${device_id}",
  "api_version": "${API_VERSION}",
  "ws_url": "${WS_URL}"
}
EOF
            success "Config written: ${config_path/$INSTALL_HOME/~}"
        fi
        chown "$INSTALL_USER:$INSTALL_USER" "$config_path"
    fi

    # ── Data directory ──
    if [[ ! -d "$DATA_DIR" ]]; then
        mkdir -p "$DATA_DIR"
        chown "$INSTALL_USER:$INSTALL_USER" "$DATA_DIR"
        success "Created data directory"
    fi

    # ── Systemd service ──
    subsection "Systemd Service"

    local service_name="sensorhead-bridge.service"
    local service_file="/etc/systemd/system/${service_name}"
    local service_src="${SENSORHEAD_DIR}/${service_name}"

    if [[ -f "$service_file" ]]; then
        success "Service file exists"
    else
        # Generate service file
        cat > "/tmp/${service_name}" <<EOF
[Unit]
Description=SensorHead Cloud Bridge
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=${INSTALL_USER}
WorkingDirectory=${SENSORHEAD_DIR}
ExecStart=${SENSORHEAD_DIR}/venv/bin/python -m sensor_head.bridge
Restart=always
RestartSec=10
Environment=PYTHONPATH=${SENSORHEAD_DIR}

[Install]
WantedBy=multi-user.target
EOF
        run_sudo "Install systemd service" \
            cp "/tmp/${service_name}" "$service_file"
        run_sudo "Reload systemd" systemctl daemon-reload
        success "Service installed"
    fi

    # Enable and start
    if ! check_service_active "$service_name"; then
        run_sudo "Enable service" systemctl enable "$service_name"
        run_sudo "Start service" systemctl start "$service_name"

        # Verify
        sleep 3
        if check_service_active "$service_name"; then
            success "Bridge service running"
        else
            warn "Service started but may not be connected yet"
            info "Check: journalctl -u ${service_name} -f"
        fi
    else
        success "Bridge service already running"
    fi

    INSTALLED_MODULES+=("sensorhead_bridge")
    success "Module 1 complete"
}

# ══════════════════════════════════════════════════════════════════════
#  MODULE 2: CEREBROCORTEX MCP SERVER
# ══════════════════════════════════════════════════════════════════════

module_2_cerebrocortex() {
    section "MODULE 2: CerebroCortex Memory"

    # ── Source code ──
    subsection "Source Code"
    if [[ -d "${CEREBRO_DIR}/src/cerebro" ]]; then
        success "CerebroCortex exists: ${CEREBRO_DIR/$INSTALL_HOME/~}"
    elif [[ -n "$CEREBRO_REPO" ]]; then
        info "Cloning CerebroCortex..."
        run_quiet "Clone CerebroCortex" \
            as_user git clone "$CEREBRO_REPO" "$CEREBRO_DIR"
    else
        # Check alternative location (current dev location)
        local alt_dir="${PROJECT_ROOT}/airlock/cerebro_future/CerebroCore"
        if [[ -d "${alt_dir}/src/cerebro" ]]; then
            info "Found CerebroCortex at dev location"
            if [[ ! -d "$CEREBRO_DIR" ]]; then
                as_user ln -sf "$alt_dir" "$CEREBRO_DIR"
                success "Linked: ${CEREBRO_DIR/$INSTALL_HOME/~} → ${alt_dir/$INSTALL_HOME/~}"
            fi
        else
            warn "CerebroCortex source not found"
            warn "Expected at: ${CEREBRO_DIR/$INSTALL_HOME/~}"
            warn "Or clone manually and re-run this module"
            return 1
        fi
    fi

    # Resolve symlinks for actual directory
    local actual_dir
    actual_dir=$(readlink -f "$CEREBRO_DIR")

    # ── Virtual environment ──
    subsection "Python Environment"
    create_venv "$actual_dir" "CerebroCortex"

    # Install dependencies
    info "Installing CerebroCortex dependencies..."
    if [[ -f "${actual_dir}/pyproject.toml" ]]; then
        (cd "$actual_dir" && as_user ./venv/bin/pip install --quiet --upgrade -e ".[all]") \
            >> "$LOG_FILE" 2>&1 && \
            success "cerebro-cortex[all] installed" || \
            warn "Some dependencies failed — check $LOG_FILE"
    else
        as_user "${actual_dir}/venv/bin/pip" install --quiet \
            "chromadb>=0.4.0" "sentence-transformers>=2.2.0" \
            "python-igraph>=0.11.0" "pydantic>=2.0.0" \
            "click>=8.0.0" "python-dateutil>=2.8.0" \
            "mcp>=0.1.0" "fastapi>=0.100.0" "uvicorn>=0.22.0" \
            >> "$LOG_FILE" 2>&1
        success "Core packages installed"
    fi

    # ── Data directory ──
    subsection "Data Directory"
    local data_dir="${actual_dir}/data"
    if [[ ! -d "$data_dir" ]]; then
        as_user mkdir -p "$data_dir"
        success "Created: ${data_dir/$INSTALL_HOME/~}"
    else
        success "Data directory exists"
    fi

    # Count existing memories
    if [[ -f "${data_dir}/cerebro.db" ]]; then
        local mem_count
        mem_count=$(sqlite3 "${data_dir}/cerebro.db" \
            "SELECT COUNT(*) FROM memory_nodes;" 2>/dev/null || echo "?")
        info "Existing memories: ${mem_count}"
    fi

    # ── Embedding model ──
    subsection "Embedding Model"
    local model_cache="${INSTALL_HOME}/.cache/huggingface/hub/models--sentence-transformers--all-MiniLM-L6-v2"
    if [[ -d "$model_cache" ]]; then
        success "Embedding model cached (all-MiniLM-L6-v2)"
    else
        info "Embedding model will download on first run (~88 MB)"
    fi

    # ── MCP launcher script ──
    subsection "MCP Launcher"
    local launcher="${actual_dir}/cerebro-mcp"
    if [[ -f "$launcher" && -x "$launcher" ]]; then
        success "MCP launcher exists and is executable"
    else
        cat > "$launcher" <<'LAUNCHER'
#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_PYTHON="${SCRIPT_DIR}/venv/bin/python"

if [ -x "$VENV_PYTHON" ]; then
    exec "$VENV_PYTHON" -m cerebro.interfaces.mcp_server "$@"
else
    export PYTHONPATH="${SCRIPT_DIR}/src:${PYTHONPATH:-}"
    exec python3 -m cerebro.interfaces.mcp_server "$@"
fi
LAUNCHER
        chmod +x "$launcher"
        chown "$INSTALL_USER:$INSTALL_USER" "$launcher"
        success "Created MCP launcher"
    fi

    # ── Claude Code MCP config hint ──
    echo ""
    info "To use CerebroCortex with Claude Code, add to your project's MCP config:"
    echo -e "  ${DIM}{"
    echo -e "    \"mcpServers\": {"
    echo -e "      \"cerebro-cortex\": {"
    echo -e "        \"command\": \"${launcher}\","
    echo -e "        \"env\": { \"CEREBRO_DATA_DIR\": \"${data_dir}\" }"
    echo -e "      }"
    echo -e "    }"
    echo -e "  }${RESET}"
    echo ""

    INSTALLED_MODULES+=("cerebrocortex")
    success "Module 2 complete"
}

# ══════════════════════════════════════════════════════════════════════
#  MODULE 3: VOICE SERVER (Piper TTS + Whisper STT)
# ══════════════════════════════════════════════════════════════════════

module_3_voice() {
    section "MODULE 3: Voice Server"

    # ── Check if running remotely (SSH tunnel) ──
    local remote_voice=false
    if pgrep -f "ssh.*voice-mcp" &>/dev/null; then
        info "Voice server currently running via SSH tunnel (remote)"
        remote_voice=true
    fi

    if ! prompt_yn "Install voice server locally on this Pi?" "y"; then
        if $remote_voice; then
            success "Keeping remote voice server (SSH tunnel)"
        else
            info "Skipping voice server installation"
        fi
        INSTALLED_MODULES+=("voice_skipped")
        return 0
    fi

    # ── Directory ──
    subsection "Source Code"
    if [[ -d "${VOICE_DIR}/voice_server" ]]; then
        success "Voice server exists: ${VOICE_DIR/$INSTALL_HOME/~}"
    else
        as_user mkdir -p "${VOICE_DIR}/voice_server"
        as_user mkdir -p "${VOICE_DIR}/data/voices"

        # Create the voice server module files
        info "Creating voice server code..."

        # __init__.py
        cat > "${VOICE_DIR}/voice_server/__init__.py" <<'EOF'
"""ApexAurum Voice Server — Piper TTS + faster-whisper STT"""
EOF

        # engine.py
        cat > "${VOICE_DIR}/voice_server/engine.py" <<'PYEOF'
"""Voice engine: multi-voice TTS (Piper) + STT (faster-whisper)"""
import base64
import io
import tempfile
import threading
from pathlib import Path

DATA_DIR = Path(__file__).parent.parent / "data"
VOICES_DIR = DATA_DIR / "voices"
DEFAULT_VOICE = "en_US-lessac-medium"

AGENT_VOICES = {
    "azoth": "en_US-ryan-high",
    "kether": "en_US-amy-medium",
    "vajra": "en_US-danny-low",
    "elysian": "en_US-kusal-medium",
    "system": DEFAULT_VOICE,
}

class VoiceEngine:
    def __init__(self):
        self._tts_cache: dict = {}
        self._stt_model = None
        self._lock = threading.Lock()

    def _get_tts(self, voice_name: str):
        if voice_name not in self._tts_cache:
            try:
                from piper import PiperVoice
                model_path = VOICES_DIR / f"{voice_name}.onnx"
                if not model_path.exists():
                    raise FileNotFoundError(f"Voice model not found: {model_path}")
                self._tts_cache[voice_name] = PiperVoice.load(str(model_path))
            except Exception as e:
                raise RuntimeError(f"Failed to load voice {voice_name}: {e}")
        return self._tts_cache[voice_name]

    def _get_stt(self):
        if self._stt_model is None:
            from faster_whisper import WhisperModel
            self._stt_model = WhisperModel(
                "base", device="cpu", compute_type="int8"
            )
        return self._stt_model

    def speak(self, text: str, voice: str | None = None, speed: float = 1.0) -> str:
        voice_name = AGENT_VOICES.get((voice or "system").lower(), DEFAULT_VOICE)
        with self._lock:
            tts = self._get_tts(voice_name)
            buf = io.BytesIO()
            import wave
            with wave.open(buf, "wb") as wav:
                wav.setnchannels(1)
                wav.setsampwidth(2)
                rate = tts.config.sample_rate
                if speed != 1.0:
                    rate = int(rate * speed)
                wav.setframerate(rate)
                tts.synthesize(text, wav)
            return base64.b64encode(buf.getvalue()).decode("ascii")

    def listen(self, audio_b64: str, language: str | None = None) -> dict:
        with self._lock:
            stt = self._get_stt()
            audio_bytes = base64.b64decode(audio_b64)
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=True) as f:
                f.write(audio_bytes)
                f.flush()
                segments, info = stt.transcribe(
                    f.name,
                    beam_size=5,
                    language=language,
                    vad_filter=True,
                )
                text = " ".join(s.text.strip() for s in segments)
                return {
                    "text": text,
                    "language": info.language,
                    "language_probability": round(info.language_probability, 3),
                }

    def available_voices(self) -> dict:
        found = {}
        if VOICES_DIR.exists():
            for f in VOICES_DIR.glob("*.onnx"):
                name = f.stem
                agents = [a for a, v in AGENT_VOICES.items() if v == name]
                found[name] = {"file": f.name, "agents": agents}
        return {"voices": found, "agent_map": AGENT_VOICES}

    def status(self) -> dict:
        tts_ok = bool(VOICES_DIR.exists() and list(VOICES_DIR.glob("*.onnx")))
        try:
            import faster_whisper
            stt_ok = True
        except ImportError:
            stt_ok = False
        return {
            "tts_available": tts_ok,
            "stt_available": stt_ok,
            "voices_loaded": list(self._tts_cache.keys()),
            "stt_loaded": self._stt_model is not None,
        }

engine = VoiceEngine()
PYEOF

        # mcp_server.py
        cat > "${VOICE_DIR}/voice_server/mcp_server.py" <<'PYEOF'
"""Voice MCP Server — 4 tools: speak, listen, voices, voice_status"""
from mcp.server.fastmcp import FastMCP
from .engine import engine

mcp = FastMCP("voice-server")

@mcp.tool()
def speak(text: str, voice: str | None = None, speed: float = 1.0) -> str:
    """Synthesize text to speech. Returns WAV audio as base64."""
    audio_b64 = engine.speak(text, voice, speed)
    return f"Audio generated ({len(audio_b64)} bytes base64). Voice: {voice or 'system'}"

@mcp.tool()
def listen(audio_base64: str, language: str | None = None) -> dict:
    """Transcribe audio to text."""
    return engine.listen(audio_base64, language)

@mcp.tool()
def voices() -> dict:
    """List available TTS voices and agent mappings."""
    return engine.available_voices()

@mcp.tool()
def voice_status() -> dict:
    """Check TTS and STT engine status."""
    return engine.status()

def main_sync():
    mcp.run(transport="stdio")

if __name__ == "__main__":
    main_sync()
PYEOF

        # __main__.py
        cat > "${VOICE_DIR}/voice_server/__main__.py" <<'PYEOF'
from .mcp_server import main_sync
main_sync()
PYEOF

        chown -R "$INSTALL_USER:$INSTALL_USER" "$VOICE_DIR"
        success "Voice server code created"
    fi

    # ── Virtual environment ──
    subsection "Python Environment"
    create_venv "$VOICE_DIR" "VoiceServer"

    info "Installing voice dependencies (this may take a while)..."
    as_user "${VOICE_DIR}/venv/bin/pip" install --quiet --upgrade \
        "piper-tts>=1.4.0" "faster-whisper>=1.2.0" "onnxruntime>=1.24.0" \
        "mcp>=0.1.0" \
        >> "$LOG_FILE" 2>&1 && \
        success "Voice packages installed" || \
        error "Voice package installation failed — check $LOG_FILE"

    # ── Voice models ──
    subsection "Voice Models (Piper)"

    local voices_dir="${VOICE_DIR}/data/voices"
    as_user mkdir -p "$voices_dir"

    local -A voice_models=(
        ["en_US-lessac-medium"]="https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/lessac/medium/en_US-lessac-medium.onnx"
        ["en_US-ryan-high"]="https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/ryan/high/en_US-ryan-high.onnx"
        ["en_US-amy-medium"]="https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/amy/medium/en_US-amy-medium.onnx"
        ["en_US-danny-low"]="https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/danny/low/en_US-danny-low.onnx"
        ["en_US-kusal-medium"]="https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/kusal/medium/en_US-kusal-medium.onnx"
    )

    local -A voice_json_urls=(
        ["en_US-lessac-medium"]="https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/lessac/medium/en_US-lessac-medium.onnx.json"
        ["en_US-ryan-high"]="https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/ryan/high/en_US-ryan-high.onnx.json"
        ["en_US-amy-medium"]="https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/amy/medium/en_US-amy-medium.onnx.json"
        ["en_US-danny-low"]="https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/danny/low/en_US-danny-low.onnx.json"
        ["en_US-kusal-medium"]="https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/kusal/medium/en_US-kusal-medium.onnx.json"
    )

    local agents=("system" "AZOTH" "KETHER" "VAJRA" "ELYSIAN")
    local i=0
    for voice_name in en_US-lessac-medium en_US-ryan-high en_US-amy-medium en_US-danny-low en_US-kusal-medium; do
        local agent="${agents[$i]}"
        local onnx_file="${voices_dir}/${voice_name}.onnx"
        local json_file="${voices_dir}/${voice_name}.onnx.json"

        if [[ -f "$onnx_file" ]]; then
            success "${voice_name} (${agent}) — already downloaded"
        else
            info "Downloading ${voice_name} (${agent})..."
            if as_user wget -q -O "$onnx_file" "${voice_models[$voice_name]}" 2>>"$LOG_FILE"; then
                # Also download the config JSON
                as_user wget -q -O "$json_file" "${voice_json_urls[$voice_name]}" 2>>"$LOG_FILE" || true
                local size
                size=$(du -h "$onnx_file" | cut -f1)
                success "${voice_name} (${agent}) — ${size}"
            else
                error "Failed to download ${voice_name}"
            fi
        fi
        ((i++))
    done

    # ── MCP launcher ──
    subsection "MCP Launcher"
    local launcher="${VOICE_DIR}/voice-mcp"
    cat > "$launcher" <<LAUNCHER
#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="\$(cd "\$(dirname "\${BASH_SOURCE[0]}")" && pwd)"
export PYTHONPATH="\${SCRIPT_DIR}:\${PYTHONPATH:-}"
exec "\${SCRIPT_DIR}/venv/bin/python3" -m voice_server.mcp_server "\$@"
LAUNCHER
    chmod +x "$launcher"
    chown "$INSTALL_USER:$INSTALL_USER" "$launcher"
    success "MCP launcher: ${launcher/$INSTALL_HOME/~}"

    # ── Systemd service (optional) ──
    subsection "Systemd Service (optional)"
    local service_name="voice-server.service"
    local service_file="/etc/systemd/system/${service_name}"

    if [[ -f "$service_file" ]]; then
        success "Voice service file exists"
    elif prompt_yn "Install voice server as a systemd service?" "n"; then
        cat > "/tmp/${service_name}" <<EOF
[Unit]
Description=ApexAurum Voice Server (Piper TTS + Whisper STT)
After=network.target

[Service]
Type=simple
User=${INSTALL_USER}
WorkingDirectory=${VOICE_DIR}
ExecStart=${VOICE_DIR}/venv/bin/python -m voice_server.mcp_server
Restart=on-failure
RestartSec=10
Environment=PYTHONPATH=${VOICE_DIR}

[Install]
WantedBy=multi-user.target
EOF
        run_sudo "Install voice service" cp "/tmp/${service_name}" "$service_file"
        run_sudo "Reload systemd" systemctl daemon-reload
        run_sudo "Enable voice service" systemctl enable "$service_name"
        success "Voice service installed (start with: sudo systemctl start ${service_name})"
    else
        info "Skipping systemd service — use MCP launcher directly"
    fi

    INSTALLED_MODULES+=("voice_server")
    success "Module 3 complete"
}

# ══════════════════════════════════════════════════════════════════════
#  MODULE 4: CAMERAS
# ══════════════════════════════════════════════════════════════════════

module_4_cameras() {
    section "MODULE 4: Cameras"

    if ! is_pi; then
        warn "Camera module requires Raspberry Pi — skipping"
        return 0
    fi

    # ── Check libcamera ──
    subsection "libcamera"
    if command -v libcamera-hello &>/dev/null; then
        success "libcamera-tools installed"
    else
        run_sudo "Install libcamera-tools" \
            apt-get install -y -qq libcamera-tools python3-libcamera python3-picamera2
    fi

    # ── Detect cameras ──
    subsection "Camera Detection"
    local cam_output
    cam_output=$(libcamera-hello --list-cameras 2>&1 || true)
    log "Camera detection: $cam_output"

    if echo "$cam_output" | grep -qi "imx500"; then
        success "IMX500 AI Camera detected (CAM0)"
    else
        warn "IMX500 not detected — check FPC cable (contacts DOWN, top port)"
    fi

    if echo "$cam_output" | grep -qi "imx708"; then
        success "IMX708 NoIR Wide detected (CAM1)"
    else
        warn "IMX708 not detected — check FPC cable (contacts DOWN, bottom port)"
    fi

    if echo "$cam_output" | grep -q "No cameras"; then
        error "No cameras detected"
        info "Check: FPC cable orientation (contacts facing DOWN toward PCB)"
        info "Check: camera_auto_detect=1 in boot config"
        info "May need reboot after enabling camera interface"
    fi

    # ── IMX500 AI models ──
    subsection "IMX500 AI Models"
    local models_dir="/usr/share/imx500-models"
    if [[ -d "$models_dir" ]]; then
        local model_count
        model_count=$(ls "$models_dir"/*.rpk 2>/dev/null | wc -l)
        success "${model_count} AI models available in ${models_dir}"
    else
        info "IMX500 models not found — install with:"
        echo -e "  ${DIM}sudo apt install imx500-models${RESET}"
    fi

    # ── Test capture ──
    if prompt_yn "Test camera capture?" "n"; then
        info "Capturing test image..."
        local test_img="/tmp/sensorhead-test-capture.jpg"
        if libcamera-still -o "$test_img" -t 2000 --nopreview 2>>"$LOG_FILE"; then
            local size
            size=$(du -h "$test_img" | cut -f1)
            success "Test capture: ${test_img} (${size})"
        else
            warn "Test capture failed — check camera connections"
        fi
    fi

    INSTALLED_MODULES+=("cameras")
    success "Module 4 complete"
}

# ══════════════════════════════════════════════════════════════════════
#  MODULE 5: BME688 AIR QUALITY (NOSE)
# ══════════════════════════════════════════════════════════════════════

module_5_bme688() {
    section "MODULE 5: BME688 Air Quality (Nose)"

    if ! is_pi; then
        warn "BME688 module requires Raspberry Pi — skipping"
        return 0
    fi

    # ── I2C detection ──
    subsection "Hardware Detection"
    if check_i2c_device "77"; then
        success "BME688 detected at I2C address 0x77"
    elif check_i2c_device "76"; then
        success "BME688 detected at I2C address 0x76 (alternate)"
    else
        warn "BME688 not detected on I2C bus"
        info "Check: I2C enabled in boot config"
        info "Check: Wiring — SDA→GPIO2, SCL→GPIO3, VIN→3.3V/5V, GND→GND"
        if ! prompt_yn "Continue BME688 setup anyway?" "n"; then
            return 0
        fi
    fi

    # ── BSEC2 SDK ──
    subsection "BSEC2 SDK (Bosch)"

    local bsec_dir="${SENSORHEAD_DIR}/BOSCH_SOFTWARE"
    local build_dir="${SENSORHEAD_DIR}/bme68x-build"
    local bsec_lib="${bsec_dir}/algo/bsec_IAQ_Sel/bin/RaspberryPi/PiFour_Armv8/libalgobsec.a"

    if [[ -f "$bsec_lib" ]]; then
        success "BSEC2 SDK found"
    else
        warn "BSEC2 SDK not found at: ${bsec_dir/$INSTALL_HOME/~}"
        echo ""
        echo -e "  ${GOLD}The BSEC2 SDK is required for full air quality intelligence.${RESET}"
        echo -e "  ${DIM}Bosch's license prevents redistribution — you need to download it:${RESET}"
        echo -e "  ${WHITE}https://www.bosch-sensortec.com/software-tools/software/bme688-software/${RESET}"
        echo ""
        echo -e "  ${DIM}Download BSEC2 v2.6.1.0, extract to:${RESET}"
        echo -e "  ${WHITE}${bsec_dir/$INSTALL_HOME/~}/${RESET}"
        echo ""

        if ! prompt_yn "BSEC2 SDK already placed? Continue with build?" "n"; then
            warn "BME688 will work in basic mode (no IAQ/VOC/CO2 estimates)"
            info "Re-run this module after placing the BSEC2 SDK"
            return 0
        fi
    fi

    # ── Build bme68x Python extension ──
    subsection "Building bme68x Python Extension"

    if [[ ! -d "$build_dir" ]]; then
        warn "bme68x build directory not found: ${build_dir/$INSTALL_HOME/~}"
        info "Clone: https://github.com/pi3g/bme68x-python-library"
        return 1
    fi

    # Check if already built and installed
    local venv_egg
    venv_egg=$(find "${SENSORHEAD_DIR}/venv/lib/" -name "bme68x*.egg" 2>/dev/null | head -1)
    local venv_so
    venv_so=$(find "${SENSORHEAD_DIR}/venv/lib/" -name "bme68x*.so" 2>/dev/null | head -1)

    if [[ -n "$venv_egg" || -n "$venv_so" ]]; then
        success "bme68x already installed in venv"
    else
        info "Building bme68x with BSEC2 (this takes ~30 seconds)..."

        # Ensure symlink to BSEC2
        local bsec_link="${build_dir}/bsec2-6-1-0_generic_release"
        if [[ ! -e "$bsec_link" ]]; then
            as_user ln -sf "$bsec_dir" "$bsec_link"
        fi

        # Build
        (
            cd "$build_dir"
            export BSEC2=64
            as_user env BSEC2=64 "${SENSORHEAD_DIR}/venv/bin/python" setup.py build
            as_user env BSEC2=64 "${SENSORHEAD_DIR}/venv/bin/python" setup.py bdist_egg
        ) >> "$LOG_FILE" 2>&1

        # Install the egg
        local egg_file
        egg_file=$(find "${build_dir}/dist/" -name "bme68x*.egg" 2>/dev/null | head -1)
        if [[ -n "$egg_file" ]]; then
            as_user "${SENSORHEAD_DIR}/venv/bin/pip" install "$egg_file" >> "$LOG_FILE" 2>&1
            success "bme68x built and installed"
        else
            error "bme68x build failed — check $LOG_FILE"
            return 1
        fi
    fi

    # ── BSEC state ──
    subsection "BSEC Calibration State"
    local state_file="${DATA_DIR}/bsec_state.json"
    if [[ -f "$state_file" ]]; then
        success "BSEC state file exists (calibration data preserved)"
    else
        info "No existing calibration — BSEC will start fresh"
        info "Full calibration takes ~48 hours of continuous operation"
        info "Accuracy: 0 (stabilizing) → 1 → 2 → 3 (calibrated)"
    fi

    INSTALLED_MODULES+=("bme688")
    success "Module 5 complete"
}

# ══════════════════════════════════════════════════════════════════════
#  MODULE 6: MLX90640 THERMAL CAMERA
# ══════════════════════════════════════════════════════════════════════

module_6_thermal() {
    section "MODULE 6: MLX90640 Thermal Camera"

    if ! is_pi; then
        warn "Thermal module requires Raspberry Pi — skipping"
        return 0
    fi

    # ── I2C detection ──
    subsection "Hardware Detection"
    if check_i2c_device "33"; then
        success "MLX90640 detected at I2C address 0x33"
    else
        warn "MLX90640 not detected on I2C bus"
        info "Check: I2C enabled + 400kHz baudrate in boot config"
        info "Check: Wiring — SDA→GPIO2, SCL→GPIO3, VIN→3.3V, GND→GND"
        info "Note: MLX90640 VIN connects to Pi 3.3V, NOT BME688 5V pass-through"
        if ! prompt_yn "Continue thermal setup anyway?" "n"; then
            return 0
        fi
    fi

    # ── Python package ──
    subsection "Python Package"
    local installed
    installed=$("${SENSORHEAD_DIR}/venv/bin/pip" show adafruit-circuitpython-mlx90640 2>/dev/null || true)

    if [[ -n "$installed" ]]; then
        success "adafruit-circuitpython-mlx90640 already installed"
    else
        info "Installing MLX90640 driver..."
        as_user "${SENSORHEAD_DIR}/venv/bin/pip" install --quiet \
            "adafruit-circuitpython-mlx90640" >> "$LOG_FILE" 2>&1 && \
            success "MLX90640 driver installed" || \
            error "MLX90640 driver installation failed"
    fi

    # ── I2C speed note ──
    info "I2C baudrate should be 400kHz for usable frame rate (~0.4s/frame)"
    info "At 100kHz default, frames take ~1.4 seconds"

    # ── Quick test ──
    if prompt_yn "Test thermal sensor?" "n"; then
        info "Reading thermal frame..."
        local test_script='
import board, busio, adafruit_mlx90640
i2c = busio.I2C(board.SCL, board.SDA, frequency=400000)
mlx = adafruit_mlx90640.MLX90640(i2c)
mlx.refresh_rate = adafruit_mlx90640.RefreshRate.REFRESH_4_HZ
frame = [0]*768
mlx.getFrame(frame)  # discard warmup
mlx.getFrame(frame)
temps = [t for t in frame if -40 < t < 300]
print(f"Min: {min(temps):.1f}C  Max: {max(temps):.1f}C  Avg: {sum(temps)/len(temps):.1f}C")
print(f"Pixels: {len(temps)}/768 valid")
'
        if "${SENSORHEAD_DIR}/venv/bin/python" -c "$test_script" 2>>"$LOG_FILE"; then
            success "Thermal sensor working"
        else
            warn "Thermal test failed — check $LOG_FILE"
        fi
    fi

    INSTALLED_MODULES+=("mlx90640")
    success "Module 6 complete"
}

# ══════════════════════════════════════════════════════════════════════
#  MODULE 7: SENTINEL CONFIG
# ══════════════════════════════════════════════════════════════════════

module_7_sentinel() {
    section "MODULE 7: Pocket Sentinel"

    info "Sentinel is built into the SensorHead Bridge"
    info "It activates via the mobile app or cloud commands"
    echo ""
    echo -e "  ${DIM}Detection modes:${RESET}"
    echo -e "    ${GOLD}Camera${RESET}  — Visual change detection (pixel diff threshold)"
    echo -e "    ${GOLD}Thermal${RESET} — Temperature anomaly detection"
    echo -e "    ${GOLD}Sound${RESET}   — Audio level monitoring (requires USB mic)"
    echo ""
    echo -e "  ${DIM}Presets:${RESET}"
    echo -e "    ${WHITE}night_watch${RESET} — High sensitivity, all sensors"
    echo -e "    ${WHITE}away_mode${RESET}   — Standard sensitivity, camera + thermal"
    echo -e "    ${WHITE}pet_watch${RESET}   — Low sensitivity, camera only"
    echo ""
    info "Configure via the ApexPocket mobile app → Sentinel tab"

    INSTALLED_MODULES+=("sentinel_info")
    success "Module 7 complete"
}

# ══════════════════════════════════════════════════════════════════════
#  POST-INSTALL
# ══════════════════════════════════════════════════════════════════════

post_install() {
    section "POST-INSTALL"

    # ── Summary ──
    subsection "Installation Summary"
    echo ""
    for mod in "${INSTALLED_MODULES[@]}"; do
        case "$mod" in
            system_base)       echo -e "  ${GREEN}✓${RESET} System Base (packages, boot config, user groups)" ;;
            sensorhead_bridge) echo -e "  ${GREEN}✓${RESET} SensorHead Bridge (cloud-connected, systemd)" ;;
            cerebrocortex)     echo -e "  ${GREEN}✓${RESET} CerebroCortex Memory (SQLite + ChromaDB)" ;;
            voice_server)      echo -e "  ${GREEN}✓${RESET} Voice Server (Piper TTS + Whisper STT)" ;;
            voice_skipped)     echo -e "  ${DIM}─${RESET} Voice Server (skipped / remote)" ;;
            cameras)           echo -e "  ${GREEN}✓${RESET} Cameras (IMX500 + IMX708)" ;;
            bme688)            echo -e "  ${GREEN}✓${RESET} BME688 Air Quality (BSEC2)" ;;
            mlx90640)          echo -e "  ${GREEN}✓${RESET} MLX90640 Thermal Camera" ;;
            sentinel_info)     echo -e "  ${GREEN}✓${RESET} Pocket Sentinel (configure via app)" ;;
        esac
    done
    echo ""

    # ── Errors ──
    if [[ ${#ERRORS[@]} -gt 0 ]]; then
        subsection "Warnings & Errors"
        for err in "${ERRORS[@]}"; do
            echo -e "  ${RED}!${RESET} ${err}"
        done
        echo ""
        info "Full log: ${LOG_FILE}"
    fi

    # ── Services status ──
    subsection "Service Status"
    if check_service_active "sensorhead-bridge.service"; then
        success "sensorhead-bridge: running"
    else
        warn "sensorhead-bridge: not running"
    fi

    if check_service_active "voice-server.service" 2>/dev/null; then
        success "voice-server: running"
    fi

    # ── Hardware check ──
    if is_pi && command -v i2cdetect &>/dev/null; then
        subsection "I2C Bus"
        if check_i2c_device "77"; then
            success "BME688 @ 0x77"
        fi
        if check_i2c_device "33"; then
            success "MLX90640 @ 0x33"
        fi
    fi

    # ── Save manifest ──
    subsection "Install Manifest"
    cat > "$MANIFEST_FILE" <<EOF
{
  "installer_version": "${INSTALLER_VERSION}",
  "install_date": "$(date -Iseconds)",
  "platform": "$(pi_model 2>/dev/null || echo 'unknown')",
  "python": "$($PYTHON_CMD --version 2>&1)",
  "modules": $(printf '%s\n' "${INSTALLED_MODULES[@]}" | \
    python3 -c "import sys,json; print(json.dumps(sys.stdin.read().strip().split('\n')))"),
  "sensorhead_dir": "${SENSORHEAD_DIR}",
  "cerebro_dir": "${CEREBRO_DIR}",
  "voice_dir": "${VOICE_DIR}",
  "log_file": "${LOG_FILE}"
}
EOF
    chown "$INSTALL_USER:$INSTALL_USER" "$MANIFEST_FILE"
    success "Manifest saved: ${MANIFEST_FILE/$INSTALL_HOME/~}"

    # ── Next steps ──
    echo ""
    echo -e "${GOLD}${BOLD}  ── What's Next ──${RESET}"
    echo ""
    echo -e "  ${WHITE}1.${RESET} Install the ${GOLD}ApexPocket${RESET} app on your Android phone"
    echo -e "  ${WHITE}2.${RESET} Open the app and scan the pairing QR code"
    echo -e "  ${WHITE}3.${RESET} Chat with an agent and try: ${DIM}\"read the room temperature\"${RESET}"
    echo -e "  ${WHITE}4.${RESET} Explore: ${DIM}\"what can you see?\"${RESET} or ${DIM}\"show me the thermal view\"${RESET}"
    echo ""
    echo -e "  ${DIM}Useful commands:${RESET}"
    echo -e "    ${DIM}journalctl -u sensorhead-bridge -f${RESET}  — Watch bridge logs"
    echo -e "    ${DIM}i2cdetect -y 1${RESET}                      — Scan I2C devices"
    echo -e "    ${DIM}systemctl status sensorhead-bridge${RESET}   — Service status"
    echo ""
    echo -e "${GOLD}${BOLD}  ══════════════════════════════════════════════════════${RESET}"
    echo -e "${GOLD}  \"The Athanor is built. The flame is lit. The Work begins.\"${RESET}"
    echo -e "${GOLD}${BOLD}  ══════════════════════════════════════════════════════${RESET}"
    echo ""
}

# ══════════════════════════════════════════════════════════════════════
#  INTERACTIVE MENU
# ══════════════════════════════════════════════════════════════════════

interactive_menu() {
    echo -e "${GOLD}${BOLD}  Choose your SensorHead configuration:${RESET}"
    echo ""
    echo -e "  ${WHITE}1)${RESET} ${GOLD}Base${RESET}      — Pi + Bridge + Cortex (no sensors)"
    echo -e "  ${WHITE}2)${RESET} ${GOLD}Eye${RESET}       — Base + cameras (visual + night)"
    echo -e "  ${WHITE}3)${RESET} ${GOLD}Nose${RESET}      — Base + BME688 air quality sensor"
    echo -e "  ${WHITE}4)${RESET} ${GOLD}Thermal${RESET}   — Base + MLX90640 thermal camera"
    echo -e "  ${WHITE}5)${RESET} ${GOLD}Full${RESET}      — Everything — three-eyed SensorHead"
    echo -e "  ${WHITE}6)${RESET} ${GOLD}Custom${RESET}    — Pick individual modules"
    echo ""
    echo -en "  ${GOLD}?${RESET} Enter choice ${DIM}[1-6]${RESET}: "
    read -r choice

    case "$choice" in
        1) apply_preset "base" ;;
        2) apply_preset "eye" ;;
        3) apply_preset "nose" ;;
        4) apply_preset "thermal" ;;
        5) apply_preset "full" ;;
        6) custom_picker ;;
        *) error "Invalid choice"; exit 1 ;;
    esac
}

custom_picker() {
    echo ""
    echo -e "  ${GOLD}Select modules to install:${RESET}"
    echo ""

    MODULES_TO_RUN=("module_0_system_base" "module_1_sensorhead_bridge")
    info "System Base + Bridge are always included"

    prompt_yn "CerebroCortex Memory?" "y" && \
        MODULES_TO_RUN+=("module_2_cerebrocortex")

    prompt_yn "Voice Server (TTS/STT on Pi)?" "n" && \
        MODULES_TO_RUN+=("module_3_voice")

    prompt_yn "Cameras (IMX500 + IMX708)?" "y" && \
        MODULES_TO_RUN+=("module_4_cameras")

    prompt_yn "BME688 Air Quality?" "y" && \
        MODULES_TO_RUN+=("module_5_bme688")

    prompt_yn "MLX90640 Thermal?" "y" && \
        MODULES_TO_RUN+=("module_6_thermal")

    MODULES_TO_RUN+=("module_7_sentinel")
}

apply_preset() {
    local preset="$1"
    info "Applying preset: ${preset}"

    # Base always included
    MODULES_TO_RUN=(
        "module_0_system_base"
        "module_1_sensorhead_bridge"
        "module_2_cerebrocortex"
    )

    case "$preset" in
        base)
            # Just the base modules
            ;;
        eye)
            MODULES_TO_RUN+=("module_4_cameras")
            ;;
        nose)
            MODULES_TO_RUN+=("module_5_bme688")
            ;;
        thermal)
            MODULES_TO_RUN+=("module_6_thermal")
            ;;
        full)
            MODULES_TO_RUN+=(
                "module_3_voice"
                "module_4_cameras"
                "module_5_bme688"
                "module_6_thermal"
            )
            ;;
        custom)
            custom_picker
            return
            ;;
        *)
            error "Unknown preset: ${preset}"
            show_help
            exit 1
            ;;
    esac

    # Sentinel info always last
    MODULES_TO_RUN+=("module_7_sentinel")
}

# ══════════════════════════════════════════════════════════════════════
#  HELP
# ══════════════════════════════════════════════════════════════════════

show_help() {
    echo ""
    echo -e "${GOLD}ApexAurum SensorHead Installer v${INSTALLER_VERSION}${RESET}"
    echo ""
    echo "Usage:"
    echo "  ./install.sh                    Interactive menu"
    echo "  ./install.sh --preset <name>    Use a preset configuration"
    echo "  ./install.sh --help             Show this help"
    echo ""
    echo "Presets:"
    echo "  base      Pi + Bridge + CerebroCortex"
    echo "  eye       Base + cameras (IMX500 + IMX708)"
    echo "  nose      Base + BME688 air quality"
    echo "  thermal   Base + MLX90640 thermal camera"
    echo "  full      Everything (three-eyed SensorHead)"
    echo "  custom    Interactive module picker"
    echo ""
    echo "Hardware:"
    echo "  Requires Raspberry Pi 5 (4GB+, 8GB recommended)"
    echo "  Python 3.11+ required"
    echo ""
    echo "Rerun:"
    echo "  Safe to re-run — detects existing installs"
    echo ""
}

# ══════════════════════════════════════════════════════════════════════
#  MAIN
# ══════════════════════════════════════════════════════════════════════

main() {
    # Parse args
    local preset=""
    while [[ $# -gt 0 ]]; do
        case "$1" in
            --preset)
                preset="${2:-}"
                shift 2
                ;;
            --help|-h)
                show_help
                exit 0
                ;;
            *)
                error "Unknown argument: $1"
                show_help
                exit 1
                ;;
        esac
    done

    # Init
    banner
    check_root
    echo -e "  ${DIM}Log: ${LOG_FILE}${RESET}"
    echo ""

    # Detect existing install
    if [[ -f "$MANIFEST_FILE" ]]; then
        info "Previous install detected"
        local prev_date
        prev_date=$(python3 -c "import json; print(json.load(open('$MANIFEST_FILE'))['install_date'])" 2>/dev/null || echo "unknown")
        info "Last installed: ${prev_date}"
        echo ""
    fi

    # Choose modules
    if [[ -n "$preset" ]]; then
        apply_preset "$preset"
    else
        interactive_menu
    fi

    # Confirm
    echo ""
    info "Modules to install: ${#MODULES_TO_RUN[@]}"
    if ! prompt_yn "Proceed with installation?"; then
        info "Aborted by user"
        exit 0
    fi

    # Execute modules
    local start_time
    start_time=$(date +%s)

    for module_fn in "${MODULES_TO_RUN[@]}"; do
        "$module_fn" || warn "Module ${module_fn} had issues"
    done

    # Post-install
    post_install

    local elapsed=$(( $(date +%s) - start_time ))
    local mins=$(( elapsed / 60 ))
    local secs=$(( elapsed % 60 ))
    echo -e "  ${DIM}Completed in ${mins}m ${secs}s${RESET}"
    echo ""
}

main "$@"
