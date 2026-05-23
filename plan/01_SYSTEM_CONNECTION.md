# 01 — System Connection: How Everything Connects

## 1. Purpose of this file

This file explains how all parts of WattsEye connect together.

This is the master map of the system.

By the end of this file, you should understand:

- What happens when an appliance turns on
- How the electricity sensor becomes data
- How the data goes into the AI model
- How routine and cost context become smart insights
- How the dashboard gets updated
- How the AC control and WhatsApp alert fit into the system

## 2. The full system flow

Visual reference:

![WattsEye system connection flow](assets/system-connection-flow.svg)

```text
Appliance turns on
↓
Main wire current changes (and if AC, the AC branch current also changes)
↓
Two CT clamps sense the current change:
  • Clamp #1 (main feeder) — sees everything combined
  • Clamp #2 (AC branch)   — sees only AC
↓
Signal conditioning circuits (one per clamp) make the signals safe and readable
↓
ADS1115 converts analog signals into digital numbers (A0 = main, A1 = voltage, A2 = AC)
↓
Raspberry Pi reads the numbers
↓
Raspberry Pi calculates power in watts (total power + direct AC power)
↓
Raspberry Pi subtracts AC reading from main signal → cleaner NILM input
↓
Power readings + AC reading are stored as a time sequence
↓
NILM models estimate non-AC appliance usage on the residual signal
↓
Dashboard updates: NILM appliance estimates + direct AC reading
↓
If needed, WhatsApp alert or IR cutoff is triggered
↓
IR signal → real AC unit (in real home) OR → IR receiver + relay (in demo rig)
```

Important addition:

```text
The AI does not stop at appliance detection.
The Raspberry Pi also compares predictions with occupancy, time of day, past routines, and cost assumptions before deciding what insight or alert to show.
```

## 3. The main components

| Component | Simple role |
|---|---|
| CT clamp #1 (main feeder) | Senses total household current for NILM |
| CT clamp #2 (AC branch) | Senses AC current directly (exact, no AI needed) |
| Signal conditioning circuits | One per clamp — makes clamp signals safe for electronics |
| ZMPT101B voltage sensor | Measures mains voltage safely |
| ADS1115 (4-channel) | Converts both clamp signals + voltage into digital numbers |
| Raspberry Pi | Main brain: reads data, runs AI, serves dashboard |
| ESP32 | Helper controller: handles occupancy sensor and IR transmit |
| LD2410 mmWave sensor | Detects whether someone is in the room |
| IR LED + transistor | Sends AC remote-control signal |
| TSOP1838 IR receiver + relay | Demo rig only — receives IR and cuts power to AC SIMULATOR outlet |
| MQTT | Device communication system between Pi and ESP32 |
| Flask dashboard | Website shown on user phone/laptop |
| Twilio | Sends WhatsApp alerts |
| Local database | Stores historical readings, predictions, occupancy, alerts, and routines |
| Optional smart plugs | Exact readings for selected plug-in devices |
| Optional Supabase cloud | Login, remote history sync, and backup storage |

## 4. Hardware-to-software connection

The hardware does not directly “know” which appliance is on.

The hardware only measures the total electricity signal.

The software and AI interpret that signal.

```text
Hardware gives: total power over time
AI gives: estimated appliance breakdown
Smart insight engine gives: forecasts, waste alerts, health warnings, and recommendations
Dashboard gives: user-friendly display
```

## 5. Why hybrid sensing works

The main clamp sees the total usage of the whole system.

Example:

```text
Base usage: 200W
Kettle turns on: total becomes 2200W
Kettle turns off: total returns to 200W
```

The AI does not need a separate sensor on the kettle. It learns that this kind of sudden 2000W jump looks like a kettle.

The dedicated AC clamp adds one important capability the main clamp alone can't reliably give:

- **Inverter ACs** (dominant in Malaysian homes) have no clean NILM signature — they ramp power continuously based on temperature feedback. The main clamp + AI alone struggles to detect them reliably.
- The dedicated AC clamp solves this completely: AC is whatever flows through the AC branch wire — no AI inference needed.
- The AC clamp reading also lets us subtract a known load from the main signal, giving NILM a cleaner input for everything else.

Different appliances create different power patterns:

| Appliance | Typical pattern |
|---|---|
| Kettle | Sudden high-power flat block |
| Fridge | Repeated on-off cycling |
| AC | Longer cycle, sometimes ramping or cycling |
| Microwave | High power with short active period |
| Washing machine | Multi-stage pattern |
| Phone charger | Low power, small pattern |

## 6. Raspberry Pi and ESP32 relationship

The system uses two computing boards because they have different strengths.

### Raspberry Pi

The Raspberry Pi is the main computer.

It handles:

- Reading power data
- Running AI models
- Hosting dashboard
- Storing data
- Sending WhatsApp requests
- Making higher-level decisions
- Learning household routines and generating smart insights

### ESP32

The ESP32 is the fast helper controller.

It handles:

- Reading the mmWave occupancy sensor
- Sending infrared commands to AC
- Receiving commands from the Raspberry Pi

## 7. Why not use only Raspberry Pi?

The Raspberry Pi can do many things, but it is not always best for fast sensor control and precise signal output.

The ESP32 is better for:

- Simple real-time sensor reading
- Controlling pins quickly
- Sending IR remote signals
- Staying responsive

So we use:

```text
Raspberry Pi = manager / brain
ESP32 = worker / hands
```

## 8. MQTT communication

MQTT is like a group chat for devices.

The Raspberry Pi runs the MQTT server, called Mosquitto.

The ESP32 joins this “chat.”

Example messages:

```text
ESP32 publishes: room/occupancy = empty
Pi publishes: ac/command = OFF
ESP32 receives OFF and sends IR signal
```

## 9. Example: kettle turns on

Step-by-step:

1. Kettle turns on.
2. Electricity usage increases quickly.
3. CT clamp senses a stronger magnetic field around the wire.
4. The clamp outputs a small signal.
5. The signal conditioning circuit makes it safe.
6. ADS1115 converts the signal into numbers.
7. Raspberry Pi reads the numbers.
8. Raspberry Pi calculates power in watts.
9. Power sequence shows a sudden jump.
10. Kettle model recognizes the pattern.
11. Dashboard shows kettle activity.

## 10. Example: AC left on in empty room

Step-by-step:

1. AC is running. The dedicated AC clamp directly confirms AC is drawing power (no AI guessing needed).
2. mmWave sensor says nobody is in the room.
3. ESP32 sends occupancy status to Raspberry Pi via MQTT.
4. Raspberry Pi decides this may be wasteful.
5. Raspberry Pi sends WhatsApp alert with estimated avoidable cost.
6. User replies YES.
7. Raspberry Pi sends MQTT command to ESP32.
8. ESP32 sends IR OFF signal.
9. In a real home: the AC unit's IR receiver picks up the signal and the AC switches off.
   In the demo rig: the TSOP1838 IR receiver picks up the signal and triggers the relay to cut power to the AC SIMULATOR outlet.
10. The dedicated AC clamp confirms zero AC power. Dashboard updates and a confirmation WhatsApp is sent to the user.

## 11. Where each subsystem begins and ends

### Electricity sensing subsystem

```text
CT clamp #1 (main) + CT clamp #2 (AC branch) + voltage sensor + 2x signal conditioning + ADS1115
```

Output:

```text
Total current/voltage + direct AC current readings
```

### AI subsystem

```text
Power readings + rolling window + PyTorch ELECTRIcity appliance models
```

Output:

```text
Predicted appliance usage
```

### Control subsystem

```text
mmWave sensor + ESP32 + MQTT + IR LED  →  (real AC OR demo rig IR receiver + relay)
```

Output:

```text
Occupancy status, AC IR command, and verified power cutoff on the AC branch
```

### Smart insight subsystem

```text
Appliance predictions + occupancy + timestamped history + tariff assumptions
```

Output:

```text
Routine-aware alerts, bill forecasts, waste score, energy coach recommendations, and appliance health warnings
```

### User interface subsystem

```text
Flask dashboard + WhatsApp alerts
```

Output:

```text
What the user sees and responds to
```

## 12. Network and cloud architecture

WattsEye should be designed as a **login-first, local-first system**:

```text
User login
-> choose home/device
-> determine data source
   live local Pi if reachable
   cloud-synced history if remote
   cached/demo data if nothing live is reachable
```

The live home loop remains local:

```text
Raspberry Pi
-> reads sensors
-> runs NILM / insight logic
-> stores local history
-> serves dashboard on home WiFi or Pi hotspot
-> controls ESP32 through local MQTT
```

Cloud services are optional and sit outside the core loop:

```text
Local database on Pi
-> offline queue
-> sync worker, when internet exists
-> Supabase Auth + energy_readings table
-> remote dashboard history
```

Recommended operating modes:

| Mode | Connection | What works |
|---|---|---|
| Best case | Login + internet + cloud | Remote access, cloud history sync, local monitoring if Pi is reachable |
| Normal case | Login + home WiFi | Live local dashboard, MQTT, sensing, AI, alerts inside LAN |
| Fallback case | Login + Pi hotspot, no internet | Offline dashboard, local storage, AI, ESP32 control |
| Remote but Pi unavailable | Login + cloud only | Synced/cached history, not guaranteed live home data |

The dashboard should show cloud status separately from device status.

```text
Device: Online locally
Cloud sync: Waiting for internet
Last synced: 10:42 AM
Data shown: Live local reading
```

## 13. Smart plug integration point

Smart plugs should connect as an optional data source, not as a replacement for the two CT clamps.

```text
Smart plug reading
-> Pi local API / MQTT topic
-> device_id mapped to appliance name


