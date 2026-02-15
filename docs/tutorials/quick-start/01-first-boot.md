# First Boot

**Estimated reading time: 7 minutes**

Get your Raspberry Pi 5 up and running with all the interfaces SensorHead needs. By the end of this guide, your Pi will be updated, configured, and ready to connect sensors.

---

## Prerequisites

Before you begin, make sure you have:

- **Raspberry Pi 5** (4GB or 8GB RAM)
- **MicroSD card (32GB+)** or an **NVMe SSD** with a compatible HAT
- **USB-C power supply (27W)** -- the official Pi 5 PSU is recommended
- **Monitor and keyboard** for initial setup (or a way to SSH in)
- **Wi-Fi network** name and password (or an Ethernet cable)
- A computer to flash the OS image

> **Note:** While a 32GB microSD card works fine for getting started, an NVMe SSD will give you significantly better performance for day-to-day use. You can always migrate later.

---

## Step 1: Download Raspberry Pi OS

Head to the official Raspberry Pi website and grab the **Raspberry Pi Imager** for your operating system (Windows, macOS, or Linux).

```
https://www.raspberrypi.com/software/
```

Install and open the Imager. You will use it to both download and flash the OS in one step.

---

## Step 2: Flash the OS

In Raspberry Pi Imager:

1. Click **Choose Device** and select **Raspberry Pi 5**.
2. Click **Choose OS** and select **Raspberry Pi OS (64-bit)** -- make sure it says Bookworm or later.
3. Click **Choose Storage** and select your microSD card or NVMe SSD.

Before you click Write, click the **gear icon** (or press Ctrl+Shift+X) to open the advanced options. This saves you a lot of manual setup later.

### Recommended settings

| Setting | Value |
|---------|-------|
| **Hostname** | `sensorhead.local` (or whatever you prefer) |
| **Enable SSH** | Yes -- use password authentication |
| **Username** | `hailo` (or your preferred username) |
| **Password** | Something strong you will remember |
| **Wi-Fi SSID** | Your network name |
| **Wi-Fi Password** | Your network password |
| **Wi-Fi Country** | Your country code (e.g., US, GB, DE) |
| **Locale** | Your timezone and keyboard layout |

Click **Save**, then **Write**. The Imager will download the OS, write it to your storage, and verify the image. This typically takes 5-10 minutes depending on your internet speed.

> **Tip:** If you are using an NVMe SSD, you may need to update the Pi 5 bootloader to boot from NVMe. The Raspberry Pi Imager can do this too -- look under "Misc utility images" for the bootloader update.

---

## Step 3: First Boot

1. Insert the flashed microSD card (or attach the NVMe SSD) to your Pi 5.
2. Connect your monitor and keyboard if you are doing a desktop setup.
3. Plug in the USB-C power supply.

The Pi will boot for the first time. This initial boot takes a bit longer than usual as the system expands the filesystem and applies your configuration. Give it a minute or two.

**If you configured SSH in the Imager**, you can skip the monitor entirely and connect from another computer:

```bash
ssh hailo@sensorhead.local
```

If `.local` hostname resolution does not work on your network, find the Pi's IP address from your router's admin page and connect directly:

```bash
ssh hailo@192.168.0.XXX
```

---

## Step 4: Update the System

Once you are logged in (either via desktop terminal or SSH), update everything to the latest packages:

```bash
sudo apt update && sudo apt upgrade -y
```

This can take several minutes on a fresh install. Let it finish completely before moving on.

> **Tip:** If the upgrade asks you about keeping or replacing configuration files, the default choice (keep the current version) is usually the right one.

---

## Step 5: Enable Interfaces

SensorHead uses I2C for its environmental sensors and the camera interface for the AI camera. You need to enable both.

Open the Raspberry Pi configuration tool:

```bash
sudo raspi-config
```

Navigate through the menus:

1. Select **Interface Options**
2. Select **I2C** and choose **Yes** to enable it
3. Go back to **Interface Options**
4. Select **Camera** (or **Legacy Camera** depending on your version) and choose **Yes** to enable it

> **Note:** On newer versions of Raspberry Pi OS, the camera stack uses `libcamera` by default and may not show a separate "Camera" toggle. That is fine -- `libcamera` is already enabled. You only need to ensure I2C is turned on.

Exit raspi-config. It will ask if you want to reboot -- say **No** for now. We have one more step.

---

## Step 6: Add Your User to Hardware Groups

Your user account needs permission to access I2C, the camera, and GPIO pins. Run this command:

```bash
sudo usermod -aG i2c,video,gpio $USER
```

This adds your current user to three groups:

- **i2c** -- access to I2C bus (environmental sensors like the BME688)
- **video** -- access to camera devices
- **gpio** -- access to GPIO pins (for future hardware expansions)

---

## Step 7: Reboot and Verify

Now reboot to apply all the changes:

```bash
sudo reboot
```

Wait about 30 seconds, then log back in. Run these two verification commands:

### Check I2C

```bash
i2cdetect -y 1
```

You should see a grid of dashes with no errors. If you already have sensors connected (like the BME688), you will see their addresses show up as hex numbers in the grid. The BME688 typically appears at address `0x76` or `0x77`.

If you get a "command not found" error, install the I2C tools:

```bash
sudo apt install -y i2c-tools
```

### Check Camera

```bash
libcamera-hello --list-cameras
```

This lists any connected cameras. If no camera is physically attached yet, it will report zero cameras found -- that is expected. If you have the IMX500 AI Camera connected, you should see it listed with its resolution and format details.

> **Note:** If `libcamera-hello` is not found, install it with `sudo apt install -y libcamera-apps`.

---

## Troubleshooting

**"Permission denied" on I2C or camera commands**
Make sure you rebooted after adding your user to the groups. The group changes only take effect after a new login session.

**Wi-Fi not connecting**
Double-check your Wi-Fi country code in raspi-config under Localisation Options. An incorrect country code can prevent Wi-Fi from working due to regulatory restrictions.

**SSH connection refused**
Ensure SSH is enabled. You can re-enable it by placing an empty file named `ssh` (no extension) in the boot partition of your SD card from another computer.

**Very slow performance on microSD**
This is normal for budget SD cards. Consider upgrading to an A2-rated card or migrating to NVMe for a dramatically better experience.

---

## What You Have Now

Your Raspberry Pi 5 is:

- Running the latest 64-bit Raspberry Pi OS
- Connected to your network via Wi-Fi or Ethernet
- Accessible over SSH
- Configured with I2C and camera interfaces enabled
- Ready to connect SensorHead hardware

---

## What's Next

In the next guide, you will install the ApexPocket app on your phone and pair it with your SensorHead.

--> [02 - Pair Your Phone](./02-pair-your-phone.md)
