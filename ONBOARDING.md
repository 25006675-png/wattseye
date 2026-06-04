# WattsEye — Agent Onboarding (start here)

Quick map for a fresh agent session. WattsEye is a Malaysian home-electricity
intelligence system: **hybrid sensing** (one dedicated CT clamp on the AC branch +
one whole-home clamp with NILM) → **coach engine** that turns signals into ringgit-
quantified recommendations → Flutter app + WhatsApp + live IR cutoff.

## Where things live
| Area | Path | Notes |
|---|---|---|
| Coach engine | `ML/insights/coach/` | correlator → quantifier → templates → ranker → feedback_loader |
| NILM models | `ML/NILM/*.pth` | 5 ELECTRiCITY checkpoints (kettle/fridge/washing_machine/hair_dryer/iron) |
| Faithful NILM model | `ML/NILM/electricity_model.py` | **use this** for inference (byte-exact vs training repo) |
| NILM eval | `ML/NILM/eval/` | `verify_f1.py` + `RESULTS.md` reproduce the published F1 |
| Signature library | `ML/signatures/signature_library.py` | edge-based event detection for the "unknown" bucket |
| Sensing | `ML/sensing/` | `ads1115_reader.py --simulate`, `synthetic_history.sqlite` |
| Backend API | `backend/api_server.py` | stdlib http.server (NOT flask, despite requirements) |
| Snapshot builder | `backend/snapshot_builder.py` | real data → `HomeSnapshot` (from_live_state / from_history) |
| Pi runtime | `backend/pi_bridge.py` | MQTT → decide cutoff → write `live_state.json` |
| Live NILM | `backend/nilm_runtime.py` | guarded by `WATTSEYE_NILM=1` |
| Flutter app | `wattseye_app/lib/` | `main.dart`, `api.dart`, `theme.dart` |
| Plan / pitch | `plan/`, `extra_info/` | see `gap.md`, `coach_loop_reference.md` |

## Read these two first
- `extra_info/gap.md` — what was wired, what's still open.
- `extra_info/coach_loop_reference.md` — the 11 signals + per-card correlator logic.

## Real vs demo (critical — don't confuse)
- **Coach engine logic is real** (correlator/quantifier/ranker). The **input** is what varies:
  - **Showcase** = `_demo_snapshot()` + `_peak_heavy_snapshot()` → all 12 archetypes as a **catalog** (not one real home).
  - **Replay/Live (no Pi)** = `snapshot_builder.from_history()` over `synthetic_history.sqlite` → ~2 real cards.
  - **Live (Pi)** = `from_live_state()` over `live_state.json` (only fresh while `pi_bridge` runs).
  - App tags each card `data_source`: `showcase` / `replay` / `live`. Flutter `_coachCards` is a static **offline fallback only**.
- API: `/api/coach/cards?mode=showcase|live`. Dashboard/Bill/History auto-switch live↔demo via `read_live_state()`; the chip shows "Live Pi"/"Demo data".

## Gotchas (learned the hard way)
- `ML/NILM/test_nilm_inference.py` is an **approximate, WRONG** reconstruction (wrong sub-network + hyperparams). It loads but does NOT reproduce the F1. Use `electricity_model.py` (the **Discriminator** is the inference net, not the Generator).
- NILM is **brittle to normalisation**: needs UK-DALE train stats (~300/471). `522/814` and self-normalisation both give **0 W**. Live rig use needs **fine-tuning**; raw rig watts are off-distribution.
- Live NILM readout = **max over recent output positions** (not the seq2point centre, which is ~window/2 late). Measured first-detection ~6–12 s. Cross-talk between similar resistive loads (kettle↔hair-dryer).
- Showcase shows 12 because of a 2-snapshot union; a single real home only trips ~2. #4 `tou_switch` and #6 `peak_window_shift` are **mutually exclusive** (off-peak vs peak-heavy).
- WhatsApp is **manual-only** today (the dashboard button → `/api/whatsapp/send`); no auto-push is wired.

## Run it (no hardware)
```powershell
# fast: API + app
python backend\api_server.py
cd wattseye_app; flutter run -d chrome     # or --dart-define=WATTSEYE_API_BASE=http://10.0.2.2:8080 for Android emu

# full live loop emulated (docs/build_now/01):
mosquitto -v ; python -m backend.pi_bridge ; python -m ML.sensing.ads1115_reader --simulate ; python backend\api_server.py
# add $env:WATTSEYE_NILM=1 before pi_bridge for live per-appliance tiles
```
Sanity: `python -m backend.pi_bridge --self-test` · `python ML/NILM/eval/verify_f1.py --pred-root <training_repo>/checkpoints_electricity/uk_dale`

## Open items
- Live NILM → `recent_events` (event segmentation on the live stream).
- Sensor calibration (`power_math` constants are placeholders).
- Drop unused `flask` from `backend/requirements.txt`; optional `run_pi.sh`.

## Conventions
- Don't commit `Wattseye .pdf` (41 MB). Keep commits scoped. Verify Dart with `flutter analyze lib/`.
