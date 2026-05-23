# 04 — Live Data Flow: How Real Sensor Data Enters the AI

## 1. Purpose of this file

This file explains the bridge between hardware and machine learning.

The hardware file explains how we measure electricity.

The ML file explains how we train the model.

This file explains how live sensor readings become model input.

It also explains how live predictions become smarter insights using stored history, occupancy, routine patterns, and cost assumptions.

This is one of the most important files because many people understand hardware and ML separately, but not how they connect.

## 2. The full live data flow

Visual reference:

![WattsEye live data pipeline](assets/live-data-pipeline.svg)

```text
CT clamp #1 (main) + CT clamp #2 (AC) + voltage sensor
↓
ADS1115 raw readings (A0 = main, A1 = voltage, A2 = AC)
↓
Convert raw readings to current and voltage for each channel
↓
Calculate real power in watts:
  • Total power (from main + voltage)
  • Direct AC power (from AC clamp + voltage)
↓
Compute residual signal = total power − direct AC power
↓
Store one reading per second for all three values
↓
Build a rolling time window (on the residual signal)
↓
Normalize the input
↓
Feed the window into PyTorch ELECTRIcity NILM models (kettle, fridge, hair_dryer, iron, washing_machine)
↓
Get non-AC appliance predictions
↓
(Internal only: log NILM AC estimate alongside the direct AC reading for offline validation; not shown on dashboard)
↓
Smooth predictions
↓
Send results to dashboard: per-appliance breakdown + direct AC reading
↓
Store locally first; sync to cloud only when internet is available
```

## 3. Step 1 — Sensor readings

Two CT clamps give current-related signals:

- Clamp #1 on the main feeder (input to ADS1115 channel A0)
- Clamp #2 on the dedicated AC branch (input to ADS1115 channel A2)

The voltage sensor gives a voltage-related signal (input to A1).

All three signals are analog.

The ADS1115 converts them into digital numbers.

The Raspberry Pi reads these numbers from all three channels.

At this point, the numbers are not yet meaningful watts.

They are still raw readings.

## 4. Step 2 — Convert raw readings into voltage and current

The Raspberry Pi needs to convert ADS1115 readings into real-world values.

Example:

```text
ADS1115 reading → sensor voltage
Sensor voltage → current estimate
Voltage sensor reading → mains voltage estimate
```

This requires calibration.

## 5. Step 3 — Calculate watts (apparent power, with an honest caveat)

The naive textbook formula is `Power = Voltage × Current`. This is correct for direct current, but Malaysian mains is a 50 Hz alternating-current sine wave — voltage swings from +340V to −340V fifty times per second, and current does the same (sometimes phase-shifted). To compute power correctly we need RMS values, not instantaneous samples.

For each one-second buffer of ADS1115 samples we compute:

```text
Vrms              = sqrt( mean( v_sample^2 ) )           over a ~1 s window
Irms_main         = sqrt( mean( i_main_sample^2 ) )
Irms_ac           = sqrt( mean( i_ac_sample^2 ) )

Apparent power S  = Vrms × Irms        (units: VA)
```

Apparent power is **what the ADS1115 can give us** at ~250 samples per second per channel. That's only about 5 samples per 50 Hz mains cycle — enough for RMS magnitudes but not enough to compute true real power on its own, because real power also needs the phase angle between voltage and current waves (the power factor φ):

```text
True real power P = Vrms × Irms × cos(φ)     (units: W)
```

For resistive loads (kettle, hair dryer heating coil, iron, incandescent lamp) `cos(φ) ≈ 1.00`, so `S ≈ P` and the apparent-power reading is the true watt reading within ~2%.

For loads with switching power supplies or motors (LED lamp, fridge compressor, **inverter AC**) `cos(φ)` is 0.6–0.9, so the apparent power overstates real watts by 10-40%. The dashboard inherits that error if we report S as W naively.

How WattsEye handles this honestly:

1. Compute apparent power S from the ADS1115 samples each second.
2. Apply a **per-appliance power-factor correction** at the insight layer. The correction factors are calibration constants (`ML/sensing/power_math.py`) measured once during commissioning against a smart plug as ground truth. For the demo rig — which uses resistive appliances (kettle, hair dryer, iron) — the correction is ≈1.00, so live numbers are accurate.
3. Label the values clearly: dashboard tiles read "Power 1500W" but the underlying field is `power_va_or_w` with a `correction_applied` boolean in the JSON.

The goal is to output three useful power values per second:

```text
Second 1: Total 230W   | AC 0W    | Residual 230W
Second 2: Total 235W   | AC 0W    | Residual 235W
Second 3: Total 2250W  | AC 0W    | Residual 2250W  (kettle on general branch)
Second 4: Total 3700W  | AC 1500W | Residual 2200W  (kettle + AC simulator)
```

For the production version (real Malaysian home with a real inverter AC and unknown loads), the ADS1115 is the limiting factor. The upgrade path is documented in plan 02 §10b: swap to a faster ADC (MCP3008) to compute true real power in software, or use a dedicated energy-metering IC (PZEM-004T, ADE7953) that returns V, I, W, PF, and energy directly. Neither is needed for the prototype demo.

## 6. Step 4 — Resample to 1 Hz

The AI model expects data at a fixed rate.

A simple choice is 1 reading per second.

This is called **1 Hz**.

Even if the sensor reads faster internally, we summarize it into one value per second.

Example:

```text
Power at 10:00:01 = 230W
Power at 10:00:02 = 232W
Power at 10:00:03 = 2200W
```

## 7. Step 5 — Store a rolling window

The model does not look at only one power value.

It looks at a window of recent power values.

WattsEye uses ELECTRIcity-style Transformer models trained with a single shared window size across all appliances:

```text
240 samples (≈ 240 seconds at 1 Hz) for all appliances
```

This is shorter than the vanilla seq2point CNN defaults (599/1023/2047) because the Transformer's attention layers extract long-range patterns from a smaller window. Using one shared window also lets the Raspberry Pi keep one buffer instead of three.

The actual window size is fixed by the trained models — it can be inspected with:

```text
state_dict['Generator.position.pe.weight'].shape[0]   # = 240
```

If the models are retrained with a different window, this number changes and the script's `DEFAULT_WINDOW_SIZE` in `ML/NILM/test_nilm_inference.py` must be updated to match.

A rolling window means the system always keeps the latest readings.

Example:

```text
At second 241: use readings 2–241
At second 242: use readings 3–242
At second 243: use readings 4–243
```

## 8. Step 6 — Normalize the input

The live input must be prepared the same way as the training data.

If the training data was normalized, the live data must also be normalized.

Example:

```text
normalized_power = (power - mean) / standard_deviation
```

This is important.

If training data and live data are prepared differently, the model may perform badly.

## 9. Step 7 — Feed into the NILM model

The Raspberry Pi loads each PyTorch ELECTRIcity `.pth` checkpoint at startup.

Each model receives the same rolling window.

Example:

```text
kettle_model(input_window)         → kettle power estimate
fridge_model(input_window)         → fridge power estimate
hair_dryer_model(input_window)     → hair dryer power estimate
```

The Pi may run several appliance models every second. For the live demo, we prioritize demo-core models first. AC is not in this list — it comes from the dedicated CT clamp, not from a model.

See plan 03 §15 for the runtime path (PyTorch first, quantization/TorchScript if too slow, TFLite only as a contingency).

## 10. Step 8 — Smooth the prediction

Raw model outputs may jump around.

Example:

```text
Kettle prediction: 0W, 1500W, 2100W, 1800W, 2050W
```

To make the dashboard look stable, we can smooth predictions.

Simple methods:

- Moving average
- Ignore tiny predictions below a threshold
- Require the prediction to stay active for a few seconds

Example rule:

```text
If kettle prediction is below 100W, show 0W.
If it stays above 1000W for 3 seconds, show kettle ON.
```

## 11. Step 9 — Send to dashboard

After smoothing, the Raspberry Pi sends the appliance predictions to the dashboard.

Example dashboard data:

```json
{
  "total_power": 3700,
  "ac_direct": 1500,
  "residual_power": 2200,
  "appliances": {
    "kettle": 2000,
    "lamp": 15,
    "fridge": 120
  }
}
```

Notes:
- `total_power` comes from Clamp #1 (main feeder)
- `ac_direct` comes from Clamp #2 (dedicated AC clamp) — shown as the AC value in the UI
- `residual_power` = total minus AC; this is the input NILM disaggregates
- The NILM model's own AC estimate is logged internally for offline validation only, not sent to the dashboard. Treating the dedicated CT clamp as the authoritative AC reading keeps the UI honest and avoids exposing a misleading "agreement %" tile (see plan 03 §23 Use 2)

The dashboard updates the appliance cards.

Before triggering smarter alerts, the Raspberry Pi should also store history and run the smart insight engine.

History to store:

- Timestamp
- Total power
- Direct AC power
- Residual power
- Appliance predictions
- Optional smart plug readings
- Occupancy state
- Estimated cost
- Alerts triggered
- User responses, if any
- Sync status, if cloud sync is enabled

This history lets WattsEye learn routines such as normal AC hours, usual kettle time, typical empty-room periods, and normal standby power.

The smart insight engine combines current predictions, occupancy, time/day, historical routine patterns, tariff assumptions, and anomaly scores.

It can output bill forecasts, waste scores, routine-aware alerts, energy coach recommendations, appliance health warnings, and standby power insights.

## 12. Step 10 — Trigger alerts

The same data can trigger alerts. The dedicated AC clamp makes the AC trigger reliable (no AI uncertainty).

Example:

```text
Dedicated AC clamp directly shows AC is on (e.g. drawing 1500W).
mmWave says room is empty.
This continues for 30 minutes.
System sends WhatsApp alert.
User replies YES.
Pi sends MQTT command to ESP32.
ESP32 fires IR LED.
In demo rig: TSOP1838 IR receiver detects signal → relay opens → AC SIMULATOR outlet loses power.
In real home: AC unit's own IR receiver picks up the signal → AC switches off.
Dedicated AC clamp confirms 0W. Confirmation WhatsApp sent back.
```

Smarter alert example:

```text
Dedicated AC clamp shows AC is on.
mmWave says room is empty.
This continues for 30 minutes.
The home is usually empty at this time.
The bill forecast is trending high.
System sends an alert with estimated avoidable cost.
```

## 13. Calibration plan

Calibration makes readings more believable.

Use known appliances.

Example:

1. Plug in a kettle rated around 2000W.
2. See what WattsEye reads.
3. If it reads 1800W, apply a correction factor.
4. Repeat with another appliance.

This helps align sensor output with real power.

## 14. Demo calibration table

Two error sources stack here and must be calibrated independently:

1. **Sensor scale error** — burden resistor tolerance, CT clamp ratio, voltage divider drift. Same per channel regardless of appliance.
2. **Power factor (PF) gap** — apparent power S = Vrms × Irms overstates real watts by `1 − cos(φ)` for non-resistive loads. Differs per appliance.

Recommended table to fill in during commissioning. Plug each appliance in alone, compare WattsEye's apparent-power reading with a calibrated reference (smart plug or clamp meter):

| Appliance | Type | Expected PF | Rated W | Measured VA | Implied PF | Notes |
|---|---|---:|---:|---:|---:|---|
| Kettle | Resistive | 1.00 | 2000 | ~2000 | ≈1.00 | Use this to fix clamp scale |
| Hair dryer (heat) | Resistive + small motor | 0.95 | 1200 | ~1260 | 0.95 | Demo-core AC proxy |
| Iron | Resistive | 1.00 | 1000 | ~1000 | ≈1.00 | Clean reference |
| Incandescent lamp | Resistive | 1.00 | 60 | ~60 | ≈1.00 | Low-power reference |
| LED lamp | SMPS | 0.65 | 9 | ~14 | 0.64 | Small but illustrative |
| Fridge (compressor running) | Inductive | 0.70 | 120 | ~170 | 0.71 | If available for testing |
| Inverter AC | Variable inductive | 0.60–0.95 | 900 | varies | varies | Production-only, not demo |

Procedure:

1. Plug in the kettle (PF ≈ 1.00 by definition) and compare WattsEye's reading to the kettle's rated wattage or a smart plug. Any mismatch is **sensor scale error** — apply a single correction factor to that clamp.
2. After scale is fixed, plug in each non-resistive appliance and record the implied PF (`measured_VA / rated_W`). Store these in `ML/sensing/power_math.py` as the `APPLIANCE_POWER_FACTORS` table.
3. At runtime, the insight layer multiplies the apparent-power reading by the appliance's PF before displaying watts and computing RM cost.

For the live demo we focus on resistive appliances (kettle, hair dryer, iron) where PF ≈ 1.00 so the readings are accurate without correction. The PF correction matters more for the production version where unknown appliances need honest watt readings.

## 15. Why live data may differ from training data

Training data comes from public datasets.

Live data comes from our demo rig.

They may differ because of:

- Different sampling rate
- Different sensor noise
- Different appliance brands
- Different voltage levels
- Different wiring setup
- Different appliance combinations

That is why calibration and demo fine-tuning matter.

## 16. Minimum live demo pipeline

For a simple working demo, we need at least:

```text
Sensor reading → watts calculation → rolling window → one or two demo models → dashboard
```

The complete system can have 10 models, alerts, anomaly detection, routine-aware insights, bill forecasting, and recommendations.

But the first working version should prove the main pipeline.

## 17. Recommended live demo priority

Priority 1:

```text
Show total power changes accurately.
```

Priority 2:

```text
Show one demo-core appliance detection, such as kettle.
```

Priority 3:

```text
Show multiple appliance predictions.
```

Priority 4:

```text
Show occupancy + AC alert flow.
```

Priority 5:

```text
Show anomaly detection.
```

Priority 6:

```text
Show smart insights: projected bill, waste score, routine-aware alert, or energy coach recommendation.
```

## 18. Backup plan

If live ML is unstable, we can still demo honestly by separating parts:

- Live sensor shows total power.
- Pre-recorded or notebook output shows appliance disaggregation.
- Dashboard mock/live hybrid shows final product experience.

This is acceptable for a prototype if we clearly explain what is live and what is simulated.

## 19. Offline-first storage and sync

Every live reading should be saved locally before any cloud upload is attempted.

Recommended local record shape:

```json
{
  "user_id": "local-demo-user",
  "device_id": "wattseye-pi-001",
  "timestamp": "2026-05-18T20:30:00+08:00",
  "total_power_watts": 3700,
  "ac_power_watts": 1500,
  "residual_power_watts": 2200,
  "source": "ct_clamp",
  "synced": false
}
```

Optional smart plug readings can use the same table shape with `source = "smart_plug"` and a smart plug `device_id`.

Cloud sync rule:

```text
If internet exists and user is logged in:
  upload unsynced rows to Supabase
  mark rows as synced locally
Else:
  keep rows locally and continue dashboard operation
```

This supports all three operating modes:

- Best case: local operation plus cloud history sync
- Normal case: local WiFi dashboard without remote cloud dependency
- Fallback case: Pi hotspot and local database only

Important UX rule:

```text
Login tells the app who the user is.
Connection status tells the app whether the data is live.
```

If the phone/laptop cannot reach the home Pi, the dashboard should clearly label the readings as synced history, cached history, or demo data. It should not imply that remote cloud data is always live.

## 20. Main takeaway

The live data flow is the bridge:

```text
Real electricity → clean watts → model input → appliance prediction → user display
```

If this bridge is unclear, teammates may understand the hardware and ML separately but not the full system.
