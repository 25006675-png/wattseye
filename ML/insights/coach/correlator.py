"""Correlator: turn HomeSnapshot signals into named Situation records.

One function per archetype. Each returns a list[Situation] (0 or more).
Pure detection — no RM math, no text. Just "does this situation hold?"

Archetype taxonomy (5 families, 12 archetypes — see recommendation.md notes):
  Waste:    1 left_on_empty, 2 phantom_standby, 3 simultaneous_peak_load
  Tariff:   4 tou_switch, 5 rp4_tier_cliff, 6 peak_window_shift
  Forecast: 7 bill_trending_high, 8 comparative_regression, 9 routine_shift
  Context:  10 weather_correlated_ac, 11 anomaly_with_action
  Capital:  12 inefficient_continuous_upgrade
"""

from __future__ import annotations

from datetime import timedelta
from typing import Iterable

from .situations import Evidence, HomeSnapshot, Situation

# Thresholds that gate detection. Centralised so they're easy to audit.
LEFT_ON_MIN_DURATION_MIN = 20
LEFT_ON_MIN_POWER_W = 200            # ignore tiny loads (phone charger)
STANDBY_FLAG_W = 30
TIER_CLIFF_KWH = 1500
TIER_CLIFF_PROXIMITY_KWH = 80        # warn when projected within 80 kWh of cliff
BILL_TREND_MULTIPLIER = 1.15         # 15% over recent 3-month average
COMPARATIVE_REGRESSION_MULTIPLIER = 1.20
ROUTINE_SHIFT_MIN_MINUTES = 60
TOU_SAVING_THRESHOLD_FRACTION = 0.6  # need >=60% off-peak to recommend ToU switch
SIMULTANEOUS_MIN_LOADS = 2
SIMULTANEOUS_MIN_TOTAL_W = 2500
HOT_DAY_TEMP_C = 33.0
HOT_DAY_AC_UPLIFT_PCT_MIN = 25.0


# ---------- helpers ----------

def _is_peak_window(ts) -> bool:
    """TNB ToU peak: 14:00-22:00 weekdays."""
    return ts.weekday() < 5 and 14 <= ts.hour < 22


def _new(archetype_id: int, key: str, family, severity, snap, **kw) -> Situation:
    return Situation(
        archetype_id=archetype_id,
        archetype_key=key,
        family=family,
        severity=severity,
        timestamp=snap.timestamp,
        appliance=kw.pop("appliance", None),
        evidence=kw.pop("evidence", []),
        raw_metrics=kw.pop("raw_metrics", {}),
    )


# ---------- Family A: Waste ----------

def detect_left_on_empty(snap: HomeSnapshot) -> list[Situation]:
    """#1 Appliance running while occupancy=away for > threshold."""
    out: list[Situation] = []
    if snap.occupancy_state != "away" or snap.occupancy_since is None:
        return out
    minutes_empty = (snap.timestamp - snap.occupancy_since).total_seconds() / 60.0
    if minutes_empty < LEFT_ON_MIN_DURATION_MIN:
        return out

    for appliance, state in snap.active_appliances.items():
        watts = state.get("watts", 0.0)
        if watts < LEFT_ON_MIN_POWER_W:
            continue
        baseline = snap.routine_baseline.get(appliance, {})
        usual_hours = baseline.get("expected_on_hours", set())
        is_unusual = snap.timestamp.hour not in usual_hours if usual_hours else True

        evidence = [
            Evidence("Occupancy", f"Room empty since {snap.occupancy_since.strftime('%H:%M')} ({int(minutes_empty)} min).", 0.9),
            Evidence("NILM", f"{appliance.replace('_', ' ').title()} drawing {watts:.0f}W.", 0.85),
            Evidence("K-Means phase", f"Current phase: {snap.current_phase}.", 0.8),
        ]
        if usual_hours:
            evidence.append(
                Evidence(
                    "Routine baseline",
                    f"{appliance.title()} normally {'on' if not is_unusual else 'off'} at this hour "
                    f"(observed over {baseline.get('observed_days', 0)} days).",
                    0.85,
                )
            )

        severity = "high" if minutes_empty >= 45 and watts >= 800 else "medium"
        out.append(Situation(
            archetype_id=1, archetype_key="left_on_empty", family="waste",
            severity=severity, timestamp=snap.timestamp, appliance=appliance,
            evidence=evidence,
            raw_metrics={
                "watts": watts,
                "minutes_empty": minutes_empty,
                "in_peak": _is_peak_window(snap.timestamp),
                "weekly_frequency": baseline.get("empty_overlap_per_week", 4),
            },
        ))
    return out


def detect_phantom_standby(snap: HomeSnapshot) -> list[Situation]:
    """#2 Overnight minimum load exceeds standby threshold."""
    if snap.standby_overnight_w < STANDBY_FLAG_W:
        return []
    evidence = [
        Evidence("NILM minimum-window", f"Overnight base load: {snap.standby_overnight_w:.0f}W (when household asleep)."),
        Evidence("Routine baseline", "Sleep phase identified by K-Means; no high-draw appliances expected."),
    ]
    return [Situation(
        archetype_id=2, archetype_key="phantom_standby", family="waste",
        severity="medium" if snap.standby_overnight_w < 80 else "high",
        timestamp=snap.timestamp, appliance=None, evidence=evidence,
        raw_metrics={"standby_w": snap.standby_overnight_w},
    )]


def detect_simultaneous_peak_load(snap: HomeSnapshot) -> list[Situation]:
    """#3 Multiple high-draw appliances during ToU peak window."""
    if not _is_peak_window(snap.timestamp):
        return []
    high_loads = [(a, s.get("watts", 0)) for a, s in snap.active_appliances.items() if s.get("watts", 0) > 500]
    if len(high_loads) < SIMULTANEOUS_MIN_LOADS:
        return []
    total = sum(w for _, w in high_loads)
    if total < SIMULTANEOUS_MIN_TOTAL_W:
        return []
    names = ", ".join(a.replace("_", " ") for a, _ in high_loads)
    evidence = [
        Evidence("NILM", f"{len(high_loads)} appliances active simultaneously: {names} ({total:.0f}W total)."),
        Evidence("ToU schedule", f"Currently in TNB peak window (14:00–22:00 weekdays)."),
    ]
    return [Situation(
        archetype_id=3, archetype_key="simultaneous_peak_load", family="waste",
        severity="medium", timestamp=snap.timestamp, appliance=None, evidence=evidence,
        raw_metrics={"total_w": total, "appliances": [a for a, _ in high_loads]},
    )]


# ---------- Family B: Tariff ----------

def detect_tou_switch(snap: HomeSnapshot) -> list[Situation]:
    """#4 User on standard tariff but pattern is off-peak heavy → recommend ToU."""
    if snap.on_tou_tariff:
        return []
    offpeak_frac = 1.0 - snap.peak_window_kwh_fraction
    if offpeak_frac < TOU_SAVING_THRESHOLD_FRACTION:
        return []
    evidence = [
        Evidence("Routine engine", f"{offpeak_frac*100:.0f}% of your last 30 days of usage fell in off-peak hours."),
        Evidence("TNB tariff calc", "ToU off-peak rate is 17.55 sen/kWh lower than peak — savings depend on actual usage split."),
    ]
    return [Situation(
        archetype_id=4, archetype_key="tou_switch", family="tariff",
        severity="medium", timestamp=snap.timestamp, appliance=None, evidence=evidence,
        raw_metrics={"offpeak_fraction": offpeak_frac, "monthly_kwh": snap.projected_monthly_kwh},
    )]


def detect_rp4_tier_cliff(snap: HomeSnapshot) -> list[Situation]:
    """#5 Projected kWh approaching the 1500 kWh tier cliff."""
    proj = snap.projected_monthly_kwh
    if proj < TIER_CLIFF_KWH - TIER_CLIFF_PROXIMITY_KWH or proj > TIER_CLIFF_KWH + 200:
        return []
    over = proj - TIER_CLIFF_KWH
    evidence = [
        Evidence("Cost engine", f"Projected month-end: {proj:.0f} kWh."),
        Evidence("TNB RP4 schedule", "Crossing 1,500 kWh raises generation rate from 27.03 to 37.03 sen/kWh on every unit."),
    ]
    severity = "high" if over > 0 else "medium"
    return [Situation(
        archetype_id=5, archetype_key="rp4_tier_cliff", family="tariff",
        severity=severity, timestamp=snap.timestamp, appliance=None, evidence=evidence,
        raw_metrics={"projected_kwh": proj, "over_cliff_kwh": max(0.0, over)},
    )]


def detect_peak_window_shift(snap: HomeSnapshot) -> list[Situation]:
    """#6 Schedulable appliances regularly run in peak window."""
    if not snap.on_tou_tariff and snap.peak_window_kwh_fraction < 0.5:
        return []  # only nudge people whose pattern actually leans peak-heavy
    schedulable = {"dishwasher", "washer", "washing_machine", "dryer", "water_heater"}
    candidates = []
    for ev in snap.recent_events:
        if ev.get("appliance") in schedulable and _is_peak_window(ev["start"]):
            candidates.append(ev)
    if len(candidates) < 3:
        return []
    appliances = sorted({c["appliance"] for c in candidates})
    total_kwh = sum(c.get("energy_kwh", 0) for c in candidates)
    evidence = [
        Evidence("NILM", f"{len(candidates)} schedulable runs in peak window over last 14 days "
                          f"({', '.join(a.replace('_', ' ') for a in appliances)})."),
        Evidence("ToU schedule", "Shifting these to after 22:00 would charge at off-peak rate."),
    ]
    return [Situation(
        archetype_id=6, archetype_key="peak_window_shift", family="tariff",
        severity="medium", timestamp=snap.timestamp, appliance=appliances[0] if appliances else None,
        evidence=evidence,
        raw_metrics={"peak_kwh": total_kwh, "appliances": appliances, "run_count": len(candidates)},
    )]


# ---------- Family C: Forecast ----------

def detect_bill_trending_high(snap: HomeSnapshot) -> list[Situation]:
    """#7 Projected bill exceeds 3-month average by >15%."""
    if snap.last_3mo_avg_kwh <= 0:
        return []
    ratio = snap.projected_monthly_kwh / snap.last_3mo_avg_kwh
    if ratio < BILL_TREND_MULTIPLIER:
        return []
    # Find top driver via NILM
    driver = None
    if snap.recent_events:
        from collections import Counter
        kwh_by_app = Counter()
        for ev in snap.recent_events:
            kwh_by_app[ev.get("appliance", "unknown")] += ev.get("energy_kwh", 0)
        if kwh_by_app:
            driver = kwh_by_app.most_common(1)[0][0]

    evidence = [
        Evidence("Cost engine", f"Projection: {snap.projected_monthly_kwh:.0f} kWh "
                                f"(+{(ratio-1)*100:.0f}% vs 3-month average of {snap.last_3mo_avg_kwh:.0f} kWh)."),
    ]
    if driver:
        evidence.append(Evidence("NILM attribution", f"Main driver: {driver.replace('_', ' ')} usage."))
    severity = "high" if ratio >= 1.25 else "medium"
    return [Situation(
        archetype_id=7, archetype_key="bill_trending_high", family="forecast",
        severity=severity, timestamp=snap.timestamp, appliance=driver, evidence=evidence,
        raw_metrics={"projected_kwh": snap.projected_monthly_kwh, "baseline_kwh": snap.last_3mo_avg_kwh,
                     "ratio": ratio, "driver": driver},
    )]


def detect_comparative_regression(snap: HomeSnapshot) -> list[Situation]:
    """#8 Same-period (week vs same week last month) regression on a specific appliance."""
    # We expect routine_baseline to contain "this_week_kwh" and "same_week_last_month_kwh"
    flagged = []
    for appliance, b in snap.routine_baseline.items():
        this_w = b.get("this_week_kwh")
        prev_w = b.get("same_week_last_month_kwh")
        if this_w is None or prev_w is None or prev_w <= 0:
            continue
        if this_w / prev_w >= COMPARATIVE_REGRESSION_MULTIPLIER:
            flagged.append((appliance, this_w, prev_w))
    out: list[Situation] = []
    for appliance, this_w, prev_w in flagged:
        delta_pct = (this_w / prev_w - 1) * 100
        evidence = [
            Evidence("NILM", f"{appliance.title()} used {this_w:.1f} kWh this week vs {prev_w:.1f} kWh same week last month "
                              f"(+{delta_pct:.0f}%)."),
            Evidence("Routine engine", "External conditions (weather, calendar) appear similar — likely usage pattern change."),
        ]
        out.append(Situation(
            archetype_id=8, archetype_key="comparative_regression", family="forecast",
            severity="medium", timestamp=snap.timestamp, appliance=appliance, evidence=evidence,
            raw_metrics={"this_kwh": this_w, "prev_kwh": prev_w, "delta_pct": delta_pct},
        ))
    return out


def detect_routine_shift(snap: HomeSnapshot) -> list[Situation]:
    """#9 K-Means phase boundaries drift > 60 min vs last month."""
    drifted = [(phase, mins) for phase, mins in snap.phase_drift_minutes.items() if abs(mins) >= ROUTINE_SHIFT_MIN_MINUTES]
    if not drifted:
        return []
    phase, mins = max(drifted, key=lambda x: abs(x[1]))
    direction = "later" if mins > 0 else "earlier"
    evidence = [
        Evidence("K-Means clustering", f"'{phase}' phase boundary has drifted {abs(mins)} min {direction} over the past 3 weeks."),
        Evidence("Routine engine", "Scheduled appliances (AC, water heater) may still follow the old timing."),
    ]
    return [Situation(
        archetype_id=9, archetype_key="routine_shift", family="forecast",
        severity="low", timestamp=snap.timestamp, appliance=None, evidence=evidence,
        raw_metrics={"phase": phase, "drift_minutes": mins},
    )]


# ---------- Family D: Context ----------

def detect_weather_correlated_ac(snap: HomeSnapshot) -> list[Situation]:
    """#10 Hot days forecast + learned AC uplift correlation."""
    if snap.hot_days_next_7 == 0 or snap.hot_day_ac_uplift_pct < HOT_DAY_AC_UPLIFT_PCT_MIN:
        return []
    evidence = [
        Evidence("Open-Meteo forecast", f"{snap.hot_days_next_7} day(s) forecast above {HOT_DAY_TEMP_C:.0f}°C in next 7 days."),
        Evidence("Routine engine (learned)", f"Your AC usage rises ~{snap.hot_day_ac_uplift_pct:.0f}% on hot days."),
    ]
    return [Situation(
        archetype_id=10, archetype_key="weather_correlated_ac", family="context",
        severity="low", timestamp=snap.timestamp, appliance="ac", evidence=evidence,
        raw_metrics={"hot_days": snap.hot_days_next_7, "uplift_pct": snap.hot_day_ac_uplift_pct},
    )]


def detect_anomaly_with_action(snap: HomeSnapshot) -> list[Situation]:
    """#11 Isolation Forest anomaly that maps to a known actionable fix."""
    if snap.last_anomaly_score is None or snap.last_anomaly_event is None:
        return []
    # Lower IF score = more anomalous; treat < -0.1 as flagged
    if snap.last_anomaly_score >= -0.1:
        return []
    ev = snap.last_anomaly_event
    appliance = ev.get("appliance", "unknown")
    hour = ev.get("start").hour if ev.get("start") else snap.timestamp.hour
    # Only emit if the anomaly is unusual-hour for an actionable appliance
    actionable_hours_off = {"water_heater": range(0, 5), "iron": range(0, 6), "kettle": range(0, 5)}
    if appliance not in actionable_hours_off or hour not in actionable_hours_off[appliance]:
        return []
    evidence = [
        Evidence("Isolation Forest", f"Event scored {snap.last_anomaly_score:.2f} — outside learned baseline for this appliance."),
        Evidence("Routine engine", f"{appliance.replace('_', ' ').title()} normally inactive at {hour:02d}:00."),
    ]
    return [Situation(
        archetype_id=11, archetype_key="anomaly_with_action", family="context",
        severity="medium", timestamp=snap.timestamp, appliance=appliance, evidence=evidence,
        raw_metrics={"anomaly_score": snap.last_anomaly_score, "hour": hour,
                     "duration_min": ev.get("duration_min", 0), "peak_w": ev.get("peak_w", 0)},
    )]


# ---------- Family E: Capital ----------

def detect_inefficient_upgrade(snap: HomeSnapshot) -> list[Situation]:
    """#12 Steady-state appliance draw exceeds efficient-class average → upgrade card."""
    out: list[Situation] = []
    for cand in snap.inefficient_continuous_loads:
        appliance = cand["appliance"]
        current_w = cand["current_w"]
        efficient_w = cand["efficient_class_w"]
        if current_w <= efficient_w * 1.3:
            continue  # not inefficient enough to be worth flagging
        evidence = [
            Evidence("NILM steady-state", f"{appliance.title()} draws {current_w:.0f}W continuous (idle)."),
            Evidence("ST efficiency registry", f"5-star class average for same size: {efficient_w:.0f}W."),
        ]
        out.append(Situation(
            archetype_id=12, archetype_key="inefficient_upgrade", family="capital",
            severity="low", timestamp=snap.timestamp, appliance=appliance, evidence=evidence,
            raw_metrics={
                "current_w": current_w, "efficient_w": efficient_w,
                "replacement_rm": cand.get("replacement_rm", 0),
                "registry_url": cand.get("registry_url", ""),
            },
        ))
    return out


# ---------- public entrypoint ----------

ALL_DETECTORS = [
    detect_left_on_empty,
    detect_phantom_standby,
    detect_simultaneous_peak_load,
    detect_tou_switch,
    detect_rp4_tier_cliff,
    detect_peak_window_shift,
    detect_bill_trending_high,
    detect_comparative_regression,
    detect_routine_shift,
    detect_weather_correlated_ac,
    detect_anomaly_with_action,
    detect_inefficient_upgrade,
]


def correlate(snap: HomeSnapshot) -> list[Situation]:
    """Run every detector and return the union of detected situations."""
    out: list[Situation] = []
    for detector in ALL_DETECTORS:
        out.extend(detector(snap))
    return out
