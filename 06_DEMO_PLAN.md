# 06 — Demo Plan: What We Show During Presentation

## 1. Purpose of this file

This file explains how we should demonstrate WattsEye.

It focuses on what happens during the live demo.

## 2. Demo goal

The demo should prove the main idea:

```text
A dedicated sensor accurately tracks the AC, a whole-home sensor + AI estimates the rest, and the system can act on what it sees.
```

The stronger demo story should also show that WattsEye turns those estimates into useful decisions:

```text
Hybrid sensing -> appliance detection + AC validation -> routine context -> bill forecast -> waste alert -> live IR cutoff
```

The demo should not try to prove every future feature perfectly.

## 3. What must work live

Minimum live demo:

1. Dashboard opens.
2. Total power (from main clamp) and AC power (from AC clamp) are both shown.
3. A general-branch appliance turns on (e.g., kettle). Only main clamp reading rises.
4. AC-branch appliance turns on (hair dryer in AC SIMULATOR outlet). Both clamps rise. Agreement % between NILM AC estimate and direct AC reading is displayed.
5. At least one demo-core appliance is identified or highlighted by NILM.
6. Live AC cutoff: WhatsApp alert → user reply → IR signal → relay opens → AC SIMULATOR outlet goes to zero on both clamps → confirmation message back.
7. At least one smart insight is shown, such as projected bill, waste score, or energy coach recommendation.

## 4. Demo-core appliances

Choose appliances that are easy to bring and easy to understand.

Recommended:

- Kettle
- Lamp
- Hair dryer
- Phone charger
- Microwave, if safe and available

Kettle and hair dryer are especially useful because their power changes are large and obvious.

## 5. Supplementary appliances

These support the story but do not need to be live-perfect.

Examples:

- AC
- Fridge
- Washing machine
- Water heater
- Rice cooker
- Iron
- Fan

They can be shown through:

- Recorded results
- Dataset validation
- Dashboard mock data
- Future scalability explanation

## 6. Recommended demo sequence

### Part 1 — Introduce the problem

Say:

```text
Most people only see their total electricity bill, but they do not know which appliance caused it.
Smart plugs require one device per appliance — and they can't easily measure hardwired loads like AC.
Our system uses two clamps inside the DB box plus AI: one dedicated clamp for the AC (the biggest load), one main clamp + AI for everything else.
```

### Part 2 — Show the hardware

Show:

- Demo box (with labeled "AC SIMULATOR" outlet visible)
- Both CT clamps (main + AC)
- Raspberry Pi
- ESP32 with IR LED
- IR receiver + relay block on the AC branch
- Dashboard device

Explain simply:

```text
This first clamp watches the total electricity flow — that feeds our NILM AI for whole-home breakdown.
This second clamp wraps the AC's own dedicated wire — it gives us exact AC power directly, no AI needed.
Together they let our AI run cleaner AND let us prove its accuracy live on the dashboard.
```

### Part 3 — Baseline reading

Open dashboard.

Show normal baseline usage.

Example:

```text
Current total power: 200W
```

### Part 4 — Turn on kettle

Turn on kettle.

Expected result:

```text
Total power jumps to around 2000W+.
Kettle card becomes active.
```

Explain:

```text
The system detects the power pattern and estimates kettle usage.
```

### Part 5 — Turn on another appliance + show NILM vs direct AC agreement

Turn on a hair dryer in the AC SIMULATOR outlet (acts as the AC proxy on the dedicated branch).

Show dashboard update:

- Both clamps now read higher
- AC card shows: `NILM estimate 1450W | Direct sensor 1500W | Agreement 96.7%`

Explain:

```text
The hair dryer is on the dedicated AC branch, so both clamps see it.
Our AI estimates AC consumption from the main signal alone — it says 1450W.
Our dedicated sensor measures 1500W exactly. Agreement is 96.7%.
This is live proof that our AI is working — you can watch the percentage update in real time.
```

Then turn on a lamp on the general branch. Only main clamp rises; AC clamp stays at its previous reading. This demonstrates the separation: the AC clamp is specific to its circuit, the NILM clamp sees everything.

### Part 6 — Live AC empty-room cutoff (the flagship Pillar 2 moment)

This is now a fully live flow, end to end on stage.

Setup:

- Hair dryer (AC proxy) is still running in the AC SIMULATOR outlet.
- mmWave sensor has been triggered into "room empty" state (cover the sensor with a sticker or step out of its field).

Flow:

```text
1. mmWave reports: room empty
2. AC clamp confirms: AC is still drawing 1500W
3. After short delay, WhatsApp alert arrives on judge's phone:
   "AC is running in an empty room. Reply Y to turn off. Estimated saving: RM 0.85/hour."
4. Judge replies "Y"
5. Pi tells ESP32 via MQTT to fire the IR off command
6. ESP32 blinks the IR LED (visible LED indicator confirms transmission)
7. IR receiver on the demo rig detects the signal
8. Relay opens — power to AC SIMULATOR outlet is cut
9. Hair dryer audibly stops
10. Dashboard updates: AC clamp now reads 0W, main clamp drops by 1500W
11. Confirmation WhatsApp comes back: "AC turned off. Saved approximately RM 0.85 so far."
```

This is the moment pure NILM cannot do. The dedicated AC clamp + IR receiver + relay loop is what makes this provably live, not simulated.

### Part 7 - Show smart insight layer

Show prepared dashboard data if there is not enough real history yet.

Examples:

```text
Projected bill: RM128, 22% higher than usual
Waste score: 81/100
Main waste: AC ran in an empty room for 42 minutes
Recommendation: enable AC auto-off after 20 minutes empty
Estimated saving: RM18/month
```

Explain:

```text
The system does not only detect appliances. It learns normal routines, checks occupancy, forecasts cost, and recommends actions.
```

### Part 8 - Show supplementary model coverage

Show a slide or notebook result saying:

```text
We train around 10 appliance models.
Live demo focuses on high-confidence demo appliances.
Supplementary models support real household coverage, such as AC, fridge, washer, and water heater.
```

### Part 9 - End with impact

Say:

```text
WattsEye helps users understand electricity usage, predict bills, reduce waste, and detect appliance problems early without installing smart plugs everywhere.
```

## 7. What is live and what can be simulated

Be clear internally.

| Feature | Live or simulated? | Notes |
|---|---|---|
| Total power sensing (Clamp #1) | Live | Must work |
| Direct AC power sensing (Clamp #2) | Live | Must work |
| NILM vs Direct AC agreement % | Live | Pillar 1 validation moment |
| Kettle detection | Live preferred | Demo-core |
| Lamp / hair dryer detection | Live preferred | Demo-core |
| AC detection (hair dryer as proxy) | Live | Via dedicated clamp, exact |
| WhatsApp alert | Live | Twilio sandbox sufficient |
| IR AC off → relay cutoff | Live | Pillar 2 flagship moment |
| Fridge anomaly | Simulated/recorded | Better as dashboard story |
| Bill forecast / waste score | Simulated or based on stored sample data | Good smart-layer proof |
| Routine-aware insight | Simulated or based on stored sample data | Needs history, so sample data is acceptable |

## 8. Backup plan if ML fails live

If live appliance recognition is unstable:

- Still show live total power measurement.
- Show pre-recorded appliance disaggregation notebook.
- Show dashboard using prepared sample data.
- Explain that live integration is in progress but the model pipeline is validated separately.

This is safer than having the whole demo fail.

## 9. Demo script sample

```text
This is WattsEye, a hybrid electricity intelligence system for Malaysian homes.

Instead of putting a smart plug on every appliance, we use two clamps inside the DB box.
The first clamp wraps the main feeder — it sees everything. We use AI (NILM) to break that down into individual appliances.
The second clamp wraps the AC's dedicated wire — it measures the AC exactly.

Why two clamps? In Malaysia, most ACs sold today are inverter type. Inverter ACs continuously vary their power, which makes them very hard for AI alone to detect reliably. A dedicated clamp solves this. AC is also the biggest single load in a Malaysian home — 30 to 50 percent of the bill — so it's worth measuring exactly.

Look at the dashboard. The baseline is around 200 watts.

When I turn on this kettle, the total power jumps. Our NILM model recognizes the pattern and labels it as kettle. The AC clamp stays at zero — the kettle isn't on the AC circuit.

Now I plug a hair dryer into the AC SIMULATOR outlet — it represents the AC. Both clamps now rise. And here's the proof our AI is working: NILM estimates 1450 watts, the dedicated sensor measures 1500 watts. We're 96.7 percent in agreement, live on stage.

Now watch this. The mmWave sensor says nobody is in the room, but the AC is still on. The system sends a WhatsApp alert to my phone. I reply Y. The ESP32 fires the IR off command — and the AC simulator cuts off. Dashboard confirms zero. Saved about 85 sen so far.

This is the architecture: one clamp for whole-home coverage, one clamp for the load that matters most. We don't replace smart plugs everywhere — we replace them where it counts, and use AI to fill the rest. Plus a smarter layer that forecasts bills, scores waste, and coaches the user on how to save.
```

## 10. Things not to overclaim

Avoid saying:

```text
All 10 models work perfectly live.
```

Better say:

```text
We train around 10 models to show scalability, but the live demo focuses on high-confidence appliances.
```

Avoid saying:

```text
The AI is always accurate.
```

Better say:

```text
The model estimates appliance usage based on learned electrical patterns, and accuracy improves with calibration and local data.
```

## 11. Demo success criteria

The demo is successful if judges understand:

1. Why one sensor is useful.
2. How AI separates appliance patterns.
3. How the dashboard gives practical value.
4. Why this is better than many smart plugs.
5. How routine-aware insights, bill forecasting, and recommendations make the system smarter.
6. How the system can scale beyond the prototype.

## 12. Demo summary

The demo should be simple:

```text
Show sensor -> turn on appliance -> show dashboard -> explain AI -> show smart insight -> show alert/control vision
```

Do not overload the live demo with too many appliances.

A clean demo with two strong appliances is better than a messy demo with 10 unstable predictions.
