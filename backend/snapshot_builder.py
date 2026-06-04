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
# Real sub-metered replay source (iAWE, Delhi). Built by ML/sensing/build_iawe_history.py.
# Delhi coords feed the weather-AC uplift; falls back to the synthetic Malaysian fixture.
IAWE_HISTORY_DB = ROOT / "ML" / "sensing" / "iawe_history.sqlite"
IAWE_COORDS = (28.61, 77.21)

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


def _weather_ac_uplift(rows: list[dict], lat: float, lon: float) -> tuple[float, float]:
    """Learned weather-AC correlation from this home's own history.

    Returns (hot_day_ac_uplift_pct, avg_daily_ac_kwh). Groups AC energy by day,
    joins outdoor daily-max temperature from the weather archive, and measures how
    much more AC runs on hot days (>33°C) vs cooler ones. Fully guarded: any failure
    (offline, no AC, no hot/cool split) yields (0.0, avg) so the card simply does not
    fire — never a fabricated number.
    """
    from collections import defaultdict

    ac_by_date: dict = defaultdict(float)
    for r in rows:
        ac_by_date[r["_ts"].date()] += float(r.get("ac_w", 0.0) or 0.0) / 60.0 / 1000.0
    if not ac_by_date:
        return 0.0, 0.0
    avg_daily_ac = sum(ac_by_date.values()) / len(ac_by_date)
    try:
        from ML.insights.coach.weather import get_archive_daily_max
        temps = get_archive_daily_max(lat, lon, min(ac_by_date).isoformat(), max(ac_by_date).isoformat())
        if not temps:
            return 0.0, avg_daily_ac
        hot = [k for d, k in ac_by_date.items() if (temps.get(d.isoformat()) or 0) > 33.0]
        cool = [k for d, k in ac_by_date.items() if 0 < (temps.get(d.isoformat()) or 0) <= 33.0]
        if not hot or not cool:
            return 0.0, avg_daily_ac
        mean_hot, mean_cool = sum(hot) / len(hot), sum(cool) / len(cool)
        if mean_cool <= 0:
            return 0.0, avg_daily_ac
        return max(0.0, (mean_hot / mean_cool - 1.0) * 100.0), avg_daily_ac
    except Exception:
        return 0.0, avg_daily_ac


def _kwh_between(rows: list[dict], col: str, start: datetime, end: datetime) -> float:
    return sum(float(r.get(col, 0.0) or 0.0) for r in rows if start < r["_ts"] <= end) / 60.0 / 1000.0


def _pick_reference_idx(rows: list[dict]) -> int:
    """Index of the most recent weekday peak-window minute with >=2 loads >500W (for #3
    simultaneous_peak_load); else the last row. Picks a representative 'now' from real data."""
    big = ("ac", "kettle", "iron", "washing_machine", "rice_cooker", "microwave", "hair_dryer")
    for i in range(len(rows) - 1, -1, -1):
        ts = rows[i]["_ts"]
        if ts.weekday() < 5 and 14 <= ts.hour < 22:
            if sum(1 for a in big if float(rows[i].get(f"{a}_w", 0.0) or 0.0) > 500) >= 2:
                return i
    return len(rows) - 1


def _inefficient_loads(rows: list[dict]) -> list[dict]:
    """Compare each continuous appliance's typical steady-state draw to the ST efficiency
    registry (archetype #12). Only fires for genuinely inefficient loads; returns [] otherwise."""
    from statistics import median
    from ML.insights.coach.efficiency_registry import compare_to_best

    out: list[dict] = []
    # (history column, registry appliance name, assumed size band)
    for col, reg_name, band in (("fridge", "refrigerator", "medium"),
                                ("water_heater", "water_heater", "medium")):
        on = [float(r.get(f"{col}_w", 0.0) or 0.0) for r in rows
              if float(r.get(f"{col}_w", 0.0) or 0.0) >= _ON_THRESHOLD.get(col, 50)]
        if len(on) < 60:          # need sustained presence to call it a continuous load
            continue
        try:
            cmp = compare_to_best(reg_name, band, round(median(on), 0))
        except Exception:
            cmp = None
        if cmp:
            cmp["appliance"] = col
            out.append(cmp)
    return out


def from_history(db_path: Path = DEFAULT_HISTORY_DB, now: datetime | None = None,
                 lat: float = 3.139, lon: float = 101.687) -> HomeSnapshot | None:
    """Build a snapshot from a `readings` log (synthetic fixture or real iAWE/bench).

    Populates every field the coach detectors read that can be derived from the data:
    standby (#2), peak fraction (#4), tier projection (#5), simultaneous peak (#3),
    real month-over-month (#7), week-over-week per appliance (#8), weather-AC uplift (#10),
    and inefficient continuous loads (#12). Occupancy-dependent (#1) is left to the live
    mmWave path; weather-forecast (#10 trigger) and ToU-assumption (#6) are set elsewhere."""
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
    # reference "now": a representative recent moment (peak-window with concurrent loads
    # if one exists, for #3) rather than blindly the last row.
    ref_idx = _pick_reference_idx(rows)
    ref = rows[ref_idx]
    rows_upto = rows[: ref_idx + 1]
    now = now or ref["_ts"]

    # occupancy: walk back while the flag is unchanged
    occupied = bool(ref.get("occupied", 1))
    occ_since = ref["_ts"]
    for r in reversed(rows_upto):
        if bool(r.get("occupied", 1)) != occupied:
            break
        occ_since = r["_ts"]
    occupancy_state = "home" if occupied else "away"

    # active appliances as of the reference row
    active: dict[str, dict[str, Any]] = {}
    for appliance in _EVENT_COLUMNS:
        w = float(ref.get(f"{appliance}_w", 0.0) or 0.0)
        if w >= _ON_THRESHOLD.get(appliance, 50):
            started = ref["_ts"]
            for r in reversed(rows_upto):
                if float(r.get(f"{appliance}_w", 0.0) or 0.0) < _ON_THRESHOLD.get(appliance, 50):
                    break
                started = r["_ts"]
            active[appliance] = {"watts": round(w, 0), "started_at": started}

    # recent events: last 24h up to `now`, across all modeled appliances
    since_24h = now - timedelta(hours=24)
    recent_events: list[dict] = []
    for appliance in _EVENT_COLUMNS:
        recent_events.extend(_segment_events(rows_upto, appliance, since_24h))
    recent_events.sort(key=lambda e: e["start"], reverse=True)

    # energy aggregates (one row == one minute)
    data_end = rows[-1]["_ts"]
    span_days = max(1.0, (data_end - rows[0]["_ts"]).total_seconds() / 86400.0)

    # projected month = most recent 30 days, normalised to 30
    recent_cut = data_end - timedelta(days=30)
    recent_rows = [r for r in rows if r["_ts"] > recent_cut]
    recent_span = max(1.0, (data_end - recent_rows[0]["_ts"]).total_seconds() / 86400.0) if recent_rows else 1.0
    monthly_kwh = round(_kwh_between(rows, "total_w", recent_cut, data_end) / recent_span * 30.0, 1)

    # real month-over-month baseline (#7): prior 30-day block, if the log spans it
    prior_cut = data_end - timedelta(days=60)
    prior_rows = [r for r in rows if prior_cut < r["_ts"] <= recent_cut]
    prior_span = (recent_cut - prior_rows[0]["_ts"]).total_seconds() / 86400.0 if prior_rows else 0.0
    if prior_rows and prior_span >= 20:
        prior_monthly = round(_kwh_between(rows, "total_w", prior_cut, recent_cut) / max(1.0, prior_span) * 30.0, 1)
        last_month_kwh = last_3mo_avg_kwh = prior_monthly
    else:
        last_month_kwh = round(monthly_kwh * 0.92, 1)   # fallback when no prior month in the log
        last_3mo_avg_kwh = round(monthly_kwh * 0.9, 1)

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
    routine_baseline: dict[str, dict[str, Any]] = {
        "ac": {"expected_on_hours": expected_ac_hours, "observed_days": round(span_days)},
        "fridge": {"expected_on_hours": set(range(24)), "observed_days": round(span_days)},
    }

    # week-over-week per appliance (#8): this week vs the same week ~1 month ago
    if span_days >= 35:
        for appliance in _EVENT_COLUMNS:
            col = f"{appliance}_w"
            this_w = _kwh_between(rows, col, data_end - timedelta(days=7), data_end)
            prev_w = _kwh_between(rows, col, data_end - timedelta(days=35), data_end - timedelta(days=28))
            if prev_w > 0.05:
                b = routine_baseline.setdefault(appliance, {})
                b["this_week_kwh"] = round(this_w, 2)
                b["same_week_last_month_kwh"] = round(prev_w, 2)

    ac_uplift_pct, avg_daily_ac = _weather_ac_uplift(rows, lat, lon)

    return HomeSnapshot(
        timestamp=now,
        occupancy_state=occupancy_state,
        occupancy_since=occ_since,
        live_power_w=round(float(ref.get("total_w", 0.0) or 0.0), 1),
        standby_overnight_w=standby,
        active_appliances=active,
        recent_events=recent_events,
        routine_baseline=routine_baseline,
        current_phase=_phase_for(now.hour),
        projected_monthly_kwh=monthly_kwh,
        last_month_kwh=last_month_kwh,
        last_3mo_avg_kwh=last_3mo_avg_kwh,
        peak_window_kwh_fraction=peak_fraction,
        hot_day_ac_uplift_pct=round(ac_uplift_pct, 1),
        avg_daily_ac_kwh=round(avg_daily_ac, 3),
        inefficient_continuous_loads=_inefficient_loads(rows),
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
