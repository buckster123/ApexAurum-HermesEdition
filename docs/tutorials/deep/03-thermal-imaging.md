# Thermal Imaging

**Estimated reading time: 13 minutes**

The MLX90640 is a 32x24 pixel far-infrared thermal sensor array that measures the surface temperature of objects in its field of view. It connects to the Raspberry Pi via I2C and provides contactless temperature measurement from -40 to +300 degrees C. SensorHead uses it for presence detection, thermal anomaly monitoring, and the Sentinel's primary trigger mechanism.

This guide covers how the sensor works, how to interpret thermal images, and how to get the most out of thermal data.

---

## Sensor Specifications

| Specification | Value |
|--------------|-------|
| Resolution | 32 x 24 pixels (768 total) |
| Temperature Range | -40 to +300 degrees C |
| Accuracy | +/- 1 degree C (typical) |
| Field of View (Standard) | 55 x 35 degrees |
| Field of View (Wide) | 110 x 75 degrees |
| I2C Address | 0x33 |
| Refresh Rate | Configurable 0.5Hz to 64Hz (default: 4Hz) |
| Interface | I2C at 400kHz or 800kHz |

> **Note:** SensorHead initializes the I2C bus at 800kHz for faster frame reads. At the default 100kHz, each frame takes approximately 1.4 seconds. At 800kHz, frame time drops to approximately 0.25 seconds, making 4Hz scanning practical.

---

## How It Works

Each of the 768 pixels is a thermopile element that detects infrared radiation proportional to the surface temperature of whatever object is in that pixel's field of view. The sensor does not emit any radiation -- it is purely passive, reading the thermal energy that all objects naturally radiate.

Key principles:

- **Surface temperature, not air temperature**: the sensor measures the temperature of surfaces (walls, furniture, skin, floors), not the air between the sensor and the object.
- **Emissivity matters**: most organic materials, painted surfaces, and fabrics have high emissivity (~0.95) and give accurate readings. Shiny metals and glass have low emissivity and read lower than actual temperature.
- **Distance affects pixel coverage**: at 1 meter, each pixel covers roughly 3x3 cm (standard FOV). At 5 meters, each pixel covers roughly 15x15 cm. Small or distant objects may not register clearly.

### Startup Warmup

The first 2 frames after power-on contain stale or noisy data from the sensor's internal buffer. The SensorHead driver automatically discards these frames during initialization. You will see this in the logs:

```
MLX90640 warming up (discarding 2 frames)...
MLX90640 warm-up complete
```

After warmup, readings are stable and reliable.

### Dead Pixel Handling

Occasionally, individual pixels return out-of-range values (below -40 or above 300 degrees C). These are dead pixels or read errors. The driver clamps them:

- Values below -40 degrees C are set to -40 degrees C
- Values above 300 degrees C are set to 300 degrees C

These clamped values are excluded from temperature statistics (min/max/avg calculations still produce meaningful results because dead pixels are rare -- typically 0-2 per sensor).

---

## I2C Bus Speed

The I2C bus speed significantly impacts thermal camera performance:

| Bus Speed | Frame Time | Effective Max Refresh |
|-----------|-----------|----------------------|
| 100 kHz (default) | ~1.4 seconds | ~0.7 Hz |
| 400 kHz | ~0.4 seconds | ~2.5 Hz |
| 800 kHz | ~0.25 seconds | ~4 Hz |

The SensorHead install script sets 800kHz in the boot configuration:

```
dtparam=i2c_arm_baudrate=800000
```

This is set in `/boot/firmware/config.txt`. If you experience I2C errors with multiple devices, try dropping to 400kHz:

```
dtparam=i2c_arm_baudrate=400000
```

> **Note:** Higher bus speeds can cause issues with some I2C devices. The BME688 works reliably at all three speeds. If you add other I2C peripherals and experience intermittent read failures, lowering the bus speed is the first thing to try.

---

## Refresh Rate

The sensor's internal refresh rate is separate from the I2C bus speed. It controls how often the sensor updates its internal pixel data:

| Setting | Rate | Use Case |
|---------|------|----------|
| REFRESH_0_5_HZ | 0.5 Hz | Ultra-low power, slow monitoring |
| REFRESH_1_HZ | 1 Hz | Low power |
| REFRESH_2_HZ | 2 Hz | Balanced |
| REFRESH_4_HZ | 4 Hz | **Default** -- good for presence detection |
| REFRESH_8_HZ | 8 Hz | Motion tracking |
| REFRESH_16_HZ | 16 Hz | Fast motion |
| REFRESH_32_HZ | 32 Hz | High speed (higher noise) |
| REFRESH_64_HZ | 64 Hz | Maximum speed (significantly more noise) |

SensorHead defaults to 4Hz. Higher refresh rates introduce more noise per frame. For the Sentinel's thermal differencing algorithm, 4Hz provides the best balance of temporal resolution and frame quality.

---

## Heatmap Generation

The SensorHead converts raw temperature arrays into colorized heatmap images using this pipeline:

```
768 temperature values
    |
    v
Normalize to 0-255 range (min/max scaling)
    |
    v
Map each value to Ironbow color LUT (256 entries)
    |
    v
Build 32x24 PIL Image
    |
    v
Correct mount orientation (rotate 90 CW, flip horizontal)
    |
    v
Upscale with nearest-neighbor interpolation (to 320x240 default)
    |
    v
Encode as JPEG
```

### The Ironbow Color Scale

The Ironbow palette is the industry-standard thermal camera color scheme. It maps temperatures from cold to hot as:

```
Black (coldest) -> Dark Blue -> Blue -> Purple -> Magenta -> Red -> Orange -> Yellow -> White (hottest)
```

The color mapping is relative to each frame's own min/max range, not absolute. This means:

- A frame showing a room at 20-25 degrees C will use the full color range across those 5 degrees.
- A frame showing a person (30-36 degrees C skin) against a room (20-22 degrees C walls) will show the person as bright yellow/white and walls as dark blue/purple.

### Nearest-Neighbor Upscaling

The heatmap is upscaled from 32x24 to a viewable resolution (default 320x240) using **nearest-neighbor** interpolation. This preserves the distinctive "blocky" thermal pixel look. Bilinear or bicubic interpolation would make the image smoother but would visually imply precision that the sensor does not actually have.

---

## Interpreting Thermal Images

### People

Human skin has a surface temperature of approximately 30-36 degrees C depending on clothing, ambient conditions, and activity level. In a room at 20-22 degrees C, a person stands out clearly as a bright warm blob.

- **Face and hands** appear warmest (skin directly exposed)
- **Clothed body** appears slightly cooler (clothing insulates)
- **Hair** can appear cooler than skin
- From across a typical room (3-5 meters), a person occupies roughly 15-40 pixels depending on distance and angle

### Pets

Dogs and cats have body temperatures of 38-39 degrees C, slightly warmer than humans. Their fur provides insulation, so the thermal signature varies:

- **Short-haired pets** have a clearer thermal signature
- **Long-haired pets** appear cooler due to fur insulation
- Pets are smaller and produce a smaller thermal blob (5-15 pixels at typical indoor distances)

### Electronics and Appliances

- **Computer/Pi CPU**: 40-80 degrees C -- shows as a hot spot
- **Monitors and TVs**: warm when on, uniform temperature across the screen
- **Power supplies**: 30-50 degrees C depending on load
- **Light bulbs (incandescent)**: extremely hot, can saturate the sensor
- **LED lights**: minimal thermal signature

### Building Features

- **Windows**: appear as cold spots (close to outdoor temperature). Single-pane windows show more contrast than double-glazed.
- **Exterior walls**: cooler than interior walls in winter, warmer in summer.
- **Doors**: gaps under doors may show as thin warm or cold lines (air leaks).
- **Heating vents**: clearly visible as warm spots when active.
- **Water pipes**: hot water pipes show as warm lines in walls/floors if close to the surface.

---

## Practical Use Cases

### Presence Detection

Thermal presence detection works in conditions where cameras fail:

- **Complete darkness**: thermal radiation does not require visible light
- **Through thin curtains**: infrared passes through many fabrics
- **Privacy-preserving**: 32x24 resolution cannot identify faces, only detect warm bodies

The Sentinel uses thermal differencing (comparing consecutive frames) rather than absolute thresholds. This approach detects **changes** in the scene:

- Person enters a room: sudden appearance of a warm region
- Person leaves a room: warm region disappears
- Person moves within a room: warm region shifts position

### Energy Efficiency

Use the thermal camera to find heat leaks:

- **Windows**: compare the thermal signature of different windows. Significantly colder windows may need better sealing or upgrading to double-glazed.
- **Door frames**: look for cold spots around the edges indicating air infiltration.
- **Wall insulation gaps**: if part of an exterior wall is noticeably colder than the rest, insulation may be missing or compressed in that section.
- **Heating distribution**: check if radiators or vents are evenly heating the room.

Best done on cold days when the indoor/outdoor temperature difference is large (10+ degrees C).

### Equipment Monitoring

Monitor electronics for overheating:

- Set up periodic thermal captures (the bridge does this every 30 seconds via telemetry)
- Establish baseline temperatures for your equipment
- Alert when temperatures exceed normal ranges
- Useful for server rooms, network closets, or any equipment that generates heat

### Pet Monitoring

Track pet presence and activity without cameras:

- Detect when a pet enters or leaves a room
- Monitor sleeping spots (warm areas that persist)
- The pet_watch Sentinel preset is tuned for this use case

---

## Anomaly Detection

The Sentinel's thermal anomaly detection works by computing per-pixel deltas between consecutive frames:

1. Read current thermal frame (768 temperature values)
2. Compare each pixel against the previous frame
3. Count pixels where the absolute temperature change exceeds `thermal_threshold_c`
4. If the count exceeds `min_changed_pixels`, trigger an alert

This approach is intentionally simple and robust:

- It does not require a trained model
- It adapts automatically to any environment
- It catches any thermal change, not just specific patterns
- False positives are managed through threshold tuning and AI confirmation

### What Triggers Anomaly Detection

| Event | Typical Delta | Typical Changed Pixels |
|-------|-------------|----------------------|
| Person entering room | 5-15 degrees C | 15-50 |
| Pet entering room | 5-12 degrees C | 5-15 |
| Door opening (exterior) | 2-10 degrees C | 10-30 |
| Oven/heater turning on | 10-50 degrees C | 5-20 |
| Sunlight shifting | 1-5 degrees C | 50-200 |
| HVAC cycling | 1-3 degrees C | 100-300 |

The default threshold (2.0 degrees C, 10 pixels) is tuned to catch people and pets while ignoring gradual environmental shifts. HVAC cycling can cause false triggers -- increase the threshold to 3.0-4.0 degrees C if this is an issue.

---

## Limitations

### Resolution

At 32x24 pixels, the thermal image is very low resolution. For context:

- A standard VGA image is 640x480 (307,200 pixels)
- The MLX90640 is 32x24 (768 pixels)
- That is **400 times fewer pixels** than VGA

This resolution is sufficient for:
- Detecting the presence of warm bodies (people, pets)
- Identifying temperature zones (warm wall vs. cold window)
- Spotting heat sources (electronics, heaters, cooking)

It is NOT sufficient for:
- Identifying who a person is
- Reading text or displays
- Detailed object recognition
- Counting fingers or distinguishing hand gestures

### Glass and Metal

Infrared radiation does not pass through glass. A window appears at its own surface temperature, not the temperature of objects behind it. You cannot use the thermal camera to see through windows.

Polished metal surfaces reflect infrared radiation from other objects, similar to how a mirror reflects visible light. The temperature reading from a shiny metal surface shows the reflected temperature of whatever is "behind" the sensor, not the metal's own temperature.

### Ambient Temperature Effects

When the ambient temperature approaches human body temperature (above 30 degrees C), the thermal contrast between a person and the background decreases significantly. In very hot environments (35+ degrees C), person detection becomes unreliable because the temperature difference may fall below the detection threshold.

Conversely, in very cold environments, the contrast is excellent and detection works at longer ranges.

### Field of View

The standard FOV is 55x35 degrees, which covers a relatively narrow cone. At 3 meters distance, the field of view covers approximately:

- Width: 3.1 meters
- Height: 1.9 meters

This means a single sensor cannot cover a large room from one corner. Position the sensor to look down a hallway or across a doorway for best coverage.

---

## Quick Reference

| Specification | Value |
|--------------|-------|
| Resolution | 32 x 24 (768 pixels) |
| Temperature Range | -40 to +300 degrees C |
| I2C Address | 0x33 |
| Default Refresh Rate | 4 Hz |
| Default I2C Speed | 800 kHz |
| Warmup Frames | 2 (auto-discarded) |
| Heatmap Output Size | 320 x 240 (default) |
| Color Palette | Ironbow (black to white) |

| Task | How |
|------|-----|
| Check sensor detection | `i2cdetect -y 1` -- look for 0x33 |
| View live heatmap | "Show me the thermal view" in chat |
| Read temperatures | "What's the thermal reading?" in chat |
| Adjust I2C speed | Edit `dtparam=i2c_arm_baudrate` in `/boot/firmware/config.txt` |
| Change refresh rate | Modify `refresh_rate` in ThermalCamera init (requires code change) |
| Sentinel thermal settings | See [Sentinel Configuration](./01-sentinel.md) |
| Heatmap orientation fix | Handled automatically (rotate + flip for physical mount) |
| Dead pixel threshold | Below -40 or above 300 degrees C (auto-clamped) |
