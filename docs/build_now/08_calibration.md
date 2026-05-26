# Step 8 — Calibration

**Goal:** make the displayed watts match reality. Raw ADC readings won't equal real
power until you set the per-channel scale constants against a known load.

**Reference:** [`../../HARDWARE_CONNECTION.md`](../../HARDWARE_CONNECTION.md) §16,
[`../../ML/sensing/README.md`](../../ML/sensing/README.md). Constants live in
[`../../ML/sensing/power_math.py`](../../ML/sensing/power_math.py) (`CalibrationConstants`,
line ~36) and are set in
[`../../ML/sensing/ads1115_reader.py`](../../ML/sensing/ads1115_reader.py) (the `CAL`
block near the top).

> ⚠️ Requires the **energised** rig (Step 7) and a **kettle** (a near-perfect
> resistive load, power factor ≈ 1.00). ⏱️ ~30 min.

---

## Why calibrate

- The **SCT-013 30A/1V** and **ZMPT101B** each have small scale errors and the ZMPT
  output depends on its trimpot. Calibration corrects those into true volts/amps.
- A **kettle** is the calibration reference because its real power ≈ its rated watts
  (PF = 1), so any mismatch is pure sensor scale error.

## Step 8.1 — Voltage scale

You roughly tuned the ZMPT trimpot in Step 7.3. Now fine-tune in software:

1. With mains on, read `reading.vrms` from the live reader.
2. Adjust `CalibrationConstants.voltage_scale` until `vrms ≈ 240 V`
   (your actual mains voltage).

## Step 8.2 — Main current scale (kettle)

1. Plug a **kettle of known rating** (e.g. 2000 W) into the **general (twin)** socket
   and switch it on.
2. Read WattsEye's apparent power on the **main** channel.
3. Adjust `CalibrationConstants.main_current_scale` until the displayed watts match
   the kettle's rated wattage.

## Step 8.3 — AC branch current scale

1. Plug a known load into the **AC-SIM single** socket.
2. Adjust `CalibrationConstants.ac_current_scale` until that channel matches.

## Step 8.4 — Power factor for non-resistive loads

For appliances that aren't pure resistive (fans, inverter ACs), record
`measured_VA / rated_W` and store it in the `APPLIANCE_POWER_FACTORS` table
(`power_math.py` line ~61) so the displayed watts are PF-corrected. (See §16 step 4.)

## Step 8.5 — Save the constants

Put the final values in the `CAL = CalibrationConstants(...)` block at the top of
`ML/sensing/ads1115_reader.py` and commit them, so every run uses the tuned scales.

```python
CAL = CalibrationConstants(
    voltage_scale=...,        # from 8.1
    main_current_scale=...,   # from 8.2
    ac_current_scale=...,     # from 8.3
)
```

---

## Accuracy note

With the ADS1115 you get accurate watts for **resistive** loads (kettle, hair-dryer,
iron) and PF-corrected estimates for inductive/switching loads. True real power on
inverter ACs needs an upgrade (PZEM-004T / ADE7953) — documented in
[`../../ML/sensing/README.md`](../../ML/sensing/README.md), **not needed for the
demo**. (§16 / `plan/02 §10a`.)

---

## 🎉 Done — the rig is live and calibrated

Full bring-up is complete: software (1–3), low-voltage hardware (4–6), mains (7),
calibration (8). The app shows the **Live Pi** chip, the dashboard reads real
watts, and the empty-room cutoff works end to end.

---

← Prev: [Step 7 — Mains box](07_mains_box.md) ·
Optional: [IR-learn — real-AC only](09_ir_learn.md)
