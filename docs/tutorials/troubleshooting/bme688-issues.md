# BME688 Not Detected

**Estimated reading time: 5 minutes**

When environmental sensor readings fail or the BME688 is not showing up on the I2C bus, work through this decision tree from top to bottom.

---

## Step 1: Is I2C Enabled?

Check if the I2C interface is turned on:

```bash
sudo raspi-config nonint get_i2c
```

- **Returns 0** -- I2C is enabled, proceed to Step 2.
- **Returns 1** -- I2C is disabled. Enable it:

  ```bash
  sudo raspi-config nonint do_i2c 0
  ```

  Reboot for the change to take effect:

  ```bash
  sudo reboot
  ```

---

## Step 2: Scan the I2C Bus

```bash
i2cdetect -y 1
```

If `i2cdetect` is not found, install it first:

```bash
sudo apt install -y i2c-tools
```

Look at the output grid for these addresses:

- **0x77 visible** -- BME688 detected at the primary SensorHead address. The hardware is connected correctly. Proceed to Step 5 (software issue).
- **0x76 visible** -- BME688 detected at the alternate address. The sensor works but may need a configuration update. See Step 2a.
- **0x33 visible** -- this is the MLX90640 thermal sensor, not the BME688. Keep looking.
- **No BME688 address visible (neither 0x76 nor 0x77)** -- wiring issue. Proceed to Step 3.

### Step 2a: Alternate Address (0x76)

The SensorHead code expects the BME688 at `0x77` by default (the `bme688_addr_alt` field in `config.py`). If your sensor is at `0x76`, the code will try both addresses automatically during fallback mode. In BSEC mode, it connects directly to `0x77`.

If your sensor is at `0x76` and BSEC initialization fails, you may need to change the SDO pin on your breakout board. On most BME688 breakouts:

- **SDO connected to VCC (or floating)** = address `0x77`
- **SDO connected to GND** = address `0x76`

Check your breakout board documentation for the SDO jumper.

---

## Step 3: Check Physical Wiring

The BME688 connects via I2C. These are the required connections:

| BME688 Pin | Pi GPIO | Physical Pin |
|-----------|---------|-------------|
| SDA | GPIO2 | Pin 3 |
| SCL | GPIO3 | Pin 5 |
| VIN | 3.3V | Pin 1 or Pin 17 |
| GND | GND | Pin 6, 9, 14, 20, 25, 30, 34, or 39 |

> **Warning:** GPIO2 and GPIO3 are the **only** I2C1 bus pins on the Raspberry Pi. No other GPIO pins will work for I2C without software I2C configuration.

Common wiring problems:

- **Loose jumper wires** -- reseat every connection. Breadboard contacts wear out over time.
- **Wrong pins** -- double-check against the Pi's GPIO pinout diagram. Pin numbering is easy to get wrong.
- **3.3V vs 5V** -- the BME688 works with either, but some breakout boards have onboard voltage regulators that prefer 5V. Check your board's documentation.
- **Qwiic/STEMMA QT cables** -- if using these connectors, make sure the cable is not reversed (some cables have different colored wires at each end).

After fixing wiring, re-run the I2C scan:

```bash
i2cdetect -y 1
```

---

## Step 4: Check User Permissions

Your user must be in the `i2c` group to access the I2C bus without root:

```bash
groups $USER | grep i2c
```

If `i2c` does not appear in the output:

```bash
sudo usermod -aG i2c $USER
```

You must log out and back in (or reboot) for the group change to take effect. Running `i2cdetect` with `sudo` works as a quick test, but the SensorHead bridge runs as your user, so proper group membership is required.

---

## Step 5: Check the BSEC2 Python Bindings

The BME688 is most useful with Bosch's BSEC2 signal processing library, which provides IAQ (Indoor Air Quality) scoring. Test if the bindings are installed:

```bash
source ~/claude-root/SensorHead/venv/bin/activate
python3 -c "import bme68x; print('bme68x OK')"
python3 -c "import bme68xConstants; print('constants OK')"
python3 -c "import bsecConstants; print('bsec OK')"
```

- **All three print OK** -- BSEC is installed. Proceed to Step 6.
- **ImportError on bme68x** -- the BSEC2 Python bindings are not built. Rebuild them:

  ```bash
  cd ~/claude-root/SensorHead/bme68x-build
  source ~/claude-root/SensorHead/venv/bin/activate
  BSEC2=64 python3 setup.py bdist_egg
  pip install dist/bme68x-*.egg
  ```

  > **Note:** The `BSEC2=64` environment variable tells the build system to link against the 64-bit BSEC library. This is required for 64-bit Raspberry Pi OS.

- **Build errors about missing BSEC library** -- make sure the BSEC SDK files exist:

  ```bash
  ls ~/claude-root/SensorHead/BOSCH_SOFTWARE/algo/bsec_IAQ_Sel/
  ```

  If this directory is empty, you need to download the Bosch BSEC 2.6.1.0 SDK and extract it here.

If BSEC cannot be built, the bridge will fall back to raw mode automatically. Raw mode provides temperature, humidity, pressure, and gas resistance but not IAQ scoring.

---

## Step 6: Check Calibration State

The BSEC algorithm maintains a calibration state that improves over time. Check if it exists:

```bash
cat ~/claude-root/SensorHead/data/bsec_state.json
```

- **File exists with state data** -- calibration is preserved. The `iaq_accuracy` field shows the last known accuracy level (0-3).
- **File not found** -- BSEC will start fresh calibration from scratch. This is normal on first run. The sensor needs approximately:
  - **5 minutes** to reach accuracy 0 (stabilizing)
  - **30 minutes** to reach accuracy 1 (uncertain)
  - **Several hours** to reach accuracy 2 (calibrating)
  - **~48 hours** to reach accuracy 3 (fully calibrated)

  Calibration state is saved automatically every 5 minutes to preserve progress across reboots.

---

## Step 7: IAQ Reads 25 or 0

If the IAQ value is stuck at 25 (or 0) and the accuracy shows 0:

- This is **normal behavior** during the initial warm-up period.
- The BME688's MOX (metal oxide) gas sensor needs time to heat up and stabilize.
- BSEC requires exposure to both clean and polluted air to calibrate properly.
- Wait for the `iaq_accuracy` field to reach at least 1 before trusting IAQ values.

To check the current accuracy in real time:

```bash
journalctl -u sensorhead-bridge -f --no-pager | grep -i "iaq\|accuracy\|bsec"
```

> **Tip:** To speed up calibration, periodically expose the sensor to fresh outdoor air (open a window near it) and then let it experience normal indoor air. The contrast helps BSEC learn the baseline faster.

---

## Still Not Working?

1. Try the raw fallback explicitly: if BSEC fails, the bridge code automatically tries `adafruit_bme680`. Install it in the SensorHead venv:

   ```bash
   pip install adafruit-circuitpython-bme680
   ```

2. Check for I2C bus contention: if you have multiple I2C devices and reads fail intermittently, the issue may be bus speed. The default 100kHz should work for all devices. Check:

   ```bash
   grep i2c_arm_baudrate /boot/firmware/config.txt
   ```

   If set to 400000 (for the MLX90640), the BME688 should still work -- but if you see issues, try removing the baudrate override and rebooting.

3. Test with a simple I2C read to confirm the device responds:

   ```bash
   i2cget -y 1 0x77 0xD0
   ```

   This reads the chip ID register. A working BME688 returns `0x61`.
