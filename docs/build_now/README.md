# Build Now — the end-to-end build, step by step

This folder is the **beginner, click-by-click build guide** for the WattsEye rig,
in the **real order you do it**. The authoritative reference (full wiring tables,
theory, safety) is [`../../HARDWARE_CONNECTION.md`](../../HARDWARE_CONNECTION.md);
this folder turns it into numbered steps anyone on the team can follow.

> ⚡ **Safety rule (from `HARDWARE_CONNECTION.md` §1):** do all **software and
> low-voltage** work first (Steps 1–6). The **mains side** (Step 7) is energised
> **only after a qualified person inspects it**. Never work on the box while it's
> plugged into the wall.

---

## The steps

| Step | Guide | Needs | Mains? |
|---|---|---|---|
| 1 | [Laptop software loop](01_laptop_software_loop.md) | This laptop only | no |
| 2 | [Flash & set up the Raspberry Pi](02_pi_setup.md) | Pi, SD card, 5V/3A PSU | no |
| 3 | [Install & run WattsEye on the Pi](03_pi_run.md) | Pi from Step 2 | no |
| 4 | [Breadboard circuits](04_breadboard_circuits.md) | Breadboard, resistors, caps, 2N2222, relay | no |
| 5 | [Sensing chain: ADS1115 ↔ Pi](05_sensing_chain.md) | ADS1115, clamps, ZMPT101B, Pi | no (low-V) |
| 6 | [ESP32 node](06_esp32_bringup.md) | ESP32, LD2410C, IR LED, relay | no |
| 7 | [Mains box: assemble, inspect, energise, test](07_mains_box.md) | The mains box parts + **inspection** | **YES** |
| 8 | [Calibration](08_calibration.md) | Energised rig + a kettle | yes |
| — | [(Optional) IR-learn — real-AC only](09_ir_learn.md) | Arduino, VS1838B, AC remote | no |

## Three phases

```
  PHASE A — software            PHASE B — low-voltage hardware       PHASE C — mains
  ┌───────────────────┐         ┌──────────────────────────────┐    ┌──────────────────┐
  │ 1 Laptop loop      │         │ 4 Breadboard circuits        │    │ 7 Mains box      │
  │ 2 Pi setup         │  ───►   │ 5 Sensing chain (ADS1115→Pi) │ ─► │   (after         │
  │ 3 Run on the Pi    │         │ 6 ESP32 node                 │    │    inspection)   │
  └───────────────────┘         └──────────────────────────────┘    │ 8 Calibration    │
                                                                     └──────────────────┘
```

- **Steps 1–3** can be done with zero hardware (1) or just the Pi (2–3).
- **Steps 4–6** are low-voltage bench work — safe, no mains. They can overlap.
- **Step 7** is the only mains step and **must** wait for inspection.
- **Step 8** tunes the software once real loads are measured.
- The **optional IR-learn** (9) is only for cutting a **real** air conditioner; the
  standard demo (a fan/relay) does **not** need it.

## What's mock vs real in the demo

The standard demo uses a **fan** (or kettle) on the AC-SIMULATOR socket, and the
cutoff is the **relay** opening — driven by a **mock IR pulse**. You do **not** need
the Arduino or a real AC remote for that. The real-AC path (Step 9) is optional.

## Reference map

| Step | Full reference in `HARDWARE_CONNECTION.md` |
|---|---|
| 1 | §14, §14.4 |
| 2 | §14.5 (OS prep) |
| 3 | §14.5 (deps, PyTorch, services) |
| 4 | §6.2 (bias), §11.1 (IR driver), §13 (relay) |
| 5 | §6.3, §7, §8, §9 |
| 6 | §10, §11, §13 |
| 7 | §1 (safety), §5 (box), §15 (steps 7–10) |
| 8 | §16, [`../../ML/sensing/README.md`](../../ML/sensing/README.md) |
| 9 | §12 |
