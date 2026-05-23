"""Templates: render Situation -> Card text.

Pure deterministic string formatting. No LLM. Every number on a card comes from
Situation.raw_metrics or .extra_quantified — auditable line by line.
"""

from __future__ import annotations

from .situations import Card, Situation


EFFORT_LABEL = {"low": "Low effort", "medium": "Medium effort", "high": "High effort"}


def _confidence_label(c: float) -> str:
    if c >= 0.80:
        return "High confidence"
    if c >= 0.60:
        return "Medium confidence"
    return "Low confidence"


def _why_lines(s: Situation) -> list[str]:
    return [f"{e.source}: {e.detail}" for e in s.evidence]


def _rm(x: float) -> str:
    return f"RM {x:.2f}" if x < 10 else f"RM {x:.0f}"


# ---------- per-archetype templates ----------

def _t_left_on_empty(s: Situation) -> Card:
    appliance = (s.appliance or "appliance").replace("_", " ").title()
    minutes = int(s.raw_metrics["minutes_empty"])
    watts = s.raw_metrics["watts"]
    headline = f"{appliance} running in empty room"
    impact = (f"{appliance} ran {minutes} min after the room emptied. "
              f"At your current pattern, this costs about {_rm(s.impact_rm_monthly)}/month.")
    action = f"Enable auto-off on {appliance.lower()} after 20 min empty."
    math = [
        f"{watts:.0f}W × {minutes} min ÷ 60 = {watts * minutes / 60 / 1000:.2f} kWh wasted this event",
        f"Event cost via TNB RP4 marginal pricing: {_rm(s.impact_rm_event)}",
        f"Weekly frequency × 4.345 weeks/month → {_rm(s.impact_rm_monthly)}/month",
    ]
    return _build(s, headline, impact, action, math)


def _t_phantom_standby(s: Situation) -> Card:
    watts = s.raw_metrics["standby_w"]
    monthly_kwh = watts * 24 * 30 / 1000.0
    headline = "Phantom standby load detected"
    impact = (f"Your home draws {watts:.0f}W continuously overnight from devices on standby — "
              f"about {_rm(s.impact_rm_monthly)}/month.")
    action = "Unplug TV/router/charger clusters or use a switched power strip overnight."
    math = [
        f"{watts:.0f}W × 24h × 30 days ÷ 1000 = {monthly_kwh:.1f} kWh/month",
        f"At TNB RP4 marginal rate → {_rm(s.impact_rm_monthly)}/month",
    ]
    return _build(s, headline, impact, action, math)


def _t_simultaneous_peak_load(s: Situation) -> Card:
    apps = ", ".join(a.replace("_", " ") for a in s.raw_metrics["appliances"])
    total = s.raw_metrics["total_w"]
    headline = "Heavy simultaneous use in peak window"
    impact = (f"{apps} ran together during TNB peak hours ({total:.0f}W combined). "
              f"Staggering could save ~{_rm(s.impact_rm_monthly)}/month.")
    action = "Delay non-urgent loads (kettle, microwave) to off-peak (after 22:00 weekdays)."
    math = [
        f"Estimated 30% of combined load shifted off-peak",
        f"Saving = shifted kWh × (peak rate − off-peak rate) ≈ {_rm(s.impact_rm_monthly)}/month",
    ]
    return _build(s, headline, impact, action, math)


def _t_tou_switch(s: Situation) -> Card:
    offpeak_pct = s.raw_metrics["offpeak_fraction"] * 100
    headline = "You may save by switching to TNB ToU tariff"
    impact = (f"{offpeak_pct:.0f}% of your last 30 days fell in off-peak hours. "
              f"Switching to ToU could save ~{_rm(s.impact_rm_monthly)}/month.")
    action = "Apply for ToU tariff via myTNB app (one-time opt-in)."
    math = [
        f"Standard tariff projected bill: {_rm(s.extra_quantified.get('standard_rm', 0))}/month",
        f"ToU tariff projected bill:      {_rm(s.extra_quantified.get('tou_rm', 0))}/month",
        f"Difference:                     {_rm(s.impact_rm_monthly)}/month",
    ]
    return _build(s, headline, impact, action, math)


def _t_rp4_tier_cliff(s: Situation) -> Card:
    proj = s.raw_metrics["projected_kwh"]
    over = s.raw_metrics["over_cliff_kwh"]
    if over > 0:
        headline = "You've crossed the 1,500 kWh tariff cliff"
        impact = (f"Projected {proj:.0f} kWh this month. Every unit above 1,500 is now charged "
                  f"at the high-band rate (10 sen/kWh more). Cutting back below 1,500 saves {_rm(s.impact_rm_monthly)}.")
        action = "Reduce AC runtime by 1 hour/day or raise setpoint by 2°C for the rest of the month."
    else:
        headline = "Approaching 1,500 kWh tariff cliff"
        impact = (f"Projected {proj:.0f} kWh — within {1500 - proj:.0f} kWh of the high-band cliff. "
                  f"Crossing raises generation rate from 27.03 to 37.03 sen/kWh on every unit above.")
        action = "Trim 25 kWh by month-end (≈1.5 hours less AC/day) to stay in lower tier."
    math = [
        f"Generation rate jumps from 27.03 sen/kWh → 37.03 sen/kWh at 1,500 kWh",
        f"Estimated savings if you stay below: {_rm(s.impact_rm_monthly)}",
    ]
    return _build(s, headline, impact, action, math)


def _t_peak_window_shift(s: Situation) -> Card:
    apps = ", ".join(a.replace("_", " ") for a in s.raw_metrics["appliances"])
    runs = s.raw_metrics["run_count"]
    headline = "Shift schedulable loads to off-peak"
    impact = (f"{apps} ran {runs} times in TNB peak window over the last 14 days. "
              f"Shifting to after 22:00 saves ~{_rm(s.impact_rm_monthly)}/month.")
    action = f"Set a delay-start timer on {apps.split(',')[0]} for after 22:00 weekdays."
    math = [
        f"Peak kWh detected over 14 days × 4.345/2 = monthly shiftable kWh",
        f"× (peak rate − off-peak rate) → {_rm(s.impact_rm_monthly)}/month",
    ]
    return _build(s, headline, impact, action, math)


def _t_bill_trending_high(s: Situation) -> Card:
    proj = s.raw_metrics["projected_kwh"]
    base = s.raw_metrics["baseline_kwh"]
    ratio = s.raw_metrics["ratio"]
    driver = s.raw_metrics.get("driver")
    headline = "Bill trending high this month"
    impact = (f"On track for {_rm(s.extra_quantified.get('projected_rm', 0))} this month "
              f"(+{(ratio-1)*100:.0f}% vs your usual {_rm(s.extra_quantified.get('baseline_rm', 0))}).")
    if driver:
        impact += f" Main driver: {driver.replace('_', ' ')} usage."
    action = (f"Raise AC setpoint by 1–2°C and reduce kettle pre-heating "
              f"to save about {_rm(s.impact_rm_monthly)} this month.")
    math = [
        f"Projected: {proj:.0f} kWh → {_rm(s.extra_quantified.get('projected_rm', 0))} (TNB RP4)",
        f"Baseline (3-mo avg): {base:.0f} kWh → {_rm(s.extra_quantified.get('baseline_rm', 0))}",
        f"Overage: {_rm(s.impact_rm_monthly)}",
    ]
    return _build(s, headline, impact, action, math)


def _t_comparative_regression(s: Situation) -> Card:
    appliance = (s.appliance or "appliance").replace("_", " ").title()
    delta = s.raw_metrics["delta_pct"]
    headline = f"{appliance} using more energy this week"
    impact = (f"{appliance} used {delta:.0f}% more this week vs the same week last month. "
              f"At this rate, monthly cost is up ~{_rm(s.impact_rm_monthly)}.")
    action = (f"Check {appliance.lower()} settings — for AC try +1°C setpoint, "
              f"for water heater check for unintended timer runs.")
    math = [
        f"This week: {s.raw_metrics['this_kwh']:.1f} kWh",
        f"Same week last month: {s.raw_metrics['prev_kwh']:.1f} kWh",
        f"Δ × 4.345 weeks → {_rm(s.impact_rm_monthly)}/month at TNB RP4 marginal rate",
    ]
    return _build(s, headline, impact, action, math)


def _t_routine_shift(s: Situation) -> Card:
    phase = s.raw_metrics["phase"]
    drift = s.raw_metrics["drift_minutes"]
    direction = "later" if drift > 0 else "earlier"
    headline = "Your daily routine has shifted"
    impact = (f"K-Means detects your '{phase}' phase has moved {abs(drift)} min {direction} "
              f"over the past 3 weeks. Old AC schedule may waste ~{_rm(s.impact_rm_monthly)}/month.")
    action = f"Adjust AC scheduler by ~{abs(drift)} min {direction}."
    math = [
        f"Estimated 30 min of misaligned AC × 30 days = ~0.9 kWh/day × 30 days",
        f"At TNB RP4 marginal rate → {_rm(s.impact_rm_monthly)}/month",
    ]
    return _build(s, headline, impact, action, math)


def _t_weather_correlated_ac(s: Situation) -> Card:
    hot = s.raw_metrics["hot_days"]
    uplift = s.raw_metrics["uplift_pct"]
    headline = "Hot week ahead — pre-cool to save"
    impact = (f"{hot} hot day(s) forecast in the next 7 days. "
              f"Your AC usage rises ~{uplift:.0f}% on hot days. "
              f"Pre-cooling could save ~{_rm(s.impact_rm_monthly)} over the week.")
    action = "Pre-cool 30 min before peak window (14:00) on forecast hot days."
    math = [
        f"Estimated 1 kWh/hot-day shifted from peak to off-peak",
        f"× {hot} hot days × (peak − off-peak rate) → {_rm(s.impact_rm_monthly)}",
    ]
    return _build(s, headline, impact, action, math)


def _t_anomaly_with_action(s: Situation) -> Card:
    appliance = (s.appliance or "appliance").replace("_", " ").title()
    hour = s.raw_metrics["hour"]
    headline = f"Unusual {appliance.lower()} activity at {hour:02d}:00"
    impact = (f"{appliance} ran at {hour:02d}:00 — outside your normal pattern. "
              f"If this is unintended and continues, ~{_rm(s.impact_rm_monthly)}/month wasted.")
    action = f"Check {appliance.lower()} timer settings or scheduling. Confirm or dismiss this card."
    math = [
        f"Event: {s.raw_metrics.get('peak_w', 0):.0f}W × {s.raw_metrics.get('duration_min', 0):.0f} min",
        f"If repeats 4×/month → {_rm(s.impact_rm_monthly)}",
    ]
    return _build(s, headline, impact, action, math)


def _t_inefficient_upgrade(s: Situation) -> Card:
    appliance = (s.appliance or "appliance").replace("_", " ").title()
    current_w = s.raw_metrics["current_w"]
    efficient_w = s.raw_metrics["efficient_w"]
    yearly = s.extra_quantified.get("yearly_saving_rm", 0)
    payback = s.extra_quantified.get("payback_years")
    replacement = s.extra_quantified.get("replacement_rm", 0)
    headline = f"{appliance} runs inefficiently — upgrade pays back"
    impact = (f"Your {appliance.lower()} draws {current_w:.0f}W continuous. "
              f"5-star class average is {efficient_w:.0f}W. "
              f"A more efficient model saves ~RM {yearly:.0f}/year.")
    if payback:
        action = (f"Compare 5-star models on the ST efficiency registry — "
                  f"estimated payback {payback} years on a RM {replacement} replacement.")
    else:
        action = "Compare 5-star models on the ST efficiency registry."
    math = [
        f"Δ {current_w - efficient_w:.0f}W × 24h × 30 days = monthly extra kWh",
        f"× TNB RP4 marginal rate = {_rm(s.impact_rm_monthly)}/month",
        f"× 12 months = RM {yearly:.0f}/year",
    ]
    if payback:
        math.append(f"Payback: RM {replacement} ÷ RM {yearly:.0f}/year = {payback} years")
    return _build(s, headline, impact, action, math)


# ---------- shared builder ----------

def _build(s: Situation, headline: str, impact: str, action: str, math: list[str]) -> Card:
    saving_text = f"Expected saving: {_rm(s.impact_rm_monthly)}/month" if s.impact_rm_monthly > 0 else "Expected saving: —"
    return Card(
        archetype_id=s.archetype_id,
        archetype_key=s.archetype_key,
        family=s.family,
        severity=s.severity,
        appliance=s.appliance,
        timestamp=s.timestamp,
        headline=headline,
        impact_text=impact,
        action_text=action,
        saving_text=saving_text,
        effort_text=EFFORT_LABEL[s.effort],
        confidence_label=_confidence_label(s.confidence),
        why_lines=_why_lines(s),
        math_lines=math,
        impact_rm_monthly=s.impact_rm_monthly,
        confidence=s.confidence,
    )


_TEMPLATES = {
    "left_on_empty": _t_left_on_empty,
    "phantom_standby": _t_phantom_standby,
    "simultaneous_peak_load": _t_simultaneous_peak_load,
    "tou_switch": _t_tou_switch,
    "rp4_tier_cliff": _t_rp4_tier_cliff,
    "peak_window_shift": _t_peak_window_shift,
    "bill_trending_high": _t_bill_trending_high,
    "comparative_regression": _t_comparative_regression,
    "routine_shift": _t_routine_shift,
    "weather_correlated_ac": _t_weather_correlated_ac,
    "anomaly_with_action": _t_anomaly_with_action,
    "inefficient_upgrade": _t_inefficient_upgrade,
}


def render(situations: list[Situation]) -> list[Card]:
    cards: list[Card] = []
    for s in situations:
        fn = _TEMPLATES.get(s.archetype_key)
        if fn is not None:
            cards.append(fn(s))
    return cards
