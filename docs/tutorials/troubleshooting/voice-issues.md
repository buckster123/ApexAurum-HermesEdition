# Voice Not Working

**Estimated reading time: 5 minutes**

When text-to-speech (TTS) or speech-to-text (STT) fails -- no audio output, transcription errors, or voice commands not recognized -- work through this decision tree from top to bottom.

---

## Step 1: Is the Voice Server Running?

The voice server can run as a systemd service or as a standalone process. Check both:

```bash
systemctl status voice-server
```

If the service is not found, check for a running process:

```bash
ps aux | grep voice
```

- **Service active or process running** -- proceed to Step 2.
- **Not running** -- start the voice server:

  ```bash
  sudo systemctl start voice-server
  ```

  Or, if running manually:

  ```bash
  cd ~/claude-root/VoiceServer
  source venv/bin/activate
  python server.py &
  ```

  Check for startup errors in the output.

---

## Step 2: Are the Voice Models Installed?

The TTS engine (Piper) requires ONNX voice model files. Check if they exist:

```bash
ls ~/claude-root/VoiceServer/data/voices/*.onnx
```

Expected output: one or more `.onnx` files (one per voice/agent).

- **Files listed** -- models are present, proceed to Step 3.
- **No files found or directory missing** -- voice models need to be downloaded. Each ONNX model also requires a matching `.onnx.json` configuration file.

  Models can be downloaded from the Piper voices repository on HuggingFace:

  ```
  https://huggingface.co/rhasspy/piper-voices
  ```

  Download at minimum one English voice model and its config JSON, then place both files in:

  ```
  ~/claude-root/VoiceServer/data/voices/
  ```

> **Note:** Each agent (AZOTH, KETHER, VAJRA, ELYSIAN) can have its own voice model assigned. The `system` voice is used as the default fallback.

---

## Step 3: Check MCP Server Connection

The voice server exposes its capabilities via MCP (Model Context Protocol). Verify it is registered:

- If using Claude Code, check the tool list -- `speak` and `listen` should appear as available tools.
- If the tools are missing, check your MCP server configuration. The voice server should be listed in your Claude Code or SensorHead MCP settings.

For Claude Code, the MCP configuration is typically in:

```bash
cat ~/.claude/settings.json
```

Look for a `voice-server` or `voice-mcp` entry in the `mcpServers` section with the correct host and port.

---

## Step 4: Test TTS Manually

If the MCP `speak` tool is available, test it with simple text. If testing outside of MCP, try Piper directly:

```bash
cd ~/claude-root/VoiceServer
source venv/bin/activate
echo "Testing one two three" | piper --model data/voices/YOUR_MODEL.onnx --output_file /tmp/test.wav
```

- **File created successfully** -- TTS engine works. Proceed to Step 5 (audio output).
- **"piper: command not found"** -- install the Piper TTS package:

  ```bash
  pip install piper-tts
  ```

- **"onnxruntime" error** -- install the ONNX runtime:

  ```bash
  pip install onnxruntime
  ```

  On Raspberry Pi, use the CPU-only version. GPU acceleration is not available.

- **Model loading error** -- verify the model file is not corrupted. Re-download it from HuggingFace.

---

## Step 5: Check Audio Output

If TTS generates audio but you cannot hear it, the issue is audio output configuration.

### List Audio Devices

```bash
aplay -l
```

This shows all available audio output devices. Look for your speaker, headphone jack, HDMI output, or USB audio device.

### Check PulseAudio

```bash
pactl info
```

If PulseAudio is not running:

```bash
pulseaudio --start
```

### Test Audio Playback

Play the test file generated in Step 4:

```bash
aplay /tmp/test.wav
```

- **Audio plays** -- speakers work. The issue may be in how the voice server routes audio output.
- **No sound** -- check volume:

  ```bash
  amixer sget Master
  ```

  If muted or at 0%:

  ```bash
  amixer sset Master 80% unmute
  ```

- **"No such device" error** -- the default audio device may be wrong. List sinks and set the correct one:

  ```bash
  pactl list sinks short
  pactl set-default-sink <SINK_NAME>
  ```

### Headless Pi (No Monitor)

If running headless (SSH only), HDMI audio will not work without a display connected. Use one of:

- USB audio adapter (most reliable)
- I2S DAC HAT (e.g., HiFiBerry, Adafruit I2S DAC)
- 3.5mm headphone jack (if your Pi model has one -- Pi 5 does not have an analog audio jack)

---

## Step 6: STT (Speech-to-Text) Not Working

STT uses the `faster-whisper` library. Test the installation:

```bash
source ~/claude-root/VoiceServer/venv/bin/activate
python3 -c "from faster_whisper import WhisperModel; print('OK')"
```

- **Prints OK** -- library is installed. Proceed to checking the microphone.
- **ImportError** -- install it:

  ```bash
  pip install faster-whisper
  ```

  > **Note:** The first time `faster-whisper` is used, it downloads the Whisper model (~150MB for the "base" model). This happens automatically but requires an internet connection. On slow connections, this can take several minutes.

### Check Microphone

List available recording devices:

```bash
arecord -l
```

If no capture devices are listed, connect a USB microphone. The Pi 5 does not have a built-in microphone.

Test recording:

```bash
arecord -d 3 -f S16_LE -r 16000 /tmp/test_mic.wav
```

This records 3 seconds of audio. Play it back:

```bash
aplay /tmp/test_mic.wav
```

If the recording is silent, check:

- **Microphone mute**: `amixer sget Capture` -- unmute if needed
- **Microphone permissions**: your user should be in the `audio` group: `groups $USER | grep audio`
- **USB microphone not recognized**: check `dmesg | tail -20` after plugging it in

---

## Step 7: Remote Voice Server (SSH Tunnel)

If the voice server runs on a different machine (e.g., a laptop or desktop with better hardware), it connects via SSH tunnel. Check the tunnel:

```bash
ps aux | grep "ssh.*voice"
```

If no tunnel process is running, re-establish it:

```bash
ssh -N -L 8765:localhost:8765 user@voice-server-host &
```

Replace `user@voice-server-host` with your voice server's SSH credentials.

---

## Still Not Working?

1. Check voice server logs for errors: `journalctl -u voice-server -n 100 --no-pager`
2. Verify Python version: Piper and faster-whisper require Python 3.9+: `python3 --version`
3. On Pi 5, ONNX inference is CPU-only and can be slow for large voice models. Use the "medium" or "small" Piper models for faster response times.
4. If audio routing is complex (multiple outputs), consider using `pavucontrol` (PulseAudio Volume Control) for a graphical interface to manage audio streams.
