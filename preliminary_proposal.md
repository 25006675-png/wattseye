This is a original proposal that got us into final top 3. But other plans in this repo is the new plan and has some changes in architecture due to various factors. 
Below is the OCR content from the slide deck, excluding the **References** slide. OCR may contain small spacing errors from the original PDF. 

---

## Page 1

**WATTSEYE**
by team Engincs

Malaysia’s first AI-powered home electricity intelligence system

---

## Page 2

**NO BREAKDOWN**
**ONE NUMBER A MONTH. ZERO INSIGHT.**

Every month, 8 million Malaysian households receive a TNB bill that tells them everything — and nothing.

**NO VISIBILITY**
**NO WARNING**
**NO ACTION**

Which appliance is costing me?

The fridge just died with no warning.

Why is my bill RM80 higher this month?

Peak-hour tariff just hit, and I’m not even home.

You can’t manage what you can’t see.

---

## Page 3

**THE BIGGEST LINE ITEM IS**
**THE MOST INVISIBLE**

**AVERAGE MALAYSIAN HOUSEHOLD ELECTRICITY CONSUMPTION BY APPLIANCE CATEGORY**

1. AC drives 25–50% of Malaysian household electricity — and up to 70% in heavy-use homes.
2. It’s hardwired. No smart plug on the market can monitor it.
3. Nobody directly measures it. Not Sensibo. Not Sense. Not anyone.

Solving electricity intelligence in Malaysia means solving the AC problem first. That’s the gap WattsEye fills.

---

## Page 4

**Why NOW?**

AC ownership in urban Malaysia: >90% and rising with climate change.

Currently: Zero Malaysian-built electricity intelligence solutions exist.

**MALAYSIA’S ELECTRICITY ROADMAP**

2024
TNB tariff revision raised cost for medium to high consumers.

2025
TOU tariff being rolled out — savings only accessible with appliance visibility.

2030
Malaysia’s NDC commits to 45% emissions intensity reduction.

---

## Page 5

**Hardware-Software Integration**

System architecture diagram — central WATTSEYE Hub with two branches:
AC Module left, near DB box icon, and WATTSEYE Plugs right, near appliance icons.

“Three components. ~85% of your bill. One picture.”

**WATTSEYE HUB**
Edge AI
Local data
WhatsApp gateway

MQTT
WiFi

AC MODULE
CT + IR + mmWave

WATTSEYE PLUGS x6
Tasmota

Hardwired ~50%
Pluggable ~35%
~85% of total bill covered

---

## Page 6

**How it works**

**CT Clamp**
Wraps around the AC’s wire inside the DB box. Reads the magnetic field — no wires cut.

**IR Blaster**
Sends infrared commands like a remote. Controls Daikin, Panasonic, York, Mitsubishi.

**mmWave Sensor**
Detects human presence via radar, including sleeping people. No camera, no privacy concern.

Sensibo controls without measuring. Sense measures without controlling.
We do both — plus occupancy. First device to fuse all three for Malaysian homes.

---

## Page 7

**Three Things No Malaysian Home Has Ever Experienced**

**Track the Ringgit**
Live Electricity Cost
Current Cost: RM 1.84 / hour
Living room + AC
Auto filters

See electricity cost in real time, broken down by every appliance. Something Malaysians have never seen before.

**Cut the Bill**
This Week’s Schedule
The system learns your household rhythm and adjusts appliances automatically: pre-cooling before peak hours, killing standby drains, turning off ACs in empty rooms.

**Catch the Failure**
Appliance Health
Dirty Filter Detected
Living Room AC
Anomaly Detected
May 20, 08:46 AM

Detect appliance degradation from electrical data alone, whether a dirty filter, aging compressor, or failing water heater, weeks before symptoms appear.

---

## Page 8

**What it does? Features**

**Live Cost Counter**
See your home’s electricity spend in ringgit per hour, by appliance in real time.

**Bill Predictor**
Daily forecast of your end-of-month TNB bill.

**AC Intelligence**
Empty-room kill, dirty-filter detection, sleep curve.

**Ghost Load Detection**
Finds standby drains and ranks them by monthly cost.

**Tariff-Aware Scheduling**
Auto-shifts heavy loads to cheaper off-peak hours.

**WhatsApp Alerts**
Conversational notifications in Bahasa Malaysia or English.

---

## Page 9

**Visual Proof**

**WhatsApp conversations**

Bro, AC bilik tidur dah on 4 jam, takde orang. pukul 2pm. Save RM3.20 sejam. Nak Wattseye matikan? [yes, off] [keep on]

Yes, off

Ok bro dah matikan

Aircond living room makin lapar elektrik 3 minggu ni. Filter mungkin kotor, boleh save RM18/bulan kalau servis.

**Frequent updates**

RM 1.84 / hour live, large type
AC: RM1.20
Fridge: RM0.18
TV: RM0.12
Standby: RM0.34

Predicted bill: RM287
RM41 vs last month

This year saved: RM287 through 43 auto-interventions

Live updates allows you to monitor your electricity consumption conditions.

Conversational. Bilingual. Native to how Malaysians already communicate. The product meets users where they already are.

---

## Page 10

**Six focus areas, All covered**

**Occupancy & Spatial Detection**
mmWave sensing distinguishes empty / occupied / sleeping

**Automated Power Control**
IR + relay control · tariff-aware scheduling

**AI Analytics & Prediction**
On-device anomaly detection · bill forecasting

**Hardware-Software Integration**
Custom AC Module + Hub + mobile + WhatsApp

**Cost & Impact Tracking**
Live RM/hour counter · Carbon Twin · bill predictor

**Scalability & Retrofitting**
Non-invasive clamp · no rewiring · modular

---

## Page 11

**Hardware Specifications**

**ESP32-WROOM-32 Microcontroller:** Wi-Fi + BLE, dual-core, runs TensorFlow Lite Micro

**BL0937 Energy metering IC:** ±1% accuracy, single-phase, proven in Sonoff S31

**SCT-013-030 CT clamp:** Non-invasive, snap-on install, no wires cut

**940nm IR LED transmitter + driver:** Whole-room reach, supports 8+ AC brands

**LD2410 mmWave Occupancy sensor:** Detects breathing, ignores stillness

**Fire-retardant ABS enclosure:** UL94 V-0 grade, DB-box safe

**Sonoff S31 smart plug base:** Reflashed with Tasmota for local MQTT

---

## Page 12

**Software and AI Logic**

**Empty room detection logic**

IF AC runtime > 90 min
AND mmWave presence == FALSE
AND Household active signature == TRUE
trigger WhatsApp confirmation ping
WAIT 5 min or User Respond == “OFF”
IR COMMAND: AC POWER OFF
LOG SAVINGS: + RM 3.20

**Edge Computing: Four ML Models**

**Anomaly detection**
Flags signature deviations, e.g. fridge cycling 40% more = door seal issue.
Isolation Forest

**AC Degradation**
Regresses draw against setpoint, temp, and runtime to detect dirty filters.
Linear Regression

**Schedule Learning**
Unsupervised pattern discovery for arrival, sleep, and departure routines.
K-Means Cluster

**Bill Prediction**
Daily projection of month-end consumption against TNB tiered tariffs.
RNN / LSTM

---

## Page 13

**Comparison between products**

Smart Plugs Tuya
Sensibo / Cielo
Sense / Emporia
WattsEye

**Sees the AC**
Smart Plugs: ❌
Sensibo / Cielo: Estimate only
Sense / Emporia: Disaggregates
WattsEye: Direct measurement

**Controls the AC**
Smart Plugs: ❌
Sensibo / Cielo: ✅
Sense / Emporia: ❌
WattsEye: ✅

**Occupancy-aware**
Smart Plugs: ❌
Sensibo / Cielo: ❌
Sense / Emporia: ❌
WattsEye: ✅

**Built for Malaysian tariffs**
Smart Plugs: ❌
Sensibo / Cielo: ❌
Sense / Emporia: ❌
WattsEye: ✅

**Bahasa Malaysia · WhatsApp**
Smart Plugs: ❌
Sensibo / Cielo: ❌
Sense / Emporia: ❌
WattsEye: ✅

**Privacy-first edge AI**
Smart Plugs: ❌
Sensibo / Cielo: ❌
Sense / Emporia: ❌
WattsEye: ✅

**Entry price**
Smart Plugs: ❌
Sensibo / Cielo: ❌
Sense / Emporia: ❌
WattsEye: ✅

Every competitor solves only a fragment. WATTSEYE solves the whole.

---

## Page 14

**Impact & Sustainability**

**Per Household, Per Year:**

RM 720 – 1,200 saved
350 kg CO₂ avoided
AC efficiency improved 15–25%
Payback in 8–12 months

**Year 1 target:** 100 pilot homes

**Year 3 target:**
Scaled to 100,000 Malaysian homes

RM 90 million returned to households yearly
35,000 tonnes CO₂ avoided yearly
Equivalent to taking ~7,500 cars off Malaysian roads

Aligned with Malaysia’s NDC 2030 commitment and the National Energy Transition Roadmap.

---

## Page 15

**Inclusivity & Stakeholder Reach**

**M40 / urban families**
Full Starter Kit at RM749, payback under one year

**B40 households**
AC Module Lite at RM169; the appliance that matters most, made affordable

**Landlords 10+ units**
Tenants benefit, owners reduce bill disputes

**Property developers**
Bundle into new condominiums as differentiator

**Small commercial**
Kedai, mamak, salons, small offices — same hardware

---

## Page 16

**Feasibility, Risks & Roadmap**

| Risk                         | Mitigation                                                  |
| ---------------------------- | ----------------------------------------------------------- |
| DB-box installation safety   | SIRIM-certified clamp · partner electrician, ~RM80, bundled |
| Multi-AC households          | One AC Module per unit; Hub aggregates                      |
| AC IR protocol coverage      | Pre-loaded library for 8 Malaysian brands · learning mode   |
| WhatsApp API cost at scale   | Aggregate alerts · subscription tier absorbs variable cost  |
| Privacy with WhatsApp alerts | Raw data stays on-device; only summaries leave              |

---

## Page 17

**Roadmap to Final Day**

**9–15 May**
AC Module v1: clamp + ESP32 + IR firmware, bench tested

**16–22 May**
Hub firmware + MQTT broker + dashboard prototype

**23–29 May**
Full integration: AC Module + Hub + 2 plugs end-to-end

**30 May–5 Jun**
Pilot deployment in one home · UX refinement · demo recording

**6 June**
Physical Final Day — full working system

---

## Page 19

**Thank You**
