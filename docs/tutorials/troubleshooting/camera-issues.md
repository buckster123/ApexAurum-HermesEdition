# Camera Not Working

**Estimated reading time: 6 minutes**

When camera captures fail, images are black, or cameras are not detected at all, work through this decision tree from top to bottom. SensorHead supports two CSI cameras: the **IMX500 AI Camera** (left eye, daylight) and the **IMX708 Wide NoIR** (right eye, night vision).

---

## Step 1: Is the Camera Interface Enabled?

Check the current camera configuration:

```bash
sudo raspi-config nonint get_camera
```

- **Returns 0** -- camera interface is enabled, proceed to Step 2.
- **Returns 1** -- camera interface is disabled. Enable it:

  ```bash
  sudo raspi-config nonint do_camera 0
  ```

  Then reboot:

  ```bash
  sudo reboot
  ```

> **Note:** On recent Raspberry Pi OS (Bookworm), the `libcamera` stack is enabled by default and there may not be a separate camera toggle. If the `get_camera` command returns an error, skip this step -- `libcamera` is already active.

---

## Step 2: Does libcamera Detect the Cameras?

```bash
libcamera-hello --list-cameras
```

Expected output for a full SensorHead (two cameras):

```
Available cameras
-----------------
0 : imx500 [4056x3040 10-bit ...] (/base/...)
1 : imx708_wide_noir [4608x2592 10-bit ...] (/base/...)
```

Possible outcomes:

- **Both cameras listed** -- hardware is fine, proceed to Step 4.
- **Only one camera listed** -- one FPC ribbon cable is disconnected or damaged. See Step 3.
- **"No cameras available!"** -- no cameras detected at all. See Step 3.

---

## Step 3: Check Physical Connections

CSI cameras connect via FPC (Flat Printed Circuit) ribbon cables. The Pi 5 has two CSI/DSI ports.

### FPC Cable Orientation

The cable connector contacts must face **toward the PCB** (down) when inserted. This is the most common cause of camera detection failures.

1. Power off the Pi completely: `sudo poweroff`
2. Gently lift the cable lock lever on each CSI connector.
3. Ensure the ribbon cable is fully seated with the metallic contacts facing the circuit board.
4. Push the lock lever back down firmly.
5. Power the Pi back on and retest with `libcamera-hello --list-cameras`.

### Try Swapping Ports

If only one camera is detected, try swapping the ribbon cables between the two CSI ports. This helps determine whether the issue is the cable, the camera module, or the port:

- **Camera works in both ports** -- the original port's cable was loose.
- **Camera fails in both ports** -- the camera module or its cable may be damaged.
- **Camera works in one port but not the other** -- the FPC cable for the failing port may be damaged.

---

## Step 4: Test a Manual Capture

Try a direct capture to rule out bridge software issues:

```bash
libcamera-still -o /tmp/test.jpg -t 2000 --nopreview
```

- **Success (file created)** -- the camera hardware works. The issue is in the SensorHead bridge software. Proceed to Step 6.
- **Error: "Camera is already in use"** -- another process has locked the camera. See Step 5.
- **Error: "Failed to start camera"** -- check boot configuration (Step 7).
- **Black image** -- the auto-exposure settle time may be too short, or the lens cap is still on. Try a longer timeout:

  ```bash
  libcamera-still -o /tmp/test.jpg -t 5000 --nopreview
  ```

---

## Step 5: Check for Conflicting Processes

Only one process can use a CSI camera at a time. Check what is using the camera:

```bash
sudo fuser /dev/video*
```

If processes are listed, identify them:

```bash
ps -p <PID> -o comm=
```

Common conflicts:

- Another `libcamera` process left running from a previous test
- The SensorHead bridge already has the camera open
- The inference engine (IMX500) holds the camera between detections

To free the camera:

```bash
sudo kill <PID>
```

Or restart the bridge (which properly releases cameras between captures):

```bash
sudo systemctl restart sensorhead-bridge
```

---

## Step 6: Check User Permissions

Your user must be in the `video` group to access cameras:

```bash
groups $USER
```

Look for `video` in the output. If missing:

```bash
sudo usermod -aG video $USER
```

Log out and back in (or reboot) for the change to take effect.

---

## Step 7: Check Boot Configuration

Examine the boot config for camera-related settings:

```bash
grep -E "camera|dtoverlay" /boot/firmware/config.txt
```

You should see:

```
camera_auto_detect=1
```

If this line is missing, add it:

```bash
sudo nano /boot/firmware/config.txt
```

Add `camera_auto_detect=1` at the end of the file. Save and reboot.

> **Warning:** Do not manually add `dtoverlay=imx500` or `dtoverlay=imx708` when `camera_auto_detect=1` is present. Auto-detect handles overlay loading automatically, and manual entries can cause conflicts.

---

## Step 8: Camera-Specific Issues

### IMX500 AI Camera

- **AI models not found**: The inference engine needs model files in `/usr/share/imx500-models/`. If this directory is empty:

  ```bash
  sudo apt install imx500-models
  ```

- **Inference works but capture fails**: The IMX500 cannot run inference and still capture simultaneously. The SensorHead bridge handles this by releasing the inference engine before visual capture. If you are running custom code, call `inference.release()` before capturing.

### IMX708 Wide NoIR

- **Images look purple or pink in daylight**: This is normal. The NoIR camera has no infrared filter, so it picks up infrared light that appears as a purple cast. The NoIR is designed for night/low-light use. In daylight, use the IMX500 instead.

- **Images are overexposed at night with IR illuminator**: Reduce the exposure time or use auto-exposure. The NoIR sensor is very sensitive to infrared illumination.

- **Wide-angle distortion at edges**: The IMX708 Wide has a 120-degree field of view. Some barrel distortion at the edges is normal and expected.

---

## Still Not Working?

1. Try a completely fresh boot: power off, unplug for 10 seconds, power back on.
2. Update system packages: `sudo apt update && sudo apt upgrade -y`
3. Check the kernel ring buffer for hardware errors: `dmesg | grep -i camera`
4. Verify the ribbon cable is not physically damaged (creased, torn contacts, bent pins on the connector).
