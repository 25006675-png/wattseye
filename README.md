# WattsEye Teammate Onboarding Folder

Read the files in this order:

1. `00_BIG_PICTURE.md`
2. `01_SYSTEM_CONNECTION.md`
3. `02_HARDWARE.md`
4. `03_MACHINE_LEARNING.md`
5. `04_LIVE_DATA_FLOW.md`
6. `05_USER_EXPERIENCE.md`
7. `06_DEMO_PLAN.md`
8. `07_TASK_BREAKDOWN.md`
9. `08_QA_DEFENSE.md`
10. `09_COMPONENTS_AND_PRICE_ESTIMATION.md`
11. `10_LOGIN_CLOUD_AND_SMART_PLUG_TASK.md`

## Purpose

This folder explains WattsEye in a beginner-friendly but detailed way so teammates can understand the full system.

## Main idea

WattsEye uses a hybrid sensing architecture — one dedicated CT clamp on the air-conditioner circuit (exact AC measurement) plus a whole-home CT clamp with AI disaggregation (everything else) — then shows insights on a dashboard.

The smarter product vision is:

```text
Hybrid sensing (AC + whole-home) -> appliance detection + AC validation -> occupancy and routine context -> smart insights -> verified IR cutoff
```

The dashboard should not only show what is using power. It should also forecast bills, detect waste, learn household routines, recommend actions, and warn about abnormal appliance behavior.

The best architecture is **login-first, local-first, with optional cloud sync**:

```text
Best case:    Login + Internet + cloud -> remote access + synced history
Normal case:  Login + Home WiFi -> live local smart home monitoring
Fallback:     Login + Pi hotspot mode -> offline/local dashboard still works
```

This keeps the core demo reliable. Login is part of the product experience, but cloud sync is optional. If the user is not connected to the home Pi or the latest readings have not synced, the dashboard may show cached, cloud-synced, or demo history instead of live home data. CT sensing, dashboard, MQTT control, and offline storage must still work without internet.

Why two clamps and not one: inverter ACs dominate Malaysian homes and have no clean NILM signature, so AI alone is unreliable for AC. The dedicated clamp solves this and also gives a live "agreement %" between the AI's AC estimate and the direct measurement — a quantified accuracy proof on stage.

## Visual diagrams

- [System connection flow](assets/system-connection-flow.svg)
- [Smart insight architecture](assets/smart-insight-architecture.svg)
- [Live data pipeline](assets/live-data-pipeline.svg)
- [Three-pillar product map](assets/three-pillars-map.svg)

## Important note

The files are written for teammate explanation and prototype planning. Hardware involving mains electricity must be checked by a qualified person before powering on.
