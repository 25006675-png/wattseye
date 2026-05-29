# WattsEye — gap analysis & wiring log

Record of the UI/logic/Pi gaps found in review and what was implemented to close
them. Hardware (clamp install, calibration) is explicitly out of scope here.

## Gaps found

1. **Coach cards ran on a hardcoded literal**, not real data. The only
   `HomeSnapshot` in the codebase was `_demo_snapshot()`. `/api/coach/cards`
   never read `synthetic_history` or `live_state` — the engine was real, the
   input was a fixture. Dashboard could go live while the coach stayed frozen.
2. **UI surfaces not wired to existing endpoints.** `/api/bill` and
   `/api/history` were served but never called — Bill and History pages were
   100% hardcoded. `/api/weather`, `/api/report/monthly` also unused.
3. **Fake "Turn off" button** — showed a snackbar, called nothing; no cutoff
   API route existed (only MQTT inside pi_bridge).
4. **No way to show both** the 12-card showcase *and* a sparse live set.
5. **Live NILM not wired into the Pi runtime** — `pi_bridge` lumps non-AC load
   into one "other" bucket; no per-appliance disaggregation at runtime.

## Implemented (this pass)

- **`backend/snapshot_builder.py`** — `from_live_state()` (Pi feed) and
  `from_history()` (synthetic_history.sqlite / real bench log) build a real
  `HomeSnapshot`. Events come from threshold segmentation; projected kWh,
  standby, peak-window fraction, AC routine baseline all derived from the log.
- **Coach modes** — `/api/coach/cards?mode=showcase|live`.
  `showcase` → demo literal (full archetype set). `live` → Pi live_state if
  fresh, else bench-log history, else demo. Each card tagged `data_source`
  (`live` / `replay` / `showcase`). Verified: showcase→10 cards, live→2 cards
  (`replay`) from the bench log.
- **Real cutoff endpoint** — `POST /api/ac/cutoff` publishes the MQTT off-command
  on `wattseye/ac/command` (pi_bridge → ESP32). Degrades honestly (paho missing
  / broker down → `sent:false` with reason; never fakes success).
- **App wiring (Flutter, 5 tabs kept):**
  - Coach tab: Showcase/Live `SegmentedButton`; per-card `LIVE`/`REPLAY` chip.
  - Bill page: headline total / kWh / effective rate / ToU comparison from
    `/api/bill` (falls back to demo numbers offline).
  - History page: live "Recent days" card from `/api/history`.
  - "Turn off" button: now calls `/api/ac/cutoff` and reports the real result.
  - `flutter analyze lib/` → no issues.

## Still open (not done here)

- **Live NILM → per-appliance tiles + events.** Wire `electricity_model.py`
  (faithful Discriminator) into `pi_bridge` so live disaggregation feeds
  `active_appliances` + `recent_events` instead of one "other" bucket.
- **Sensor calibration** — `power_math` constants are placeholders; live watts
  need the `build_now/08` calibration before they're trustworthy.
- **Minor:** drop unused `flask` from `backend/requirements.txt`; optional
  `run_pi.sh` to launch broker+reader+bridge+api together.
