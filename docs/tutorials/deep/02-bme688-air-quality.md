# BME688 Air Quality

**Estimated reading time: 14 minutes**

The BME688 is Bosch's environmental sensor that measures temperature, humidity, barometric pressure, and volatile organic compounds (VOCs) through a metal oxide (MOX) gas sensor. Combined with the BSEC2 signal processing library, it provides an Indoor Air Quality (IAQ) index, CO2 equivalent estimation, breath VOC detection, and AI-powered gas classification.

This guide explains what each measurement means, how BSEC calibration works, and how to interpret the data in practice.

---

## What the BME688 Measures

The sensor has four physical measurement channels:

| Channel | What It Measures | Unit | Typical Indoor Range |
|---------|-----------------|------|---------------------|
| Temperature | Air temperature | degrees C | 18-28 |
| Humidity | Relative humidity | % RH | 30-60 |
| Pressure | Barometric pressure | hPa | 980-1040 |
| Gas Resistance | MOX sensor resistance | Ohms | 10k-500k |

The gas resistance channel is the most interesting. The MOX sensor has a heated metal oxide surface that reacts with volatile organic compounds in the air. When VOCs are present, the resistance drops. Clean air produces high resistance; polluted air produces low resistance.

Raw gas resistance by itself is hard to interpret because it varies with temperature, humidity, and the sensor's own history. This is where BSEC comes in.

---

## What BSEC2 Adds

BSEC (Bosch Sensortec Environmental Cluster) is a proprietary signal processing library that transforms raw sensor data into meaningful air quality metrics. The SensorHead uses BSEC 2.6.1.0, the latest version for the BME688.

BSEC provides these additional outputs:

| Output | Unit | Description |
|--------|------|------------|
| IAQ (Indoor Air Quality) | 0-500 | Composite air quality index |
| Static IAQ | 0-500 | IAQ variant for stationary sensors |
| CO2 Equivalent | ppm | Estimated CO2 based on VOC correlation |
| Breath VOC Equivalent | ppm | Estimated breath-related VOCs |
| Gas Percentage | 0-100% | AI gas classification confidence |
| Compensated Temperature | degrees C | Temperature corrected for self-heating |
| Compensated Humidity | % RH | Humidity corrected for temperature offset |
| IAQ Accuracy | 0-3 | Calibration quality indicator |

### Compensated vs. Raw Values

The BME688's gas heater generates heat that affects the temperature and humidity readings. BSEC compensates for this self-heating effect. The result:

- **Compensated temperature** reads approximately 3-5 degrees C lower than the raw temperature. This is the correct ambient temperature.
- **Compensated humidity** is adjusted based on the corrected temperature.
- **Raw values** are still available for reference but should not be used for ambient conditions.

> **Note:** The 3-5 degree C offset between raw and compensated temperature is normal and expected. If you compare the BME688 reading with a standalone thermometer, the compensated value should be close. The raw value will always read high.

---

## The IAQ Scale

The IAQ index is the primary air quality metric. It ranges from 0 (best) to 500 (worst), following Bosch's defined quality bands:

| IAQ Range | Quality | Description | Recommended Action |
|-----------|---------|-------------|-------------------|
| 0-50 | Excellent | Clean, fresh air | None needed |
| 51-100 | Good | Acceptable air quality | None needed |
| 101-150 | Lightly Polluted | Sensitive individuals may notice effects | Consider ventilation |
| 151-200 | Moderately Polluted | Increased discomfort likely | Open windows |
| 201-250 | Heavily Polluted | Significant health effects possible | Ventilate immediately |
| 251-350 | Severely Polluted | Health warnings, reduce exposure | Leave the area or purify |
| 351-500 | Extremely Polluted | Emergency conditions | Evacuate, investigate source |

### What Affects IAQ

Common indoor sources that raise IAQ:

- **Cooking**: especially frying, baking, and gas stoves (IAQ can spike to 200+ during active cooking)
- **Cleaning products**: sprays, bleach, solvents
- **New furniture/paint**: off-gassing formaldehyde and other VOCs
- **People breathing**: CO2 and breath VOCs accumulate in poorly ventilated rooms
- **Candles and incense**: particulate and VOC emissions
- **Adhesives and glues**: strong VOC sources
- **Pets**: dander and biological VOCs

Common sources that improve IAQ:

- **Opening windows**: fresh air exchange reduces VOC buildup
- **Running an air purifier**: removes particulates and some VOCs
- **Plants**: some species absorb specific VOCs (though the effect is modest)

---

## BSEC Calibration Deep Dive

BSEC is not just a formula -- it is a machine learning system that adapts to your specific sensor and environment over time. Understanding calibration is critical to getting accurate readings.

### Accuracy Levels

Every IAQ reading comes with an accuracy indicator (0-3):

| Level | Label | Meaning | Time After Power-On |
|-------|-------|---------|-------------------|
| 0 | Stabilizing | Sensor warming up, readings unreliable | 0-5 minutes |
| 1 | Uncertain | Some calibration data, low confidence | ~30 minutes |
| 2 | Calibrating | Actively learning baseline, improving | Hours |
| 3 | Calibrated | Fully calibrated, readings reliable | ~48 hours |

> **Warning:** Do not trust IAQ values when accuracy is 0. The sensor returns a fixed value (typically 25) during this phase. Wait for accuracy 1 or higher before using IAQ for any decisions.

### How Calibration Works

BSEC calibration is fundamentally about learning the "clean air baseline" for your specific sensor in your specific environment. The algorithm needs to observe:

1. **Clean air**: the lowest VOC levels your environment experiences (typically with windows open or in the morning before activity)
2. **Polluted air**: elevated VOC levels from normal activity (cooking, people present, etc.)

The contrast between these two states is what allows BSEC to calculate a meaningful IAQ index. If the sensor only ever sees the same air quality, it has nothing to compare against and calibration stalls.

### Calibration Tips

- **Do not seal the sensor in an enclosure** during initial calibration. It needs air circulation.
- **Open a window** near the sensor at least once during the first 48 hours. This gives BSEC a "clean air" reference point.
- **Normal daily activity** (cooking, cleaning, people coming and going) naturally provides the "polluted air" reference.
- **Do not move the sensor** between very different environments during calibration. Let it settle in one location.

### State Persistence

BSEC calibration state is saved to disk every 5 minutes (configurable via `bsec_save_interval` in config):

```
~/claude-root/SensorHead/data/bsec_state.json
```

This file contains:

```json
{
  "state": [/* binary state array */],
  "saved_at": 1739000000.0,
  "iaq_accuracy": 3,
  "bsec_version": "2.6.1.0"
}
```

State persistence means:

- **Rebooting** does not lose calibration. The bridge restores the saved state on startup.
- **Power outages** lose at most 5 minutes of calibration progress.
- **Deleting the state file** resets calibration to zero. Only do this if you intentionally want to recalibrate (e.g., after moving the sensor to a new building).

> **Tip:** After reaching accuracy 3 for the first time, back up the state file. If something goes wrong, you can restore it instead of waiting 48 hours again.

---

## CO2 Equivalent

The `co2_equivalent_ppm` output is an **estimation**, not a direct measurement. The BME688 does not have a CO2 sensor. Instead, BSEC correlates the VOC pattern with typical CO2 levels based on the observation that indoor CO2 and VOC concentrations often track together (both rise when people are in a room and ventilation is poor).

| CO2 Equivalent | Typical Meaning |
|----------------|----------------|
| 400-600 ppm | Fresh air / well-ventilated |
| 600-1000 ppm | Occupied room, acceptable |
| 1000-2000 ppm | Stuffy, ventilation recommended |
| 2000+ ppm | Poor ventilation, cognitive effects possible |

### Limitations

- CO2 equivalent is **useful for trends**, not absolute values. If the number is rising, air quality is declining.
- **Cooking and cleaning** will spike the CO2 equivalent even though actual CO2 has not changed. The VOC spike is real; the CO2 label is misleading in these cases.
- For true CO2 measurement, you need a dedicated NDIR (Non-Dispersive Infrared) CO2 sensor like the SCD40 or MH-Z19B.

The `co2_accuracy` field follows the same 0-3 scale as IAQ accuracy.

---

## Breath VOC Equivalent

The `breath_voc_ppm` output estimates volatile organic compounds associated with human respiration. This metric rises when people are present in a room, especially in poorly ventilated spaces.

Practical uses:

- **Occupancy estimation**: rising breath VOC in a room suggests people are present.
- **Ventilation adequacy**: if breath VOC stays elevated, the room needs more fresh air.
- **Meeting room air quality**: track how air quality degrades during long meetings.

The values are very small (typically 0.1-5.0 ppm range), so the reading includes four decimal places for precision.

---

## Gas Resistance

The raw `gas_resistance_ohm` value is the electrical resistance of the MOX sensor element. This is the most direct measurement the sensor provides:

- **Higher resistance = cleaner air** (fewer reactive molecules on the sensor surface)
- **Lower resistance = more VOCs present**

Typical values:

| Resistance | Air Quality |
|-----------|------------|
| 200k-500k Ohms | Very clean air |
| 50k-200k Ohms | Normal indoor air |
| 10k-50k Ohms | Elevated VOCs |
| Under 10k Ohms | Heavy VOC contamination |

Gas resistance is useful as a raw signal when BSEC is not available (raw fallback mode) or when you want to build your own analysis on top of the raw data. It varies significantly with temperature and humidity, so comparing values across different conditions requires normalization.

---

## BSEC Configuration Profiles

The SensorHead uses BSEC in Low Power (LP) mode with a 3-second sample interval. The BOSCH_SOFTWARE directory contains multiple BSEC configuration profiles:

```
~/claude-root/SensorHead/BOSCH_SOFTWARE/algo/bsec_IAQ_Sel/config/bme688/
```

Profile naming convention: `bme688_[sel|reg]_[voltage]_[interval]_[days]`

| Profile | Heater Voltage | Sample Interval | Calibration Days |
|---------|---------------|-----------------|-----------------|
| `bme688_sel_18v_3s_4d` | 1.8V | 3 seconds | 4 days |
| `bme688_sel_18v_300s_4d` | 1.8V | 300 seconds (5 min) | 4 days |
| `bme688_sel_18v_3s_28d` | 1.8V | 3 seconds | 28 days |
| `bme688_sel_33v_3s_4d` | 3.3V | 3 seconds | 4 days |
| `bme688_sel_33v_300s_4d` | 3.3V | 300 seconds | 4 days |

The SensorHead default (`BSEC_SAMPLE_RATE_LP`) corresponds to the 3-second interval profile. For battery-powered applications, the 300-second profile uses significantly less power but responds much slower to air quality changes.

---

## Practical Use Cases

### Cooking Detection

The BME688 reliably detects cooking activity. IAQ typically rises from baseline (30-60) to 150-300 during active cooking, especially frying. The rise begins within 1-2 minutes of starting to cook and takes 15-30 minutes to return to baseline after cooking ends (depending on ventilation).

### Window Open/Closed Detection

When a window is opened, you will typically see:

- Temperature change (toward outdoor temperature)
- Humidity change
- IAQ improvement (fresh air influx)
- Gas resistance increase

The combination of these changes, happening simultaneously, is a strong indicator of a ventilation event.

### 24-Hour Air Quality Trends

Over a full day, IAQ typically follows a pattern:

- **Night (sleeping)**: gradual CO2/VOC buildup in the bedroom, IAQ 50-120
- **Morning**: IAQ improves as people move around and doors open
- **Cooking times**: IAQ spikes to 150-300
- **Afternoon**: steady state, IAQ 40-80 with normal activity
- **Evening**: gradual buildup again as the house closes up

Tracking this pattern over weeks reveals ventilation habits and helps optimize when to open windows.

### Mold Risk Assessment

High humidity (above 70% RH) combined with poor ventilation (elevated IAQ / low gas resistance) over extended periods creates conditions favorable for mold growth. The BME688 can flag this combination:

- Sustained humidity above 65% for more than 6 hours
- IAQ above 150 simultaneously
- Temperature in the 15-25 degrees C range (optimal for mold)

---

## Quick Reference

| Metric | Good | Concerning | Bad |
|--------|------|-----------|-----|
| IAQ | 0-100 | 101-200 | 201+ |
| IAQ Accuracy | 2-3 | 1 | 0 |
| CO2 Equivalent | Under 800 ppm | 800-1500 ppm | 1500+ ppm |
| Humidity | 40-60% | 30-40% or 60-70% | Under 30% or over 70% |
| Gas Resistance | Over 100k Ohms | 50k-100k Ohms | Under 50k Ohms |

| Task | How |
|------|-----|
| Check current readings | "What's the air quality?" in chat |
| View calibration status | Check `iaq_accuracy` field (0-3) |
| Force state save | Bridge saves automatically every 5 minutes |
| Reset calibration | Delete `data/bsec_state.json` and restart bridge |
| Check sensor health | `i2cdetect -y 1` -- look for 0x77 |
| Raw fallback | Automatic if BSEC fails; provides temp/humidity/pressure/gas only |
| State file location | `~/claude-root/SensorHead/data/bsec_state.json` |
| BSEC version check | Shown in sensor status and bridge startup logs |
