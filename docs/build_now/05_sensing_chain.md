# Step 5 — Sensing chain: ADS1115 ↔ Pi (clamps + voltage)

**Goal:** connect the ADS1115 ADC to the Pi over I²C, feed it the two current
clamps (via the bias networks from Step 4) and the ZMPT101B voltage sensor, and
read **real values** — all at **low voltage**, before any mains.

**Reference:** [`../../HARDWARE_CONNECTION.md`](../../HARDWARE_CONNECTION.md)
§6.3 (clamps), §7 (voltage), §8 (ADC↔Pi), §9 (reading).

> 🟢 Low-voltage only. The clamps and ZMPT are **not** on mains yet — that's Step 7.
> Here you just wire the electronics and confirm the Pi reads them. ⏱️ ~45 min.

---

## Prerequisites

- Pi is set up and running the services (Steps 2–3); I²C enabled.
- The **two bias networks** are built on the breadboard (Step 4).
- You have the **ADS1115**, the **2× SCT-013 clamps** (3.5 mm jacks), and the
  **ZMPT101B** module.

---

## Step 5.1 — Wire the ADS1115 to the Pi (I²C, 4 wires)

Power the Pi **off** first. Then wire per `HARDWARE_CONNECTION.md` §8.1:

| ADS1115 pin | Raspberry Pi pin | Note |
|---|---|---|
| `VDD` | **3.3 V** (pin 1) | ADC full-scale matches the Pi |
| `GND` | **GND** (pin 6) | **common ground for everything** |
| `SCL` | **GPIO3 / SCL1** (pin 5) | I²C clock |
| `SDA` | **GPIO2 / SDA1** (pin 3) | I²C data |
| `ADDR` | **GND** | sets I²C address `0x48` |

> ⚠️ **All grounds tie together** — Pi, ADS1115, the bias networks, and the ZMPT101B
> must share GND, or the readings are meaningless.

## Step 5.2 — Detect it

Power the Pi back on, SSH in, and:

```bash
i2cdetect -y 1
```

✅ You should see **`48`** in the grid. If not, see troubleshooting.

## Step 5.3 — Connect the current clamps (low voltage)

From Step 4 you have two **1.65 V bias networks**. Connect each clamp's 3.5 mm jack
and route the biased output to the ADS1115 (§6.3):

| Clamp | bias node (sleeve) | ADS1115 input (tip) |
|---|---|---|
| SCT-013 **#1** (main) | → 1.65 V midpoint of bias net #1 | **A0** |
| SCT-013 **#2** (AC) | → 1.65 V midpoint of bias net #2 | **A2** |

With no current flowing (clamps not around any wire yet), **A0 and A2 should idle at
~1.65 V**.

## Step 5.4 — Connect & tune the ZMPT101B voltage sensor

The ZMPT101B's **low-voltage side** goes to the ADS1115 (§7.2):

| ZMPT101B pin | Connect to |
|---|---|
| `VCC` | **5 V** (Pi pin 2/4) |
| `GND` | common GND |
| `OUT` | **ADS1115 A1** |

> ⚠️ The ZMPT101B's **mains-side screw terminals stay disconnected** until Step 7.
> Tuning the trimpot meaningfully needs mains, so you'll **finish §7.3 tuning in
> Step 7**. For now just wire the low-voltage side.

## Step 5.5 — Read live values on the Pi

Stop the simulated reader from Step 3.6 (Ctrl+C in session C) and run the **real**
reader (no `--simulate`):

```bash
cd wattseye && source .venv/bin/activate
pip install adafruit-circuitpython-ads1x15      # the Pi-only ADC driver
python -m ML.sensing.ads1115_reader             # real ADC + MQTT
```

With nothing energised you'll see near-zero currents and an untuned voltage — that's
expected. What you're confirming here is that **the Pi talks to the ADS1115 and
publishes `wattseye/power`**. Watch it flow:

```bash
mosquitto_sub -h localhost -t wattseye/power -v
```

✅ Success: a `wattseye/power` message ticks once per second with real (if tiny)
`irms_main`/`irms_ac` and a `vrms` number. Real magnitudes come after **Step 7**
(mains) and **Step 8** (calibration).

---

## Troubleshooting

| Symptom | Fix |
|---|---|
| `i2cdetect` shows nothing | I²C not enabled (`raspi-config`, Step 3.1 + reboot); check SDA/SCL on pins 3/5; check VDD/GND |
| Shows a different address (e.g. `49`) | `ADDR` isn't tied to GND; the code expects `0x48` |
| A0/A2 don't idle near 1.65 V | Bias divider wrong (Step 4); measure the midpoint with a multimeter (~1.65 V) |
| `ModuleNotFoundError: board` / `adafruit_ads1x15` | `pip install adafruit-circuitpython-ads1x15` inside the venv (Pi only) |
| Reader runs but no `wattseye/power` | Mosquitto not running, or run without `--no-mqtt`; check broker (Step 3.2) |

---

← Prev: [Step 4 — Breadboard circuits](04_breadboard_circuits.md) ·
Next: [Step 6 — ESP32 node](06_esp32_bringup.md) →
