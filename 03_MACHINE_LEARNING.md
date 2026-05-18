# 03 — Machine Learning: How the AI Works

## 1. Purpose of this file

This file explains the machine learning part of WattsEye.

It focuses on:

- What the AI is trying to do
- What data the AI uses
- Why one sensor can estimate many appliances
- Why we train around 10 models
- Which models are demo-critical
- How the models run on Raspberry Pi
- How routine-aware detection and appliance health insights make the system smarter

## 2. What is NILM?

NILM means **Non-Intrusive Load Monitoring**.

Simple meaning:

```text
Use one main electricity signal to estimate individual appliance usage.
```

Non-intrusive means we do not put a sensor on every appliance.

Instead, we monitor the whole home from one main point.

In WattsEye, NILM runs on the main feeder clamp's signal. The dedicated AC clamp does **not** run NILM — it just measures AC power directly. The two work together: the dedicated AC reading is also used to clean up the NILM input (subtraction) and to validate the model in real-time.

## 3. What the model receives

The model receives a time sequence of total power readings.

Example:

```text
200W, 205W, 210W, 2200W, 2190W, 2185W, 210W
```

This is not just one number.

It is a pattern over time.

The model learns from the shape of the pattern.

## 4. What the model predicts

Each appliance model predicts how much power that appliance is using.

Example:

```text
Input: total power over time
Kettle model output: 2000W
Fridge model output: 0W
AC model output: 0W
Lamp model output: 15W
```

The dashboard combines these model outputs into an appliance breakdown.

## 5. Why appliance patterns are different

Different appliances use electricity differently.

| Appliance | Pattern |
|---|---|
| Kettle | Sudden high-power block |
| Fridge | Repeated cycling |
| AC | Long high-power cycles or ramping behavior |
| Microwave | Short high-power usage |
| Washing machine | Multi-stage usage |
| Lamp | Low and stable usage |
| Phone charger | Very low and sometimes changing usage |
| Iron | Heating cycles on and off |
| Rice cooker | Heating then warming pattern |

The AI learns these patterns.

## 6. Why we train around 10 models

We want to show that WattsEye can scale beyond only one or two appliances.

So we may train around 10 appliance-specific models.

However, not all models are equally important for the live prototype.

We divide them into two groups:

## 7. Demo-core models

These are the models we focus on for live demonstration.

They should be easier to verify on stage.

Examples:

- Kettle
- Lamp
- Hair dryer
- Phone charger
- Microwave, if available

These appliances are useful because:

- We can physically bring them or simulate them easily.
- The power change is visible.
- The judges can understand the result quickly.
- They reduce live demo risk.

## 8. Supplementary models

These models support the bigger product vision.

Examples:

- Air conditioner
- Fridge
- Washing machine
- Water heater
- Rice cooker
- Iron
- Fan
- Dishwasher

These may be shown through:

- Validation notebooks
- Recorded dashboard output
- Dataset evaluation
- Product story
- Future scalability slide

We should not claim that all 10 models are live-demo perfect.

Better wording:

```text
The architecture supports around 10 appliance-specific models.
For live demonstration, we prioritize high-confidence demo appliances.
Additional models show broader household coverage.
```

## 9. Model architecture

The ML plan uses a known NILM approach called **sequence-to-point learning**.

Simple meaning:

```text
The model looks at a window of past power readings and predicts the appliance power at a target point.
```

Example:

```text
Input window: last 599 seconds of total power
Output: current kettle power estimate
```

This is useful because appliances are easier to identify from patterns over time, not from one instant reading.

## 10. Why one model per appliance?

Instead of one giant model, we can use multiple appliance-specific models.

Each model asks:

```text
Does my appliance pattern appear in this signal?
```

Example:

- Kettle model checks for kettle pattern.
- Fridge model checks for fridge pattern.
- AC model checks for AC pattern.

This is easier to develop, test, and explain.

## 11. Training data

We use public electricity datasets because collecting our own clean data would take too long.

Possible datasets:

- UK-DALE for common appliances like kettle, fridge, microwave, washing machine, dishwasher
- ENERTALK for Asian homes and AC-related patterns
- Pecan Street for heavy AC usage if accessible
- MCEC-Thai or iAWE for regional/tropical validation

Own demo rig data can still be collected, but it should be treated as fine-tuning or calibration, not the main dependency.

## 12. Why not depend only on our own data?

Because collecting good training data is slow.

We would need:

- Many appliance examples
- Clean labels
- Different usage situations
- Enough days of data
- Correct sensor calibration

For a short prototype timeline, that is risky.

Public datasets help us start faster.

## 13. Fine-tuning with demo appliances

Even though public datasets are useful, our live demo appliances may behave differently.

So we should collect some data from the actual demo appliances.

Example:

1. Record kettle alone.
2. Record lamp alone.
3. Record hair dryer alone.
4. Record combinations.
5. Use this to calibrate or fine-tune the demo models.

This makes the live demo more reliable.

## 14. Model evaluation

We should evaluate using standard NILM metrics.

Common metrics:

| Metric | Meaning |
|---|---|
| F1 score | How well the model detects appliance on/off events |
| MAE | Average error in predicted power |
| SAE | Error in total energy estimate |

For demo-core appliances, we mainly care that the result is understandable and stable during the live demo.

## 15. TFLite conversion

The models are trained on a laptop or cloud notebook.

But the final prototype should run on Raspberry Pi.

So the trained models need to be converted into **TensorFlow Lite** format.

This makes them smaller and faster for edge devices.

## 16. Quantization

Quantization reduces model size and improves speed.

Simple meaning:

```text
Make the model lighter so Raspberry Pi can run it faster.
```

But we must check that accuracy does not drop too much.

## 17. Live inference concept

In the live system:

1. Raspberry Pi receives power reading every second.
2. It stores recent readings in a rolling window.
3. It sends the window into each appliance model.
4. Each model outputs estimated appliance power.
5. The predictions are smoothed.
6. The smart insight engine compares predictions with occupancy, routine history, and cost assumptions.
7. The dashboard updates.

## 18. Routine-aware detection

Visual reference:

![WattsEye smart insight architecture](assets/smart-insight-architecture.svg)

Routine-aware detection means WattsEye learns what is normal for this specific home at different times.

Examples:

```text
Kettle usually appears around 7 AM.
AC usually runs at night.
The home is usually empty on weekday afternoons.
Standby power is usually around 80W overnight.
```

This is not the same as appliance detection.

Appliance detection answers:

```text
What appliance is probably running?
```

Routine-aware detection answers:

```text
Is this behavior normal for this home at this time?
```

For the prototype, this can start as a simple statistics-based layer instead of a complex model.

Example features:

- Hour of day
- Day of week
- Appliance on/off duration
- Typical appliance start time
- Occupancy state
- Average power by time period
- Recent usage compared with the last few days

Example rule:

```text
If AC is on, room is empty, and this is outside the usual AC schedule, increase alert priority.
```

## 19. Bill forecasting and energy coach

The ML output can also support bill forecasting and recommendations.

Simple forecasting:

```text
Projected monthly bill = current month-to-date cost / days passed * days in month
```

Smarter forecasting can compare current usage with the user's normal pattern.

Example:

```text
Your projected bill is 22% higher than usual.
Most extra usage came from AC between 2 PM and 5 PM.
```

The energy coach should recommend specific actions, not generic advice.

Example:

```text
Raise AC temperature by 1-2 degrees or enable auto-off after 20 minutes empty.
Estimated saving: RM18/month.
```

## 20. Appliance health score

Appliance health uses the same historical pattern idea, but focuses on whether an appliance is behaving differently from its own normal behavior.

Example:

```text
Fridge Health: 72/100
Reason: compressor cycling is more frequent than usual this week.
Possible causes: door seal issue, dirty coil, or high room temperature.
```

This should be framed as an early warning, not a confirmed diagnosis.

## 21. Important limitation

NILM is not perfect.

If two appliances turn on at the same time, the signal becomes harder to separate.

Low-power appliances are harder to detect than high-power appliances.

Appliances from different brands may behave differently.

**Inverter air conditioners are NILM's worst case in Malaysia.** Unlike non-inverter ACs that have clean on/off cycles, inverter ACs continuously vary their power based on temperature feedback. This means there is no clean event for the model to detect, no constant power level to recognize, and the signal blends into the background load over time. This is exactly why WattsEye uses a dedicated CT clamp on the AC circuit instead of trying to detect AC purely through NILM.

That is why the prototype should focus live demo on high-confidence appliances first.

Routine-aware detection also has limitations.

It needs historical data before it becomes useful. Early in setup, the system should say it is still learning the home's routine.

It should avoid overclaiming:

```text
Good: This usage is unusual compared with your recent pattern.
Avoid: This appliance is definitely faulty.
```

## 22. Best way to explain the ML to others

Say this:

```text
We are not using AI to magically know the appliance.
We are training models to recognize power patterns.
Each appliance has a different electrical signature.
The model looks at the total power signal and estimates which signatures are present.
```

## 23. How the dedicated AC clamp makes NILM better

The dedicated AC clamp is not just a separate sensor for the AC. It also makes the NILM model better in three ways:

### Use 1 — Signal subtraction for cleaner NILM input

Before running NILM on the main signal, subtract the dedicated AC reading. This removes the loudest and most variable load from the NILM input:

```text
Main signal       = AC + kettle + fridge + lamp + everything else
Dedicated AC      = AC only
Residual (input)  = kettle + fridge + lamp + everything else  ← NILM runs on this
```

The residual signal is easier for NILM to disaggregate because the most NILM-hostile load (inverter AC) has already been removed.

### Use 2 — Live model validation

The NILM model also estimates AC from the main signal alone. Compare that estimate to the dedicated reading in real-time:

```text
Agreement % = (NILM AC estimate) / (Direct AC reading) × 100
```

When agreement is high (>90%), the model's other appliance estimates have higher implied credibility. This is the live "accuracy proof" moment shown on the dashboard.

### Use 3 — Free auto-labeled training data

Every second, we log `(main signal window, dedicated AC reading)`. Over weeks of operation in a real home, this becomes a fully-labeled training set for that specific home's AC, with no manual tagging by the user. Future model fine-tuning can use this dataset.

## 24. ML summary

The ML system does this:

```text
(Main signal − Dedicated AC) → appliance-specific NILM models → estimated non-AC appliance usage
Dedicated AC reading           → direct AC power (no AI needed)
```

The goal is not to make all 10 models perfect for the first prototype.

The goal is to prove the architecture:

```text
Hybrid sensing + AI gives reliable AC measurement AND useful appliance-level insight for everything else.
```

The smarter product goal is:

```text
Hybrid sensing helps the home understand usage, predict cost, prevent waste, and warn about abnormal behavior.
```
