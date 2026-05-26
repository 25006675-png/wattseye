# Step 7 — Mains box: assemble, inspect, energise, test

**Goal:** build the plug-through "mini distribution board", get it **inspected**,
then energise and run the live tests (fan/kettle on the sockets, then the live
cutoff).

**Reference:** [`../../HARDWARE_CONNECTION.md`](../../HARDWARE_CONNECTION.md)
§1 (safety), §5 (box build), §13.2 (relay mains side), §15 (steps 7–10).

> 🛑 **DANGER — 240 V mains.** This is the only step with lethal voltage. The
> assembly (7.1) is unpowered and safe to do anytime. **Do NOT energise (7.3+)
> until a lecturer/technician/electrician has inspected the wiring.**

---

## Step 7.1 — Assemble the box (UNPOWERED — safe to do now)

From `HARDWARE_CONNECTION.md` §5.3. The plug stays **out of the wall** the entire
time.

1. Mount the **SIEMENS twin socket** in the **3+7 PVC box** (general branch) and the
   **SIEMENS single socket** in the **3+3 PVC box** (AC-SIM branch). Label the single
   one **"AC SIMULATOR"**.
2. Inside a **weatherproof 8×6×3 enclosure**, mount the **fuse holder**, both
   **SCT-013 clamps**, the **PCT-213** junctions, and the **relay**.
3. Route the inlet from the **13 A fused plug top** through a **PG9 gland**; fit a
   **10 A fuse**.
4. Wire **LIVE → fuse → (clamp #1) → PCT split → branches**; neutral and earth per
   §5.2. Use PCT-213 levers for every junction; heat-shrink any exposed strands.
5. Clip **SCT-013 #1** around the **single live wire** after the fuse; **SCT-013 #2**
   around the **AC-branch live** only. (Around one conductor only — never
   live+neutral together.)
6. Wire the **relay mains side** in series with the AC-SIM live (§13.2):
   `AC-branch LIVE → relay COM`, `relay NO → AC-SIM socket LIVE`.
7. Bring the **clamp jacks** and **ZMPT101B mains leads** out through a gland to the
   low-voltage area. The ZMPT mains terminals connect **across LIVE–NEUTRAL** after
   the fuse.

> 🟢 Everything to here is mechanical + low-current routing. No power yet.

## Step 7.2 — Inspection (mandatory gate)

**Have a qualified person check the wiring** before power: fuse in live, earth
bonded everywhere, no exposed copper, clamps around single conductors, enclosure
closed. Do not proceed until they approve. (§1)

## Step 7.3 — Energise + tune the voltage sensor

1. Plug in. Confirm the Pi + ADS1115 reader (Step 5) is running.
2. **Tune the ZMPT101B trimpot** (§7.3): adjust the blue multi-turn pot until the
   `vrms` reading lands near **~240 V** (or, on a scope, the OUT sine centres ~1.65 V
   with peaks under 3.3 V). This is the voltage half of calibration.

## Step 7.4 — Branch tests (proves the clamps)

| Test | Plug a load into… | Expect |
|---|---|---|
| **General branch** | the **twin** socket (e.g. kettle) | **A0 (main)** rises; **A2 (AC)** stays ~0 |
| **AC branch** | the **AC-SIM single** socket (e.g. fan/hair-dryer) | **both A0 and A2** rise |

Watch live: `mosquitto_sub -h localhost -t wattseye/power -v` on the Pi, or
`/api/dashboard` from the laptop.

## Step 7.5 — Live cutoff (the demo moment, Milestone 2)

With the ESP32 (Step 6) running and a fan on the AC-SIM socket:

1. Leave the room / clear the LD2410C's view so occupancy goes **EMPTY** with the AC
   "on" → the bridge fires `wattseye/ac/command {"command":"off"}`.
2. The ESP32 sends the **mock IR pulse** and **opens the relay** → the AC-SIM socket
   dies → the fan stops → **A2 drops to ~0** on the dashboard.

> You can also trigger it manually from the Pi:
> `mosquitto_pub -h localhost -t wattseye/ac/command -m '{"command":"off"}'`

✅ That visible "the AC turned off and the power dropped" is the core demo.

---

## Safety checklist (every time)

- [ ] Plug **out of the wall** during any wiring change
- [ ] Inline **fuse in the live** conductor
- [ ] **Earth** bonded to all metal + socket earth pins
- [ ] **No exposed copper**; enclosure closed
- [ ] Clamps clip **one insulated conductor** only
- [ ] Mains kept **physically separate** from the breadboard/Pi/ESP32

---

← Prev: [Step 6 — ESP32 node](06_esp32_bringup.md) ·
Next: [Step 8 — Calibration](08_calibration.md) →
