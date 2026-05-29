"""Adapter: build a coach `HomeSnapshot` from real data instead of a literal.

The coach engine layers never read raw data — they read a `HomeSnapshot`. Until
now the only snapshot was the hand-written `_demo_snapshot()` literal. This
module is the missing seam between real signals and the coach:

    from_live_state()    -> backend/live_state.json   (the Pi runtime feed)
    from_history(db)     -> ML/sensing/synthetic_history.sqlite  (or a real
                            bench log with the same `readings` schema)

Each returns a `HomeSnapshot` or `None`. `None` means "no usable data" and the
caller (api_server) should fall back to the demo snapshot. Live data realistically
yields 1-2 cards; the 30-day history yields a fuller set — both run through the
exact same coach pipeline as the demo.
"""

from __future__ import annotations

import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from ML.insights.coach.situations import HomeSnapshot

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_HISTORY_DB = ROOT / "ML" / "sensing" / "synthetic_history.sqlite"

RM_PER_KWH = 0.45  # rough flat rate for back-converting a projected bill to kWh

# Appliance columns in the history schema that we segment into events.
_EVENT_COLUMNS = [
    "ac", "kettle", "fridge", "hair_dryer", "iron", "washing_machine",
    "rice_cooker", "tv", "microwave", "computer", "fan",
]
# On-thresholds (W) for event segmentation — coarse, demo-grade.
_ON_THRESHOLD = {
    "ac": 200, "kettle": 800, "fridge": 40, "hair_dryer": 300, "iron": 400,
    "washing_machine": 100, "rice_cooker": 150, "tv": 30, "microwave": 300,
    "computer": 40, "fan": 30,
}


def _phase_for(hour: int) -> str:
    if 6 <= hour < 11:
        return "morning"
    if 11 <= hour < 18:
        return "work"
    if 18 <= hour < 23:
        return "evening"
    return "sleep"


# --------------------------------------------------------------------------- #
# Live state -> HomeSnapshot
# --------------------------------------------------------------------------- #
def from_live_state() -> HomeSnapshot | None:
    """Build a snapshot from the Pi's live_state.json, or None if absent/stale."""
    from backend.live_state import read_live_state

    live = read_live_state()
    if live is None:
        return None

    now = datetime.fromisoformat(live["timestamp"]) if live.get("timestamp") else datetime.now()
    since = None
    if live.get("occupancy_since"):
        try:
            since = datetime.fromisoformat(live["occupancy_since"])
        except ValueError:
            since = None

    active: dict[str, dict[str, Any]] = {}
    for item in live.get("active_appliances", []):
        name = str(item.get("name", "")).strip()
        if not name:
            continue
        active[name] = {"watts": float(item.get("watts", 0.0)), "started_at": since or now}

    projected_kwh = 350.0
    if live.get("projected_bill_rm"):
        projected_kwh = round(float(live["projected_bill_rm"]) / RM_PER_KWH, 1)

    return HomeSnapshot(
        timestamp=now,
        occupancy_state=live.get("occupancy_state", "unknown"),
        occupancy_since=since,
        live_power_w=float(live.get("live_power_w", 0.0)),
        active_appliances=active,
        projected_monthly_kwh=projected_kwh,
        day_of_month=now.day,
    )


# --------------------------------------------------------------------------- #
# History DB -> HomeSnapshot
# --------------------------------------------------------------------------- #
def _segment_events(rows: list[dict], appliance: str, since: datetime) -> list[dict]:
    """Threshold-segment one appliance column into discrete ON events after `since`."""
    col = f"{appliance}_w"
    threshold = _ON_THRESHOLD.get(appliance, 50)
    events: list[dict] = []
    active = False
    start_ts = None
    peak = 0.0
    energy_wh = 0.0
    for row in rows:
        ts = row["_ts"]
        if ts < since:
            continue
        w = float(row.get(col, 0.0) or 0.0)
        if w >= threshold:
            if not active:
                active, start_ts, peak, energy_wh = True, ts, w, 0.0
            peak = max(peak, w)
            energy_wh += w / 60.0  # one row == one minute
        elif active:
            duration_min = (ts - start_ts).total_seconds() / 60.0
            if duration_min >= 2:
                events.append({
                    "appliance": appliance, "start": start_ts, "end": ts,
                    "peak_w": round(peak, 0), "energy_kwh": round(energy_wh / 1000.0, 3),
                    "phase": _phase_for(start_ts.hour),
                })
            active = False
    return events


def from_history(db_path: Path = DEFAULT_HISTORY_DB, now: datetime | None = None) -> HomeSnapshot | None:
    """Build a snapshot from a 30-day-ish `readings` log (synthetic or real bench)."""
    if not Path(db_path).exists():
        return None
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    rows_raw = conn.execute("SELECT * FROM readings ORDER BY timestamp").fetchall()
    conn.close()
    if not rows_raw:
        return None

    rows = [dict(r) for r in rows_raw]
    for r in rows:
        r["_ts"] = datetime.fromisoformat(r["timestamp"])
    last = rows[-1]
    now = now or last["_ts"]

    # occupancy: walk back while the flag is unchanged
    occupied = bool(last.get("occupied", 1))
    occ_since = last["_ts"]
    for r in reversed(rows):
        if bool(r.get("occupied", 1)) != occupied:
            break
        occ_since = r["_ts"]
    occupancy_state = "home" if occupied else "away"

    # active appliances from the last row
    active: dict[str, dict[str, Any]] = {}
    for appliance in _EVENT_COLUMNS:
        w = float(last.get(f"{appliance}_w", 0.0) or 0.0)
        if w >= _ON_THRESHOLD.get(appliance, 50):
            started = last["_ts"]
            for r in reversed(rows):
                if float(r.get(f"{appliance}_w", 0.0) or 0.0) < _ON_THRESHOLD.get(appliance, 50):
                    break
                started = r["_ts"]
            active[appliance] = {"watts": round(w, 0), "started_at": started}

    # recent events: last 24h, across all modeled appliances
    since_24h = now - timedelta(hours=24)
    recent_events: list[dict] = []
    for appliance in _EVENT_COLUMNS:
        recent_events.extend(_segment_events(rows, appliance, since_24h))
    recent_events.sort(key=lambda e: e["start"], reverse=True)

    # energy aggregates (one row == one minute)
    total_kwh = sum(float(r.get("total_w", 0.0) or 0.0) for r in rows) / 60.0 / 1000.0
    span_days = max(1.0, (rows[-1]["_ts"] - rows[0]["_ts"]).total_seconds() / 86400.0)
    monthly_kwh = round(total_kwh / span_days * 30.0, 1)

    # overnight standby (00:00-05:00 minimum band)
    night = [float(r.get("total_w", 0.0) or 0.0) for r in rows if r["_ts"].hour < 5]
    standby = round(min(night), 1) if night else 0.0

    # peak-window fraction (weekday 14:00-22:00)
    peak_wh = sum(float(r.get("total_w", 0.0) or 0.0) for r in rows
                  if r["_ts"].weekday() < 5 and 14 <= r["_ts"].hour < 22)
    all_wh = sum(float(r.get("total_w", 0.0) or 0.0) for r in rows) or 1.0
    peak_fraction = round(peak_wh / all_wh, 3)

    # routine baseline for AC: hours where AC is on >30% of days
    ac_hours: dict[int, list[float]] = {}
    for r in rows:
        ac_hours.setdefault(r["_ts"].hour, []).append(float(r.get("ac_w", 0.0) or 0.0))
    expected_ac_hours = {h for h, vals in ac_hours.items()
                         if sum(v >= _ON_THRESHOLD["ac"] for v in vals) / max(1, len(vals)) > 0.3}
    routine_baseline = {
        "ac": {"expected_on_hours": expected_ac_hours, "observed_days": round(span_days)},
        "fridge": {"expected_on_hours": set(range(24)), "observed_days": round(span_days)},
    }

    return HomeSnapshot(
        timestamp=now,
        occupancy_state=occupancy_state,
        occupancy_since=occ_since,
        live_power_w=round(float(last.get("total_w", 0.0) or 0.0), 1),
        standby_overnight_w=standby,
        active_appliances=active,
        recent_events=recent_events,
        routine_baseline=routine_baseline,
        current_phase=_phase_for(now.hour),
        projected_monthly_kwh=monthly_kwh,
        last_month_kwh=round(monthly_kwh * 0.92, 1),
        last_3mo_avg_kwh=round(monthly_kwh * 0.9, 1),
        peak_window_kwh_fraction=peak_fraction,
        day_of_month=now.day,
    )


if __name__ == "__main__":
    import argparse

    ap = argparse.ArgumentParser(description="Preview a coach snapshot from real data.")
    ap.add_argument("--source", choices=["history", "live"], default="history")
    args = ap.parse_args()

    snap = from_live_state() if args.source == "live" else from_history()
    if snap is None:
        print(f"No usable {args.source} data.")
        raise SystemExit(1)
    print(f"source={args.source}  ts={snap.timestamp}  occ={snap.occupancy_state}  "
          f"live={snap.live_power_w}W  active={list(snap.active_appliances)}  "
          f"events={len(snap.recent_events)}  proj_kwh={snap.projected_monthly_kwh}  "
          f"peak_frac={snap.peak_window_kwh_fraction}")
