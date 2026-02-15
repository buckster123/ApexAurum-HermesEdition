# Mobile App Setup

**Estimated time:** 10-15 minutes

> The ApexPocket companion app is your primary interface to the ApexAurum system. From your phone, you can chat with AI agents, read sensor data, browse memories, participate in Council deliberations, monitor your SensorHead's soul status, and control the Sentinel security system. This guide walks you through installing and configuring the app.

---

## Prerequisites

- An **Android** phone running Android 8.0 (API level 26) or newer
- Approximately 50MB of free storage for the app
- An ApexAurum account (created during [03 - Cloud Pairing](03-cloud-pairing.md))
- Internet connection on your phone (WiFi or mobile data)

> **Note:** The ApexPocket app is currently Android-only. iOS support is planned but not yet available. The web dashboard at `https://frontend-production-5402.up.railway.app` works on any device with a modern browser and provides most of the same features.

---

## Getting the APK

The ApexPocket app is distributed as an Android APK (Android Package) file. There are two ways to get it:

### Option A: Download from the Web Dashboard

1. Sign into the web dashboard on your phone's browser
2. Navigate to **Downloads** or **Pocket** in the sidebar
3. Tap the **"Download ApexPocket APK"** button
4. The APK file downloads to your phone's Downloads folder

### Option B: Scan a QR Code

If you completed the SensorHead installer with cloud pairing, the post-install screen may have displayed a QR code. Scan it with your phone's camera to open the download link directly.

Alternatively, the QR code is available on the web dashboard's Devices page next to your registered SensorHead.

---

## Installing the APK

Because ApexPocket is not distributed through the Google Play Store, Android will ask for permission to install from an "unknown source."

1. **Open the downloaded APK file.** You can find it in your Downloads folder or tap the download notification.

2. **If prompted**, Android will show a message: "For your security, your phone is not allowed to install unknown apps from this source."

3. **Tap "Settings"** (the link in the prompt), then toggle ON **"Allow from this source"** for your browser or file manager.

4. **Go back** and tap **"Install"**. The installation takes a few seconds.

5. **Tap "Open"** when the installation completes, or find "ApexPocket" in your app drawer.

> **Note:** "Unknown sources" is a standard Android security feature. It simply means the APK was not downloaded from the Play Store. The ApexPocket app requires only standard permissions and does not access your contacts, photos, or other personal data beyond what is explicitly listed in the Permissions section below.

---

## First Launch

When you open ApexPocket for the first time, you will see a login screen.

### Sign In with Your Account

Enter the email and password you used to create your ApexAurum account during cloud pairing. Tap **"Sign In"**.

### Alternative: Scan Pairing QR

If you have the pairing QR code from the web dashboard visible on another screen (laptop, tablet, or the Pi's monitor), tap **"Scan QR Code"** instead. The app will open your phone's camera -- point it at the QR code. This fills in the server URL and authenticates in one step.

### Initial Sync

After signing in, the app syncs with the cloud:
- Downloads your conversation history
- Loads agent configurations
- Checks for connected SensorHead devices
- Pulls your memory index (cortex entries)

This initial sync takes 5-15 seconds depending on your connection speed and how much history exists.

---

## App Screens

ApexPocket has five main screens, accessible from the bottom navigation bar:

### Chat

The primary screen. Talk to any of the four AI agents in a conversational interface.

- **Agent selector** -- Tap the agent name or avatar in the header bar to switch between AZOTH, KETHER, VAJRA, and ELYSIAN. Each agent has a distinct personality and conversational style.
- **Message input** -- Type your message at the bottom. Tap the send button or press Enter.
- **Voice input** -- Tap and hold the microphone icon to speak instead of typing (requires Microphone permission and voice server configured on Pi).
- **Tool results** -- When an agent uses a tool (reading a sensor, taking a photo, searching memory), the result appears inline in the conversation with a distinct visual style.
- **Conversation list** -- Swipe right or tap the menu icon to see your conversation history. Start new conversations with the "+" button.

### Memories

Browse and search the CerebroCortex memory system.

- **Memory list** -- Recent memories displayed as cards with tags, timestamps, and salience scores.
- **Search** -- Semantic search bar at the top. Type a concept or question and the system finds related memories by meaning, not just keywords.
- **Graph view** -- Tap the constellation icon to see a force-directed graph of memory nodes and their relationships. Nodes glow based on recency and importance. Tap a node to read its content; drag to rearrange.
- **Create memory** -- Tap "+" to manually store a memory. Useful for saving notes, reminders, or facts you want the agents to know.

### Council

Multi-agent deliberation for complex questions.

- **New Council** -- Tap "+" and frame a question. All four agents discuss it in rounds, building on each other's perspectives.
- **Live streaming** -- Watch the deliberation in real time as agents take turns responding.
- **History** -- Browse past Council sessions and their outcomes.

> **Note:** Council requires the Adept tier ($30/mo) or higher.

### Pulse

Monitor the SensorHead's status and soul energy.

- **Soul status** -- A visual representation of the system's current state (energy level, active sensors, connection quality).
- **Sensor readings** -- Current temperature, humidity, air quality, and thermal snapshot.
- **Music** -- If the music generation feature is available on your tier, browse and play generated tracks.
- **Sentinel** -- View and control the security sentinel's mode (night watch, away, pet watch, off).

### Settings

Account and app configuration.

- **Account** -- Email, subscription tier, usage stats.
- **Device** -- Connected SensorHead status, device name, connection quality.
- **Appearance** -- Theme (dark/light/auto), font size.
- **Notifications** -- Configure which events trigger push notifications (see Notification Setup below).
- **Voice** -- Auto-Read TTS toggle, haptic feedback, voice speed.
- **Agent prompts** -- Toggle between "Lite" (shorter, faster) and "Full" (complete personality prompts) mode. Full mode gives agents richer personalities but uses more tokens.
- **Prompt depth** -- Fine-tune how much personality context is included in each message.
- **About** -- App version, licenses, support links.

---

## Permissions

ApexPocket requests the following Android permissions:

| Permission | Required? | Purpose |
|-----------|-----------|---------|
| Internet | Yes | Communicating with the cloud backend |
| Notifications | Recommended | Receiving alerts from agents, Council results, Sentinel events |
| Camera | Optional | Scanning QR codes for device pairing |
| Microphone | Optional | Voice input (speech-to-text via the Pi or cloud) |

The app does not request access to your contacts, photos, location, phone, SMS, or storage beyond its own app directory.

---

## Notification Setup

Notifications keep you informed about events even when the app is in the background.

1. Open ApexPocket and go to **Settings > Notifications**
2. Enable the categories you want:

| Category | What It Notifies |
|----------|-----------------|
| Agent Messages | When an agent sends a proactive message (not in response to your chat) |
| Council Alerts | When a Council deliberation you started reaches a conclusion |
| Sentinel Events | When the Sentinel detects motion, sound, or thermal anomaly |
| Soul Whispers | Periodic reflective messages from agents based on memory and mood |
| System | Connection status changes, update availability |

3. Android may also prompt you to allow notifications for the ApexPocket app at the OS level. Tap "Allow."

> **Note:** "Soul Whispers" are optional ambient messages where agents share observations or reflections based on sensor data and memory patterns. They are not urgent alerts -- think of them as the system "thinking aloud." Disable this category if you prefer silence between direct conversations.

---

## Home Screen Widget

ApexPocket includes an Android widget that shows the SensorHead's soul energy level and provides a quick-chat shortcut.

**To add the widget:**

1. Long-press on an empty area of your phone's home screen
2. Tap **"Widgets"**
3. Scroll to find **"ApexAurum"** in the list
4. Tap and hold the **"Soul Widget"** and drag it to your home screen
5. Release to place it

The widget displays:
- Current soul energy level (a visual meter)
- Connection status (green dot = connected, red = disconnected)
- Tap to open a quick-chat dialog without fully launching the app

The widget updates every 15 minutes in the background. Tap it to force a refresh.

---

## Settings Walkthrough

### Auto-Read (TTS)

When enabled, the app reads agent responses aloud using the voice server. Each agent has a unique voice character. This requires the voice server to be configured (see [05 - Voice Setup](05-voice-setup.md)).

Toggle: **Settings > Voice > Auto-Read (TTS)**

### Haptic Feedback

Provides subtle vibration feedback when:
- An agent starts responding (short pulse)
- A tool execution completes (double pulse)
- A Sentinel alert arrives (long pulse)

Toggle: **Settings > Voice > Haptic Feedback**

### Full Agent Prompts vs. Lite

**Full mode** sends the complete agent personality prompt with each message. This gives agents rich, distinctive personalities but uses more API tokens (affects your monthly message count).

**Lite mode** sends a condensed prompt. Agents are still distinct but less nuanced. Uses fewer tokens, stretching your message allowance further.

Toggle: **Settings > Agent Prompts > Full/Lite**

### Prompt Depth

A slider (1-5) that controls how much context is included in each message to the AI:

| Depth | Description |
|-------|-------------|
| 1 | Minimal -- agent name and basic role only |
| 2 | Light -- core personality traits |
| 3 | Standard -- full personality, tool descriptions |
| 4 | Rich -- personality + recent memory context |
| 5 | Maximum -- everything including soul state and ambient data |

Higher depth produces more characterful responses but uses more tokens. Default is 3.

Slider: **Settings > Agent Prompts > Prompt Depth**

---

## Switching Agents

You are not locked into one agent per conversation. To switch who you are talking to mid-conversation:

1. Tap the **agent name** in the chat header (e.g., "AZOTH")
2. A dropdown appears showing all four agents with their colors and brief descriptions:
   - **AZOTH** (gold) -- The Alchemist. Philosophical, symbolic, sees deeper patterns.
   - **KETHER** (violet) -- The Crown. Analytical, systematic, provides structure and oversight.
   - **VAJRA** (blue) -- The Diamond Cutter. Direct, efficient, action-oriented.
   - **ELYSIAN** (green) -- The Dreamer. Empathic, creative, emotionally attuned.
3. Tap the agent you want to talk to next

The new agent sees the full conversation history and can pick up where the previous agent left off, but will respond in their own voice and style.

---

## Offline Behavior

ApexPocket caches data locally for when you lose internet:

- **Conversation history** -- Previously loaded messages are available offline. You can scroll through past conversations.
- **Memory entries** -- Recently viewed memories are cached.
- **Sensor data** -- The last known sensor readings are displayed with a "last updated" timestamp.

**What does NOT work offline:**
- Sending new messages (requires the cloud to process via AI)
- Sensor commands (requires the cloud to relay to your Pi)
- Council deliberations
- Music generation

When internet returns, the app automatically reconnects and syncs. No data is lost -- unsent messages are not queued (they simply do not send until you have connectivity and tap send again).

---

## Updating the App

When a new version of ApexPocket is available:

1. The app shows an update banner at the top of the screen
2. Tap "Update" to download the new APK
3. Install over the existing app (your data is preserved)

You can also check manually: **Settings > About > Check for Updates**

The app version is displayed in **Settings > About**. If you are reporting a bug, include this version number.

---

## Troubleshooting

### "Unable to connect" on login

- Check that your phone has internet access
- Verify the cloud backend is healthy by visiting `https://backend-production-507c.up.railway.app/health` in your phone's browser
- If you see a JSON response with `"status": "ok"`, the backend is running
- Double-check your email and password

### App installs but crashes on launch

- Ensure you are running Android 8.0 or newer: **Phone Settings > About Phone > Android Version**
- Try clearing the app's data: **Phone Settings > Apps > ApexPocket > Storage > Clear Data**
- Re-download and reinstall the APK

### Notifications not arriving

- Check Android notification settings: **Phone Settings > Apps > ApexPocket > Notifications > Allow**
- Check in-app notification settings: **Settings > Notifications**
- Some phone manufacturers (Xiaomi, Huawei, Samsung) aggressively kill background apps. Search for your phone model + "allow background activity" for instructions on whitelisting ApexPocket.

### Agent responses are slow

- Response time depends on your subscription tier and current cloud load
- The Opus model is slower but more capable than Sonnet or Haiku
- Check your connection quality in **Settings > Device**

### SensorHead shows "Disconnected" in the app

- Verify the bridge is running on your Pi: `systemctl status sensorhead-bridge`
- Check the bridge logs: `journalctl -u sensorhead-bridge -n 20`
- The bridge may be reconnecting after a network interruption -- wait 30 seconds and check again

---

## What's Next

- [05 - Voice Setup](05-voice-setup.md) -- Give each agent a unique voice with text-to-speech
- [Sentinel Configuration](../deep/01-sentinel-config.md) -- Fine-tune your security monitoring
- [CerebroCortex Deep Guide](../deep/04-cerebrocortex.md) -- Master the memory system
