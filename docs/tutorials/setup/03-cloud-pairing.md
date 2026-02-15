# Cloud Pairing

**Estimated time:** 10-15 minutes

> This guide explains how to connect your SensorHead to the ApexAurum cloud. Once paired, you can control your SensorHead from anywhere -- from the mobile app on your phone, from the web dashboard on your laptop, or from a Claude Code session. The cloud acts as a relay between your devices and the AI agents.

---

## Prerequisites

- A SensorHead with the software installer completed (see [02 - Software Install](02-software-install.md))
- The SensorHead bridge service installed (`sensorhead-bridge.service`)
- Internet access on your Pi (WiFi or Ethernet)
- A web browser on any device (phone, laptop, tablet)

---

## How the Cloud Works

The ApexAurum cloud is a hosted backend that serves three purposes:

1. **Command relay** -- Routes messages between your phone and your SensorHead. When you type "read the temperature" in the mobile app, the cloud forwards that to your Pi, executes the command, and sends the result back to your phone.

2. **AI agent hosting** -- The four agents (AZOTH, KETHER, VAJRA, ELYSIAN) run in the cloud, powered by Anthropic's Claude API. They interpret your requests, choose which tools to invoke, and compose responses.

3. **State persistence** -- Conversation history, memory entries, music library, file vault, and account settings are stored in the cloud database so they are available across all your devices.

**Architecture diagram:**

```
Phone (ApexPocket App)
    |
    | HTTPS + WebSocket (encrypted)
    v
ApexAurum Cloud Backend (Railway)
    |    |
    |    +-- AI Agents (Claude API)
    |    +-- Database (PostgreSQL + pgvector)
    |    +-- File Storage (S3)
    |
    | WebSocket (encrypted, persistent)
    v
Your Raspberry Pi (SensorHead Bridge)
    |
    +-- Cameras (IMX500, IMX708)
    +-- Thermal (MLX90640)
    +-- Environment (BME688)
    +-- Voice (Piper TTS, Whisper STT)
    +-- Memory (CerebroCortex)
```

Your Pi never needs to be directly reachable from the internet. The bridge opens an outgoing WebSocket connection to the cloud and keeps it alive. All communication flows through this tunnel. No port forwarding, no dynamic DNS, no firewall changes required.

---

## Step 1: Create an Account

Open a web browser and navigate to:

```
https://frontend-production-5402.up.railway.app
```

Click "Sign Up" and create an account with your email and a password. You will receive a verification email (check your spam folder if it does not arrive within a few minutes).

> **Note:** If you already have an ApexAurum account from using the web dashboard or another device, skip to Step 2. One account can manage multiple SensorHead devices.

---

## Step 2: Choose a Subscription Tier

After signing in, navigate to the Billing page. ApexAurum offers four subscription tiers:

| Tier | Price | Monthly Messages | AI Models | Key Features |
|------|-------|-----------------|-----------|-------------|
| Seeker | $10/mo | 200 | Haiku, Sonnet | Basic chat, single agent, core tools |
| Adept | $30/mo | 1,000 | All models + 50 Opus/mo | Multi-agent, Council deliberation, full tool suite |
| Opus | $100/mo | 5,000 | All models + 500 Opus/mo | Priority processing, extended memory, music generation |
| Azothic | $300/mo | 20,000 | All models + 2,000 Opus/mo | Unlimited features, dream engine, dedicated support |

For a SensorHead setup, the **Adept** tier is the minimum recommended tier because it unlocks multi-agent conversations and the full tool suite (including sensor commands). The Seeker tier works but limits you to a single agent and fewer tools.

Payment is handled through Stripe. You can upgrade or downgrade at any time.

---

## Step 3: Register Your Device

After subscribing, navigate to **Devices** in the web dashboard sidebar (or find it under Settings > Devices).

Click **"Register New Device"** and fill in:

- **Device Name** -- A friendly name for this SensorHead (e.g., "Office SensorHead", "Living Room Pi", "Lab Unit"). This name appears in the mobile app when selecting which device to connect to.
- **Device Type** -- Select "SensorHead" from the dropdown.

Click **Register**. The system generates a unique device token.

---

## Step 4: Copy the Device Token

After registration, you will see a device token displayed on screen. It looks like this:

```
apex_dev_a3f8b291c4e7d056
```

**Copy this token carefully.** You will need it in the next step. The token is shown once at registration. If you lose it, you can regenerate it from the device settings page, but the old token will stop working.

> **Warning:** Treat the device token like a password. Anyone with this token can connect a bridge to your account. Do not share it publicly or commit it to a git repository.

---

## Step 5: Configure the SensorHead Bridge

On your Raspberry Pi, edit the bridge configuration file:

```bash
nano ~/claude-root/SensorHead/config.json
```

If the installer already created this file (because you entered a token during install), it will look something like this:

```json
{
  "cloud_url": "https://backend-production-507c.up.railway.app",
  "device_token": "YOUR_TOKEN_HERE",
  "device_id": "some-uuid",
  "api_version": "v1",
  "ws_url": "wss://backend-production-507c.up.railway.app/ws/bridge"
}
```

Replace `YOUR_TOKEN_HERE` with the device token from Step 4:

```json
{
  "cloud_url": "https://backend-production-507c.up.railway.app",
  "device_token": "apex_dev_a3f8b291c4e7d056",
  "device_id": "some-uuid",
  "api_version": "v1",
  "ws_url": "wss://backend-production-507c.up.railway.app/ws/bridge"
}
```

Save and exit (in nano: `Ctrl+O` to save, `Ctrl+X` to exit).

**Configuration fields explained:**

| Field | Purpose | Default |
|-------|---------|---------|
| `cloud_url` | HTTPS base URL for the cloud backend API | `https://backend-production-507c.up.railway.app` |
| `device_token` | Authentication token from the device registration | Must be set manually |
| `device_id` | Unique identifier for this Pi instance | Auto-generated UUID |
| `api_version` | API version string | `v1` |
| `ws_url` | WebSocket URL for the persistent bridge connection | `wss://backend-production-507c.up.railway.app/ws/bridge` |

---

## Step 6: Restart the Bridge Service

Apply the new configuration by restarting the bridge:

```bash
sudo systemctl restart sensorhead-bridge
```

The bridge will read the updated `config.json`, connect to the cloud, authenticate with your device token, and establish the persistent WebSocket.

---

## Step 7: Verify the Connection

Watch the bridge logs in real time:

```bash
journalctl -u sensorhead-bridge -f
```

A successful connection looks like this:

```
SensorHead Bridge v1.x.x starting
Loading config from /home/hailo/claude-root/SensorHead/config.json
Connecting to wss://backend-production-507c.up.railway.app/ws/bridge
WebSocket connected
Authenticating with device token...
Authentication successful — device registered as "Office SensorHead"
Bridge connected to cloud
Heartbeat: OK (latency: 45ms)
```

Press `Ctrl+C` to stop watching logs (the service continues running in the background).

**If the connection fails**, you will see messages like:

```
Authentication failed — invalid token
```
Check that you copied the token correctly in Step 5.

```
Connection refused / Connection timed out
```
Check your Pi's internet connection: `ping google.com`

```
SSL certificate error
```
Your system clock may be wrong. Set it: `sudo timedatectl set-ntp true`

You can also verify from the web dashboard: navigate to **Devices** and check that your device shows a green "Connected" status indicator.

---

## How the Bridge Stays Connected

The SensorHead bridge is designed for reliability:

**Persistent WebSocket:** The bridge maintains a single long-lived WebSocket connection to the cloud. This is more efficient than polling and allows instant bidirectional communication.

**Heartbeat:** Every 25 seconds, the bridge sends a ping to the cloud. If the cloud does not respond within 10 seconds, the bridge considers the connection lost and reconnects.

**Automatic reconnection:** If the connection drops (network blip, cloud restart, WiFi interruption), the bridge reconnects automatically with exponential backoff:

| Attempt | Wait Before Retry |
|---------|-------------------|
| 1 | 5 seconds |
| 2 | 10 seconds |
| 3 | 20 seconds |
| 4 | 40 seconds |
| 5 | 80 seconds |
| 6 | 160 seconds |
| 7+ | 300 seconds (5 minutes, maximum) |

After a successful reconnection, the backoff resets to 5 seconds.

**Boot resilience:** The systemd service is configured with `Restart=always` and `RestartSec=10`, so if the bridge process crashes for any reason, systemd restarts it after 10 seconds. The service starts automatically on boot (`WantedBy=multi-user.target`).

---

## Security

**Token authentication:** Every bridge connection must present a valid device token. Tokens are tied to your user account and specific device. Revoke a token from the web dashboard to disconnect a device.

**Encrypted transport:** All communication uses WSS (WebSocket Secure), which is WebSocket over TLS. This is the same encryption used by HTTPS. Data in transit is encrypted between your Pi and the cloud.

**No inbound ports:** Your Pi does not listen on any public port. All connections are outgoing. Your home firewall and NAT work normally without any configuration.

**Scoped access:** The bridge can only execute commands authorized by your account's subscription tier. A Seeker-tier account cannot invoke Opus-tier tools even if the bridge supports them locally.

---

## Managing Multiple Devices

You can register multiple SensorHead devices under one account. Each gets its own token and appears as a separate device in the web dashboard and mobile app.

To switch between devices in the mobile app, tap the device name in Settings and select from the list.

Use cases for multiple devices:
- One SensorHead at home, one at the office
- Separate sensors in different rooms (bedroom thermal monitor, kitchen air quality)
- A development/testing unit alongside a production unit

---

## Unpairing a Device

To disconnect a SensorHead from your account:

1. On the web dashboard, go to **Devices**
2. Click the device you want to remove
3. Click **"Revoke Token"** or **"Remove Device"**
4. On the Pi, stop the bridge: `sudo systemctl stop sensorhead-bridge`

The device token becomes invalid immediately. If the bridge was running, it will fail to authenticate on its next connection attempt and log an authentication error.

---

## Troubleshooting

### Bridge logs show "Authentication failed"

- Double-check the token in `config.json` -- extra spaces or missing characters will cause failure
- Verify the token has not been revoked on the web dashboard
- Regenerate the token from Devices > your device > "Regenerate Token"

### Bridge connects but device shows "Offline" on dashboard

- There may be a delay of up to 30 seconds for the dashboard to update
- Refresh the page
- Check that the `device_id` in your config matches what the cloud expects

### "Connection refused" errors

- Verify the cloud backend is healthy: `curl -s https://backend-production-507c.up.railway.app/health`
- If the health check fails, the cloud may be temporarily down for maintenance
- The bridge will auto-reconnect when the cloud comes back

### Bridge works but commands time out

- Check that the relevant sensor modules are installed (a "read temperature" command fails if Module 5 was not installed)
- Check the bridge logs for error details during command execution
- Verify sensor hardware is still connected: `i2cdetect -y 1`

---

## What's Next

- [04 - Mobile App Setup](04-mobile-app.md) -- Install the ApexPocket app on your phone and connect to your SensorHead
- [05 - Voice Setup](05-voice-setup.md) -- Configure text-to-speech so agents can speak with unique voices
