# Step 4 — Breadboard circuits (bias networks, IR driver, relay)

**Goal:** build the three small low-voltage circuits the rig needs, on a
breadboard, so they're ready for the sensing chain (Step 5) and the ESP32 (Step 6).

**Reference:** [`../../HARDWARE_CONNECTION.md`](../../HARDWARE_CONNECTION.md)
§6.2 (bias), §11.1 (IR driver), §13.1/§13.3 (relay).

> 🟢 Pure low-voltage assembly. No mains. ⏱️ ~1 hour for all three.

---

## Breadboard basics (30-second primer)

- The **long side rails** (`+` red, `–` blue) run the whole length — use for shared
  **3.3 V/5 V** and **GND**.
- The **short numbered rows** are joined across each row (5 holes), but **broken at
  the centre gap**.

Same row = connected; jump between rows with wires; share power/ground via the rails.

---

## Circuit A — The 1.65 V bias network (×2, for the clamps)

**Why:** the SCT-013 clamp outputs an AC voltage that swings **±** around 0 V. The
ADS1115 only reads **positive** voltages, so we lift it to sit around **1.65 V**.
(§6.1–§6.2) Build **two**: clamp #1 → ADS1115 **A0**, clamp #2 → **A2** (wired in
Step 5).

### Parts (per network, ×2 total)
- 2× **10 kΩ** resistor · 1× **10 µF** electrolytic capacitor · the clamp's 3.5 mm jack

### Wiring
```
  3.3V ──[ 10kΩ ]──┬── (M) midpoint ≈1.65V ──[ 10µF ]── GND
                   │                            (+ leg to M, – stripe leg to GND)
  GND  ──[ 10kΩ ]──┘
                   │
   SCT-013 sleeve ─┴───────────── (M) midpoint node
   SCT-013 tip ────────────────── ADS1115 input (A0 for #1, A2 for #2)  [wired in Step 5]
```

1. Pick an empty row = node **M**.
2. 10 kΩ from **3.3 V rail** → **M**; another 10 kΩ from **M** → **GND rail** (two in
   series → ~1.65 V at M).
3. **10 µF cap**: **+ leg** → **M**, **– (stripe) leg** → **GND**.
4. **SCT-013 sleeve** → **M**; **tip** goes to the ADS1115 in Step 5.
5. Repeat in a second block for clamp #2.

> ⚠️ The electrolytic cap is **polarised** — the stripe leg is **negative** → GND.

**Test now:** with 3.3 V/GND on the rails, a multimeter on node **M** reads
**≈ 1.6–1.7 V**.

---

## Circuit B — IR LED driver (2N2222)

**Why:** an ESP32 GPIO can't drive the IR LED brightly, so the **2N2222** switches
it. (§11.1)

### Parts
- 1× **IR LED** (940 nm) · 1× **2N2222** · 1× **1 kΩ** (base) · 1× **100 Ω** (LED series)

### 2N2222 pinout
Flat face toward you, legs down: **E – B – C** (left → right).

### Wiring
```
  ESP32 GPIO4 ──[ 1kΩ ]── Base (middle leg)

  5V ──[ 100Ω ]── IR LED anode (+, long leg)
                  IR LED cathode (–, flat/short) ── Collector (right leg)

  Emitter (left leg) ── GND
```

**Test now:** trigger it from the ESP32 (Step 6) or the §11.3 demo blink; point a
**phone camera** at the LED — you'll see a faint **purple/white flash** (IR is
invisible to the eye). §11.4

---

## Circuit C — Relay (logic side only, NO mains)

**Why:** the relay cuts the AC-SIM socket — the visible "AC off" moment. Here we
wire only the **logic side**; the mains side waits for Step 7. (§13)

### Logic-side wiring
| Relay module pin | Connect to |
|---|---|
| `VCC` | **5 V** rail |
| `GND` | **GND** rail |
| `IN` | ESP32 **GPIO18** |

> The board has an **HLT active-high/low selector**. The sketch assumes
> **active-LOW** (`IN = LOW` energises). If backwards, flip that jumper or swap
> `acSimOn()`/`acSimOff()` in code.

**Test now (logic only):** from the ESP32 (Step 6), send `{"command":"off"}` /
`{"command":"on"}` — you'll **hear the relay click**. Its **COM/NO/NC** mains
terminals stay **empty** until Step 7.

> ⚠️ Never switch 240 V on the breadboard. The relay's mains side is wired inside
> the enclosure in [Step 7](07_mains_box.md), after inspection.

---

## How these come together later

| Circuit | Feeds | Goes live in |
|---|---|---|
| A — bias ×2 | ADS1115 A0/A2 | [Step 5](05_sensing_chain.md) |
| B — IR driver | ESP32 GPIO4 | [Step 6](06_esp32_bringup.md) |
| C — relay | ESP32 GPIO18 (logic) / AC-SIM (mains) | Step 6 (logic) / [Step 7](07_mains_box.md) (mains) |

---

← Prev: [Step 3 — Install & run on the Pi](03_pi_run.md) ·
Next: [Step 5 — Sensing chain](05_sensing_chain.md) →
