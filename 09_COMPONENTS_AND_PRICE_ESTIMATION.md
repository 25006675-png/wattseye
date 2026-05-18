# 09 — Components List and Price Estimation

## Purpose of this file

This file helps the team understand **what we need to buy, what we may already have, what quantities are required, and how much the prototype may cost**.

This is not the final shopping list yet. It is a **budget planning file**.

Prices can change depending on seller, shipping, quality, and whether the item is local stock or overseas stock. For the final purchase, we should compare 2–3 sellers before buying.

---

# 1. How this list is organized

Each component has:

- **Quantity** — how many we need
- **Priority** — what feature it supports and whether it is necessary or optional
- **Estimated price range** — based on typical Malaysian retailers (Shopee, Lazada, Cytron, electronic shops)

Priority levels:

- **Necessary — Core sensing**: required for *any* working WattsEye demo
- **Necessary — AC hybrid**: required for the dedicated AC sensing + live cutoff (Pillar 1 validation + Pillar 2)
- **Necessary — Control & occupancy**: required for the empty-room AC alert (Pillar 2)
- **Necessary — Safety & build**: required because the rig uses mains electricity
- **Optional — Polish**: improves reliability or presentation but is not required
- **Optional — Scale**: needed only if expanding past single-AC demo (extra ACs, extra rooms)

---

# 2. Prototype component categories

## A. Core electricity sensing parts

These are needed for the main promise of WattsEye:

> A dedicated AC sensor measures the AC exactly, and a whole-home sensor + AI estimates everything else.

| Component | Qty | Price (RM) | Why we need it | Priority |
|---|---:|---:|---|---|
| CT clamp sensor (SCT-013-030) — Main feeder | 1 | 25–60 | NILM input: whole-home current sensing | Necessary — Core sensing |
| CT clamp sensor (SCT-013-030) — Dedicated AC | 1 | 25–60 | Exact AC measurement on the dedicated AC branch | Necessary — AC hybrid |
| ZMPT101B voltage sensor module | 1 | 10–25 | Measures mains voltage safely for accurate power (V × I) | Necessary — Core sensing |
| ADS1115 ADC module (4-channel) | 1 | 6–25 | Converts both clamps + voltage into digital values | Necessary — Core sensing |
| Burden resistor (~33Ω) | 2 | 1–5 total | One per CT clamp — converts clamp output current to voltage | Necessary — Core sensing + AC hybrid |
| 10kΩ resistors (for voltage divider) | 4–10 | 1–5 total | 2 per CT clamp signal path — creates 1.65V midpoint | Necessary — Core sensing + AC hybrid |
| Capacitor for signal coupling (e.g. 10µF) | 2–4 | 1–5 total | One per CT clamp — DC-blocks the AC signal | Necessary — Core sensing + AC hybrid |

**Subtotal: RM 69–185**

---

## B. Main computing and control parts

These parts run the software, AI model, dashboard, and device control.

| Component | Qty | Price (RM) | Why we need it | Priority |
|---|---:|---:|---|---|
| Raspberry Pi 4 (2GB or 4GB RAM) | 1 | 250–650 | Main brain: sensor reading, ML inference, dashboard, MQTT, Twilio | Necessary — Core sensing |
| Raspberry Pi USB-C 5V 3A power supply | 1 | 25–60 | Stable power for Pi | Necessary — Core sensing |
| MicroSD card 32GB or 64GB | 1 | 20–50 | Stores OS, code, models, logs | Necessary — Core sensing |
| ESP32 dev board | 1 | 8–35 | Reads mmWave, transmits IR commands | Necessary — Control & occupancy |
| USB cable for ESP32 | 1 | 5–15 | Programming + power | Necessary — Control & occupancy |

**Subtotal: RM 308–810**

Note: Raspberry Pi is the most expensive and price-volatile item. If we already have one, the total cost drops significantly.

---

## C. Occupancy and AC-control feature parts

These parts support the empty-room AC alert and IR cutoff (Pillar 2).

| Component | Qty | Price (RM) | Why we need it | Priority |
|---|---:|---:|---|---|
| LD2410 mmWave human presence sensor | 1 | 25–35 | Detects whether the room is occupied (Pillar 2 trigger) | Necessary — Control & occupancy |
| IR LED (transmitter) | 1–3 | 1–5 total | Sends AC remote-control signal | Necessary — Control & occupancy |
| NPN transistor 2N2222 (for IR LED) | 1–3 | 1–5 total | Lets ESP32 drive the IR LED brightly | Necessary — Control & occupancy |
| Resistors for IR transmit circuit (100Ω, 220Ω) | Several | 1–5 total | Protects LED and transistor | Necessary — Control & occupancy |
| **IR receiver module (TSOP1838)** | 1 | 5–10 | Detects the IR signal on the demo rig so the relay can cut power | Necessary — AC hybrid |
| **Relay module (5V single channel, opto-isolated, mains-rated)** | 1 | 15–25 | Actually cuts power to the AC SIMULATOR outlet on IR command | Necessary — AC hybrid |
| **NPN transistor + resistors (drives relay from IR receiver)** | 1 set | 2–5 | Analog path from IR receiver output to relay coil (no MCU needed) | Necessary — AC hybrid |
| Small wires / heat shrink / tape | Some | 5–15 | Keeps IR + relay circuits stable | Optional — Polish |
| Arduino Nano (alternative MCU path for relay control) | 1 | 25–35 | Only if not using the simpler analog receiver-to-relay path | Optional — Polish |

**Subtotal: RM 55–140** (without Arduino Nano)

---

## D. Prototyping and wiring parts

These make the circuit easier to build and test.

| Component | Qty | Price (RM) | Why we need it | Priority |
|---|---:|---:|---|---|
| Breadboard | 1–2 | 1–10 each | Build circuits without soldering | Necessary — Core sensing |
| Jumper wires (set) | 1 set | 5–20 | Connects modules together | Necessary — Core sensing |
| Screw terminal blocks | Several | 5–20 | Safer wire connection inside demo box, used to split bus into general + AC branches | Necessary — Safety & build |
| Small PCB / perfboard | 1 | 5–20 | More stable version after breadboard testing | Optional — Polish |
| Multimeter | 1 | 20–80 | Testing continuity, voltage, wiring safety | Necessary — Safety & build |
| USB keyboard/mouse/HDMI cable for Pi setup | 1 set | 0–50 | Only if not using SSH/headless setup | Optional — Polish |

**Subtotal: RM 36–200**

---

## E. Demo rig and safety parts

These are for the physical demo box. Because this system touches mains electricity, this category matters a lot.

| Component | Qty | Price (RM) | Why we need it | Priority |
|---|---:|---:|---|---|
| Clear plastic enclosure / electrical box | 1 | 20–80 | Holds demo wiring safely and visibly | Necessary — Safety & build |
| Extension socket / outlet bank (general outlets) | 1 | 15–40 | For plugging in general appliances (kettle, lamp, fan, hair dryer) | Necessary — Safety & build |
| Outlet for AC SIMULATOR (single socket, can be from the outlet bank) | 1 | 10–15 | Dedicated outlet on the AC branch | Necessary — AC hybrid |
| 13A plug + power cable | 1 | 10–30 | Power input for demo rig | Necessary — Safety & build |
| Inline fuse holder + 10A fuse | 1 | 5–20 | Protects circuit on fault | Necessary — Safety & build |
| Earth wire + cable lugs | Set | 5–20 | Safety grounding | Necessary — Safety & build |
| Strain relief / cable gland | 1–2 | 3–15 | Prevents cable being pulled loose | Necessary — Safety & build |
| Insulation tape / heat shrink | Some | 5–15 | Covers and protects connections | Necessary — Safety & build |
| Labels / warning stickers (incl. "AC SIMULATOR" outlet label) | Some | 2–10 | Makes the rig safer + clearer to judges | Necessary — Safety & build |

**Subtotal: RM 75–245**

Important: Do not power the demo rig until a lecturer, lab technician, or electrician checks the wiring.

---

## F. Demo appliances

We do not need to buy all of these if the team can borrow them.

| Appliance | Qty | Price (RM if buying) | Purpose | Priority |
|---|---:|---:|---|---|
| Kettle | 1 | 30–100 | Clear high-power on/off pattern (Pillar 1 demo) | Necessary — Core sensing demo |
| Hair dryer | 1 | 30–100 | Use as AC proxy in the AC SIMULATOR outlet (Pillar 2 demo) | Necessary — AC hybrid demo |
| Lamp | 1 | 10–40 | Simple low-power appliance, shown on general branch | Optional — Polish |
| Phone charger | 1 | 0–30 | Small load, shows NILM limitation honestly | Optional — Polish |
| Microwave | 1 | Borrow | Strong appliance signature | Optional — Polish |
| Fan | 1 | 30–100 | Common Malaysian appliance | Optional — Polish |
| Rice cooker | 1 | 50–150 | Asian household relevance | Optional — Polish |
| Portable AC / actual AC | 1 | Borrow only | Not practical for live stage — hair dryer serves as proxy | Optional — Scale |

**Subtotal if buying only essential demo appliances (kettle + hair dryer): RM 60–200**

---

# 3. Total estimated budget

## Tier 1 — Lower-cost build (Raspberry Pi borrowed)

What it includes:

- Both CT clamps + voltage sensor + ADC + signal conditioning
- ESP32 + mmWave + IR transmit
- IR receiver + relay for live AC cutoff
- Safer demo rig with split-bus wiring
- Borrow Raspberry Pi, multimeter, demo appliances

> **Estimated cost: RM 285–595**

## Tier 2 — Full prototype (Raspberry Pi purchased, all parts new)

What it includes:

- Everything in Tier 1
- New Raspberry Pi 4 + power supply + SD card
- Multimeter
- Some demo appliances bought new
- Better enclosure + labels

> **Estimated cost: RM 735–1,445**

## Tier 3 — Pillar 1 only, no AC hybrid (NOT recommended)

What it cuts:

- Second CT clamp + its signal conditioning (~RM 30–70)
- IR receiver + relay block (~RM 25–45)
- AC SIMULATOR outlet labeling

What we lose: live AC cutoff, live agreement % moment, reliable inverter AC detection. This was the original "pure NILM" plan and we have pivoted away from it. Listed here for reference only.

> **Cost saving: RM 85–145**
> **Cost in demo strength: very high — not worth the save**

---

# 4. What we should buy first

## First purchase batch: prove power sensing works (Tier 1 core)

| Item | Qty | Reason |
|---|---:|---|
| CT clamp (SCT-013-030) | 2 | Main + AC sensing |
| ZMPT101B voltage sensor | 1 | Voltage measurement |
| ADS1115 ADC | 1 | Convert analog signals |
| Burden resistors, dividers, caps | 2 sets | One signal conditioning path per clamp |
| Breadboard + jumper wires | 1 set | Prototype the circuit |
| Raspberry Pi 4 + PSU + SD card | 1 | Main computer |
| Multimeter | 1 | Safety + debugging |

**Goal after Batch 1**: Raspberry Pi reads both clamps + voltage and shows total watts + AC watts separately.

---

## Second purchase batch: build the safe demo rig

| Item | Qty | Reason |
|---|---:|---|
| Plastic enclosure | 1 | Houses wiring safely |
| Inline fuse + holder | 1 | Protects circuit |
| Terminal blocks | 4–6 | Split bus into general + AC branches |
| Cable gland / strain relief | 1–2 | Prevents cable pulling |
| 13A plug + cable | 1 | Power inlet |
| Outlet bank | 1 | General appliance outlets |
| Single outlet + "AC SIMULATOR" label | 1 | Dedicated AC outlet |
| Insulation tape / heat shrink | Some | Safety |

**Goal after Batch 2**: Safe demo rig with two physically separate branches (general + AC), with the AC clamp wrapped around the AC branch wire.

---

## Third purchase batch: add control and live cutoff

| Item | Qty | Reason |
|---|---:|---|
| ESP32 dev board | 1 | mmWave + IR transmit controller |
| LD2410 mmWave sensor | 1 | Occupancy detection (Pillar 2 trigger) |
| IR LED + 2N2222 + resistors | 1 set | IR transmit |
| TSOP1838 IR receiver | 1 | Detect IR signal in demo rig |
| 5V relay module (opto-isolated, mains rated) | 1 | Cut power to AC SIMULATOR outlet |
| Transistor + resistors for relay drive | 1 set | Analog path from receiver to relay |

**Goal after Batch 3**: Empty-room detection → IR command → relay opens → AC SIMULATOR outlet cuts off → dashboard confirms.

---

# 5. What we can borrow instead of buying

To reduce cost, try to borrow:

- Raspberry Pi (biggest single saving)
- Multimeter
- Kettle, hair dryer, lamp, fan, microwave, rice cooker
- Extension socket
- Basic wires
- Enclosure
- Screw terminals
- Soldering iron

---

# 6. Necessary vs Optional summary

## Necessary for full hybrid demo (all three pillars + live cutoff)

- 2× CT clamp + signal conditioning (1 main + 1 AC)
- ZMPT101B voltage sensor
- ADS1115 ADC
- Raspberry Pi + PSU + SD card
- ESP32 + USB cable
- LD2410 mmWave sensor
- IR LED + transistor + resistors
- TSOP1838 IR receiver + transistor + resistors
- 5V relay module
- Breadboard + jumpers
- Terminal blocks
- Demo enclosure, fuse, plug, strain relief, earth wire, tape, labels
- Multimeter
- Kettle (general branch demo)
- Hair dryer (AC SIMULATOR proxy)

## Optional (improves polish but not required)

- PCB / perfboard (after breadboard works)
- Arduino Nano (if not using the simpler analog IR receiver → relay path)
- Extra appliances (lamp, fan, charger, microwave, rice cooker) for richer demo
- HDMI / keyboard / mouse for Pi (only if not using SSH)
- Dashboard tablet stand
- Printed labels and warning stickers

## Optional (for scaling beyond the prototype)

- Additional CT clamps (3rd, 4th) — for multi-AC homes
- Additional mmWave sensors — for multi-room occupancy detection
- Additional IR blasters — for multi-room AC control
- Portable AC unit — only if a real AC is available at the venue with permission

---

# 7. Budget risk notes

## Risk 1: Raspberry Pi price changes a lot

The Raspberry Pi may cost much more than expected depending on stock and RAM size.

Mitigation:

- Borrow from lab if possible
- Use Raspberry Pi 4 with 2GB or 4GB if enough
- Use a laptop for training and only use Pi for inference/demo
- If Pi is unavailable, run dashboard and ML on a laptop first, then port to Pi later

---

## Risk 2: Cheap modules may be inconsistent

Very cheap ADS1115, ZMPT101B, CT clamp, or TSOP1838 modules may have variable quality.

Mitigation:

- Buy 1 extra of small parts (clamp, IR receiver) if budget allows
- Test each sensor separately before full integration
- Calibrate with known appliances

---

## Risk 3: Mains-rated relay choice matters

A cheap relay rated only for low-current DC will fail when switching mains.

Mitigation:

- Choose a relay module rated explicitly for AC 250V at 10A or higher
- Prefer modules with opto-isolation between the logic side and the mains side
- Inspect the solder joints before powering on

---

## Risk 4: Safety parts get ignored

Safety parts look boring, but they are critical.

Mitigation:

- Put safety parts in the first budget, not as "later if enough money"
- Get wiring checked before powering on

---

# 8. Recommended budget table for proposal / teammate planning

| Budget level | What it includes | Estimated cost |
|---|---|---:|
| Pillar 1 only (NILM-only, *not recommended*) | Main clamp + Pi + dashboard, no AC hybrid, no live cutoff | RM 450–900 |
| Hybrid lower-cost (borrow Pi) | Both clamps + ESP32 + mmWave + IR transmit + receiver + relay + safe rig | RM 285–595 |
| Hybrid full prototype | Above + new Pi + multimeter + new demo appliances + polish | RM 735–1,445 |
| Hybrid + scale (multi-AC) | Above + extra clamps + extra mmWave + extra IR blasters per room | RM 900–1,800+ |

---

# 9. Final recommendation

For our team, the best strategy is:

1. **Do not buy everything at once.**
2. First prove that the Raspberry Pi can read both clamps and the voltage sensor.
3. Then build the safe demo rig with the split-bus wiring (general branch + AC branch).
4. Then add NILM inference on the main clamp signal.
5. Then add the ESP32 + mmWave + IR transmit + IR receiver + relay for the live cutoff demo.
6. Then polish the dashboard with the agreement % moment and smart insight cards.

The buying order should follow the build order.

The most important early milestones are:

> Milestone 1: Pi reads both clamps. Plugging a kettle into the general branch raises only the main reading; plugging a hair dryer into the AC SIMULATOR outlet raises both.
>
> Milestone 2: ESP32 sends IR → IR receiver detects it → relay cuts power to AC SIMULATOR outlet, confirmed by both clamp readings going to zero.

If those two work, the hardware foundation of the hybrid architecture is proven. NILM and the smart-insight layer become much easier to demonstrate after that.
