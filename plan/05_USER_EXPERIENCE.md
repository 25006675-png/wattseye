# 05 — User Experience: What the User Sees

## 1. Purpose of this file

This file explains WattsEye from the user’s point of view.

It focuses on what the user sees, not the technical details behind it.

## 2. Main user promise

The user wants to know:

```text
What is using electricity?
How much is it costing me?
Am I wasting power?
Is something wrong with an appliance?
What should I do to reduce the bill?
```

WattsEye answers these questions through a dashboard and alerts.

The smarter version should feel like an energy coach, not only a meter.

Connectivity should feel dependable:

```text
Internet available: user logs in and can view synced history remotely.
Home WiFi: user logs in and sees live local dashboard data.
No router/internet: user logs in locally through the Pi hotspot and the system still monitors locally.
```

The dashboard must always make the data source clear:

```text
Live from home Pi
Synced 12 minutes ago
Cached local history
Demo/sample data
```

## 3. First-time setup concept

In a real product:

1. The device is installed inside the home's distribution board (DB box).
2. Two CT clamps are clipped around two existing wires inside the DB box:
   - Clamp #1 wraps the main feeder wire (whole-home)
   - Clamp #2 wraps the dedicated air-conditioner circuit wire
3. The device connects to WiFi.
4. The user opens the dashboard on phone or laptop.
5. The system starts learning and displaying electricity usage. Over the first 1–2 weeks, it learns the home's specific routines and AC signature.

For the prototype:

1. We use a demo box instead of a real house DB box.
2. The demo box has a split internal bus: one branch for general appliances, one dedicated branch for the AC SIMULATOR outlet.
3. We plug appliances into the demo box's two zones to show how the two clamps behave differently.
4. The dashboard shows live readings.

## 4. Main dashboard screen

The dashboard should show:

- Current total power usage
- Estimated cost today
- Projected monthly bill
- Appliance breakdown
- Energy efficiency / waste score
- Routine-aware insights
- Appliance health status
- Recommended action
- Alerts or warnings
- Recent usage graph

Example:

```text
Total Power Now: 3700W
Today's Cost: RM 3.20
Projected Monthly Bill: RM 96.00
Waste Score: 81/100

Appliances:
Kettle: 2000W   (NILM estimate)
Fridge: 120W   (NILM estimate)
Lamp:    15W   (NILM estimate)
AC:    1500W   (Direct measurement)
         NILM estimate 1450W | Direct 1500W | Agreement 96.7%

Insight:
Your AC usage is 22% higher than your normal weekday pattern.
```

## 5. Appliance cards

Each appliance can be shown as a card.

Example card:

```text
Kettle
Status: ON
Power: 2000W
Estimated cost: RM 1.10/hour
```

Another example:

```text
Fridge
Status: Normal
Power: 120W
Pattern: regular cycling
Health: 92/100
```

AC card (uses dedicated sensor + NILM comparison):

```text
Air Conditioner
Status: ON
Power: 1500W (Direct sensor)
AI estimate: 1450W
Agreement: 96.7%
Estimated cost: RM 0.85/hour
```

## 6. Smart insight cards

The dashboard should include smart insight cards that translate data into action.

Examples:

```text
Bill Forecast
Projected monthly bill: RM128
Status: 22% higher than usual
Main reason: extra AC usage between 2 PM and 5 PM
```

```text
Energy Coach
Recommendation: enable AC auto-off after 20 minutes empty.
Estimated saving: RM18/month.
```

```text
Standby Power
Your home uses around 85W when no major appliance is active.
Estimated standby cost: RM18/month.
```

## 7. User flow: checking live usage

```text
User opens dashboard
↓
User sees total power
↓
User sees appliance breakdown
↓
User understands which appliance is using the most power
```

The goal is to make electricity usage visible.

## 8. User flow: appliance turns on

Example with kettle:

```text
User turns on kettle
↓
Total power rises
↓
System detects kettle pattern
↓
Dashboard updates kettle card
↓
User sees kettle power and cost
```

This should happen quickly enough to feel live.

## 9. User flow: AC left on in empty room

```text
Dedicated AC clamp directly confirms AC is running (exact, no AI guess)
↓
mmWave sensor detects nobody in room
↓
System waits for a safe threshold, such as 30 minutes
↓
System sends WhatsApp alert
↓
User replies YES
↓
System turns off AC using IR signal
↓
Dedicated AC clamp confirms zero power → dashboard updates and confirmation WhatsApp is sent
```

Example message:

```text
AC has been running in an empty room for 30 minutes.
Do you want to turn it off?
Reply YES to turn off.
```

## 10. User flow: routine-aware waste alert

```text
System learns normal household routine
鈫?AC runs outside normal schedule
鈫?Room is empty
鈫?Projected bill is trending high
鈫?System sends higher-priority alert with estimated avoidable cost
```

Example message:

```text
AC has been running in an empty room for 30 minutes.
This is outside your usual AC schedule and may add around RM1.20 today.
Turn it off?
```

## 11. User flow: abnormal appliance warning

```text
System learns normal appliance behavior
↓
Appliance starts behaving differently
↓
Anomaly score increases
↓
Dashboard shows warning
```

Example warning:

```text
Fridge behavior looks unusual.
It is cycling more often than normal.
Consider checking the compressor or door seal.
```

## 12. User flow: bill forecast and recommendation

```text
System compares current month usage with normal pattern
鈫?Projected bill is higher than usual
鈫?System identifies the biggest cause
鈫?Dashboard recommends one concrete saving action
```

Example:

```text
Your projected bill is RM128, about 22% higher than usual.
Most extra usage came from AC in the afternoon.
Suggestion: enable empty-room auto-off.
```

## 13. What the user should not need to understand

The user should not need to understand:

- CT clamp physics
- ADC conversion
- TensorFlow Lite
- MQTT
- Signal conditioning
- NILM model architecture
- Routine-learning algorithm
- Anomaly score calculation

The user only needs to see useful results.

## 14. Dashboard pages suggestion

### Page 1 — Home overview

Shows:

- Total usage now
- Today’s cost
- Monthly projection
- Top active appliances

### Page 2 — Appliance breakdown

Shows:

- Appliance cards
- Power usage
- Usage history
- Estimated cost

### Page 3 — Alerts

Shows:

- AC left on
- Unusual appliance behavior
- High usage warning
- Routine-aware waste alerts
- Estimated avoidable cost

### Page 4 — Insights

Shows:

- Most expensive appliance today
- Usage trend
- Saving tips
- Bill forecast
- Waste score
- Energy coach recommendations
- Standby power estimate

### Page 5 - Appliance health

Shows:

- Appliance health score
- Normal vs unusual behavior
- Possible causes
- Suggested check

### Optional page - Account and sync

Only needed if the cloud layer is enabled.

Shows:

- Login / register / logout
- Current user email
- Selected home/device
- Data source: live local, synced cloud, cached, or demo
- Cloud sync status
- Last successful sync time
- Number of local readings waiting to sync

Cloud status wording should be calm and clear:

```text
Cloud sync paused. Local monitoring is still running.
```

Not:

```text
System offline.
```

### Optional page - Smart plugs

Shows:

- Paired smart plugs
- Appliance name assigned to each plug
- Current plug power
- Online/offline status
- Whether the plug reading is used as exact data or validation data

## 15. Good UX wording

Use simple user-friendly language.

Instead of:

```text
NILM disaggregation confidence is 0.82.
```

Say:

```text
Kettle likely turned on.
```

Instead of:

```text
Anomaly score exceeded isolation threshold.
```

Say:

```text
This appliance is behaving differently from usual.
```

Instead of:

```text
Routine model deviation detected.
```

Say:

```text
This usage is unusual for your normal weekday pattern.
```

## 16. What the dashboard should prove in demo

For the prototype, the dashboard should prove:

1. Total power changes when appliances turn on.
2. The system can estimate appliance usage.
3. The user can understand cost and usage easily.
4. The system can send useful alerts.
5. The system can forecast bills and recommend a useful action.
6. The product feels practical, not just technical.

## 17. User experience summary

The user experience is:

```text
Open dashboard -> see appliance usage -> understand routine and cost impact -> receive useful recommendations -> save electricity and detect problems early
```

The user should feel:

```text
Now I finally know where my electricity bill is coming from.
```
