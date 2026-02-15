# Voice Setup

**Estimated time:** 15-20 minutes (local install) or 5-10 minutes (remote configuration)

> Each ApexAurum agent has a unique voice. AZOTH speaks with deep resonance, KETHER with clear authority, VAJRA with clipped directness, and ELYSIAN with warm gentleness. This guide covers configuring text-to-speech (TTS) and speech-to-text (STT) so you can hear agents speak and talk to them using your voice.

---

## Prerequisites

- SensorHead software installed (see [02 - Software Install](02-software-install.md))
- For local TTS: Raspberry Pi 5 with at least 4GB RAM (8GB recommended)
- For STT (speech recognition): A USB microphone connected to the Pi
- For mobile voice: ApexPocket app installed (see [04 - Mobile App Setup](04-mobile-app.md))

---

## How Voice Works

The voice system has two components:

**Text-to-Speech (TTS)** -- Converts agent text responses into spoken audio. Powered by [Piper](https://github.com/rhasspy/piper), a fast neural TTS engine that runs locally without internet. Each agent is assigned a different Piper voice model, giving them distinct vocal characteristics.

**Speech-to-Text (STT)** -- Converts your spoken words into text for the agents to process. Powered by [faster-whisper](https://github.com/SYSTRAN/faster-whisper), a high-performance implementation of OpenAI's Whisper model, running locally on the Pi's CPU.

Both components run as a single Voice Server that exposes four tools via MCP (Model Context Protocol): `speak`, `listen`, `voices`, and `voice_status`.

---

## Voice Models

Each agent is assigned a Piper voice model that matches their personality:

| Agent | Voice Model | Character | Quality | Size |
|-------|------------|-----------|---------|------|
| AZOTH | `en_US-ryan-high` | Deep, resonant, measured pacing | High | ~100MB |
| KETHER | `en_US-amy-medium` | Clear, authoritative, precise | Medium | ~65MB |
| VAJRA | `en_US-danny-low` | Direct, clipped, no-nonsense | Low | ~30MB |
| ELYSIAN | `en_US-kusal-medium` | Warm, gentle, flowing | Medium | ~65MB |
| System | `en_US-lessac-medium` | Neutral, clear, informational | Medium | ~65MB |

**Quality levels explained:**

- **Low** -- Smallest model, fastest synthesis, slightly robotic. Suits VAJRA's terse style.
- **Medium** -- Good balance of naturalness and speed. The standard choice.
- **High** -- Most natural-sounding, slowest synthesis. Used for AZOTH because his philosophical responses benefit from richer intonation.

All models are English (US). Total download size for all five models: approximately 361MB.

---

## Option A: Local Voice Server on the Pi (Recommended)

Running the voice server directly on the Pi is the simplest and most reliable option. It requires no external dependencies -- everything runs locally.

### Step 1: Install via the Unified Installer

If you ran the installer with the `full` preset, the voice server is already installed. If not, re-run:

```bash
cd ~/claude-root/SensorHead
sudo ./install.sh --preset full
```

Or install just the voice module by running interactively and selecting it:

```bash
sudo ./install.sh
# Choose option 6 (Custom)
# Select "Voice Server (TTS/STT on Pi)?" → y
```

### Step 2: Verify Voice Model Files

Check that all five voice models were downloaded:

```bash
ls -lh ~/claude-root/VoiceServer/data/voices/
```

Expected output:

```
-rw-r--r-- 1 hailo hailo  65M  en_US-lessac-medium.onnx
-rw-r--r-- 1 hailo hailo  65M  en_US-lessac-medium.onnx.json
-rw-r--r-- 1 hailo hailo 100M  en_US-ryan-high.onnx
-rw-r--r-- 1 hailo hailo 100M  en_US-ryan-high.onnx.json
-rw-r--r-- 1 hailo hailo  65M  en_US-amy-medium.onnx
-rw-r--r-- 1 hailo hailo  65M  en_US-amy-medium.onnx.json
-rw-r--r-- 1 hailo hailo  30M  en_US-danny-low.onnx
-rw-r--r-- 1 hailo hailo  30M  en_US-danny-low.onnx.json
-rw-r--r-- 1 hailo hailo  65M  en_US-kusal-medium.onnx
-rw-r--r-- 1 hailo hailo  65M  en_US-kusal-medium.onnx.json
```

Each voice model consists of two files: the `.onnx` model (the neural network weights) and the `.onnx.json` configuration (sample rate, phoneme map, etc.).

If any model is missing, download it manually:

```bash
cd ~/claude-root/VoiceServer/data/voices/

# Example: download the AZOTH voice
wget https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/ryan/high/en_US-ryan-high.onnx
wget https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/ryan/high/en_US-ryan-high.onnx.json
```

### Step 3: Test the Voice Server

Run the voice server directly to test it:

```bash
cd ~/claude-root/VoiceServer
./venv/bin/python -c "
from voice_server.engine import engine
status = engine.status()
print('TTS available:', status['tts_available'])
print('STT available:', status['stt_available'])
voices = engine.available_voices()
print('Voices found:', len(voices['voices']))
for name, info in voices['voices'].items():
    agents = ', '.join(info['agents']) if info['agents'] else 'none'
    print(f'  {name} -> {agents}')
"
```

Expected output:

```
TTS available: True
STT available: True
Voices found: 5
  en_US-lessac-medium -> system
  en_US-ryan-high -> azoth
  en_US-amy-medium -> kether
  en_US-danny-low -> vajra
  en_US-kusal-medium -> elysian
```

### Step 4: Configure MCP Integration

The voice server connects to Claude Code (and by extension, to agents) via the Model Context Protocol. The installer creates a launcher script at:

```
~/claude-root/VoiceServer/voice-mcp
```

To use it with Claude Code, add it to your project's MCP configuration. In your Claude Code project settings (`.mcp.json` or equivalent):

```json
{
  "mcpServers": {
    "voice-server": {
      "command": "/home/hailo/claude-root/VoiceServer/voice-mcp"
    }
  }
}
```

After adding this configuration, Claude Code will have access to the `speak`, `listen`, `voices`, and `voice_status` tools.

### Resource Usage

The voice server loads models on demand (lazy loading). Resource consumption varies:

| State | RAM Usage | CPU Usage |
|-------|-----------|-----------|
| Idle (no models loaded) | ~50MB | None |
| One voice model loaded | ~200MB | None |
| All five models loaded | ~700MB | None |
| During TTS synthesis | ~700MB | 50-100% one core |
| During STT transcription | ~900MB | 100% one core |

On a Pi 5 with 4GB RAM, loading all models simultaneously is possible but tight. The voice engine uses lazy loading and caches models after first use, so the first `speak` call for each agent takes a second to load the model, then subsequent calls are fast.

On a Pi 5 with 8GB RAM, resource usage is comfortable even with all other services running (bridge, CerebroCortex, sensors).

---

## Option B: Remote Voice Server (SSH Tunnel)

If your Pi has limited RAM (4GB with many services) or you prefer running the voice server on a more powerful machine (laptop, desktop), you can use an SSH tunnel to connect a remote voice server.

### On the Remote Machine (Laptop/Desktop)

1. Clone or copy the VoiceServer code to your laptop
2. Create a virtual environment and install dependencies:

```bash
cd /path/to/VoiceServer
python3 -m venv venv
./venv/bin/pip install piper-tts faster-whisper onnxruntime mcp
```

3. Download the voice models to `data/voices/` (same as the Pi setup above)
4. Run the voice server:

```bash
./voice-mcp
```

### On the Pi

Set up an SSH key for passwordless authentication between the Pi and your laptop:

```bash
# Generate a key (if you don't already have one)
ssh-keygen -t ed25519 -N "" -f ~/.ssh/id_ed25519

# Copy the key to your laptop
ssh-copy-id your-username@your-laptop-ip
```

Create an MCP configuration that tunnels through SSH. In your Claude Code project settings:

```json
{
  "mcpServers": {
    "voice-server": {
      "command": "ssh",
      "args": [
        "-o", "StrictHostKeyChecking=no",
        "your-username@your-laptop-ip",
        "/path/to/VoiceServer/voice-mcp"
      ]
    }
  }
}
```

This tells Claude Code to launch the voice server on the remote machine via SSH and communicate with it over the SSH tunnel.

**Trade-offs of remote voice:**

| Aspect | Local (Pi) | Remote (Laptop) |
|--------|-----------|-----------------|
| Latency | Lowest (~100ms for short phrases) | Higher (~300-500ms, depends on network) |
| RAM on Pi | ~700MB peak | ~0MB (runs elsewhere) |
| Reliability | Always available when Pi is on | Requires laptop to be on and connected |
| Setup complexity | Simple (installer handles it) | Moderate (SSH keys, network config) |

---

## Using Voice in the Mobile App

The mobile app can use the voice system in two ways:

### Text-to-Speech (Hearing Agents)

1. Open ApexPocket
2. Go to **Settings > Voice > Auto-Read (TTS)**
3. Toggle it ON

Now, when an agent responds in chat, the app sends the text to the voice server on your Pi, receives the audio, and plays it through your phone's speaker. Each agent's response is spoken in their unique voice.

You can adjust the speech speed in **Settings > Voice > Speech Speed** (0.5x slow to 2.0x fast).

### Speech-to-Text (Talking to Agents)

1. In the chat screen, tap and hold the **microphone icon** next to the text input field
2. Speak your message
3. Release the button
4. The audio is sent to the Pi's voice server for transcription
5. The transcribed text appears in the input field
6. Tap send (or the app sends automatically, depending on your settings)

STT uses the faster-whisper "base" model quantized to int8 for CPU inference. It supports automatic language detection but is optimized for English.

---

## Speech-to-Text Details

The STT engine (faster-whisper) has the following characteristics:

| Property | Value |
|----------|-------|
| Model | Whisper base |
| Quantization | int8 (CPU-optimized) |
| Languages | Auto-detection; best for English |
| Latency | ~1-3 seconds for a 10-second clip |
| Accuracy | Good for clear speech; degrades with background noise |
| VAD | Built-in Voice Activity Detection (filters silence) |

**For best results:**
- Use a decent USB microphone (not the cheapest option)
- Speak clearly at a normal pace
- Minimize background noise
- Keep utterances under 30 seconds (longer clips take proportionally longer)

The STT model file (~150MB) downloads automatically on first use via the faster-whisper library.

---

## Testing Voice End-to-End

### Test TTS from Claude Code

If you have the voice MCP configured in Claude Code, you can test directly:

```
Use the speak tool to say "The Athanor's flame burns bright" with the azoth voice
```

Claude Code will call the `speak` tool, which returns base64-encoded WAV audio. The audio plays if your Claude Code environment supports it.

### Test TTS from the Command Line

```bash
cd ~/claude-root/VoiceServer
./venv/bin/python -c "
from voice_server.engine import engine
audio_b64 = engine.speak('Hello, I am AZOTH.', voice='azoth')
import base64
with open('/tmp/test-voice.wav', 'wb') as f:
    f.write(base64.b64decode(audio_b64))
print('Audio saved to /tmp/test-voice.wav')
print(f'Size: {len(audio_b64)} bytes base64')
"
```

Play the resulting file:

```bash
aplay /tmp/test-voice.wav
```

If you do not hear audio, check your audio output:

```bash
# List audio devices
aplay -l

# Check PulseAudio/PipeWire
pactl info
```

### Test STT from the Command Line

Record a short audio clip and transcribe it:

```bash
# Record 5 seconds of audio (requires a microphone)
arecord -d 5 -f S16_LE -r 16000 -c 1 /tmp/test-input.wav

# Transcribe
cd ~/claude-root/VoiceServer
./venv/bin/python -c "
import base64
from voice_server.engine import engine
with open('/tmp/test-input.wav', 'rb') as f:
    audio_b64 = base64.b64encode(f.read()).decode()
result = engine.listen(audio_b64)
print('Transcription:', result['text'])
print('Language:', result['language'])
print('Confidence:', result['language_probability'])
"
```

### Test from the Mobile App

1. Open ApexPocket
2. Enable Auto-Read in Settings > Voice
3. Chat with any agent: "Say hello in your own words"
4. You should hear the response spoken aloud in the agent's voice

---

## Running as a Systemd Service

If you want the voice server to run continuously as a background service (useful if multiple clients connect to it), the installer can set this up:

```bash
sudo ./install.sh
# Choose Custom, select Voice Server
# When asked "Install voice server as a systemd service?" → y
```

Or manually create the service:

```bash
sudo tee /etc/systemd/system/voice-server.service > /dev/null <<EOF
[Unit]
Description=ApexAurum Voice Server (Piper TTS + Whisper STT)
After=network.target

[Service]
Type=simple
User=$USER
WorkingDirectory=$HOME/claude-root/VoiceServer
ExecStart=$HOME/claude-root/VoiceServer/venv/bin/python -m voice_server.mcp_server
Restart=on-failure
RestartSec=10
Environment=PYTHONPATH=$HOME/claude-root/VoiceServer

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable voice-server
sudo systemctl start voice-server
```

Check the service:

```bash
systemctl status voice-server
journalctl -u voice-server -f
```

---

## Troubleshooting

### "Voice model not found" error

The voice engine cannot find the `.onnx` file for the requested voice.

```bash
# Check which models are present
ls ~/claude-root/VoiceServer/data/voices/*.onnx

# Re-download a missing model (example: AZOTH)
wget -O ~/claude-root/VoiceServer/data/voices/en_US-ryan-high.onnx \
  https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/ryan/high/en_US-ryan-high.onnx
wget -O ~/claude-root/VoiceServer/data/voices/en_US-ryan-high.onnx.json \
  https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/ryan/high/en_US-ryan-high.onnx.json
```

### No audio output

```bash
# Check if PulseAudio or PipeWire is running
pactl info

# List available audio outputs
pactl list sinks short

# Test audio output directly
speaker-test -t wav -c 1

# If using HDMI for audio, it may not be the default output
# Set the default sink:
pactl set-default-sink <sink-name-from-list>
```

If you are running headless (no monitor), audio output goes to HDMI by default, which may not be connected. For headless setups with a speaker, use a USB DAC or configure the 3.5mm jack (if your Pi case exposes it):

```bash
# Force audio to 3.5mm jack (Pi 5)
# Add to /boot/firmware/config.txt:
dtparam=audio=on
```

### STT returns empty text

- Check that your microphone is detected: `arecord -l`
- Check audio input levels: `alsamixer` (press F4 to switch to Capture)
- Ensure the faster-whisper model downloaded successfully (it downloads on first use)
- Try recording and playing back audio to verify the mic works:

```bash
arecord -d 3 -f S16_LE -r 16000 -c 1 /tmp/mic-test.wav
aplay /tmp/mic-test.wav
```

### Voice server uses too much memory

If the Pi is running low on RAM:

1. Use the remote voice option (Option B) to offload to a laptop
2. Reduce loaded models -- the engine loads models lazily, so only agents you actively use consume RAM
3. Restart the voice server to unload all models: `sudo systemctl restart voice-server`

### MCP connection fails in Claude Code

```bash
# Test the launcher script directly
~/claude-root/VoiceServer/voice-mcp

# If it prints an error about missing modules, the venv may be broken
# Recreate it:
rm -rf ~/claude-root/VoiceServer/venv
cd ~/claude-root/VoiceServer
python3 -m venv venv
./venv/bin/pip install piper-tts faster-whisper onnxruntime mcp
```

### Synthesis is slow

Piper TTS speed depends on the model quality level and the Pi's CPU:

| Model Quality | ~Time for 50 words (Pi 5) |
|--------------|--------------------------|
| Low | ~0.3 seconds |
| Medium | ~0.8 seconds |
| High | ~2.0 seconds |

If synthesis is too slow:
- Consider switching AZOTH from `high` to `medium` quality (edit `AGENT_VOICES` in `engine.py`)
- Ensure no other CPU-intensive processes are running
- Check CPU throttling: `vcgencmd get_throttled` (should return `0x0`)

---

## Verification Checklist

- [ ] Voice model files exist in `~/claude-root/VoiceServer/data/voices/` (10 files: 5 `.onnx` + 5 `.onnx.json`)
- [ ] `voice_status` tool reports TTS available and STT available
- [ ] Test synthesis produces a playable WAV file
- [ ] Audio output works (speaker, headphones, or HDMI)
- [ ] USB microphone is detected by `arecord -l` (if using STT)
- [ ] MCP launcher script is executable: `ls -la ~/claude-root/VoiceServer/voice-mcp`
- [ ] Mobile app Auto-Read setting produces audible speech

---

## What's Next

- [Sentinel Configuration](../deep/01-sentinel-config.md) -- Set up security monitoring with camera, thermal, and sound detection
- [BME688 Air Quality](../deep/02-bme688-air-quality.md) -- Deep dive into IAQ scores, BSEC calibration, and gas scanning
- [CerebroCortex](../deep/04-cerebrocortex.md) -- Master the memory system with semantic search and graph navigation
