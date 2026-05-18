# 08 — Q&A Defense: How to Answer Difficult Questions

## 1. Purpose of this file

This file prepares the team for questions from judges, lecturers, or teammates.

The goal is to answer clearly and honestly without overclaiming.

## 2. Q: Why not just use smart plugs?

Smart plugs need one device per appliance. That becomes expensive and inconvenient — a 15-appliance home needs 15 plugs.

They also cannot easily monitor hardwired appliances like AC, water heaters, or built-in ovens.

WattsEye uses a hybrid sensing architecture: one dedicated CT clamp on the air-conditioner circuit (the biggest single load in a Malaysian home, and the load smart plugs handle worst because most ACs are hardwired or use special sockets) plus one whole-home clamp with AI disaggregation for everything else.

Two clamps cover what 10–15 smart plugs would, with no per-appliance setup. Users who specifically want per-device tracking on something like a gaming PC can still add an optional smart plug — we treat smart plugs as a complement, not a competitor.

## 3. Q: How can one sensor detect many appliances?

The main feeder clamp reads the total electricity usage.

Each appliance creates a different power pattern.

For example:

- Kettle creates a sudden high-power block.
- Fridge cycles on and off.
- Microwave has short high-power usage.
- Washing machine has multiple stages.

The AI learns these patterns and estimates which appliances are active inside the total signal. For the AC specifically, we use a separate dedicated clamp because inverter ACs (Malaysia's dominant type) have no clean signature for NILM to recognize.

## 3a. Q: Why have a second clamp dedicated to AC?

Three reasons:

1. **Inverter ACs are NILM's worst case.** They continuously vary their compressor speed based on temperature feedback, so there is no clean on/off event for the model to detect. Most ACs sold in Malaysia today are inverter type.
2. **AC is the biggest single load** in a Malaysian home (30–50% of the bill). The appliance worth measuring most accurately is also the one NILM struggles with most — a dedicated sensor solves both problems at once.
3. **It enables a live cutoff demo** — when the IR system commands the AC off, the dedicated clamp confirms power actually dropped to zero. Pure NILM cannot reliably do this on stage.

The dedicated AC clamp also makes NILM better: by subtracting the known AC reading from the main signal, NILM gets a cleaner input for detecting non-AC appliances.

## 4. Q: Is the AI always accurate?

No.

NILM is an estimation problem.

Accuracy depends on:

- Appliance type
- Signal quality
- Training data
- Calibration
- Whether appliances overlap
- Similarity between training homes and real home

We improve reliability by:

- Starting with high-confidence appliances for the live demo
- Calibration and fine-tuning with demo rig data
- Using the dedicated AC clamp to remove the most NILM-hostile load (inverter AC) from the input signal before running disaggregation
- Showing a live agreement % between NILM's AC estimate and the direct AC reading, so users can see the model's accuracy in real-time on the AC and infer general health from it

## 4a. Q: What does the live agreement % actually prove?

The agreement percentage compares the NILM model's AC estimate with the direct measurement from the dedicated AC clamp. It is direct proof that the AI is working correctly for the AC specifically, and a strong credibility indicator that the same model is working reasonably for other appliances.

It does *not* prove every individual appliance estimate is accurate to the same degree. We are honest about that: it is a live competence indicator, not a per-appliance guarantee.

## 5. Q: What if two appliances turn on at the same time?

That is harder.

If two appliances overlap, their patterns combine.

The model may still estimate them if it has seen similar combinations during training.

But the prediction may be less confident.

That is why we smooth predictions and show likely appliance usage rather than pretending it is always perfect.

## 5a. Q: What if there are two of the same appliance (e.g., two lamps, two kettles, two ACs)?

Honest answer: pure NILM cannot reliably tell two identical appliances apart from one combined load. Two 1500W kettles look the same as one 3000W kettle from the main feeder signal.

How we handle each case:

- **Two identical small/medium appliances** (e.g., two LED lamps, two phone chargers): we report them as combined power for that appliance type. *"Lamps: 30W (2 active)"* is the honest framing, not *"Lamp A: 15W, Lamp B: 15W"*.
- **Two AC units on the same dedicated breaker**: the AC clamp on that circuit reports their combined power. Cannot be separated, but Pillar 2 ("at least one AC is running in an empty room") still works.
- **Two AC units on separate breakers** (more common — code-compliant Malaysian wiring puts each AC on its own breaker): one dedicated clamp per AC circuit. The architecture scales linearly — N AC units = N+1 clamps (one main + N AC clamps). Each AC is measured individually.
- **Two appliances of similar wattage but different type** (e.g., kettle vs hair dryer, both ~1500W resistive): NILM may confuse them based on power magnitude alone. We mitigate using multi-feature classification (duration, harmonics, time-of-day priors).

So the honest answer is: NILM groups appliances by class, not by physical unit. If you want per-unit tracking for two identical appliances, that is where an optional smart plug on one of them makes sense.

## 6. Q: Why train around 10 models if the demo only focuses on a few?

We train around 10 models to show scalability.

But the live demo focuses on high-confidence appliances that we can test reliably on stage.

The supplementary models support the product vision and show that the architecture can expand to real household coverage.

This is a better prototype strategy than trying to make all 10 models live-perfect immediately.

## 7. Q: Which models are demo-critical?

Demo-critical models are the ones we can physically verify during the live demo.

Examples:

- Kettle
- Lamp
- Hair dryer
- Phone charger
- Microwave, if available

These are easier to show and easier for judges to understand.

## 8. Q: Which models are supplementary?

Supplementary models include appliances that matter in real homes but may be harder to demo live.

Examples:

- AC
- Fridge
- Washing machine
- Water heater
- Rice cooker
- Iron
- Fan

They can be shown using validation results, recorded demos, or dashboard simulation.

## 9. Q: Where is the Malaysian training data?

For the prototype, we use public NILM datasets to avoid depending on slow data collection.

We choose datasets that cover common appliances and regional similarities where possible.

For Malaysian deployment, local fine-tuning would be part of the next phase.

The prototype proves the architecture first.

## 10. Q: Why use public datasets?

Because collecting clean appliance-level electricity data is time-consuming.

To train from scratch, we would need many days or weeks of labeled data.

Public datasets let us build a working model faster.

We can still collect demo rig data for calibration and fine-tuning.

## 11. Q: Why use Raspberry Pi?

Raspberry Pi is powerful enough to:

- Read sensor data
- Run lightweight AI models
- Host a dashboard
- Store readings
- Communicate with other devices

It is also small, affordable, and suitable for edge computing.

## 12. Q: Why use ESP32 as well?

The Raspberry Pi handles higher-level computing.

The ESP32 handles real-time sensor and control tasks.

ESP32 is better for:

- Reading mmWave sensor
- Sending IR remote signals
- Fast GPIO control

So the Pi is the brain, and ESP32 is the helper controller.

## 13. Q: Why not put everything on the cloud?

Cloud processing needs internet.

Electricity monitoring and alerts should still work locally.

Running models on the Raspberry Pi improves:

- Privacy
- Responsiveness
- Offline capability
- Demo reliability

Cloud can be added later for analytics, but the core system can run locally.

## 14. Q: Is the system safe?

The concept can be safe if built properly.

The CT clamp measures current without cutting the live wire.

However, the demo box still involves mains electricity, so we must:

- Use a fuse
- Keep live conductors enclosed
- Connect earth properly
- Separate high-voltage and low-voltage parts
- Get a qualified person to inspect before power-on

Safety is a hardware design requirement, not an optional feature.

## 15. Q: Can the system control AC automatically?

The system can send IR signals like a normal AC remote.

For the prototype, we demonstrate the complete loop live:

- mmWave detects empty room
- The dedicated AC clamp confirms AC is drawing power
- WhatsApp alert is sent to the user's phone
- User replies YES
- ESP32 fires IR command
- In the demo rig: TSOP1838 IR receiver detects the signal → relay opens → power to AC SIMULATOR outlet is cut → dedicated AC clamp confirms zero power
- In a real home: the AC unit's own IR receiver acts on the signal directly (no relay needed)

In a real product, user confirmation and safety settings should be included before automatic control.

## 16. Q: What exactly is live in the demo?

A strong answer:

```text
The live demo focuses on real-time power sensing, dashboard update, and selected demo-core appliance recognition.
Some supplementary models and AC scenarios may be shown through recorded validation or simulation because they are harder to reproduce safely on stage.
```

This is honest and defensible.

## 17. Q: What is the biggest technical risk?

The biggest risk is the gap between public training data and our real demo hardware data.

The model may work well on datasets but need calibration for our sensor and appliances.

We reduce this risk by:

- Starting with easy demo appliances
- Calibrating with known loads
- Fine-tuning using demo rig data
- Having backup visualizations

## 18. Q: Why not use a very advanced model like Transformer?

For a prototype, reliability and explainability matter more than model complexity.

Sequence-to-point CNN is already a known NILM approach.

It is lighter and easier to run on Raspberry Pi.

Advanced models can be future work.

## 19. Q: How does the system estimate cost?

The system estimates energy usage over time.

Energy is calculated from power:

```text
Energy = Power × Time
```

Then it applies electricity tariff assumptions to estimate cost.

For prototype purposes, cost is an estimate, not an official bill.

## 20. Q: What is the main innovation?

The innovation is not just measuring electricity.

The innovation is combining:

```text
Hybrid sensing (dedicated AC + whole-home NILM) + AI appliance disaggregation + routine-aware insights + bill forecasting + energy coaching + occupancy-aware control + verified IR cutoff + early anomaly warning
```

The hybrid sensing architecture is the key engineering choice. Pure NILM struggles with inverter ACs (Malaysia's dominant AC type), and pure dedicated-clamp systems can't cover non-AC appliances without a smart plug each. WattsEye combines them: dedicated sensing where it matters (AC), AI disaggregation everywhere else. This turns raw electricity data into practical decisions.

## 21. Q: What makes the system smart beyond detecting appliances?

Appliance detection is only the first layer.

The smarter layer combines:

- Power pattern recognition
- Occupancy sensing
- Household routine learning
- Cost forecasting
- Waste scoring
- Appliance health monitoring

Example:

```text
The system detects AC usage.
It checks whether the room is empty.
It compares the usage with the normal schedule.
It estimates the cost impact.
Then it recommends a specific action.
```

So WattsEye is not only saying:

```text
AC is on.
```

It can say:

```text
AC has been running in an empty room outside your usual schedule.
This may add around RM1.20 today. Turn it off?
```

## 22. Q: Does routine-aware detection replace the appliance ML model?

No.

They answer different questions.

```text
Appliance ML: What appliance is probably running?
Routine-aware logic: Is this behavior normal for this home at this time?
```

The best system uses both.

For example:

```text
AC detected as ON + room empty + unusual time + projected bill high = stronger alert
```

## 23. Q: How can we implement routine-aware detection for the prototype?

We do not need a complex model at first.

A prototype can use simple historical baselines:

- Average usage by hour of day
- Average usage by day of week
- Usual appliance start time
- Usual appliance duration
- Occupancy pattern by time
- Normal standby power level

Then the system compares live behavior with the baseline.

Example:

```text
If AC normally runs after 8 PM but runs at 2 PM while the room is empty, mark it as unusual.
```

## 24. Q: Is appliance health score a diagnosis?

No.

It is an early warning based on usage pattern changes.

Good wording:

```text
Fridge behavior looks unusual compared with its recent normal pattern.
Consider checking the door seal or compressor.
```

Avoid saying:

```text
Your fridge compressor is definitely broken.
```

## 25. Q: What should we not overclaim?

Do not claim:

```text
The system perfectly detects every appliance.
```

Do not claim:

```text
All 10 models are fully validated in Malaysian homes.
```

Do not claim:

```text
The prototype is ready for direct home installation without certification.
```

Do not claim:

```text
The system can perfectly know every household routine immediately.
```

Better claim:

```text
Routine-aware insights improve as the system collects local history.
For the prototype, we demonstrate the logic using stored sample data and selected live signals.
```

Better claim:

```text
The prototype demonstrates the architecture and validates the core idea using selected appliances, public NILM datasets, and live power sensing.
```

## 26. Best final defense sentence

```text
WattsEye is designed to prove that a hybrid sensing architecture — one dedicated CT clamp on the air-conditioner circuit plus a whole-home CT clamp with edge AI disaggregation — combined with routine-aware insights and occupancy-driven IR control, can give Malaysian users accurate AC monitoring, appliance-level breakdown, bill forecasts, waste prevention, energy recommendations, and verified live cutoff without requiring smart plugs on every appliance.
```
