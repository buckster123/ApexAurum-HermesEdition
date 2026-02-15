# SensorHead Basics

**Estimated reading time: 8 minutes**

Your SensorHead is not just a Pi with a chat interface. It is a multi-sensor array that can see, feel, and sense the environment around it. This guide walks you through reading temperature, taking photos, viewing thermal imagery, and running object detection -- all by asking your agent.

---

## What SensorHead Can Do

SensorHead combines three categories of sensing:

| Category | Hardware | What It Detects |
|----------|----------|----------------|
| **See** | IMX500 AI Camera | Photos, object detection, scene classification, pose estimation |
| **Feel** | BME688 Environmental Sensor | Temperature, humidity, barometric pressure, air quality (IAQ), gas resistance |
| **Sense** | MLX90640 Thermal Array | 32x24 pixel thermal heatmap, heat sources, presence detection |

Every sensor is accessible through natural language. You do not need to run commands or write code -- just ask your agent.

---

## Step 1: Read the Environment

Start a chat with any agent and ask:

```
What's the temperature?
```

The agent calls the `sensorhead_environment` tool and reads the BME688 sensor. You will get back a full environmental snapshot:

| Reading | What It Means | Typical Indoor Value |
|---------|--------------|---------------------|
| **Temperature** | Air temperature in Celsius | 18-25 C |
| **Humidity** | Relative humidity percentage | 30-60% |
| **Pressure** | Barometric pressure in hPa | 1000-1025 hPa |
| **IAQ** | Indoor Air Quality index | 0-500 (lower is better) |
| **Gas Resistance** | Raw VOC sensor reading in ohms | Varies widely |

### Understanding the IAQ Scale

The Indoor Air Quality index is one of the most useful readings. Here is what the numbers mean:

| IAQ Range | Rating | What To Do |
|-----------|--------|-----------|
| 0 - 50 | Excellent | Nothing -- your air is great |
| 51 - 100 | Good | Normal conditions, no action needed |
| 101 - 150 | Moderate | Consider ventilating if the trend is upward |
| 151 - 200 | Unhealthy | Open windows or turn on ventilation |
| 201 - 300 | Poor | Significant ventilation needed, investigate source |
| 301 - 500 | Hazardous | Leave the area and ventilate thoroughly |

The IAQ reading accounts for volatile organic compounds (VOCs) like cooking fumes, cleaning products, paint, and off-gassing from furniture. It takes about 15-30 minutes after startup for the BME688 to calibrate and give reliable IAQ readings.

> **Tip:** You can also ask specifically for air quality by saying "How's the air quality?" The agent will call `sensorhead_air_quality` and give you a detailed report with recommendations.

---

## Step 2: Take a Photo

Ask your agent:

```
Take a photo.
```

The agent calls the `sensorhead_photo` tool, which captures a still image from the IMX500 AI Camera. The photo is returned in the chat for you to view.

The IMX500 is special -- it has a built-in AI accelerator chip that can run neural networks directly on the camera sensor. This means the camera can do more than just take photos:

| Capability | Command | What It Does |
|-----------|---------|-------------|
| **Photo** | "Take a photo" | Captures a still image |
| **Object Detection** | "What can you see?" | Identifies and labels objects in the frame |
| **Scene Classification** | "Classify this scene" | Categorizes what the camera is looking at (office, kitchen, outdoors, etc.) |
| **Pose Estimation** | "Is anyone standing there?" | Detects human body poses and positions |

All of this AI processing happens on the camera chip itself, not on the Pi's CPU. This keeps things fast and frees the Pi to handle other tasks.

---

## Step 3: View the Thermal Image

Ask your agent:

```
Show me the thermal view.
```

The agent calls `sensorhead_thermal_image`, which reads the MLX90640 thermal sensor array and generates a color-mapped heatmap.

### Reading the Heatmap

The thermal image is a 32x24 pixel grid where each pixel represents a temperature measurement. The color mapping runs from cool to hot:

| Color | Temperature |
|-------|------------|
| **Dark blue / purple** | Coldest areas in view |
| **Green / yellow** | Mid-range temperatures |
| **Orange / red** | Warmest areas in view |
| **White** | Hottest spots |

Common things you will see:

- **People** show up as warm blobs (around 30-37 C skin temperature)
- **Electronics** like laptops and monitors glow warm
- **Windows** appear cool compared to walls (especially in winter)
- **Heating vents** are bright spots of warmth

> **Note:** The first two frames after the sensor starts up are discarded automatically. This is because the MLX90640 needs a brief warmup period to give accurate readings. You will not notice this in practice -- the agent handles it silently.

### Getting Raw Data

If you want the actual temperature numbers rather than a visual:

```
What are the thermal readings?
```

This calls `sensorhead_thermal_data` and returns the raw temperature values from the 32x24 grid, along with min, max, and average temperatures.

---

## Step 4: Run Object Detection

Ask your agent:

```
What can you see?
```

The agent captures a frame from the camera and runs the on-chip object detection model. You will get back a list of detected objects with confidence scores:

```
I can see:
- Person (94% confidence) - center of frame
- Laptop (87% confidence) - lower right
- Chair (72% confidence) - left side
- Coffee mug (68% confidence) - on desk
```

The detection model recognizes common everyday objects. It works best with good lighting and objects that are within a few meters of the camera.

---

## Step 5: Check for People

Ask your agent:

```
Is anyone in the room?
```

This is a compound query. The agent combines data from multiple sensors:

- **Thermal array** to detect warm bodies (fast, works in the dark)
- **Visual camera** to confirm with object detection (more detailed, needs light)

By combining both, the agent can give you a more reliable answer than either sensor alone. The thermal sensor catches people even in complete darkness, while the camera provides visual confirmation and can tell you who or what is there.

---

## Bonus: Sentinel Mode

SensorHead has an automated monitoring mode called **Sentinel** that watches for changes without you having to ask.

### What Sentinel Does

When armed, Sentinel continuously monitors the thermal and visual sensors for significant changes -- someone entering a room, a sudden temperature shift, unexpected motion. When it detects something, it logs the event and can send you a notification.

### Arming Sentinel

You can ask your agent:

```
Arm the sentinel.
```

Or configure it in the app under the SensorHead settings panel.

### Checking Sentinel Status

```
What's the sentinel status?
```

### Viewing Events

```
Show me the sentinel events.
```

This returns a timeline of detection events with timestamps and, where available, snapshot images of what triggered the alert.

> **Tip:** Sentinel is designed for passive monitoring -- checking on a room while you are away, watching for deliveries, keeping an eye on pets. It is not a replacement for a dedicated security system, but it is a surprisingly useful awareness tool.

---

## Putting It All Together

Now you know how to use each sensor individually. But the real power comes from combining them. Here are some natural ways to use SensorHead in daily life:

**Morning routine:**
"What's the temperature and air quality?" -- Check conditions before deciding whether to open windows.

**Working from home:**
"Is the air getting stale?" -- The BME688 tracks IAQ trends, so the agent can tell you if air quality is declining over time.

**Away from home:**
"Is anyone in the house?" -- Thermal plus visual confirmation while you are out.

**At night:**
"Show me the thermal view of the living room." -- See what is happening without needing visible light.

**Full picture:**
"Give me a scene report." -- The agent runs `sensorhead_scene_report`, which combines all sensors into a single comprehensive overview: environmental conditions, visual scene description, thermal analysis, and occupancy assessment.

---

## Troubleshooting

**"Sensor not responding" or timeout errors**

- Check that the sensor is properly connected to the Pi's I2C bus: `i2cdetect -y 1`
- The BME688 should appear at address `0x76` or `0x77`
- The MLX90640 should appear at address `0x33`

**Camera returns a black image**

- Make sure nothing is covering the lens.
- Check camera connection: `libcamera-hello --list-cameras`
- Try rebooting the Pi: `sudo reboot`

**IAQ readings seem wrong (stuck at 0 or 500)**

- The BME688 needs 15-30 minutes of warmup time after power-on to calibrate its gas sensor.
- If it has been running for a while and readings are still off, check the sensor wiring.

**Thermal image looks noisy or has dead pixels**

- This is normal for the MLX90640 at the edges of the array.
- Ensure the sensor has a clear view -- even thin obstructions can affect readings.
- Try `sensorhead_thermal_data` for raw values to see if specific pixels are consistently anomalous.

---

## What You Have Now

Over the course of these five guides, you have:

1. Set up a Raspberry Pi 5 from scratch
2. Paired it with your phone via the ApexPocket app
3. Met the four AI agents and learned how to switch between them
4. Stored and recalled persistent memories with CerebroCortex
5. Read environmental data, taken photos, viewed thermal imagery, and run object detection

Your SensorHead is a fully operational AI-powered environmental awareness system. The agents know you, they can see and feel the space around you, and they remember everything you tell them.

---

## Where to Go From Here

These quick-start guides covered the fundamentals. For deeper exploration:

- **Deep Dives** -- detailed guides on specific features like the Dream Engine, Council deliberations, and advanced Sentinel configuration
- **Troubleshooting** -- comprehensive solutions for common issues
- **Setup Guides** -- hardware assembly, sensor calibration, and network configuration

Welcome to the Village.
