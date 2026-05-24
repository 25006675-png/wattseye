# WattsEye — Hardware Connection Guide (As-Built)

This document explains how to wire and connect **the exact hardware that was
purchased** for WattsEye, step by step, down to individual pins and the code
that reads each sensor. It supersedes the generic bill of materials in
[`plan/02_HARDWARE.md`](plan/02_HARDWARE.md) and
[`plan/09_COMPONENTS_AND_PRICE_ESTIMATION.md`](plan/09_COMPONENTS_AND_PRICE_ESTIMATION.md)
wherever the purchased part differs from what those files assumed.

> ⚡ **This rig connects to 240 V AC mains.** Read [§1 Safety](#1-safety-read-first)
> before touching anything. Do all low-voltage wiring and software first; only
> energise the mains side after a qualified person has checked it.

---

## Contents

1. [Safety (read first)](#1-safety-read-first)
2. [What was bought vs. what the plan assumed](#2-what-was-bought-vs-what-the-plan-assumed)
3. [Full as-built bill of materials](#3-full-as-built-bill-of-materials)
4. [System block diagram](#4-system-block-diagram)
5. [Subsystem A — Mains plug-through box](#5-subsystem-a--mains-plug-through-box)
6. [Subsystem B — Current sensing (SCT-013 30A/1V)](#6-subsystem-b--current-sensing-sct-013-30a1v)
7. [Subsystem C — Voltage sensing (ZMPT101B)](#7-subsystem-c--voltage-sensing-zmpt101b)
8. [Subsystem D — ADC to Raspberry Pi (ADS1115 over I²C)](#8-subsystem-d--adc-to-raspberry-pi-ads1115-over-i²c)
9. [Subsystem E — Reading samples and computing power](#9-subsystem-e--reading-samples-and-computing-power)
10. [Subsystem F — Occupancy (LD2410C mmWave)](#10-subsystem-f--occupancy-ld2410c-mmwave)
11. [Subsystem G — IR transmit (AC cutoff command)](#11-subsystem-g--ir-transmit-ac-cutoff-command)
12. [Subsystem H — IR receive / learn codes (VS1838B)](#12-subsystem-h--ir-receive--learn-codes-vs1838b)
13. [Subsystem I — Relay (live cutoff for the demo)](#13-subsystem-i--relay-live-cutoff-for-the-demo)
14. [End-to-end data flow into the app](#14-end-to-end-data-flow-into-the-app)
15. [Bring-up and test order](#15-bring-up-and-test-order)
16. [Calibration](#16-calibration)
17. [Repo file reference index](#17-repo-file-reference-index)

---

## 1. Safety (read first)

The mains side of this build carries **~240 V AC** (Malaysian single phase). It
can kill. The rules from [`plan/02_HARDWARE.md §3`](plan/02_HARDWARE.md) apply:

- Never work on the rig while the 13 A plug is in the wall socket.
- All mains conductors (live/brown, neutral/blue, earth/green-yellow) live
  **inside a closed enclosure** — the PVC surface boxes and weatherproof
  enclosures you bought. No exposed copper.
- Keep an **inline fuse** in the live conductor before everything else.
- Connect **earth** to every metal part and to the socket earth pin.
- Keep the **mains side physically separated** from the low-voltage electronics
  (ADS1115, Pi, ESP32, breadboards). The only things that cross between them are:
  the **CT clamp** (which never touches copper — it clips *around* the insulated
  live wire) and the **relay contacts**.
- Use the **cable glands (PG9)** for strain relief so cables cannot be pulled loose.
- **Get the wiring inspected by a lecturer, lab technician, or electrician
  before powering on.**

The software, sensor reading, and IR/relay logic can all be tested at low voltage
first. Energise mains last.

---

## 2. What was bought vs. what the plan assumed

Good news: the purchased set **covers the full hybrid architecture** — current,
voltage, ADC, compute, occupancy, IR, and live cutoff. Two things differ from
the plan and change the wiring:

| Topic | Plan assumed | You actually bought | Consequence |
|---|---|---|---|
| CT clamp type | SCT-013-**000** (current output, needs **33 Ω burden resistor**) — see [`plan/02 §6`](plan/02_HARDWARE.md) | SCT-013 **30A/1V** (voltage output, **burden resistor already inside**) | **Do NOT add a 33 Ω burden resistor.** Wiring it would be wrong. You only need the DC-bias midpoint network ([§6](#6-subsystem-b--current-sensing-sct-013-30a1v)). |
| Build style | CT clamps inside a home DB box | A **plug-through "smart socket box"** (13 A plug → fuse → sockets), clamp clips the live wire inside the box | Same electrical idea, simpler and portable for a demo ([§5](#5-subsystem-a--mains-plug-through-box)). |
| mmWave variant | LD2410 | LD2410**C** (compact; UART + a presence GPIO) | Identical role; pinout in [§10](#10-subsystem-f--occupancy-ld2410c-mmwave). |

Everything else maps cleanly onto the plan.

---

## 3. Full as-built bill of materials

Every item from the four order screenshots, grouped by the subsystem it serves.
Quantities are as ordered.

### 3.1 Sensing — current, voltage, ADC

| Part (as listed) | Qty | Role in WattsEye | Connects to |
|---|---:|---|---|
| **SCT-013 Current Transformer Clamp — 30A/1V** | 2 | Clamp #1 main feeder + Clamp #2 dedicated AC branch | ADS1115 A0 / A2 (via bias network) |
| **AC Voltage Sensor Module ZMPT101B (single phase)** | 2 | Mains voltage (Vrms). 1 in use, 1 spare/2nd node | ADS1115 A1 |
| **ADS1115 ADC Module — 4 Channel** | 2 | 16-bit analog→digital for clamps + voltage. 1 in use, 1 spare/2nd node | Raspberry Pi I²C |

### 3.2 Compute / control

| Part | Qty | Role | Notes |
|---|---:|---|---|
| **Raspberry Pi** (implied: Aluminium Heat sink for Rpi 2/3/3B+ ×2, MicroSD 32GB Class10 ×1) | 1 | Main brain: read ADS1115, compute power, run ML, host API | Pi board + USB-C/microUSB PSU not in screenshots — assumed on hand |
| **NodeMCU / ESP32 (ESP-12E / ESP8266) WiFi module** | 1 | IR transmit + occupancy + WiFi link to Pi | See [§10](#10-subsystem-f--occupancy-ld2410c-mmwave), [§11](#11-subsystem-g--ir-transmit-ac-cutoff-command) |
| **Arduino NANO V3 (FT232, ATmega328, Type-C)** | 1 | Optional: IR-learn rig, or relay/IR controller | See [§12](#12-subsystem-h--ir-receive--learn-codes-vs1838b) |

### 3.3 Occupancy + IR + relay

| Part | Qty | Role |
|---|---:|---|
| **LD2410C 24 GHz mmWave human presence radar** | 2 | Room occupancy (empty-room AC trigger, Pillar 2) |
| **IR 940 nm Transmitter LED + VS1838B Receiver (pack)** | ~8 | IR LED transmits AC "off"; VS1838B receives/learns codes |
| **Transistor 2N2222 (NPN)** | 8 | Drives the IR LED (and small-signal switching) |
| **Relay Board Module — 1 Channel, 5V (opto-isolated, HLT active-high/low)** | 1 | Cuts power to the **AC-SIMULATOR** socket on IR/command (demo only) |

### 3.4 Mains build / enclosure / wiring

| Part | Qty | Role |
|---|---:|---|
| **Malaysia SIRIM 13A Fused 3-Pin Plug Top** | 2 | Mains inlet plug(s) for the box |
| **Wayer Elektrik 3-Core Flexible Cable 1.5 mm² (70/0076), pure copper** | 15 m | Mains wiring (live/neutral/earth) inside and to inlet |
| **SIEMENS DELTA Relfa 13A Socket Outlet (single)** | 1 | The **AC-SIMULATOR** outlet (dedicated AC branch) |
| **SIEMENS DELTA Relfa 13A Socket Outlet (twin)** | 1 | General-appliance outlets (general branch) |
| **Fuse Holder (5×20 mm)** | 4 | Inline fuse holders for the live conductor |
| **5×20 mm Glass Fuse — 10A** | 14 | Fuse element (spares included) |
| **PVC Surface Box (3+3)** | 1 | Mounts a socket / houses wiring |
| **PVC Surface Box (3+7)** | 1 | Mounts a socket / houses wiring |
| **Weatherproof PVC Enclosure 8×6×3** | 3 | Houses the mains + clamp + relay safely |
| **Nylon Cable Gland PG9** | 5 | Strain relief where cables enter the boxes |
| **PCT-213 Lever Wire Connector (3-conductor)** | 10 | Safe mains junctions (live/neutral/earth splits) |
| **Quick Wiring Terminal Block CH-2/CH-3 (press type), 2-way** | 2 | Low-current / branch junctions |
| **Quick Wiring Terminal Block CH-2/CH-3 (press type), 3-way** | 2 | Low-current / branch junctions |
| **Heat Shrink Tube 2:1, 5 mm, 5 m** | 1 | Insulating joints |

### 3.5 Prototyping / passives

| Part | Qty | Role |
|---|---:|---|
| **Solderless Breadboard (half size, 400 points)** | 3 | Build bias networks + IR + relay drive without soldering |
| **Component pack — Resistors** | 1 | Bias dividers (10 kΩ), IR LED (~100 Ω), base (~1 kΩ) |
| **Component pack — Ceramic Capacitors** | 1 | Bias-node decoupling, IR timing |
| **Component pack — Electrolytic Capacitors (E-cap) + Potentiometer** | 1 | 10 µF bias decoupling; pot for tuning |
| **Jumper wires — M-M 20 cm / F-F 20 cm / M-F 10 cm** | sets | Module interconnects |

---

## 4. System block diagram

As-built signal flow. Thick lines (`=`) are **mains**; thin lines (`-`) are
low-voltage signals.

```text
                 240V WALL SOCKET
                        ║
                 [13A Fused Plug Top]              ← Subsystem A
                        ║  (LIVE / NEUTRAL / EARTH, 1.5mm² 3-core)
                 [5×20mm Fuse Holder + 10A fuse]   (inline, LIVE)
                        ║
        SCT-013 #1 clips around LIVE here ─────────┐  ← Subsystem B (main)
                        ║                          │
                 [PCT-213 junction = mini DB]      │
                 ╠════════════════════╗            │
            GENERAL branch         AC branch       │
                 ║                     ║            │
                 ║         SCT-013 #2 clips LIVE ───┤  ← Subsystem B (AC)
                 ║                     ║            │
                 ║              [RELAY NO contact]  │   ← Subsystem I (demo cutoff)
                 ║                     ║            │
          [SIEMENS twin       [SIEMENS single      │
           socket]             socket = AC-SIM]    │
                                                   │
      ZMPT101B across LIVE-NEUTRAL ────────────────┤  ← Subsystem C (voltage)
                                                   │
                                                   ▼
                                    ┌──────── ADS1115 ────────┐ ← Subsystem D
                                    │ A0 = main current        │
                                    │ A1 = voltage             │
                                    │ A2 = AC current          │
                                    │ A3 = spare               │
                                    └──── I²C (SDA/SCL) ───────┘
                                                   │
                                          RASPBERRY PI         ← Subsystem E
                                   reads samples → power_math →
                                   ML insights → backend API
                                                   │ WiFi
                                                   ▼
                  ESP32  ── IR LED (2N2222) ──▶ AC unit / VS1838B   ← Subsystems G/H
                    │
                    └── LD2410C presence ──▶ occupancy             ← Subsystem F
```

The relationship to the product story (whole-home clamp + dedicated AC clamp) is
the same as [`README.md`](README.md) and [`plan/01_SYSTEM_CONNECTION.md`](plan/01_SYSTEM_CONNECTION.md);
only the physical housing (a portable plug-through box) differs.

---

## 5. Subsystem A — Mains plug-through box

This is the safe enclosure that turns one wall socket into a measured
"mini distribution board" with two branches: **general** and **AC-simulator**.
It mirrors [`plan/02_HARDWARE.md §15`](plan/02_HARDWARE.md), built from your
actual SIEMENS sockets, fuse holders, PVC boxes, glands, and PCT connectors.

### 5.1 Wiring order (live conductor, brown)

```text
13A plug LIVE pin
   → 1.5mm² brown wire (through PG9 gland into enclosure)
   → 5×20mm fuse holder (10A fuse)
   → [SCT-013 #1 clips around this wire]        (main / whole-home current)
   → PCT-213 3-way connector  ── the "split point"
        ├─→ GENERAL branch live → SIEMENS twin socket L
        └─→ AC branch live
               → [SCT-013 #2 clips around this wire]   (dedicated AC current)
               → RELAY common (COM)        (see §13)
               → RELAY normally-open (NO)  → SIEMENS single socket L  (AC-SIM)
```

### 5.2 Neutral (blue) and earth (green/yellow)

- **Neutral**: plug N → PCT-213 3-way → both sockets' N terminals. The ZMPT101B
  also taps neutral here (see [§7](#7-subsystem-c--voltage-sensing-zmpt101b)).
- **Earth**: plug E → PCT-213 3-way → both sockets' E terminals → and bond any
  metal. Earth is **never** switched or fused.

### 5.3 Build steps

1. Mount the SIEMENS **twin** socket in the **3+7 PVC box** (general branch) and
   the SIEMENS **single** socket in the **3+3 PVC box** (AC-SIM branch). Label the
   single one **"AC SIMULATOR"** with tape.
2. Mount the fuse holder, both SCT-013 clamps, the PCT-213 junctions, and the
   relay inside a **weatherproof 8×6×3 enclosure** (the "mini DB").
3. Route the inlet cable from the **13A fused plug top** through a **PG9 gland**
   into the enclosure. Fit a 10 A fuse in the holder.
4. Wire live → fuse → (clamp #1) → PCT split → branches, per §5.1. Wire neutral
   and earth per §5.2. Use PCT-213 levers for every mains junction; insulate any
   exposed strand with heat shrink.
5. Clip **SCT-013 #1** around the **single live wire** just after the fuse
   (not live+neutral together — see [`plan/02 §17 Mistake 1`](plan/02_HARDWARE.md)).
6. Clip **SCT-013 #2** around the **AC-branch live wire** only.
7. Leave the relay contacts open for now (relay wired but logic unpowered).
8. Bring the three **3.5 mm clamp jacks** and the **ZMPT101B sensor wires** out
   through another gland to the low-voltage area. **Do not** route mains to the
   breadboard.
9. **Inspection before power.** Then energise.

> Demo loads: plug a **kettle** into the general (twin) socket and a **hair dryer**
> into the AC-SIM socket as the AC proxy — same as [`plan/06_DEMO_PLAN.md`](plan/06_DEMO_PLAN.md).

---

## 6. Subsystem B — Current sensing (SCT-013 30A/1V)

### 6.1 Why your clamp is wired differently from the plan

The **30A/1V** SCT-013 has a **built-in burden resistor**. It outputs a
**voltage** that swings **±1 V (RMS) at 30 A** — i.e. ≈ ±1.414 V peak at full
scale. The current-output SCT-013-000 in [`plan/02 §6`](plan/02_HARDWARE.md)
would need an external 33 Ω burden resistor; **yours does not — skip that
resistor entirely.** Adding one would load the output and corrupt readings.

What you still need: an AC signal centred on **0 V** can't be read by the ADS1115
(it only reads positive voltages), so you bias it to a **~1.65 V midpoint** so the
sine wobbles around 1.65 V instead of 0 V (concept = [`plan/02 §7-8`](plan/02_HARDWARE.md)).

Full-scale check: 1.65 V ± 1.414 V → 0.24 V … 3.06 V, comfortably inside the
ADS1115's 0–3.3 V single-ended range. Good headroom; no divider needed.

### 6.2 Bias network (build once per clamp, on the breadboard)

The SCT-013 3.5 mm jack has two conductors: **tip** and **sleeve**.

```text
3.3V ──[ 10kΩ ]──┬── 1.65V midpoint node ──[ 10µF ]── GND
                 │
GND  ──[ 10kΩ ]──┘
                 │
   SCT-013 sleeve ───────────── 1.65V midpoint node
   SCT-013 tip    ───────────── ADS1115 analog input (A0 for main, A2 for AC)
```

- Two **10 kΩ** resistors form the 1.65 V divider (from the resistor pack).
- One **10 µF** electrolytic (E-cap pack) stabilises the midpoint.
- Build **two identical** networks: clamp #1 → **A0**, clamp #2 → **A2**.

### 6.3 Connections summary

| SCT-013 #1 (main) | → | ADS1115 A0 (tip), 1.65 V node (sleeve) |
| SCT-013 #2 (AC) | → | ADS1115 A2 (tip), 1.65 V node (sleeve) |

The software removes the 1.65 V offset in firmware with `rms_centered()` in
[`ML/sensing/power_math.py`](ML/sensing/power_math.py) — so a small bias error is
harmless, but keep the divider close to 1.65 V.

---

## 7. Subsystem C — Voltage sensing (ZMPT101B)

The ZMPT101B safely scales 240 V mains down to a small signal so we can compute
`Power = Vrms × Irms` ([`plan/02 §10`](plan/02_HARDWARE.md)).

### 7.1 Mains side (inside the enclosure)

- The module has two screw terminals for the **mains sample**. Connect them
  **across LIVE and NEUTRAL** after the fuse (tap the PCT-213 junctions).
- This is mains voltage — keep it inside the enclosure, insulated.

### 7.2 Low-voltage side (to the ADS1115)

| ZMPT101B pin | Connect to |
|---|---|
| `VCC` | **5 V** (Pi pin 2/4) — module runs best at 5 V |
| `GND` | Common GND |
| `OUT` | **ADS1115 A1** |

### 7.3 Critical: tune the onboard trimpot

The ZMPT101B has a blue multi-turn **potentiometer** that sets output gain and
offset. Because VCC is 5 V but the ADS1115 reads up to 3.3 V:

1. With mains connected (after inspection) and the OUT pin on a scope or read
   live via the ADS1115, **turn the trimpot** until the output sine is centred
   around ~1.65 V with peaks staying **below 3.3 V** (aim ≈ 1.65 V ± 1.2 V).
2. If you don't have a scope, read A1 with the script in [§9](#9-subsystem-e--reading-samples-and-computing-power)
   and adjust until `vrms` lands near the expected ~240 V after calibration.

> The 2nd ZMPT101B + 2nd ADS1115 you bought can build an independent second
> measurement node (e.g. a separate room/box) or stay as spares.

---

## 8. Subsystem D — ADC to Raspberry Pi (ADS1115 over I²C)

The Raspberry Pi has **no analog inputs**, so the ADS1115 converts the clamp and
voltage signals to digital over I²C ([`plan/02 §9`](plan/02_HARDWARE.md)).

### 8.1 Wiring (matches plan §9 exactly)

| ADS1115 pin | Raspberry Pi pin | Note |
|---|---|---|
| `VDD` | 3.3 V (pin 1) | Powers the ADC at 3.3 V so its full-scale matches the Pi |
| `GND` | GND (pin 6) | Common ground for **everything** (Pi, ADS, bias nets, ZMPT) |
| `SCL` | GPIO3 / SCL1 (pin 5) | I²C clock |
| `SDA` | GPIO2 / SDA1 (pin 3) | I²C data |
| `ADDR` | GND | Sets I²C address `0x48` |
| `A0` | ← SCT-013 #1 (main current), biased | |
| `A1` | ← ZMPT101B `OUT` (voltage) | |
| `A2` | ← SCT-013 #2 (AC current), biased | |
| `A3` | spare | future 2nd AC / expansion |

> Power the ADS1115 at **3.3 V** but the ZMPT101B at **5 V** (its OUT, tuned by
> the trimpot, must still stay under 3.3 V — see §7.3). All grounds tie together.

### 8.2 Enable I²C on the Pi

```bash
sudo raspi-config        # Interface Options → I2C → Enable
sudo reboot
# verify the ADS1115 appears at 0x48:
sudo apt-get install -y i2c-tools python3-pip
i2cdetect -y 1           # expect "48" in the grid
```

### 8.3 Install the Python driver

```bash
pip3 install adafruit-circuitpython-ads1x15
```

---

## 9. Subsystem E — Reading samples and computing power

The repo already contains the **honest power math** in
[`ML/sensing/power_math.py`](ML/sensing/power_math.py): it computes RMS from a
1-second buffer, then apparent power `S = Vrms × Irms`, then a per-appliance
power-factor correction. See [`ML/sensing/README.md`](ML/sensing/README.md) and
[`plan/02 §10a`](plan/02_HARDWARE.md) for *why* it works this way (the ADS1115's
~250 SPS/channel gives RMS magnitude, not instantaneous real power).

### 9.1 New file to add: a live reader on the Pi

This is the only hardware-specific glue not yet in the repo. Create
`ML/sensing/ads1115_reader.py`:

```python
"""Read SCT-013 + ZMPT101B via ADS1115 and emit a PowerReading once per second.

Wiring (see HARDWARE_CONNECTION.md §6-8):
    A0 = main feeder current (SCT-013 #1, biased to 1.65 V)
    A1 = mains voltage       (ZMPT101B OUT)
    A2 = dedicated AC current(SCT-013 #2, biased to 1.65 V)
"""
from __future__ import annotations

import time
import board
import busio
import adafruit_ads1x15.ads1115 as ADS
from adafruit_ads1x15.analog_in import AnalogIn

from power_math import compute_power_reading, CalibrationConstants

# Calibrate these once against a known kettle (see HARDWARE_CONNECTION.md §16).
CAL = CalibrationConstants(
    voltage_scale=1.00,       # tune so vrms ≈ 240 V on a known load
    main_current_scale=1.00,  # tune so kettle watts match its rating
    ac_current_scale=1.00,
)

# SCT-013 30A/1V scaling: 30 A per 1 V output → 30 A/V.
AMPS_PER_VOLT = 30.0
# ZMPT101B is tuned (trimpot) so 1 V at OUT ≈ this many real volts; refine in cal.
VOLTS_PER_VOLT = 240.0  # placeholder; set during calibration

def main(samples_per_second: int = 250):
    i2c = busio.I2C(board.SCL, board.SDA)
    ads = ADS.ADS1115(i2c, address=0x48)
    ads.data_rate = 860            # fastest; we still net ~250 SPS/ch after mux
    a_main = AnalogIn(ads, ADS.P0)
    a_volt = AnalogIn(ads, ADS.P1)
    a_ac   = AnalogIn(ads, ADS.P2)

    while True:
        v_buf, i_main_buf, i_ac_buf = [], [], []
        t_end = time.time() + 1.0
        while time.time() < t_end:
            # .voltage is in volts at the ADC pin (already 1.65 V-biased).
            v_buf.append(a_volt.voltage * VOLTS_PER_VOLT)
            i_main_buf.append(a_main.voltage * AMPS_PER_VOLT)
            i_ac_buf.append(a_ac.voltage * AMPS_PER_VOLT)

        reading = compute_power_reading(v_buf, i_main_buf, i_ac_buf, CAL)
        # rms_centered() inside compute_power_reading removes the 1.65 V offset.
        print(reading)   # → feed this into the backend (see §14)
        # e.g. publish over MQTT / write to a shared file / POST to the API

if __name__ == "__main__":
    main()
```

Key functions this calls, already in the repo:

- `compute_power_reading(...)` → returns a `PowerReading` with `vrms`,
  `irms_main`, `irms_ac`, `apparent_main_va`, `apparent_ac_va`,
  `apparent_residual_va` — [`ML/sensing/power_math.py:135`](ML/sensing/power_math.py).
- `apparent_to_real_watts(va, appliance)` → applies the PF table to turn VA into
  displayed watts — [`ML/sensing/power_math.py:173`](ML/sensing/power_math.py).
- `real_power_breakdown(...)` → per-appliance watt split (AC branch + NILM
  residual) — [`ML/sensing/power_math.py:183`](ML/sensing/power_math.py).

### 9.2 Sanity-check the math without hardware

```bash
python ML/sensing/power_math.py
```

This runs the built-in 50 Hz synthetic kettle + inverter-AC demo
(`_demo()` at [`ML/sensing/power_math.py:214`](ML/sensing/power_math.py)) so you
can confirm the pipeline before the clamps are even connected.

---

## 10. Subsystem F — Occupancy (LD2410C mmWave)

The LD2410C detects whether the room is occupied — even someone sitting still —
which drives the **empty-room AC** insight (Pillar 2). See
[`plan/02 §13`](plan/02_HARDWARE.md). It runs at 3.3 V logic and gives you **two**
ways to read it.

### 10.1 Pinout

| LD2410C pin | Connect to | Note |
|---|---|---|
| `VCC` | 5 V | module accepts 5 V; logic is 3.3 V |
| `GND` | Common GND | |
| `TX` | MCU RX | UART, **256000 baud** (rich data: distance, energy) |
| `RX` | MCU TX | only needed to *configure* the sensor |
| `OUT` / `OT2` | MCU GPIO | **simple digital**: HIGH = presence, LOW = empty |

### 10.2 Easiest path — digital presence pin to ESP32

Wire `OUT`/`OT2` to an ESP32 GPIO (e.g. GPIO5) and just read HIGH/LOW:

```cpp
const int PRESENCE_PIN = 5;   // LD2410C OUT/OT2

void setup() {
  Serial.begin(115200);
  pinMode(PRESENCE_PIN, INPUT);
}

void loop() {
  bool occupied = digitalRead(PRESENCE_PIN);
  Serial.println(occupied ? "OCCUPIED" : "EMPTY");
  // publish to the Pi over WiFi/MQTT; the empty→AC-on condition fires the alert
  delay(500);
}
```

### 10.3 Richer path — UART

For distance + motion/static energy values, read the UART frames at 256000 baud
with a library such as `ncmreef/LD2410` (Arduino) and forward the parsed state to
the Pi. The occupancy result feeds the empty-room logic in
[`ML/insights/occupancy_engine.py`](ML/insights/occupancy_engine.py) via the
orchestrator ([`ML/insights/insight_orchestrator.py`](ML/insights/insight_orchestrator.py)).

> You bought **2× LD2410C** — one per room if you want multi-room occupancy, or
> one live + one spare.

---

## 11. Subsystem G — IR transmit (AC cutoff command)

The IR LED sends the same kind of signal as the AC's remote. In a **real home**
the AC's own receiver acts on it; on the **demo rig** the VS1838B/relay path acts
on it instead. The hardware is correct as bought — only the firmware payload
changes between demo and real AC ([`plan/02 §14`](plan/02_HARDWARE.md)).

### 11.1 Driver circuit (IR LED + 2N2222)

The ESP32 GPIO is too weak to drive the IR LED brightly, so the 2N2222 switches it:

```text
ESP32 GPIO4 ──[ 1kΩ ]── Base (2N2222)
                         Collector ── IR LED cathode (–)
                         Emitter ──── GND
5V ──[ 100Ω ]── IR LED anode (+)
```

- 1 kΩ base resistor and 100 Ω LED series resistor from the resistor pack.
- 2N2222: flat side facing you, pins are **E – B – C** (left→right).

### 11.2 Firmware — real inverter AC (brand frame)

Use the `IRremoteESP8266` library and the correct brand object
([`plan/02 §14`](plan/02_HARDWARE.md)):

```cpp
#include <IRremoteESP8266.h>
#include <IRsend.h>
#include <ir_Daikin.h>          // swap for ir_Panasonic.h / ir_Midea.h etc.

const uint16_t IR_LED_PIN = 4;  // matches the GPIO above
IRDaikinESP ac(IR_LED_PIN);

void setup() {
  ac.begin();
}

void turnAcOff() {
  ac.off();                     // sets the power bit OFF in the state frame
  ac.send();                    // transmits the full brand-specific frame
}

void loop() {
  // call turnAcOff() when the Pi signals an empty-room event
}
```

### 11.3 Firmware — demo rig (plain carrier)

For the VS1838B + relay demo path, any 38 kHz burst works — no brand code needed:

```cpp
#include <IRsend.h>
IRsend irsend(4);
void setup(){ irsend.begin(); }
void loop(){ irsend.sendNEC(0x00FF02FD, 32); delay(3000); } // any code triggers relay
```

### 11.4 Verify the LED actually fires

Point a **phone camera** at the IR LED — IR shows up as a faint purple/white
glow on most phone cameras ([`plan/02 §16 step 4`](plan/02_HARDWARE.md)).

---

## 12. Subsystem H — IR receive / learn codes (VS1838B)

The VS1838B is a 38 kHz IR **receiver** (same role as the TSOP1838 in the plan).
Two uses:

1. **Learn your real AC remote's "off" frame**, then replay it from the ESP32.
2. **Demo-rig detector**: feed a relay so the cutoff is visible on stage.

### 12.1 Pinout (VS1838B, facing the dome: OUT – GND – VCC)

| VS1838B pin | Connect to |
|---|---|
| `OUT` | MCU input (e.g. Arduino Nano D2 or ESP32 GPIO) |
| `GND` | GND |
| `VCC` | 3.3 V or 5 V |

### 12.2 Capture a remote code (Arduino Nano + IRremote)

```cpp
#include <IRremote.hpp>
const int RECV_PIN = 2;        // VS1838B OUT

void setup() {
  Serial.begin(115200);
  IrReceiver.begin(RECV_PIN, ENABLE_LED_FEEDBACK);
  Serial.println("Point your AC remote and press OFF...");
}

void loop() {
  if (IrReceiver.decode()) {
    IrReceiver.printIRResultShort(&Serial);   // prints protocol + code
    IrReceiver.resume();
  }
}
```

Note the printed protocol/value, then reproduce it from the ESP32 in
[§11](#11-subsystem-g--ir-transmit-ac-cutoff-command). For long inverter-AC
frames, capture the raw timing buffer and replay with `sendRaw()`.

---

## 13. Subsystem I — Relay (live cutoff for the demo)

The 1-channel 5 V relay module physically cuts power to the **AC-SIMULATOR**
socket on command — the visible "the AC turned off" moment. This is **demo-only**;
a real home AC responds to IR directly and needs no relay
([`plan/02 §14a`](plan/02_HARDWARE.md)).

> ✅ This is the correct way to switch mains. **Never** try to switch 240 V with
> the 2N2222 — that transistor is small-signal only (≈40 V / 0.8 A). The relay's
> opto-isolation keeps the mains side away from the logic side.

### 13.1 Logic side

| Relay module pin | Connect to |
|---|---|
| `VCC` | 5 V |
| `GND` | Common GND |
| `IN` | MCU GPIO (ESP32 or Nano) |

Your board has an **HLT active-high/active-low selector** — set it to match your
firmware (most cheap modules are **active-LOW**: `IN = LOW` energises the relay).

### 13.2 Mains side (inside the enclosure, in series with AC-SIM live)

```text
AC branch LIVE  ──▶ Relay COM
Relay NO        ──▶ SIEMENS single socket (AC-SIM) LIVE
(Relay NC unused)
```

So when the relay is **not** energised, NO is open → AC-SIM socket is **off**;
energise to close NO → socket **on**. (Choose NO/NC + active-high/low so the
default state matches what you want during boot.)

### 13.3 Control code (ESP32, active-low example)

```cpp
const int RELAY_IN = 18;
void setup(){ pinMode(RELAY_IN, OUTPUT); digitalWrite(RELAY_IN, HIGH); } // off
void acSimOn()  { digitalWrite(RELAY_IN, LOW);  }   // close NO → power on
void acSimOff() { digitalWrite(RELAY_IN, HIGH); }   // open  NO → power cut
```

### 13.4 Demo chain

`LD2410C says EMPTY` → Pi decides → ESP32 sends IR (§11) → VS1838B detects (§12)
→ ESP32/Nano calls `acSimOff()` → AC-SIM socket dies → both SCT-013 readings for
the AC branch drop to ~0 → dashboard confirms. This is **Milestone 2** in
[`plan/09 §9`](plan/09_COMPONENTS_AND_PRICE_ESTIMATION.md).

---

## 14. End-to-end data flow into the app

The backend currently serves a **demo snapshot**; the hardware replaces it at one
well-marked seam.

- The API the Flutter app consumes is [`backend/api_server.py`](backend/api_server.py).
- The function to replace with live data is **`dashboard_payload()`** at
  [`backend/api_server.py:41`](backend/api_server.py) — the
  [`backend/README.md`](backend/README.md) explicitly says: *"Replace
  `dashboard_payload()` with live Pi sensor/database data when the hardware
  pipeline is ready; keep the JSON keys the same so the Flutter app continues to
  work."*

Wiring the hardware in:

```text
ads1115_reader.py (§9)  →  PowerReading every 1s
        │
        ▼
real_power_breakdown()  →  {ac: W, residual NILM split: W...}   (power_math.py)
        │
        ▼
insight_orchestrator.py →  cost / occupancy / health / routine engines
        │
        ▼
dashboard_payload() in backend/api_server.py  (swap demo snapshot for live values)
        │  GET /api/dashboard  (JSON contract unchanged)
        ▼
Flutter app  (lib/api.dart → DashboardSnapshot)  shows "Live Pi" chip
```

The app already flips its status chip from **"Demo data"** to **"Live Pi"** the
moment `/api/dashboard` returns live values — see `_refreshBackendData()` in
[`wattseye_app/lib/main.dart`](wattseye_app/lib/main.dart) and the typed client
in [`wattseye_app/lib/api.dart`](wattseye_app/lib/api.dart). No app changes are
needed as long as the JSON keys stay the same.

Occupancy and relay/IR events from the ESP32 reach the Pi over WiFi/MQTT and feed
the same orchestrator; the WhatsApp alert path is already wired through
[`backend/api_server.py`](backend/api_server.py) (`/api/whatsapp/send`).

---

## 15. Bring-up and test order

Follow this sequence (expanded from [`plan/02 §16`](plan/02_HARDWARE.md)). Do
**1–6 at low voltage**, mains only after inspection.

1. **Math first, no hardware:** `python ML/sensing/power_math.py` → confirm the
   synthetic kettle/AC numbers look right.
2. **I²C up:** enable I²C, `i2cdetect -y 1` shows `48`.
3. **ADS1115 alone:** read A0–A3 raw; floating inputs should drift, grounded
   should read ~0.
4. **Bias networks:** build the two 1.65 V dividers; confirm A0/A2 idle near
   1.65 V with clamps plugged but no current.
5. **ESP32 + LD2410C:** print OCCUPIED/EMPTY as you enter/leave the room (§10).
6. **IR loop (low voltage):** ESP32 → IR LED, confirm with phone camera (§11.4);
   VS1838B prints a code (§12); relay clicks on command (§13, logic only).
7. **Mains inspection** by a qualified person.
8. **Energise.** General branch test: plug a kettle into the **twin** socket →
   only **A0 (main)** rises, **A2 (AC)** stays ~0.
9. **AC branch test:** plug a hair dryer into the **AC-SIM** socket → **both A0
   and A2** rise.
10. **Live cutoff:** trigger IR → relay opens → AC-SIM dies → A2 → ~0 on the
    dashboard. (Milestone 2.)
11. **Calibrate** (next section).

---

## 16. Calibration

Raw readings won't equal real watts until you calibrate the per-channel scale.
The workflow lives in [`ML/sensing/README.md`](ML/sensing/README.md) and uses
`CalibrationConstants` from [`ML/sensing/power_math.py:36`](ML/sensing/power_math.py):

1. **Voltage:** with the ZMPT101B trimpot set (§7.3), adjust
   `CalibrationConstants.voltage_scale` until `reading.vrms` ≈ 240 V.
2. **Current:** plug a **kettle** (PF ≈ 1.00 by physics) into the general branch.
   Any gap between WattsEye's apparent power and the kettle's rated wattage is
   **sensor scale error** — adjust `main_current_scale` until it matches.
3. Repeat on the AC branch with a known load to set `ac_current_scale`.
4. For non-resistive appliances, record `measured_VA / rated_W` and store it in
   the `APPLIANCE_POWER_FACTORS` table
   ([`ML/sensing/power_math.py:61`](ML/sensing/power_math.py)) so the displayed
   watts are PF-corrected.

Accuracy note ([`plan/02 §10a`](plan/02_HARDWARE.md)): with the ADS1115 you get
accurate watts for **resistive** loads (kettle, hair dryer, iron) and
PF-corrected estimates for inductive/switching loads. For true real power on
inverter ACs, the upgrade path (MCP3008 or PZEM-004T/ADE7953) is documented in
[`ML/sensing/README.md`](ML/sensing/README.md) — **not needed for the demo**.

---

## 17. Repo file reference index

| Topic | File |
|---|---|
| Generic hardware theory (CT clamps, conditioning, safety) | [`plan/02_HARDWARE.md`](plan/02_HARDWARE.md) |
| Budget / BOM the parts were chosen from | [`plan/09_COMPONENTS_AND_PRICE_ESTIMATION.md`](plan/09_COMPONENTS_AND_PRICE_ESTIMATION.md) |
| System connection narrative | [`plan/01_SYSTEM_CONNECTION.md`](plan/01_SYSTEM_CONNECTION.md) |
| Live data flow + PF reasoning (§5) | [`plan/04_LIVE_DATA_FLOW.md`](plan/04_LIVE_DATA_FLOW.md) |
| Demo plan (loads, milestones) | [`plan/06_DEMO_PLAN.md`](plan/06_DEMO_PLAN.md) |
| Power math (RMS, apparent power, PF table, calibration) | [`ML/sensing/power_math.py`](ML/sensing/power_math.py), [`ML/sensing/README.md`](ML/sensing/README.md) |
| Live reader to add on the Pi | `ML/sensing/ads1115_reader.py` (new — see [§9](#9-subsystem-e--reading-samples-and-computing-power)) |
| Insight orchestration | [`ML/insights/insight_orchestrator.py`](ML/insights/insight_orchestrator.py) |
| Occupancy logic | [`ML/insights/occupancy_engine.py`](ML/insights/occupancy_engine.py) |
| Backend API + the seam to replace with live data | [`backend/api_server.py`](backend/api_server.py) (`dashboard_payload()`, line 41), [`backend/README.md`](backend/README.md) |
| Flutter app data layer | [`wattseye_app/lib/api.dart`](wattseye_app/lib/api.dart), [`wattseye_app/lib/main.dart`](wattseye_app/lib/main.dart) |

---

*Mains electricity is dangerous. Build and test the low-voltage and software
parts first, and have the mains wiring checked by a qualified person before
powering on.*
