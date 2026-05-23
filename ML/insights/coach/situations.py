"""Data classes shared by all five Coach layers.

A HomeSnapshot is the input every layer reads.
A Situation is what the correlator emits.
The quantifier mutates Situation with RM impact and confidence.
The template layer produces a Card from a Situation.
The ranker assigns score and surfaced flag to Cards.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Literal

Family = Literal["waste", "tariff", "forecast", "context", "capital"]
Severity = Literal["low", "medium", "high"]
Effort = Literal["low", "medium", "high"]


@dataclass(frozen=True)
class Evidence:
    """One piece of supporting detection — used in the 'Why this appeared' expandable."""

    source: str                # e.g. "NILM", "Occupancy", "Routine baseline", "K-Means"
    detail: str                # human-readable line
    confidence: float = 1.0    # 0-1, used when joining for joint confidence


@dataclass
class Situation:
    """Output of the correlator. One named, evidence-backed claim."""

    archetype_id: int                       # 1..12
    archetype_key: str                      # snake_case identifier
    family: Family
    severity: Severity
    timestamp: datetime
    appliance: str | None                   # primary appliance, if any
    evidence: list[Evidence]
    raw_metrics: dict[str, Any]             # numbers the quantifier needs

    # Filled by the quantifier
    impact_rm_monthly: float = 0.0
    impact_rm_event: float = 0.0
    effort: Effort = "low"
    confidence: float = 0.0
    extra_quantified: dict[str, Any] = field(default_factory=dict)


@dataclass
class Card:
    """User-facing card. Output of the template layer + ranker."""

    archetype_id: int
    archetype_key: str
    family: Family
    severity: Severity
    appliance: str | None
    timestamp: datetime

    # From templates
    headline: str
    impact_text: str
    action_text: str
    saving_text: str
    effort_text: str
    confidence_label: str        # "High" / "Medium" / "Low"
    why_lines: list[str]         # rendered evidence lines
    math_lines: list[str]        # rendered quantification breakdown

    # Carried through
    impact_rm_monthly: float
    confidence: float

    # From ranker
    score: float = 0.0
    rank: int = 0
    surfaced: bool = False


@dataclass
class HomeSnapshot:
    """Single input the coach engine reads. Wraps all upstream signals.

    Caller (a route handler / streamlit demo / cron) is responsible for
    assembling this from NILM, occupancy, routine_engine, K-Means, weather,
    etc.  The coach layers never touch raw data directly.
    """

    timestamp: datetime
    city: str = "Kuala Lumpur"

    # Live state
    occupancy_state: Literal["home", "away", "asleep", "unknown"] = "home"
    occupancy_since: datetime | None = None
    live_power_w: float = 0.0
    standby_overnight_w: float = 0.0

    # NILM appliance state — appliance_name -> dict(watts, started_at, mean_watts)
    active_appliances: dict[str, dict[str, Any]] = field(default_factory=dict)

    # Recent events (last 24h) — list of dicts(appliance, start, end, peak_w, energy_kwh, phase)
    recent_events: list[dict[str, Any]] = field(default_factory=list)

    # Routine baseline learned by routine_engine — appliance -> {expected_on_hours: set,
    #   typical_start_minute: int, typical_kwh_per_day: float, observed_days: int}
    routine_baseline: dict[str, dict[str, Any]] = field(default_factory=dict)

    # K-Means phase information
    current_phase: str = "unknown"                  # morning/work/evening/sleep
    phase_drift_minutes: dict[str, int] = field(default_factory=dict)  # phase -> drift vs last month

    # Billing
    projected_monthly_kwh: float = 350.0
    last_month_kwh: float = 320.0
    last_3mo_avg_kwh: float = 310.0
    on_tou_tariff: bool = False
    afa_sen_per_kwh: float = 0.0
    day_of_month: int = 1                           # 1..28-31

    # Anomaly score for the most recent event (Isolation Forest)
    last_anomaly_score: float | None = None
    last_anomaly_event: dict[str, Any] | None = None

    # ToU mismatch precomputed: fraction of last-30-day kWh that fell in peak window
    peak_window_kwh_fraction: float = 0.5

    # Weather (today + 7-day forecast)
    today_temp_c: float | None = None
    today_max_temp_c: float | None = None
    hot_days_next_7: int = 0                        # count of forecast days > 33°C
    hot_day_ac_uplift_pct: float = 0.0              # learned correlation, 0-1+

    # Capital-upgrade candidates (steady-state inefficient loads)
    inefficient_continuous_loads: list[dict[str, Any]] = field(default_factory=list)
    # Each: {appliance, current_w, efficient_class_w, replacement_rm, registry_url}

    # User-feedback state for ranker
    dismissed_archetypes: dict[str, datetime] = field(default_factory=dict)
    # archetype_key -> last dismissed timestamp
    recently_shown: dict[str, datetime] = field(default_factory=dict)
    # archetype_key -> last shown timestamp
