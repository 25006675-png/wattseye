# (Optional) IR-learn — capture a real AC remote's OFF code

> ⚠️ **OPTIONAL — only for the *real-AC* demo.** The standard WattsEye demo uses a
> **fan/kettle on the AC-SIM socket** and cuts it with the **relay**, driven by a
> **mock IR pulse** (`USE_REAL_AC false`). That needs **no remote, no Arduino, no
> IR-learn**. Do this **only** if you want to cut a *real* air conditioner.

**Goal:** read the infrared "OFF" signal your real air-conditioner remote sends, so
the ESP32 can replay it (Step 6.8) to turn a real AC off.

**Reference:** [`../../HARDWARE_CONNECTION.md`](../../HARDWARE_CONNECTION.md) §12.
**Sketch:** [`../../firmware/arduino_ir_learn/arduino_ir_learn.ino`](../../firmware/arduino_ir_learn/arduino_ir_learn.ino).

> 🟢 Safe bench task. No Pi, no mains. Just USB + 3 jumper wires + the AC remote.
> ⏱️ ~30 minutes.

---

## What you need

- **Arduino Nano V3** (Type-C / FT232) + USB cable
- **1× VS1838B** IR receiver (small black 3-leg dome)
- **3× female-to-female (F-F) jumper wires** (no breadboard needed)
- Your **real air-conditioner remote**

---

## Step 1 — VS1838B legs

Dome facing you, legs left→right: **OUT – GND – VCC**.

## Step 2 — Wire it (3 F-F jumpers)

Each leg gets its own wire; the VS1838B hangs off the wires (the *wire* reaches, not
the leg).

| VS1838B leg | Arduino Nano pin |
|---|---|
| **OUT** | **D2** |
| **GND** | **GND** (the one next to D2) |
| **VCC** | **3V3** *(or 5V)* — **never `RST`** |

## Step 3 — Arduino IDE + library

- Install **Arduino IDE 2.x** (arduino.cc).
- **Tools → Manage Libraries…**, install **`IRremote`** by **Armin Joachimsmeyer
  (z3t0)** v3.x/4.x. *(Not `IRremoteESP8266` — that's the ESP32 transmit one.)*

## Step 4 — Open the sketch

**File → Open →** `firmware\arduino_ir_learn\arduino_ir_learn.ino`. No edits needed
(`RECV_PIN = 2`).

## Step 5 — Board + port

**Board →** Arduino Nano · **Port →** the new COMx · **Processor →** `ATmega328P`
*(if upload fails, try `ATmega328P (Old Bootloader)`)*.

## Step 6 — Upload, then Serial Monitor @ 115200

You'll see `WattsEye IR learn — point the AC remote and press OFF...`. Point the AC
remote at the dome (~10–20 cm) and press **OFF**.

## Step 7 — Read the result

- **Known protocol:** `Protocol=NEC Address=0x4 Command=0x7 ...` → write down
  Protocol / Address / Command.
- **`UNKNOWN`** (common for inverter ACs): copy the whole **raw timing array**.

## Step 8 — Save it

Paste into `firmware\captured_ir_codes.txt` with the AC brand/model. Then use it in
[Step 6.8](06_esp32_bringup.md#step-68--optional-real-ac-code).

---

## Troubleshooting

| Symptom | Fix |
|---|---|
| Upload "not in sync" | Processor → **ATmega328P (Old Bootloader)**; confirm COM |
| No COM port | Charge-only/bad cable, or missing FTDI driver |
| Blank on button press | VCC↔OUT swapped; press closer; baud = 115200 |
| Always `UNKNOWN` | Normal for inverter ACs — use the raw timing |

---

← Back to [Step 8 — Calibration](08_calibration.md) · [Index](README.md)
