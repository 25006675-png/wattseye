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

WattsEye uses the **ELECTRIcity** approach (Sykiotis et al., 2022) — a Transformer-based sequence-to-point NILM architecture. It is built on top of the standard seq2point idea (look at a window of past power, predict the appliance at a target point) but replaces the CNN backbone with a small Transformer encoder.

Simple meaning:

```text
The model looks at a window of past power readings and predicts the appliance power at a target point.
A Transformer's attention layers learn which moments in the window matter most for each appliance.
```

Architecture details for the shipped checkpoints (`ML/NILM/*.pth`):

```text
Input window:     240 samples (≈ 240 seconds at 1 Hz)
Front conv:       1 → 64 channels, kernel 5
Position encoding: learned, length 240
Transformer:      2 blocks, 8 heads, d_model = 64, d_ff = 256
Head:             ConvTranspose1d + mean pool + Linear(64→128) + Linear(128→1)
Trained as:       Generator half of a GAN-style training loop (Discriminator weights also live in the .pth but are not used at inference)
```

Why ELECTRIcity instead of vanilla seq2point CNN: published results show better F1/MAE on UK-DALE and REFIT for the same appliance set, and the attention layers extract enough long-range structure that a shorter 240-sample window suffices. Trade-off: it is heavier than a CNN, so Pi-side inference speed must be benchmarked before claiming live multi-appliance inference. See §15-16 below for the runtime story.

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

## 15. Runtime format on the Raspberry Pi

The models are trained on a laptop or cloud notebook in **PyTorch**, and shipped as `.pth` checkpoints under `ML/NILM/`. For the prototype we run inference on the Pi directly in PyTorch — `ML/NILM/test_nilm_inference.py` shows the load + inference path.

Order of operations:

1. **First, benchmark PyTorch inference on the Pi.** Run `test_nilm_inference.py --all` on a Raspberry Pi 4 and measure ms/inference per model. If each model finishes well under 1000 ms / (number of live models), we hit the 1 Hz live budget and no further work is needed.
2. **If too slow, optimise without leaving PyTorch first.** Try `torch.set_num_threads`, `torch.jit.trace` to TorchScript, and `torch.quantization` int8 post-training quantization. These usually deliver 2-4× speed-up with no framework change.
3. **Only if still too slow, convert to ONNX or TFLite.** PyTorch → ONNX is straightforward; ONNX → TFLite is possible but the Transformer attention layers sometimes need manual op fixes. Treat this as a contingency, not the default path.

The original plan called for TFLite from the start. We have moved away from that because (a) the ELECTRIcity Transformer doesn't convert cleanly to TFLite without rework, and (b) PyTorch on a Pi 4 is fast enough for small Transformer models in most cases. The benchmark in step 1 is the decision point.

## 16. Quantization (optional optimisation)

Quantization reduces model size and improves speed by representing weights in int8 instead of float32.

Simple meaning:

```text
Make the model lighter so Raspberry Pi can run it faster.
```

For WattsEye, quantization is an **optional optimisation**, not a required step. We only apply it if the step-1 benchmark above shows we are missing the 1 Hz live budget. PyTorch supports post-training dynamic quantization with two lines of code (`torch.quantization.quantize_dynamic`); we can apply that before considering a full TFLite rewrite.

Whatever path is used, accuracy must be re-checked against the validation set after quantization, since attention layers can be sensitive to int8.

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
Projected monthly bill = monthly_kwh_estimate -> TNB Tariff A bill calculator
```

The "TNB Tariff A bill calculator" is implemented in `ML/insights/tnb_tariff.py` and matches the **TNB Regulatory Period 4 (RP4) Domestic tariff** that took effect on 1 July 2025 and runs through 31 December 2027. It is not a flat sen/kWh rate. The calculator reproduces the actual bill structure:

```text
Generation charge     27.03 sen/kWh    (37.03 sen/kWh if monthly usage > 1500 kWh)
+ Capacity charge      4.55 sen/kWh
+ Network charge      12.85 sen/kWh
- EEI rebate          0-25 sen/kWh    (tiered by monthly band, top rebate 1-200 kWh)
+/- AFA               variable        (Automatic Fuel Adjustment, published monthly; waived <=600 kWh)
+ Retail charge       RM10/month      (waived <=600 kWh)
```

Why this matters for the pitch:

- TNB does not expose a public consumer-facing API for tariff lookups. The schedule above is hardcoded from TNB's published RP4 documentation with full source URLs listed in `ML/insights/tnb_tariff.py` docstring and in `ML/insights/README.md`. The AFA constant must be refreshed each TNB billing cycle. Primary references: [myTNB tariff page](https://www.mytnb.com.my/tariff), [TNB press release 30 June 2025](https://www.tnb.com.my/assets/newsclip/30062025a.pdf), [paultan.org breakdown](https://paultan.org/2025/06/21/tnb-new-electricity-tariff-calculation-from-july-2025/), [SolarSunYield EEI table](https://www.solarsunyield.com/latestnews/nid/169869/).
- Most student energy projects use a single flat rate (e.g. RM 0.50/kWh). WattsEye reproduces the actual bill structure including the EEI rebate and the high-band cliff at 1500 kWh.
- The same module supports the optional **Time-of-Use (ToU) tariff** (peak 14:00-22:00 weekdays, off-peak otherwise) introduced under RP4. WattsEye can run both calculations on the same usage history and tell the user which tariff would be cheaper for their actual routine. This is a real product feature — TNB customers must opt in to ToU and most are not sure whether it would save them money.

Smarter forecasting compares current usage with the user's normal pattern.

Example:

```text
Your projected bill is 22% higher than usual.
Most extra usage came from AC between 2 PM and 5 PM (peak ToU window).
```

The energy coach should recommend specific actions, not generic advice.

Example:

```text
Raise AC temperature by 1-2 degrees or enable auto-off after 20 minutes empty.
Estimated saving: RM18/month at your current band (350 kWh/month, RP4 standard).
```

Or, when the user's load profile leans late-night/weekend:

```text
Your usage pattern is 65% off-peak. Switching to TNB's Time-of-Use tariff
could save about RM12/month based on the last 30 days.
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

### Use 2 — Internal model validation (not a UI tile)

During development and calibration, the NILM model also estimates AC from the main signal alone. We compare that estimate to the dedicated CT clamp reading offline:

```text
MAE_ac  = mean( |NILM AC estimate − Direct AC reading| )   over a logged window
F1_ac   = event-detection score on AC on/off transitions
```

These metrics live in a validation notebook, not on the dashboard. Reasons we do not show this as a live UI tile:

- The dedicated CT clamp is the displayed "ground truth," but it is itself a sensor with ±a few percent error — there is no third, more-precise reference to grade against on stage.
- In the demo rig the AC SIMULATOR outlet sits on the same circuit both clamps observe, so any "agreement" reading is largely a property of the wiring, not the model.
- A naive ratio (NILM/Direct) divides by zero when AC is off and shows misleading >100% when NILM overshoots.

The honest pitch is: AC is shown as a direct measurement; non-AC NILM accuracy is reported as F1/MAE against UK-DALE and ENERTALK in the validation notebook.

For internal development only, a power-monitoring smart plug placed inline with the AC SIMULATOR outlet can act as a temporary third reference to sanity-check both the dedicated CT clamp calibration and the NILM AC estimate. This is a dev workflow, not a production feature.

### Use 3 — Free auto-labeled training data

Every second, we log `(main signal window, dedicated AC reading)`. Over weeks of operation in a real home, this becomes a fully-labeled training set for that specific home's AC, with no manual tagging by the user. Future model fine-tuning can use this dataset.

## 24. Full ML lineup beyond NILM

NILM is the headline technique but not the only one. The complete WattsEye ML stack maps to the four pitch boxes:

| # | Technique | Job | Training data | Implementation |
|---|---|---|---|---|
| 1 | ELECTRIcity Transformer (§9 above) | Appliance disaggregation | UK-DALE / ENERTALK | `ML/NILM/*.pth` — done |
| 2 | Isolation Forest (sklearn) | Anomaly detection on appliance signatures | Home's first 30 days as healthy baseline + synthetic injections | `ML/anomaly/isolation_forest.py` — planned |
| 3 | K-Means clustering (sklearn) | Discover daily activity phases (morning / work / evening / sleep) | Home's occupancy + appliance log | `ML/routine/kmeans_phases.py` — planned |
| 4 | Linear Regression (sklearn) | Appliance health drift — e.g. fridge cycle 40% longer than baseline = door seal or compressor issue | UK-DALE / REFIT fridge submeter (months of healthy data per home) | `ML/anomaly/appliance_health_regression.py` — planned |

The TNB RP4 tariff calculator (`ML/insights/tnb_tariff.py`, see §19) sits alongside the four ML models as smart bill modelling — it is deterministic math, not ML, and we are honest about that.

Why these four and not others:

- **Isolation Forest** suits a "many normal examples, no labelled anomalies" data regime — which is exactly what a home with logged history gives us.
- **K-Means** is unsupervised, defensible, and recognisable. It naturally clusters activity into 3-5 daily phases that the existing statistical routine engine then refines.
- **Linear Regression** is the right tool for appliance health: predict `expected_duty_cycle = f(hour_of_day, day_of_week)` from learned baseline, flag residuals over a threshold. We tried framing this as dirty-AC-filter detection but no public dataset has clean-vs-dirty filter labels — so the model targets refrigerator efficiency drift instead, which UK-DALE and REFIT support.
- We deliberately do **not** use RNN/LSTM for bill prediction. The bill is deterministic given consumption — see §19. The only forecast needed is future kWh, which a 7-day rolling average handles. LSTM would be ML for ML's sake.

## 24a. Coach engine — turning ML output into action cards

ML signals are useless until they become a specific, quantified action. The Coach engine
(`ML/insights/coach/`) is the layer that does that. It runs a five-step pipeline:

```text
HomeSnapshot
  → correlator   (join NILM + Occupancy + K-Means + Routine + IF into named Situations)
  → quantifier   (attach RM impact via tnb_tariff.marginal_cost_rm + joint confidence)
  → templates    (deterministic card text — no LLM on the load-bearing path)
  → ranker       (score = √impact × confidence × novelty × dismiss_decay × severity)
  → list[Card]   (top 2 surfaced, rest secondary)
```

The system ships **12 recommendation archetypes** organised into 5 families:

| Family | Archetypes |
|---|---|
| Waste | 1 left_on_empty, 2 phantom_standby, 3 simultaneous_peak_load |
| Tariff (Malaysia-specific) | 4 tou_switch, 5 rp4_tier_cliff, 6 peak_window_shift |
| Forecast | 7 bill_trending_high, 8 comparative_regression, 9 routine_shift |
| Context | 10 weather_correlated_ac, 11 anomaly_with_action |
| Capital | 12 inefficient_upgrade (links to ST efficiency registry) |

Design rules:
- Every numeric claim on a card traces to `raw_metrics` + a tariff call — auditable line by line.
- Templates are deterministic; an LLM is only used (optionally) for narrative weekly digests, never for numbers.
- Archetypes #4 and #5 use the TNB RP4 tariff model directly and are the strongest differentiators vs Sense / Bidgely / Emporia (none of which model TNB RP4).
- Weather context (#10) uses Open-Meteo (`ML/insights/coach/weather.py`), 1-hour disk cache, 9 Malaysian cities.

Routine-aware detection no longer has its own UI tab. Routine evidence is embedded
inside each Coach card under "Why this appeared" — see plan 05 §14.

## 25. ML summary

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
