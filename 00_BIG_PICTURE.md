# 00 — Big Picture: What Are We Building?

## 1. Project name

**WattsEye**

## 2. One-sentence explanation

WattsEye is a home electricity monitoring system that uses a **hybrid sensing architecture** — one dedicated sensor on the air conditioner circuit plus a whole-home main sensor with **AI disaggregation** — to estimate which appliances are using power, how much they cost, and whether something wasteful or abnormal is happening.

## 3. The problem

Most homes only know their total electricity bill at the end of the month.

The problem is:

- Users do not know which appliance is wasting electricity.
- Users only see the total bill, not appliance-level usage.
- Smart plugs require one plug per appliance.
- Smart plugs cannot easily monitor hardwired appliances like air conditioners, water heaters, or built-in systems.
- Users may forget to turn off AC, heaters, or other high-power appliances.
- Appliances may become inefficient or faulty before users notice.

## 4. Our solution

Instead of using many smart plugs, WattsEye uses **two CT clamp sensors** inside the home's distribution board (DB box):

1. **Main clamp** wraps around the main feeder wire and reads the **total** electricity usage of the whole home.
2. **AC clamp** wraps around the dedicated air-conditioner circuit and reads **only the AC** directly.

Then machine learning (NILM — Non-Intrusive Load Monitoring) disaggregates the main signal into individual appliances. The dedicated AC reading is used both as a precise AC measurement and as ground truth to validate the AI in real-time.

Example:

```text
Main clamp signal
= AC + fridge + kettle + lamp + microwave + other appliances

AC clamp signal
= AC only (exact, no AI estimation needed)
```

Why two clamps and not one:

- **Inverter ACs** dominate Malaysian homes today and have no clean NILM signature — AI alone is unreliable for them. A dedicated clamp solves this completely.
- AC is the **biggest load** in a Malaysian home (30–50% of bill) and the load most worth measuring accurately.
- Code (MS IEC 60364) requires AC to be on its own dedicated circuit, so a dedicated clamp can be installed at the DB box **without rewiring the home**.

The AI looks at the shape of electricity usage on the main signal and estimates which non-AC appliance is active.

## 5. Simple analogy

Imagine standing outside a room where many people are talking.

At first, you hear one messy sound.

But if you know each person’s voice, you can guess who is speaking.

WattsEye works similarly:

- The total electricity signal is the messy sound.
- Each appliance has its own “electricity voice.”
- The AI learns those voices.
- The system estimates which appliance is using power.

## 6. What makes this different from smart plugs?

| Smart Plug System | WattsEye |
|---|---|
| Needs one smart plug per appliance | Two clamps cover the whole home (one main + one AC) |
| Cannot easily monitor hardwired appliances | Wraps non-invasively around any wire — works for hardwired AC, water heater, oven |
| More setup work per appliance | One-time installation at the DB box |
| Shows usage only for plugged devices | Whole-home breakdown via NILM + exact AC measurement |
| Hardware-heavy | Hybrid: light hardware + smart AI |

WattsEye does not try to replace every smart plug. Instead, it focuses on the loads that actually move the bill — air conditioning (exact measurement) plus other major appliances (NILM estimation). A user can still add optional smart plugs later for specific high-interest devices.

## 7. Three main product pillars

Visual reference:

![WattsEye three-pillar product map](assets/three-pillars-map.svg)

### Pillar 1 — Appliance-level electricity breakdown

The dashboard shows estimated power usage, cost, timing, and explanation for each appliance.

Example:

```text
Kettle: 2000W   (NILM estimate)
Fridge: 120W   (NILM estimate)
AC:     900W   (Direct measurement, exact)
Lamp:    15W   (NILM estimate)
```

Because the AC has a dedicated sensor, the dashboard can show the AI's NILM estimate next to the direct measurement to display real-time accuracy:

```text
AC: NILM estimate 870W | Direct sensor 900W | Agreement 96.7%
```

It can also show an event timeline and confidence explanation:

```text
7:05 AM - Kettle likely turned on
Reason: sudden 2000W rise lasting around 3 minutes
```

### Pillar 2 — Smart waste prevention

The system can detect waste by combining appliance detection, occupancy, routines, and cost forecasting.

Example situations:

```text
AC is running, but nobody is in the room.
AC usage is higher than usual for this time of day.
This month's bill is projected to be higher than normal.
```

Then it can send a useful alert or recommendation:

```text
AC is on in an empty room. Turn it off?
```

If the user says yes, the ESP32 sends an infrared signal to turn off the AC. In a real home, the IR signal is received by the AC unit directly. In the demo rig, an IR receiver paired with a relay receives the signal and cuts power to the AC-simulator outlet, so judges can see the cutoff happen live on stage (dashboard confirms zero power on the AC circuit).

### Pillar 3 — Appliance abnormality warning

The system can learn normal appliance behavior and give appliance health warnings.

If an appliance starts behaving differently, the system can warn the user.

Example:

```text
Your fridge compressor seems to be cycling more often than usual.
This may indicate inefficiency or early fault.
```

## 8. Smart insight layer

The smarter version of WattsEye is not only appliance detection.

It adds a decision layer after the AI predictions:

```text
Power patterns
-> appliance predictions
-> occupancy status
-> household routine patterns
-> cost and health analysis
-> alerts, scores, forecasts, and recommendations
```

Examples of smart insights:

- Bill forecast: projected monthly cost before the bill arrives
- Waste score: daily score based on avoidable electricity use
- Energy coach: practical recommendations to save money
- Routine-aware alerts: warnings only when behavior is unusual for that home
- Appliance health score: early warning when usage patterns drift from normal
- Standby power detection: estimate always-on background load

## 9. What we are building for the prototype

For the prototype, we are not trying to build a perfect full commercial product.

We are building a working demonstration that proves the idea:

```text
Two clamps (main + AC) -> total + exact AC data -> AI disaggregation + validation -> smart insight layer -> dashboard -> live alerts + IR cutoff
```

## 10. Important prototype strategy

We may train around **10 appliance models**, but not all of them are equally important for the live demo.

We split them into:

### Demo-core models

These are the appliances we want to show live.

Examples:

- Kettle
- Lamp
- Hair dryer
- Phone charger
- Microwave, if available

### Supplementary models

These support the pitch and show scalability.

Examples:

- Air conditioner
- Fridge
- Washing machine
- Water heater
- Rice cooker
- Iron
- Fan

The live demo focuses on appliances that are easy to test on stage. The extra models show that the system can scale to a real home.

## 11. The project in one simple line

**WattsEye is like a Fitbit for your house: a dedicated sensor accurately tracks the AC (the biggest load), an AI sensor disaggregates the rest of the home, and your phone shows usage, forecasts, waste, recommendations, and early warnings — without putting a smart plug on every appliance.**

## 12. Architecture coverage tiers

WattsEye combines three coverage tiers in one product:

| Tier | Approach | What it covers | Accuracy |
|---|---|---|---|
| Tier 1 | Dedicated CT clamp at DB box | Air conditioner circuit | Exact (direct measurement) |
| Tier 2 | NILM disaggregation on main feeder | Major appliances (kettle, microwave, washer, water heater, fridge, etc.) | Estimated (AI) |
| Tier 3 | Baseline subtraction | Standby load + small electronics | Aggregate only |
| Optional | Smart plug integration | Specific high-interest devices the user wants tracked individually | Exact per device |

Each tier covers what it does best. The dedicated AC clamp specifically handles inverter ACs (Malaysia's dominant AC type), which NILM alone is unreliable on.
