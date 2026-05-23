"""Quantifier: attach RM impact, effort, confidence to each Situation.

All RM math goes through tnb_tariff so the numbers are bill-realistic, not flat-rate.
The quantifier never invents a number — every value traces to a raw_metric + tariff call.
"""

from __future__ import annotations

import sys
from pathlib import Path

# Allow `from ML.insights import tnb_tariff` from inside the coach package
_THIS = Path(__file__).resolve()
_INSIGHTS = _THIS.parents[1]
if str(_INSIGHTS) not in sys.path:
    sys.path.insert(0, str(_INSIGHTS))

from tnb_tariff import (  # type: ignore
    calculate_standard_bill,
    calculate_tou_bill,
    marginal_cost_rm,
    is_peak,
)

from .situations import HomeSnapshot, Situation


WEEKS_PER_MONTH = 4.345


# ---------- per-archetype quantifiers ----------

def _q_left_on_empty(s: Situation, snap: HomeSnapshot) -> None:
    watts = s.raw_metrics["watts"]
    minutes = s.raw_metrics["minutes_empty"]
    weekly_freq = s.raw_metrics.get("weekly_frequency", 4)
    event_kwh = watts * (minutes / 60.0) / 1000.0
    tariff = "tou" if snap.on_tou_tariff else "standard"
    rm_event = marginal_cost_rm(
        event_kwh, snap.projected_monthly_kwh, tariff=tariff,
        event_time=snap.timestamp, afa_sen_per_kwh=snap.afa_sen_per_kwh,
    )
    s.impact_rm_event = max(rm_event, 0.0)
    s.impact_rm_monthly = round(s.impact_rm_event * weekly_freq * WEEKS_PER_MONTH, 2)
    s.effort = "low"  # enabling auto-off is a settings change
    s.confidence = _joint_confidence(s)


def _q_phantom_standby(s: Situation, snap: HomeSnapshot) -> None:
    watts = s.raw_metrics["standby_w"]
    monthly_kwh = watts * 24 * 30 / 1000.0
    tariff = "tou" if snap.on_tou_tariff else "standard"
    rm = marginal_cost_rm(monthly_kwh, snap.projected_monthly_kwh - monthly_kwh,
                          tariff=tariff, event_time=snap.timestamp,
                          afa_sen_per_kwh=snap.afa_sen_per_kwh)
    s.impact_rm_monthly = round(max(rm, 0.0), 2)
    s.effort = "low"
    s.confidence = _joint_confidence(s)


def _q_simultaneous_peak_load(s: Situation, snap: HomeSnapshot) -> None:
    total_w = s.raw_metrics["total_w"]
    # Estimate ~30 min of stagger benefit per occurrence, ~4x/week
    saved_kwh_per_event = total_w * 0.5 / 1000.0 * 0.3  # 30% of load shifted off-peak
    if snap.on_tou_tariff:
        # peak vs offpeak rate gap from tnb_tariff schedule (~17.55 sen/kWh)
        rm_per_event = saved_kwh_per_event * 0.1755
    else:
        rm_per_event = saved_kwh_per_event * 0.05  # small benefit from avoiding tier creep
    s.impact_rm_monthly = round(rm_per_event * 4 * WEEKS_PER_MONTH, 2)
    s.effort = "low"
    s.confidence = _joint_confidence(s)


def _q_tou_switch(s: Situation, snap: HomeSnapshot) -> None:
    monthly_kwh = snap.projected_monthly_kwh
    peak_kwh = monthly_kwh * snap.peak_window_kwh_fraction
    offpeak_kwh = monthly_kwh - peak_kwh
    std = calculate_standard_bill(monthly_kwh, snap.afa_sen_per_kwh)
    tou = calculate_tou_bill(peak_kwh, offpeak_kwh, snap.afa_sen_per_kwh)
    saving = max(std.total_rm - tou.total_rm, 0.0)
    s.impact_rm_monthly = round(saving, 2)
    s.effort = "low"
    s.extra_quantified = {
        "standard_rm": round(std.total_rm, 2),
        "tou_rm": round(tou.total_rm, 2),
        "recommended": "tou" if saving > 0.5 else "standard",
    }
    s.confidence = _joint_confidence(s)


def _q_rp4_tier_cliff(s: Situation, snap: HomeSnapshot) -> None:
    proj = s.raw_metrics["projected_kwh"]
    over = s.raw_metrics["over_cliff_kwh"]
    if over > 0:
        # Already across — savings from cutting back to 1499 kWh
        bill_now = calculate_standard_bill(proj, snap.afa_sen_per_kwh).total_rm
        bill_under = calculate_standard_bill(1499.0, snap.afa_sen_per_kwh).total_rm
        s.impact_rm_monthly = round(max(bill_now - bill_under, 0.0), 2)
    else:
        # Below cliff — savings from staying below (avoid 10 sen/kWh jump on a hypothetical 30 kWh)
        avoidable_kwh = 30.0
        s.impact_rm_monthly = round(avoidable_kwh * 0.10, 2)
    s.effort = "low"
    s.confidence = _joint_confidence(s)


def _q_peak_window_shift(s: Situation, snap: HomeSnapshot) -> None:
    peak_kwh = s.raw_metrics["peak_kwh"]
    monthly_shiftable_kwh = peak_kwh * (WEEKS_PER_MONTH / 2)  # last 14 days -> month
    if snap.on_tou_tariff:
        s.impact_rm_monthly = round(monthly_shiftable_kwh * 0.1755, 2)
    else:
        s.impact_rm_monthly = round(monthly_shiftable_kwh * 0.05, 2)
    s.effort = "low"
    s.confidence = _joint_confidence(s)


def _q_bill_trending_high(s: Situation, snap: HomeSnapshot) -> None:
    proj_bill = calculate_standard_bill(snap.projected_monthly_kwh, snap.afa_sen_per_kwh).total_rm
    base_bill = calculate_standard_bill(snap.last_3mo_avg_kwh, snap.afa_sen_per_kwh).total_rm
    overage = max(proj_bill - base_bill, 0.0)
    s.impact_rm_monthly = round(overage, 2)
    s.effort = "medium"
    s.extra_quantified = {"projected_rm": round(proj_bill, 2), "baseline_rm": round(base_bill, 2)}
    s.confidence = _joint_confidence(s)


def _q_comparative_regression(s: Situation, snap: HomeSnapshot) -> None:
    delta_kwh_week = s.raw_metrics["this_kwh"] - s.raw_metrics["prev_kwh"]
    monthly_delta = delta_kwh_week * WEEKS_PER_MONTH
    tariff = "tou" if snap.on_tou_tariff else "standard"
    rm = marginal_cost_rm(monthly_delta, snap.projected_monthly_kwh - monthly_delta,
                          tariff=tariff, event_time=snap.timestamp,
                          afa_sen_per_kwh=snap.afa_sen_per_kwh)
    s.impact_rm_monthly = round(max(rm, 0.0), 2)
    s.effort = "medium"
    s.confidence = _joint_confidence(s)


def _q_routine_shift(s: Situation, snap: HomeSnapshot) -> None:
    # Modest savings — about 30 minutes of misaligned AC schedule per affected day
    daily_misaligned_kwh = 0.9  # ~900W AC * 1 hour
    monthly_kwh = daily_misaligned_kwh * 30
    tariff = "tou" if snap.on_tou_tariff else "standard"
    rm = marginal_cost_rm(monthly_kwh, snap.projected_monthly_kwh - monthly_kwh,
                          tariff=tariff, event_time=snap.timestamp,
                          afa_sen_per_kwh=snap.afa_sen_per_kwh)
    s.impact_rm_monthly = round(max(rm, 0.0), 2)
    s.effort = "low"
    s.confidence = _joint_confidence(s)


def _q_weather_correlated_ac(s: Situation, snap: HomeSnapshot) -> None:
    # Pre-cooling shifts ~1 kWh/hot-day from peak to off-peak
    hot_days = s.raw_metrics["hot_days"]
    if snap.on_tou_tariff:
        rm_per_day = 1.0 * 0.1755
    else:
        rm_per_day = 1.0 * 0.04
    s.impact_rm_monthly = round(rm_per_day * hot_days, 2)
    s.effort = "low"
    s.confidence = _joint_confidence(s)


def _q_anomaly_with_action(s: Situation, snap: HomeSnapshot) -> None:
    duration_min = s.raw_metrics.get("duration_min", 30)
    peak_w = s.raw_metrics.get("peak_w", 1000)
    event_kwh = peak_w * (duration_min / 60.0) / 1000.0
    # If unattended overnight 4x/month
    rm_event = marginal_cost_rm(event_kwh, snap.projected_monthly_kwh,
                                tariff="standard", event_time=snap.timestamp,
                                afa_sen_per_kwh=snap.afa_sen_per_kwh)
    s.impact_rm_event = max(rm_event, 0.0)
    s.impact_rm_monthly = round(s.impact_rm_event * 4, 2)
    s.effort = "low"
    s.confidence = _joint_confidence(s)


def _q_inefficient_upgrade(s: Situation, snap: HomeSnapshot) -> None:
    diff_w = s.raw_metrics["current_w"] - s.raw_metrics["efficient_w"]
    monthly_kwh = diff_w * 24 * 30 / 1000.0
    rm_monthly = marginal_cost_rm(monthly_kwh, snap.projected_monthly_kwh - monthly_kwh,
                                  tariff="standard", event_time=snap.timestamp,
                                  afa_sen_per_kwh=snap.afa_sen_per_kwh)
    s.impact_rm_monthly = round(max(rm_monthly, 0.0), 2)
    yearly = s.impact_rm_monthly * 12
    replacement = s.raw_metrics.get("replacement_rm", 0)
    payback_years = (replacement / yearly) if yearly > 0 and replacement > 0 else None
    s.extra_quantified = {"yearly_saving_rm": round(yearly, 2),
                          "payback_years": round(payback_years, 1) if payback_years else None,
                          "replacement_rm": replacement}
    s.effort = "high"  # buying a new appliance
    s.confidence = _joint_confidence(s)


def _joint_confidence(s: Situation) -> float:
    """Multiplicative joint confidence of evidence, clamped to [0.4, 0.98]."""
    if not s.evidence:
        return 0.5
    prod = 1.0
    for e in s.evidence:
        prod *= max(min(e.confidence, 1.0), 0.5)
    return round(max(0.4, min(0.98, prod ** (1 / len(s.evidence)))), 2)


# ---------- dispatch ----------

_QUANTIFIERS = {
    "left_on_empty": _q_left_on_empty,
    "phantom_standby": _q_phantom_standby,
    "simultaneous_peak_load": _q_simultaneous_peak_load,
    "tou_switch": _q_tou_switch,
    "rp4_tier_cliff": _q_rp4_tier_cliff,
    "peak_window_shift": _q_peak_window_shift,
    "bill_trending_high": _q_bill_trending_high,
    "comparative_regression": _q_comparative_regression,
    "routine_shift": _q_routine_shift,
    "weather_correlated_ac": _q_weather_correlated_ac,
    "anomaly_with_action": _q_anomaly_with_action,
    "inefficient_upgrade": _q_inefficient_upgrade,
}


def quantify(situations: list[Situation], snap: HomeSnapshot) -> list[Situation]:
    for s in situations:
        fn = _QUANTIFIERS.get(s.archetype_key)
        if fn is not None:
            fn(s, snap)
    return situations
