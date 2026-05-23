# 07 — Task Breakdown: Who Does What

## 1. Purpose of this file

This file turns the project into tasks.

It helps teammates know what to build, test, and prepare.

## 2. Main workstreams

We can split the project into seven workstreams:

1. Hardware
2. Raspberry Pi backend
3. Machine learning
4. ESP32 control system
5. Dashboard / frontend
6. Demo and pitch preparation
7. Login, optional cloud sync, and smart plug layer

The smarter version also needs a cross-cutting smart insight layer. This sits mostly in Raspberry Pi backend, machine learning, and dashboard work.

Login should be part of the app experience, but cloud sync and smart plugs should stay isolated and optional. This layer must not block the CT sensor pipeline, local dashboard, MQTT, or final demo.

## 3. Hardware team tasks

| Task | Priority | Notes |
|---|---|---|
| Prepare hardware list | High | Confirm what we already have and what to buy (2 CT clamps now) |
| Build demo box design with split bus | High | Must include safety layout + general/AC branch separation |
| Wire inlet, fuse, terminal block split, outlets | High | Needs supervision |
| Mount CT clamp #1 on main feeder wire | High | Clamp around main live wire only |
| Mount CT clamp #2 on AC branch wire | High | Wraps the AC branch only (before AC SIMULATOR outlet) |
| Connect voltage sensor | High | Must be safe and enclosed |
| Build signal conditioning circuits (one per clamp) | High | Two parallel paths, A0 and A2 on ADS1115 |
| Connect ADS1115 to Raspberry Pi | High | I2C connection, use channels A0, A1, A2 |
| Build IR receiver + relay block | High | Required for live AC cutoff demo |
| Wire relay contact in series with AC SIMULATOR outlet | High | Mains-rated relay only, supervised |
| Test known appliance readings on both clamps | High | For calibration; verify split-bus behavior |
| Prepare hardware diagram | Medium | For teammate explanation and presentation |

## 4. Raspberry Pi backend tasks

| Task | Priority | Notes |
|---|---|---|
| Install Raspberry Pi OS | High | Basic setup |
| Enable I2C | High | Needed for ADS1115 |
| Read ADS1115 values from A0, A1, A2 | High | First sensor test (main, voltage, AC) |
| Convert readings to voltage/current per channel | High | Needs calibration formula for each clamp |
| Compute Vrms / Irms from one-second sample buffers | High | Use `ML/sensing/power_math.py:compute_power_reading` |
| Calibrate clamp scale against a resistive load (kettle) | High | Sets `CalibrationConstants` in power_math; PF≈1.00 for resistive |
| Measure per-appliance PF for non-resistive loads | Medium | Update `APPLIANCE_POWER_FACTORS` table after testing |
| Apply PF correction (apparent VA → real W) before dashboard | High | `apparent_to_real_watts(va, appliance)` |
| Calculate apparent power: total, direct AC, residual | High | Core data output (three VA values per second) |
| Log NILM AC estimate alongside direct AC reading (internal only) | Medium | For offline validation notebook; not shown on dashboard |
| Store one reading per second for all three values | High | Needed for ML rolling window |
| Store historical predictions and occupancy | High | Needed for routine-aware insights |
| Load PyTorch `.pth` ELECTRIcity models | High | For live inference; see `ML/NILM/test_nilm_inference.py` |
| Run NILM model on residual signal (total − direct AC) | High | Cleaner input → better non-AC disaggregation |
| Build smart insight engine | High | Routines, forecast, waste score, recommendations |
| Calculate bill forecast | Medium | Uses cost history and tariff assumption |
| Calculate waste score | Medium | Summarizes avoidable waste |
| Serve Flask dashboard API | High | Send data to frontend |
| Install Mosquitto MQTT | Medium | For ESP32 communication |
| Add WhatsApp/Twilio test endpoint | Medium | Backend can send one test WhatsApp alert without sensors |
| Add WhatsApp/Twilio reply webhook | Medium | Backend can receive `Y/YES` replies and log the response |
| Add offline sync queue fields | Medium | Mark rows as synced/unsynced for optional cloud upload |
| Add smart plug ingestion endpoint/topic | Low | Optional exact readings for selected plug-in devices |

## 5. Machine learning tasks

| Task | Priority | Notes |
|---|---|---|
| Set up Python environment | High | Conda or venv |
| Download public datasets | High | UK-DALE, ENERTALK, etc. |
| Preprocess data to common format | High | Same sampling rate |
| Train kettle model | High | First proof of pipeline |
| Train other demo-core models | High | Lamp/hair dryer may need own data |
| Train supplementary models | Medium | AC, fridge, washer, etc. |
| Evaluate models | High | F1, MAE, SAE |
| Benchmark PyTorch inference on Raspberry Pi 4 | High | Decision point: stay PyTorch vs. quantize vs. convert |
| Apply post-training quantization or TorchScript if needed | Medium | Only if Pi benchmark misses 1 Hz budget |
| Convert to ONNX/TFLite (contingency) | Low | Only if quantized PyTorch is still too slow |
| Build routine-aware detection logic | High | Time/day + occupancy + historical usage |
| Build appliance health scoring logic | Medium | Compare current behavior with normal pattern |
| Build standby power detection | Medium | Detect always-on background load |
| Prepare ML result visuals | Medium | For pitch/demo |

## 6. ESP32 control tasks

| Task | Priority | Notes |
|---|---|---|
| Set up ESP32 development environment | High | Arduino IDE or PlatformIO |
| Read LD2410 mmWave sensor | High | Occupancy detection |
| Connect ESP32 to WiFi | High | Needed for MQTT |
| Publish occupancy to MQTT | High | ESP32 → Pi |
| Subscribe to AC command topic | High | Pi → ESP32 |
| Build IR LED transistor circuit | High | Needed for AC control |
| Send test IR signal | High | Confirm with phone camera (IR shows as light) |
| Build IR receiver + relay circuit (analog path) | High | Needed for live demo cutoff |
| Confirm end-to-end IR → relay → AC SIMULATOR outlet cutoff | High | Pillar 2 must work |
| Add AC brand remote code (Daikin/Panasonic/etc.) via IRremoteESP8266 | **P0 if real-AC demo, P2 otherwise** | Inverter ACs require full state frames, not a generic OFF pulse. Demo rig (TSOP1838+relay) accepts any 38kHz carrier and does not need brand codes. |

## 7. Dashboard/frontend tasks

| Task | Priority | Notes |
|---|---|---|
| Build dashboard layout | High | Simple and clean |
| Show total power (main clamp) | High | Must work live |
| Show direct AC power (AC clamp) | High | Pillar 1 validation moment |
| Surface offline NILM accuracy metrics (F1, MAE) in validation notebook | Medium | Lives in the notebook, not the dashboard |
| Show appliance cards | High | Kettle/lamp/hair dryer etc. |
| Show cost estimate | Medium | Based on tariff assumptions |
| Show projected bill | High | Key smart insight |
| Show waste score | Medium | Makes waste easy to understand |
| Show energy coach recommendation | Medium | Turns data into action |
| Show routine-aware insight | Medium | Example: unusual AC usage |
| Show appliance health score | Medium | Fridge/AC abnormality story |
| Show graph over time | Medium | Makes demo more visual |
| Show alert panel | Medium | AC empty-room alert |
| Connect to Flask API | High | Live data |
| Add demo mode | Medium | Useful backup |
| Build login/register/logout screens | Medium | Frontend-owned UI; connects to local/demo auth first, then Supabase Auth |
| Show cloud sync status | Low | Clearly separates local device status from cloud status |
| Show data source label | Medium | Live local, synced cloud, cached, or demo |
| Show optional smart plug readings | Low | Exact readings for selected plug-in devices |

## 8. Login, optional cloud sync, and smart plug tasks

This workstream is useful but should still be tightly scoped. Login is part of the app experience; cloud sync and smart plugs are replaceable.

| Task | Priority | Notes |
|---|---|---|
| Define login flow contract | P1 | Frontend owns screens; backend/cloud teammate defines auth states, redirects, and required fields |
| Prepare mock/local auth first | P2 | Acceptable before Supabase is ready |
| Connect Supabase Auth backend/config | P2 | Email/password auth or equivalent; only after local/demo login works |
| Add local/demo auth mode | P1 | Lets hotspot/offline demo still require login |
| Add selected home/device state | P2 | Needed to explain whose data is shown |
| Add data source label | P1 | Shows live local, synced cloud, cached, or demo data |
| Create Supabase `energy_readings` table | P2 | `user_id`, `device_id`, `timestamp`, `power_watts`, `synced` minimum |
| Insert one Supabase test reading manually | P2 | Proves table, connection, and permissions |
| Add local-to-cloud sync worker plan | P2 | Upload unsynced local readings when internet exists |
| Add cloud sync status on dashboard | P2 | Shows last sync and pending rows |
| Add optional smart plug schema | P2 | `smart_plugs` table or local device map |
| Document the layer | P1 | See `10_LOGIN_CLOUD_AND_SMART_PLUG_TASK.md` |

## 9. WhatsApp/Twilio alert setup task

This is a backend environment task. It proves the notification channel works before connecting it to real sensor logic.

| Task | Priority | Notes |
|---|---|---|
| Create Twilio WhatsApp sandbox/account setup notes | P2 | Include sender number, join code, and setup screenshots if possible |
| Add required environment variables | P2 | `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`, `TWILIO_WHATSAPP_FROM`, `TEST_WHATSAPP_TO` |
| Build send-test alert route/function | P2 | Sends: `WattsEye test alert: AC is running in an empty room. Reply Y to turn off.` |
| Build reply webhook route/function | P2 | Receives WhatsApp replies from Twilio and logs `Y/YES/NO` |
| Document webhook testing method | P2 | Use local tunnel only for testing if needed |
| Keep control action separate | P1 | Webhook should not directly own MQTT, ESP32, or IR cutoff |

Boundary:

```text
WhatsApp task proves:
backend -> Twilio -> WhatsApp user
WhatsApp user -> Twilio -> backend

Core team still owns:
sensor decision -> MQTT command -> ESP32 IR -> power confirmation
```

Do not assign this workstream responsibility for:

- Raspberry Pi data collection
- Core CT sensor logic
- Main dashboard live data
- MQTT architecture
- Offline local storage
- Final demo integration

## 10. Demo and pitch tasks

| Task | Priority | Notes |
|---|---|---|
| Prepare demo script | High | Avoid confusion during presentation |
| Decide live appliances | High | Choose reliable ones |
| Prepare backup recording | High | In case live ML fails |
| Prepare system diagram | High | Explain architecture quickly |
| Prepare ML explanation slide | High | One sensor + AI patterns |
| Prepare smart insight slide | High | Routine + forecast + recommendation |
| Prepare Q&A document | High | For judges |
| Practice full demo | High | Time the flow |
| Prepare safety explanation | Medium | Important if demo uses mains electricity |

## 11. Recommended build order

### Stage 1 — Prove power reading

Goal:

```text
Raspberry Pi can read total power from sensor.
```

Tasks:

- Build sensor circuit.
- Read ADS1115.
- Calculate approximate watts.
- Test with known appliance.

### Stage 2 — Prove dashboard

Goal:

```text
Dashboard updates when power changes.
```

Tasks:

- Build Flask API.
- Build simple dashboard.
- Show total power live.

### Stage 3 — Prove ML offline

Goal:

```text
Model can identify appliance patterns using dataset/notebook.
```

Tasks:

- Train kettle model.
- Evaluate model.
- Benchmark inference on the Pi (`test_nilm_inference.py --all`).

### Stage 4 — Prove live ML

Goal:

```text
Live sensor readings can enter model and update dashboard.
```

Tasks:

- Create rolling window.
- Normalize input.
- Run PyTorch model.
- Smooth prediction.
- Show appliance card.

### Stage 5 — Add control and alerts

Goal:

```text
System can detect empty room and send alert/control command.
```

Tasks:

- Connect ESP32 and mmWave.
- Use MQTT.
- Add WhatsApp/Twilio.
- Add IR control.

### Stage 6 - Add smart insight layer

Goal:

```text
System can turn appliance predictions into routine-aware insights, bill forecasts, and recommendations.
```

Tasks:

- Store timestamped power, predictions, occupancy, cost, and alerts.
- Learn simple routine baselines by hour/day.
- Add projected monthly bill.
- Add waste score.
- Add energy coach recommendation.
- Add appliance health score for at least one appliance story.
- Show these insights on the dashboard.

## 12. Priority labels

Use these labels in project management:

```text
P0 = must work for demo
P1 = strongly preferred
P2 = nice to have
P3 = future / pitch only
```

Suggested priorities:

| Feature | Priority |
|---|---|
| Total power sensing (Clamp #1) | P0 |
| Direct AC power sensing (Clamp #2) | P0 |
| Dashboard live total + AC power | P0 |
| NILM accuracy notebook (F1, MAE) | P1 |
| Kettle detection | P0/P1 |
| Second demo appliance detection | P1 |
| PyTorch ELECTRIcity inference on Pi (on residual signal) | P1 |
| mmWave occupancy detection | P1 |
| IR transmit (ESP32 → IR LED) | P1 |
| IR receiver + relay live cutoff (demo rig) | P0 |
| AC empty-room alert | P0 |
| WhatsApp/Twilio alert channel | P2 |
| Bill forecasting | P1 |
| Routine-aware alert | P1/P2 |
| Energy coach recommendation | P1/P2 |
| Waste score | P2 |
| Appliance health score | P2 |
| Standby power detection | P2 |
| Full 10 appliance dashboard | P2 |
| Anomaly detection | P2/P3 |
| Automatic AC control loop | P1 |
| Login/register/logout | P1 |
| Supabase Auth + `energy_readings` table | P2 |
| Supabase history sync | P2 |
| Optional smart plug exact readings | P2 |

## 13. Simple weekly plan

### Week 1

- Finalize architecture.
- Set up Pi and ML environment.
- Build basic dashboard mockup.
- Start hardware sourcing.

### Week 2

- Build power sensing pipeline.
- Train first demo-core model.
- Start dashboard API.
- Test ESP32 occupancy separately.

### Week 3

- Integrate live data with dashboard.
- Benchmark on the Pi; only quantize/convert if needed.
- Test demo appliances.
- Add MQTT and alert flow.

### Week 4

- Polish dashboard.
- Prepare demo script.
- Record backup demo.
- Practice Q&A.
- Fix reliability issues.
- Keep optional cloud/smart plug work behind a feature flag or separate route, while the login route remains part of the app.

## 14. Task ownership template

Use this table:

| Task | Owner | Priority | Status | Deadline | Notes |
|---|---|---|---|---|---|
| Read ADS1115 from Pi |  | P0 | Not started |  |  |
| Train kettle model |  | P0 | Not started |  |  |
| Build dashboard total power card |  | P0 | Not started |  |  |
| ESP32 reads mmWave |  | P1 | Not started |  |  |
| Login/register/logout screens |  | P1 | Not started |  | Frontend-owned |
| Login/auth backend contract |  | P1 | Not started |  | Backend/cloud-owned |
| Supabase Auth + energy table |  | P2 | Not started |  |  |
| WhatsApp/Twilio test alert |  | P2 | Not started |  |  |
| WhatsApp reply webhook |  | P2 | Not started |  |  |
| Login/cloud/smart plug task guide |  | P1 | Not started |  |  |

## 15. Main project management principle

Do not build the hardest version first.

Build in this order:

```text
Working simple system → reliable demo → expanded features → polished pitch
```

A simple working demo beats a huge unstable system.
