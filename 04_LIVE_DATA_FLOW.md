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
Feed the window into TFLite NILM models (kettle, fridge, lamp, etc.)
↓
Get non-AC appliance predictions
↓
Compute NILM-vs-direct AC agreement %
↓
Smooth predictions
↓
Send results to dashboard: per-appliance breakdown + direct AC + agreement %
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

## 5. Step 3 — Calculate watts

Once we have currents (from both clamps) and voltage, we calculate two power values per second:

```text
Total power     = Voltage × Current_from_Clamp_1  (whole home)
Direct AC power = Voltage × Current_from_Clamp_2  (AC branch only)
Residual power  = Total power − Direct AC power   (everything except AC)
```

In real AC systems, power calculation can be more complex because voltage and current are waves.

For a prototype, we estimate real-time power using sampled voltage and current values over a short time window.

The goal is to output three useful power values per second:

```text
Second 1: Total 230W   | AC 0W    | Residual 230W
Second 2: Total 235W   | AC 0W    | Residual 235W
Second 3: Total 2250W  | AC 0W    | Residual 2250W  (kettle on general branch)
Second 4: Total 3700W  | AC 1500W | Residual 2200W  (kettle + AC simulator)
```

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

Example window size:

```text
599 seconds for kettle or microwave
1023 seconds for fridge or AC
2047 seconds for washing machine
```

A rolling window means the system always keeps the latest readings.

Example:

```text
At second 600: use readings 1–599
At second 601: use readings 2–600
At second 602: use readings 3–601
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

## 9. Step 7 — Feed into TFLite model

The Raspberry Pi loads the TFLite models.

Each model receives the rolling window.

Example:

```text
kettle_model(input_window) → kettle power estimate
fridge_model(input_window) → fridge power estimate
ac_model(input_window) → AC power estimate
```

If we train around 10 models, the Pi may run multiple models every second.

For the live demo, we can prioritize demo-core models first.

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
    "fridge": 120,
    "ac_nilm_estimate": 1450
  },
  "ac_agreement_percent": 96.7
}
```

Notes:
- `total_power` comes from Clamp #1 (main feeder)
- `ac_direct` comes from Clamp #2 (dedicated AC clamp)
- `residual_power` = total minus AC; this is the input NILM disaggregates
- `ac_nilm_estimate` is the AI's guess from the main signal alone, kept for validation
- `ac_agreement_percent` = ac_nilm_estimate / ac_direct × 100 — shown live for credibility

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

Create a table like this during testing:

| Appliance | Expected power | Measured power | Correction needed? |
|---|---:|---:|---|
| Kettle | 2000W | 1900W | Yes |
| Lamp | 15W | 18W | Small error |
| Hair dryer | 1200W | 1150W | Small error |

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
