"""Top-level coach engine: HomeSnapshot -> ranked list[Card].

Pipeline:
  HomeSnapshot
    -> correlator.correlate()       (detection)
    -> quantifier.quantify()        (RM, confidence, effort)
    -> templates.render()           (card text)
    -> ranker.rank()                (score, surface flag)
    -> list[Card] sorted by score
"""

from __future__ import annotations

from dataclasses import asdict
from datetime import datetime
from typing import Any

from .correlator import correlate
from .quantifier import quantify
from .ranker import rank
from .situations import Card, HomeSnapshot
from .templates import render
from .weather import get_forecast_safe


def generate_cards(snap: HomeSnapshot, surface_count: int = 2,
                   include_weather: bool = True,
                   push_whatsapp: bool = False,
                   whatsapp_dry_run: bool = False) -> list[Card]:
    """Run the full pipeline. Returns scored cards sorted highest first.

    Args:
        snap: HomeSnapshot input
        surface_count: how many top cards get surfaced=True
        include_weather: if True and snap.today_temp_c is None, fetch via Open-Meteo
        push_whatsapp: if True, also push eligible surfaced cards via WhatsApp
                       (subset defined by whatsapp.PUSH_ARCHETYPES — see whatsapp.md §2)
        whatsapp_dry_run: if push_whatsapp=True, render but don't actually call Twilio
    """
    if include_weather and snap.today_temp_c is None:
        fc = get_forecast_safe(snap.city)
        if fc is not None:
            snap.today_temp_c = fc.current_temp_c
            snap.today_max_temp_c = fc.today_max_c
            snap.hot_days_next_7 = fc.hot_days_over_33c

    situations = correlate(snap)
    situations = quantify(situations, snap)
    cards = render(situations)
    cards = rank(cards, snap, surface_count=surface_count)

    if push_whatsapp:
        from .whatsapp import push_eligible_cards
        push_eligible_cards(cards, dry_run=whatsapp_dry_run)

    return cards


def card_to_dict(card: Card) -> dict[str, Any]:
    """JSON-serializable view of a Card for the frontend."""
    d = asdict(card)
    d["timestamp"] = card.timestamp.isoformat(timespec="minutes")
    return d


def cards_to_json(cards: list[Card]) -> list[dict[str, Any]]:
    return [card_to_dict(c) for c in cards]


# ---------- demo / smoke test ----------

def _demo_snapshot() -> HomeSnapshot:
    """A synthetic snapshot that triggers most archetypes — for the mock UI."""
    now = datetime(2026, 5, 22, 15, 30)
    return HomeSnapshot(
        timestamp=now,
        city="Kuala Lumpur",
        occupancy_state="away",
        occupancy_since=datetime(2026, 5, 22, 14, 19),  # 71 min empty
        live_power_w=1850.0,
        standby_overnight_w=48.0,
        active_appliances={
            "ac": {"watts": 1200.0, "started_at": datetime(2026, 5, 22, 14, 5)},
            "fridge": {"watts": 110.0, "started_at": datetime(2026, 5, 22, 0, 0)},
        },
        recent_events=[
            {"appliance": "ac", "start": datetime(2026, 5, 22, 14, 5), "end": now,
             "peak_w": 1200, "energy_kwh": 1.7, "phase": "work"},
            {"appliance": "kettle", "start": datetime(2026, 5, 22, 7, 12), "end": datetime(2026, 5, 22, 7, 16),
             "peak_w": 2050, "energy_kwh": 0.14, "phase": "morning"},
            {"appliance": "dishwasher", "start": datetime(2026, 5, 21, 19, 30), "end": datetime(2026, 5, 21, 20, 30),
             "peak_w": 1800, "energy_kwh": 1.4, "phase": "evening"},
            {"appliance": "dishwasher", "start": datetime(2026, 5, 19, 20, 5), "end": datetime(2026, 5, 19, 21, 0),
             "peak_w": 1800, "energy_kwh": 1.4, "phase": "evening"},
            {"appliance": "washer", "start": datetime(2026, 5, 18, 18, 30), "end": datetime(2026, 5, 18, 19, 30),
             "peak_w": 600, "energy_kwh": 0.6, "phase": "evening"},
            {"appliance": "washer", "start": datetime(2026, 5, 17, 19, 15), "end": datetime(2026, 5, 17, 20, 15),
             "peak_w": 600, "energy_kwh": 0.6, "phase": "evening"},
        ],
        routine_baseline={
            "ac": {"expected_on_hours": {19, 20, 21, 22, 23}, "observed_days": 14,
                   "empty_overlap_per_week": 4,
                   "this_week_kwh": 28.4, "same_week_last_month_kwh": 20.5},
            "fridge": {"expected_on_hours": set(range(24)), "observed_days": 14},
        },
        current_phase="work",
        phase_drift_minutes={"evening": 75},
        projected_monthly_kwh=1480.0,
        last_month_kwh=1200.0,
        last_3mo_avg_kwh=1180.0,
        on_tou_tariff=False,
        peak_window_kwh_fraction=0.32,
        last_anomaly_score=-0.42,
        last_anomaly_event={"appliance": "water_heater", "start": datetime(2026, 5, 22, 2, 14),
                            "duration_min": 35, "peak_w": 2400},
        hot_days_next_7=3,
        hot_day_ac_uplift_pct=45.0,
        inefficient_continuous_loads=[
            {"appliance": "fridge", "current_w": 180, "efficient_class_w": 90,
             "replacement_rm": 1800,
             "registry_url": "https://www.st.gov.my/en/energy-efficient-appliances"},
        ],
    )


if __name__ == "__main__":
    import json
    snap = _demo_snapshot()
    cards = generate_cards(snap, surface_count=2, include_weather=False)
    print(f"\n=== Generated {len(cards)} cards ===\n")
    for c in cards:
        flag = "** SURFACED" if c.surfaced else "  (secondary)"
        print(f"{flag}  #{c.archetype_id:2d} [{c.family:8s}] {c.headline}")
        print(f"            impact={c.impact_rm_monthly:>6.2f} RM/mo  conf={c.confidence:.2f}  "
              f"sev={c.severity:6s}  score={c.score}")
    print()
    if cards:
        print(json.dumps(card_to_dict(cards[0]), indent=2, default=str))
