# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

> Deeper context lives in `ONBOARDING.md` (agent quick-map), `extra_info/gap.md`
> (what's wired vs open), and `extra_info/coach_loop_reference.md` (the signals +
> per-card correlator logic). Read those before non-trivial work.

## What this is

WattsEye is a Malaysian home-electricity intelligence system. **Hybrid sensing**
(one dedicated CT clamp on the air-con branch for exact AC power + one whole-home
clamp with NILM disaggregation for everything else) feeds a **coach engine** that
turns signals into ringgit-quantified recommendations, surfaced via a Flutter app,
manual WhatsApp alerts, and a live IR cutoff for the AC.

Why two clamps: inverter ACs (dominant in Malaysia) have no clean NILM signature,
so AI alone is unreliable — the dedicated clamp measures AC directly, and NILM
accuracy for other appliances is validated offline against public datasets, not as
a live UI tile.

## Commands

```powershell
# Backend API only (stdlib http.server, serves the app's data) — port 8080
python backend\api_server.py

# Flutter app (web). API base defaults to http://localhost:8080
cd wattseye_app; flutter run -d chrome
#   Android emulator → host loopback:
#   flutter run --dart-define=WATTSEYE_API_BASE=http://10.0.2.2:8080

# Full live loop emulated, no hardware (run each in its own shell):
mosquitto -v
python -m backend.pi_bridge            # add $env:WATTSEYE_NILM=1 first for live per-appliance tiles
python -m ML.sensing.ads1115_reader --simulate
python backend\api_server.py

# Flutter checks (run from wattseye_app/)
flutter analyze lib/                    # ALWAYS verify Dart changes with this
flutter test                            # widget tests (test/widget_test.dart)

# Sanity / eval
python -m backend.pi_bridge --self-test
python ML\NILM\eval\verify_f1.py --pred-root <training_repo>/checkpoints_electricity/uk_dale
```

There is no Python test runner configured (no pytest setup); Python "tests" are the
self-test flags and the NILM eval scripts above.

## Architecture

**Coach engine** (`ML/insights/coach/`) is the heart. Pipeline:
`correlator` → `quantifier` (TNB RP4 tariff math, ringgit) → `templates` →
`ranker` → `feedback_loader`. Driven by `coach_engine.py`. This logic is **real**;
only its **input snapshot** varies (see below).

**Backend** (`backend/`) is plain Python `http.server` — **NOT Flask**, despite
`requirements.txt` listing it (flask is unused/removable). Key pieces:
- `api_server.py` — HTTP endpoints (`/api/dashboard`, `/api/coach/cards?mode=…`,
  `/api/bill`, `/api/history`, `/api/whatsapp/send`, `/api/ac/cutoff`, …).
- `snapshot_builder.py` — turns real data into a `HomeSnapshot`
  (`from_live_state()` / `from_history()`).
- `pi_bridge.py` — Pi runtime: MQTT in → decide cutoff → write `live_state.json`.
- `nilm_runtime.py` — live NILM, guarded by env `WATTSEYE_NILM=1`.

**ML** (`ML/`): `NILM/` (5 ELECTRiCITY `.pth` checkpoints + eval), `signatures/`
(edge-based event detection for the "unknown" bucket), `routine/`, `anomaly/`,
`sensing/` (ADS1115 reader with `--simulate`, `synthetic_history.sqlite`).

**Flutter app** (`wattseye_app/lib/`): `main.dart` (all pages + widgets — single
large file), `api.dart` (HTTP client + models), `theme.dart` (`AppTheme` design
tokens; Inter font bundled in `assets/fonts/`). Pages: Dashboard, Coach, Bill,
History, Profile. UI gracefully falls back to hardcoded demo data when the backend
is offline.

## Real vs demo — do not confuse

The coach logic is real; the **data source** is what changes, and every card is
tagged `data_source` (`showcase` / `replay` / `live`):
- **Showcase** = `_demo_snapshot()` + `_peak_heavy_snapshot()` union → all 12
  archetypes as a **catalog** (not one real home).
- **Replay / Live without Pi** = `from_history()` over `synthetic_history.sqlite`
  → ~2 real cards.
- **Live (Pi)** = `from_live_state()` over `live_state.json`, only fresh while
  `pi_bridge` runs.
- Flutter's static `_coachCards` list is an **offline fallback only**.

The Dashboard/Bill/History auto-switch live↔demo via `read_live_state()`; the AppBar
chip shows "Live Pi" / "Demo data".

## Gotchas (learned the hard way)

- NILM inference: use `ML/NILM/electricity_model.py` (the **Discriminator** is the
  inference net, not the Generator). `ML/NILM/test_nilm_inference.py` is an
  **approximate, WRONG** reconstruction — it loads but does not reproduce the F1.
- NILM is brittle to normalisation: needs UK-DALE train stats (~300/471). `522/814`
  and self-normalisation both yield 0 W. Live rig watts are off-distribution and
  need fine-tuning.
- Live NILM readout = max over recent output positions (not the seq2point centre).
  Measured first-detection ~6–12 s.
- WhatsApp is **manual-only** (dashboard button → `/api/whatsapp/send`); no auto-push.
- Cards #4 `tou_switch` and #6 `peak_window_shift` are mutually exclusive (off-peak
  vs peak-heavy snapshots).

## Conventions

- Do **not** commit `Wattseye .pdf` (~41 MB).
- Keep commits scoped; verify Dart with `flutter analyze lib/`.
- Hardware touching mains electricity must be checked by a qualified person before
  powering on.
