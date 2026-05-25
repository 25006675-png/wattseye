"""Shared live-state file — the seam between the Pi runtime and the API server.

`pi_bridge.py` (the Pi brain) writes a dashboard-shaped JSON document here once
per second. `api_server.py`'s `dashboard_payload()` reads it: if the file is
present and fresh, the dashboard shows live values and the app flips its chip
from "Demo data" to "Live Pi"; otherwise the backend falls back to the built-in
demo snapshot. Keeping the contract in this one module means the writer and the
reader can never drift apart.

The JSON keys MUST match what `dashboard_payload()` already returns so the
Flutter app needs no changes (see HARDWARE_CONNECTION.md §14):

    {
      "timestamp":        ISO-8601 string,
      "live_power_w":     float,
      "today_cost_rm":    float,
      "projected_bill_rm":float,
      "occupancy_state":  "home" | "away" | "asleep" | "unknown",
      "occupancy_since":  ISO-8601 string,
      "active_appliances":[ {"name","watts","today_kwh","today_rm"}, ... ],
      "source":           "live_pi"          # marker the app/log can key on
    }
"""

from __future__ import annotations

import json
import os
import tempfile
import time
from pathlib import Path

# Sits next to api_server.py. Gitignored — it is runtime state, not source.
LIVE_STATE_PATH = Path(__file__).resolve().parent / "live_state.json"

# If the file hasn't been refreshed within this many seconds we treat the Pi
# runtime as down and fall back to demo data, rather than showing stale numbers.
DEFAULT_MAX_AGE_S = 15.0


def write_live_state(payload: dict) -> None:
    """Atomically write the dashboard payload. Safe to call once per second.

    Writes to a temp file in the same directory then os.replace()s it, so a
    reader never sees a half-written file.
    """
    payload = {**payload, "source": "live_pi", "_written_at": time.time()}
    LIVE_STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=str(LIVE_STATE_PATH.parent), suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(payload, handle)
        os.replace(tmp, LIVE_STATE_PATH)
    finally:
        if os.path.exists(tmp):
            os.remove(tmp)


def read_live_state(max_age_s: float = DEFAULT_MAX_AGE_S) -> dict | None:
    """Return the live payload if present and fresh, else None.

    `None` is the signal for the caller to fall back to demo data. The
    `_written_at` bookkeeping key is stripped before returning.
    """
    if not LIVE_STATE_PATH.exists():
        return None
    try:
        data = json.loads(LIVE_STATE_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    written_at = data.pop("_written_at", None)
    if written_at is None or (time.time() - float(written_at)) > max_age_s:
        return None
    return data
