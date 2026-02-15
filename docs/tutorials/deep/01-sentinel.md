# Sentinel Configuration

**Estimated reading time: 12 minutes**

The Sentinel is the SensorHead's autonomous monitoring system. It runs as a background loop inside the bridge service, continuously scanning the thermal camera for changes and optionally confirming detections with the IMX500 AI Camera. When something triggers, it pushes alerts through the WebSocket to the cloud -- which forwards them to your phone as push notifications.

This guide covers how Sentinel works, how to tune its parameters, and how to set it up for different scenarios.

---

## How Sentinel Works

### Architecture

Sentinel runs as an async loop alongside the bridge's other tasks (telemetry, command handling, heartbeat). The detection pipeline flows through three stages:

```
Thermal Scan (0.5s interval)
    |
    v
Delta Threshold Check (per-pixel temperature change)
    |
    v  [trigger]
AI Confirmation (IMX500 object detection)
    |
    v  [classified]
Alert Push (WebSocket -> Cloud -> Phone)
```

The thermal camera (MLX90640) provides a 32x24 pixel temperature grid at 2Hz. Sentinel compares each frame against the previous one, counting how many pixels changed by more than the configured threshold. If enough pixels changed, a "trigger" fires.

After a trigger, if AI confirmation is enabled, the IMX500 runs object detection to classify what caused the thermal change. This converts a generic "motion" event into a specific label like "person", "cat", or "dog". After the AI check completes, the inference engine is released so the IMX500 camera remains available for manual captures.

Finally, a NoIR camera snapshot is captured and attached to the alert (unless disabled), and the complete event is pushed to the cloud.

### What Gets Sent

Each alert is a `SentinelEvent` containing:

| Field | Description |
|-------|------------|
| `event_type` | "motion", "person", "cat", "dog", "bird", etc. |
| `timestamp` | Unix timestamp of the detection |
| `thermal_delta` | Maximum per-pixel temperature change (degrees C) |
| `changed_pixels` | Number of pixels that exceeded the threshold |
| `thermal_min_c` | Coldest point in the thermal frame |
| `thermal_max_c` | Hottest point in the thermal frame |
| `thermal_avg_c` | Average temperature across the frame |
| `ai_detections` | List of AI detection results (label, confidence, bounding box) |
| `snapshot_b64` | Base64-encoded NoIR camera JPEG (if enabled) |

---

## Configuration Parameters

All Sentinel parameters can be changed at runtime without restarting the bridge. You can configure them through the mobile app's Sentinel tab, through a chat command to AZOTH ("configure the sentinel with higher sensitivity"), or directly via the bridge API.

### Thermal Detection

| Parameter | Default | Range | Description |
|-----------|---------|-------|-------------|
| `thermal_threshold_c` | 2.0 | 0.5 - 10.0 | Minimum per-pixel temperature change (in degrees C) to count as "changed". Lower values detect subtler changes but produce more false triggers. |
| `min_changed_pixels` | 10 | 1 - 768 | Minimum number of changed pixels required to fire a trigger. The thermal grid is 32x24 = 768 pixels total. A person walking through the frame typically changes 15-50 pixels. |
| `scan_interval` | 0.5 | 0.1 - 10.0 | Seconds between thermal scans. Default 0.5s gives 2Hz scanning. Faster scanning catches quicker movement but uses more CPU. |

### AI Confirmation

| Parameter | Default | Description |
|-----------|---------|-------------|
| `ai_confirm` | true | Whether to run IMX500 object detection after a thermal trigger. Disabling this makes alerts faster but less specific (all events report as "motion"). |
| `ai_confidence` | 0.3 | Minimum detection confidence (0.0-1.0) for AI results. Lower values catch more but include more false positives. |
| `ai_labels` | ["person", "cat", "dog", "bird"] | Detection labels that upgrade the event type from "motion" to the specific label. Only labels in this list are considered. |

### Rate Limiting

| Parameter | Default | Description |
|-----------|---------|-------------|
| `cooldown_s` | 30.0 | Minimum seconds between consecutive alerts. Prevents alert storms during sustained activity (e.g., a pet walking back and forth). |
| `max_alerts_per_hour` | 20 | Hard cap on alerts per rolling hour. After this limit, triggers are detected but alerts are suppressed until the hour resets. |

### Snapshots

| Parameter | Default | Description |
|-----------|---------|-------------|
| `include_snapshot` | true | Whether to attach a NoIR camera JPEG to each alert. Disabling this reduces alert size and speeds up delivery. |
| `snapshot_quality` | 60 | JPEG compression quality (1-100). Lower values produce smaller files. 60 is a good balance for mobile delivery. |
| `snapshot_max_dim` | 640 | Maximum pixel dimension for alert images. Images larger than this are downscaled to fit. |

### Schedule

| Parameter | Default | Description |
|-----------|---------|-------------|
| `active_start` | "" (always) | Start time in 24-hour "HH:MM" format (e.g., "22:00"). Empty means always active when armed. |
| `active_end` | "" (always) | End time in 24-hour "HH:MM" format (e.g., "07:00"). Overnight wrapping works correctly (22:00 to 07:00 means active from 10 PM to 7 AM). |

---

## Built-in Presets

Sentinel includes four built-in presets for common use cases. Load a preset through the app, a chat command, or directly:

### default

The baseline configuration. Balanced sensitivity for general-purpose monitoring.

```
thermal_threshold_c: 2.0
min_changed_pixels: 10
cooldown_s: 30.0
max_alerts_per_hour: 20
ai_confirm: true
ai_labels: ["person", "cat", "dog", "bird"]
```

### night_watch

High sensitivity for overnight security monitoring. Detects smaller thermal changes and allows more frequent alerts.

```
thermal_threshold_c: 1.5
min_changed_pixels: 5
cooldown_s: 20.0
active_start: "22:00"
active_end: "07:00"
ai_labels: ["person", "cat", "dog", "bird"]
```

Best for: front door monitoring, garage security, overnight building surveillance.

### away_mode

Maximum sensitivity for when nobody should be in the space. Only alerts on human detection, with a short cooldown for rapid response.

```
thermal_threshold_c: 1.0
min_changed_pixels: 3
cooldown_s: 15.0
ai_labels: ["person"]
```

Best for: leaving your home or office, vacation mode, restricted area monitoring.

### pet_watch

Reduced sensitivity to avoid false triggers from pet movement. Longer cooldown to prevent notification fatigue.

```
thermal_threshold_c: 2.5
min_changed_pixels: 8
cooldown_s: 60.0
ai_labels: ["cat", "dog", "bird"]
```

Best for: checking on pets while away, pet activity logging, pet door monitoring.

---

## How to Arm and Disarm

### From the Mobile App

Open the ApexPocket app, navigate to the **Sentinel** tab. You will see:

- An **Arm/Disarm** toggle
- The current preset name
- A preset selector to switch between presets
- Live status showing scan count, trigger count, and last alert time

Tap the toggle to arm or disarm. When armed, the Sentinel indicator in the app header glows amber.

### From Chat

You can ask any agent to control the Sentinel:

- "Arm the sentinel"
- "Disarm the sentinel"
- "Switch sentinel to night watch mode"
- "Set sentinel cooldown to 45 seconds"
- "How many alerts has the sentinel triggered today?"

### Programmatically

The bridge accepts these WebSocket commands:

| Action | Parameters | Description |
|--------|-----------|-------------|
| `sentinel_arm` | none | Arms the sentinel, resets baseline frame |
| `sentinel_disarm` | none | Disarms the sentinel |
| `sentinel_configure` | any config params as key-value pairs | Hot-updates specific parameters |
| `sentinel_load_preset` | `{"preset": "night_watch"}` | Loads a built-in preset |
| `sentinel_status` | none | Returns full status with config and stats |

---

## Alert Routing

When Sentinel detects an event, the alert flows through this chain:

1. **SentinelEvent created** with thermal data, AI detections, and optional snapshot.
2. **WebSocket push** from bridge to cloud backend.
3. **Cloud processing**: the alert is stored in the database and forwarded to the user's active sessions.
4. **Push notification** sent to the ApexPocket app via Firebase Cloud Messaging (FCM).
5. **Optional agent commentary**: if configured, the assigned agent (usually AZOTH) generates a short comment on the event -- for example, "Motion detected at the front door at 2:34 AM. Thermal signature suggests a person."

Push notifications include:
- Event type (motion, person, cat, etc.)
- Timestamp
- Thermal delta summary
- Snapshot thumbnail (if available)

---

## Tuning Tips

### Avoid Windows and Direct Sunlight

The thermal camera detects surface temperature changes, not movement. Placing the SensorHead facing a window will cause false triggers as sunlight shifts throughout the day, clouds pass, and outdoor temperatures change. Point the camera at interior spaces instead.

### Thermal vs. Visual Detection

Thermal detection works in complete darkness and through thin materials like curtains. It cannot be defeated by wearing dark clothing or moving slowly. However, it is less specific than visual detection -- a warm pipe and a person both look like warm blobs. Use AI confirmation to distinguish between them.

### Balancing Sensitivity and Noise

- **High false triggers**: increase `thermal_threshold_c` and `min_changed_pixels`.
- **Missing real events**: decrease both values. Also check that the thermal camera has a clear line of sight to the monitored area.
- **Too many notifications**: increase `cooldown_s` or decrease `max_alerts_per_hour`.
- **Not enough detail on events**: enable AI confirmation, include snapshots, and lower `ai_confidence` for more detection candidates.

### Temperature Considerations

The thermal camera measures absolute surface temperatures. In a room where the ambient temperature is close to human body temperature (hot summer day, 35C+), the thermal contrast between a person and the background is minimal. Sentinel works best when there is at least a 5C difference between the expected background and the objects you want to detect.

### Cooldown Strategy

The cooldown timer starts when an alert is sent, not when a trigger occurs. During the cooldown window, the thermal scanner continues running and recording triggers, but alerts are suppressed. This means:

- A 30-second cooldown still detects continuous movement -- it just does not flood you with notifications.
- If the cooldown is too short and activity is continuous, you will hit the `max_alerts_per_hour` cap. The hourly cap resets every 60 minutes from when counting started.

---

## Quick Reference

| Task | Command / Setting |
|------|------------------|
| Arm sentinel | App toggle, or "arm the sentinel" in chat |
| Disarm sentinel | App toggle, or "disarm the sentinel" in chat |
| Load preset | App preset selector, or `sentinel_load_preset` |
| Check status | `sentinel_status` or app Sentinel tab |
| Reduce false triggers | Increase `thermal_threshold_c` (try 3.0-4.0) |
| Increase sensitivity | Decrease `thermal_threshold_c` (try 1.0-1.5) |
| Reduce notifications | Increase `cooldown_s` (try 60-120) |
| Night-only monitoring | Set `active_start: "22:00"`, `active_end: "07:00"` |
| Person-only alerts | Set `ai_labels: ["person"]` with `ai_confirm: true` |
| Disable snapshots | Set `include_snapshot: false` |
| Available presets | default, night_watch, away_mode, pet_watch |
