# Full SensorHead Build

**Estimated time:** 45-60 minutes (hardware assembly + first boot verification)

> This guide walks you through assembling the complete ApexAurum SensorHead from bare components. By the end, you will have a Raspberry Pi 5 with two cameras, a thermal sensor, and an environmental sensor -- all wired, powered, and verified at the hardware level. Software installation is covered in the next guide.

---

## Prerequisites

- A clean, well-lit workspace with room to lay out components
- A small Phillips-head screwdriver (if your heatsink or case requires one)
- A monitor, keyboard, and mouse for initial Pi setup (or SSH access via another computer)
- A microSD card reader (built into many laptops, or use a USB adapter)
- Basic familiarity with plugging cables into circuit boards -- no soldering required

---

## Parts List

| Part | Role | Est. Price | Notes |
|------|------|-----------|-------|
| Raspberry Pi 5 (4GB or 8GB) | Main compute board | $60-80 | 8GB recommended if running voice locally |
| MicroSD Card 32GB+ (A2 speed class) | Boot and storage media | $10-15 | A2 class provides faster random I/O; alternatively, use an NVMe SSD with a Pi 5 HAT |
| NVMe SSD (optional, replaces SD) | Faster storage alternative | $20-30 | Requires an M.2 HAT or bottom-mount adapter for Pi 5 |
| USB-C Power Supply 27W | Power | $15 | Use the official Raspberry Pi 5 PSU; generic 15W supplies cause undervoltage |
| IMX500 AI Camera Module | On-chip AI vision | $70 | Sony neural network accelerator built into the sensor, 12.3MP, runs inference without CPU load |
| IMX708 Wide-Angle NoIR Camera | Night-capable wide vision | $30 | No infrared filter -- sees in the dark with IR illumination, 12MP, 120-degree FOV |
| MLX90640 Thermal Camera (Breakout) | Far-infrared thermal imaging | $55 | 32x24 pixel thermal array, I2C interface at address 0x33, -40 to 300 degrees C range |
| BME688 Breakout Board (pi3g or Adafruit) | Environmental sensing | $20-30 | Temperature, humidity, barometric pressure, indoor air quality (IAQ), volatile organic compounds (VOC) |
| 22-pin FPC Camera Cables x2 | Connect cameras to Pi | $5-10 | Wide-to-narrow adapter cables for Pi 5's smaller connectors; usually one ships with each camera |
| Jumper Wires (female-to-female) | I2C sensor wiring | $3-5 | 4 wires minimum; Qwiic/STEMMA QT cables work if your breakouts have those connectors |
| Case or Enclosure | Protection and mounting | $5-30 | Optional: 3D printed bracket, wooden riser (our reference build), or commercial Pi 5 case |
| USB Microphone | Voice input | $15 | Optional: any USB mic works; needed for speech-to-text |
| Heatsink or Active Cooler | Thermal management | $5-15 | Strongly recommended; the official Pi 5 active cooler clips onto the board |

**Minimum build (Pi only):** ~$85 -- Raspberry Pi 5 + SD card + power supply. You can add sensors later.

**Full "three-eyed" SensorHead:** ~$250-300 -- everything above. Two cameras, thermal array, environmental sensor, voice microphone.

---

## Assembly Steps

### Step 1: Prepare the Raspberry Pi

Unbox the Pi 5. Before connecting anything else, attach the heatsink or active cooler. The official Pi 5 active cooler clips onto the board with spring-loaded push pins and connects to a small fan header between the camera ports.

If using a MicroSD card, flash Raspberry Pi OS (64-bit, Bookworm or later) using the Raspberry Pi Imager tool on another computer. Insert the flashed card into the slot on the bottom of the Pi 5 (the spring-loaded slot on the edge opposite the USB ports).

If using an NVMe SSD, mount it on your M.2 HAT first, then attach the HAT to the Pi according to the HAT manufacturer's instructions. Flash the OS to the SSD instead of a MicroSD.

> **Note:** Do NOT power on the Pi yet. Connect all cables and sensors first.

### Step 2: Connect the BME688 Environmental Sensor

The BME688 breakout communicates over I2C, which uses two data lines plus power and ground. The pi3g breakout board has a standard 4-pin header.

**Wiring (BME688 breakout to Pi 5 GPIO header):**

| BME688 Pin | Pi 5 Pin | Pi 5 GPIO | Wire Color (suggested) |
|-----------|----------|-----------|----------------------|
| SDA | Pin 3 | GPIO2 (SDA1) | Blue or White |
| SCL | Pin 5 | GPIO3 (SCL1) | Yellow or Green |
| VIN | Pin 4 | 5V Power | Red |
| GND | Pin 6 | Ground | Black |

The pi3g BME688 breakout board uses I2C address `0x77` by default. Some Adafruit breakouts use `0x76` -- check your board's documentation.

> **Note:** The BME688 connects to the Pi's 5V rail (Pin 4). The breakout board has its own voltage regulator and is 5V-tolerant. This is different from the MLX90640 in the next step.

Push the female jumper wire connectors firmly onto the GPIO pins. They should click gently into place. The Pi 5 GPIO header is the 40-pin double row along one edge of the board.

**GPIO Pin Reference (physical pin numbers, top-left is Pin 1 when USB ports face away from you):**

```
              3V3  (1) (2)  5V    <-- BME688 VIN goes here (Pin 4 = 5V)
   BME688 SDA (3) (4)  5V
   BME688 SCL (5) (6)  GND   <-- BME688 GND goes here
              (7) (8)
              ...
```

### Step 3: Mount the MLX90640 Thermal Camera

The MLX90640 also uses I2C, sharing the same SDA and SCL lines as the BME688. Both devices can coexist on the same I2C bus because they have different addresses (0x77 for BME688, 0x33 for MLX90640).

**There are two wiring options:**

**Option A -- Daisy-chain through BME688 (if your breakout has a secondary header):**

Some BME688 breakouts (including pi3g) have pass-through headers. Connect the MLX90640's SDA and SCL to the BME688's secondary I2C header. Connect VIN to the Pi's 3.3V rail (NOT the BME688's 5V pass-through) and GND to any ground pin.

**Option B -- Connect directly to Pi GPIO (recommended):**

| MLX90640 Pin | Pi 5 Pin | Pi 5 GPIO | Wire Color (suggested) |
|-------------|----------|-----------|----------------------|
| SDA | Pin 3 | GPIO2 (SDA1) | Blue or White (shared with BME688) |
| SCL | Pin 5 | GPIO3 (SCL1) | Yellow or Green (shared with BME688) |
| VIN | Pin 1 | 3.3V Power | Orange |
| GND | Pin 9 | Ground | Black |

You can stack two female jumper wires onto the same GPIO pin (Pin 3 for SDA, Pin 5 for SCL) so both sensors share the bus.

> **Warning:** The MLX90640 MUST be powered from the Pi's 3.3V rail (Pin 1 or Pin 17), NOT from 5V. Feeding 5V into the MLX90640's VIN will damage the sensor. If you are daisy-chaining through a BME688 breakout that passes through 5V, do NOT connect the MLX90640's VIN to that pass-through. Use a separate wire to Pin 1 (3.3V) on the Pi.

The MLX90640 breakout board is small and can be mounted facing outward from your enclosure. Its field of view is approximately 55 degrees (standard) or 110 degrees (wide FOV variant). Orient it toward the area you want to monitor thermally.

### Step 4: Install the IMX500 AI Camera (CAM0)

The Pi 5 has two camera ports (CSI connectors). The IMX500 AI Camera goes into **CAM0**, which is the port closest to the USB-C power connector and Ethernet jack -- the "top" port when the Pi is oriented with USB ports facing you.

**FPC Cable Installation:**

1. Locate the CAM0 port. It has a small black or white plastic latch that flips up.
2. Gently pull the latch upward (it hinges, do not remove it).
3. Slide the 22-pin FPC cable into the connector with the **metal contacts facing DOWN toward the PCB**. The blue reinforcement strip faces up.
4. Push the latch back down to lock the cable in place. It should click and hold the cable firmly.
5. Connect the other end to the IMX500 camera module using the same procedure.

> **Warning:** FPC cable orientation is the most common assembly mistake. On the Pi 5, contacts face DOWN (toward the board). On some camera modules, contacts face UP (toward you). Check both ends. A reversed cable will result in the camera not being detected at all -- no error message, just silence.

The IMX500 has an on-chip Sony neural network accelerator (the "AI" in AI Camera). It can run object detection, pose estimation, and classification models directly on the camera sensor without using the Pi's CPU. The inference results stream alongside the image data.

### Step 5: Install the IMX708 NoIR Camera (CAM1)

The IMX708 Wide-Angle NoIR camera goes into **CAM1**, the port closer to the HDMI connectors -- the "bottom" port.

Follow the same FPC cable procedure as Step 4:

1. Flip up the latch on the CAM1 connector.
2. Insert the cable with **metal contacts facing DOWN**.
3. Close the latch.
4. Connect the other end to the IMX708 module.

The "NoIR" designation means this camera has No Infrared filter. Unlike a standard camera that blocks infrared light (making photos look natural to the human eye), the NoIR camera lets IR through. This means:

- In daylight, images may have a slight pinkish/reddish tint (normal)
- In darkness with an IR illuminator, the camera can see clearly
- The wide-angle lens provides approximately 120-degree field of view

### Step 6: Assemble the Enclosure

The enclosure is your choice. Here are three proven options:

**Option A -- Vertical Wooden Riser (Reference Build):**

Our reference SensorHead uses a small wooden block or shelf riser with the Pi mounted vertically. Cameras point outward from the top edge, the thermal sensor faces forward at chest height, and the BME688 sits exposed to open air for accurate environmental readings. This design maximizes airflow to the BME688 while giving the cameras a good vantage point.

**Option B -- 3D Printed Bracket:**

Several Pi 5 camera mount designs are available on Printables and Thingiverse. Search for "Raspberry Pi 5 dual camera mount" for options that accommodate two CSI cameras. Mount the thermal sensor separately with adhesive or a small bracket.

**Option C -- Commercial Pi Case with Modifications:**

Standard Pi 5 cases work, but you will need to route the FPC cables through openings. Some cases have built-in camera mounts. The I2C sensor wires can exit through ventilation slots or a cut-out in the case.

> **Note:** Both cameras can be mounted upside-down (rotated 180 degrees). The software handles rotation correction via configuration. This gives you more flexibility in enclosure design.

**Sensor Placement Tips:**

- Keep the BME688 away from the Pi's heatsink -- the Pi generates heat that will skew temperature and humidity readings
- Point the MLX90640 toward the area you want to monitor (a doorway, a room, a desk)
- Position cameras with overlapping or complementary fields of view

### Step 7: Power Up and Verify

Connect the USB-C power supply to the Pi 5. The first boot takes approximately 2 minutes. You will see a green LED blink on the Pi during boot, then it stabilizes.

**If you have a monitor connected**, follow the Raspberry Pi OS setup wizard (language, WiFi, password).

**If you are connecting via SSH**, you need to have pre-configured WiFi credentials and SSH access in the Raspberry Pi Imager before flashing. The Pi will appear on your network with the hostname you chose (default: `raspberrypi.local`).

Once booted and logged in, run these verification commands:

**Verify I2C sensors:**

```bash
sudo apt install -y i2c-tools    # if not already installed
i2cdetect -y 1
```

Expected output shows a grid. Look for:
- `33` -- MLX90640 thermal camera
- `77` -- BME688 environmental sensor (or `76` on some boards)

```
     0  1  2  3  4  5  6  7  8  9  a  b  c  d  e  f
00:                         -- -- -- -- -- -- -- --
10: -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- --
20: -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- --
30: -- -- -- 33 -- -- -- -- -- -- -- -- -- -- -- --
40: -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- --
50: -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- --
60: -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- --
70: -- -- -- -- -- -- -- 77
```

If a sensor does not appear, check its wiring. The most common issues are loose jumper wires and swapped SDA/SCL lines.

**Verify cameras:**

```bash
libcamera-hello --list-cameras
```

Expected output should list two cameras:

```
Available cameras
-----------------
0 : imx500 [4056x3040 12-bit RGGB] (/base/...)
    Modes: ...
1 : imx708_wide_noir [4608x2592 10-bit RGGB] (/base/...)
    Modes: ...
```

If a camera does not appear:
- Check the FPC cable orientation (contacts DOWN on the Pi end)
- Verify `camera_auto_detect=1` is in `/boot/firmware/config.txt`
- A reboot may be required after enabling the camera interface

### Step 8: Run the Install Script

With hardware verified, you are ready for software. The unified installer handles everything from here:

```bash
git clone <repository-url> ~/claude-root/SensorHead
cd ~/claude-root/SensorHead
chmod +x install.sh
sudo ./install.sh --preset full
```

See [02 - Software Install](02-software-install.md) for the full walkthrough of what the installer does.

### Step 9: Cloud Pairing

After the software is installed, you need to connect your SensorHead to the ApexAurum cloud so you can interact with it from your phone:

1. Create an account at the ApexAurum web dashboard
2. Register your device and get a pairing token
3. Enter the token during install (or edit `config.json` afterward)
4. Restart the bridge service

See [03 - Cloud Pairing](03-cloud-pairing.md) for detailed instructions.

### Step 10: Test All Sensors

Once the bridge is running and connected to the cloud, test each sensor from the mobile app or from a Claude Code session:

| Command / Prompt | What It Tests |
|-----------------|---------------|
| "Read the room temperature" | BME688 -- temperature, humidity, pressure |
| "What's the air quality?" | BME688 -- IAQ index, VOC level |
| "Show me the thermal view" | MLX90640 -- thermal frame capture |
| "What can you see?" | IMX708 -- visible light photo |
| "Identify what's in front of you" | IMX500 -- AI-accelerated object detection |
| "Take a photo with both cameras" | Both cameras in sequence |

If a sensor does not respond, check the troubleshooting section below.

---

## Common Mistakes

| Mistake | Symptom | Fix |
|---------|---------|-----|
| FPC cable reversed (contacts up instead of down) | Camera not detected by `libcamera-hello` | Remove cable, reinsert with metal contacts facing the PCB (down) |
| MLX90640 connected to 5V instead of 3.3V | Sensor may overheat or give erratic readings; risk of permanent damage | Immediately disconnect power; rewire VIN to Pin 1 (3.3V) |
| SDA and SCL swapped | I2C devices not detected by `i2cdetect` | Swap the two data wires; SDA is Pin 3, SCL is Pin 5 |
| Using a 15W USB-C supply instead of 27W | Pi throttles under load; undervoltage lightning bolt icon on screen | Use the official 27W Pi 5 PSU |
| Camera cable in wrong port | Wrong camera shows on wrong index, or one camera missing | IMX500 goes in CAM0 (top port, near USB-C); IMX708 goes in CAM1 (bottom port, near HDMI) |
| BME688 too close to Pi heatsink | Temperature reads 5-15 degrees higher than actual room temperature | Move the sensor away from heat sources; use longer jumper wires |
| I2C not enabled in boot config | `i2cdetect` returns "Could not open file" error | Add `dtparam=i2c_arm=on` to `/boot/firmware/config.txt` and reboot |

---

## Wiring Diagram Summary

```
Raspberry Pi 5 GPIO Header (physical pin numbers)
===================================================

Pin 1  [3V3 Power] -----> MLX90640 VIN (3.3V ONLY!)
Pin 2  [5V Power]  -----> BME688 VIN
Pin 3  [GPIO2/SDA] -----> BME688 SDA + MLX90640 SDA (shared bus)
Pin 4  [5V Power]  -----> (available)
Pin 5  [GPIO3/SCL] -----> BME688 SCL + MLX90640 SCL (shared bus)
Pin 6  [Ground]    -----> BME688 GND
Pin 7  ...
Pin 8  ...
Pin 9  [Ground]    -----> MLX90640 GND

CAM0 (top port, near USB-C/Ethernet): IMX500 AI Camera
CAM1 (bottom port, near HDMI):        IMX708 Wide NoIR Camera
```

---

## Verification Checklist

After completing assembly, confirm each item:

- [ ] Pi boots to desktop or SSH login within 2 minutes
- [ ] `i2cdetect -y 1` shows `33` (MLX90640) and `77` (BME688)
- [ ] `libcamera-hello --list-cameras` shows both imx500 and imx708_wide_noir
- [ ] No undervoltage warnings (lightning bolt icon or `dmesg | grep voltage`)
- [ ] Heatsink or active cooler is attached and functioning
- [ ] Sensor wires are secure (gentle tug test -- they should not slip off)

---

## What's Next

- [02 - Software Install](02-software-install.md) -- Run the unified installer to set up the bridge, memory, voice, and sensor drivers
- [03 - Cloud Pairing](03-cloud-pairing.md) -- Connect your SensorHead to the ApexAurum cloud
- [04 - Mobile App Setup](04-mobile-app.md) -- Install the ApexPocket companion app on your phone
