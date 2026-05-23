"""Weekly digest — single summary card sent on Sundays (or on-demand).

Architecturally a 13th archetype but lives separately because:
- It rolls up 7 days of state instead of detecting one situation
- It always fires (no correlator gate)
- It goes to WhatsApp + Coach tab as a stand-alone artifact

Same pipeline shape: Situation-ish input → quantifier → template → WhatsApp.
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from .situations import Card, HomeSnapshot

ACTION_LOG_PATH = Path(__file__).resolve().parent / "_user_actions.json"


def _load_user_actions() -> list[dict[str, Any]]:
    if not ACTION_LOG_PATH.exists():
        return []
    try:
        return json.loads(ACTION_LOG_PATH.read_text())
    except (OSError, json.JSONDecodeError):
        return []


def _actions_this_week(now: datetime) -> dict[str, int]:
    since = now - timedelta(days=7)
    counts = {"accept": 0, "dismiss": 0, "snooze": 0, "question": 0}
    for a in _load_user_actions():
        try:
            ts = datetime.fromisoformat(a["timestamp"])
        except (KeyError, ValueError):
            continue
        if ts >= since and a.get("intent") in counts:
            counts[a["intent"]] += 1
    return counts


def generate_weekly_digest(snap: HomeSnapshot, *, now: datetime | None = None,
                           assumed_saved_rm: float = 0.0) -> Card:
    """Return a Card that summarises the last 7 days of WattsEye activity.

    The Coach tab can render it as a special "weekly" card; WhatsApp can push
    it via push_eligible_cards() if you add 'weekly_digest' to PUSH_ARCHETYPES
    (we leave it out by default so it's a manual trigger).
    """
    now = now or snap.timestamp
    # Use %d (zero-padded) for cross-platform — Windows lacks %-d
    week_label = (now - timedelta(days=6)).strftime("%b %d") + " - " + now.strftime("%b %d")

    # Real numbers from the snapshot
    week_kwh = snap.last_3mo_avg_kwh * 7 / 30
    week_rm_est = round(week_kwh * 0.34, 2)  # rough TNB RP4 effective rate

    actions = _actions_this_week(now)
    accepted = actions["accept"]
    dismissed = actions["dismiss"]

    headline = f"WattsEye weekly summary, week of {week_label}"
    impact = (
        f"You used about {week_kwh:.0f} kWh this week (~RM {week_rm_est:.0f}). "
        f"You actioned {accepted} recommendation(s), saving an estimated "
        f"RM {assumed_saved_rm:.2f}. {dismissed} dismissed; "
        f"{12 - accepted - dismissed} still active in Coach."
    )
    action = "Open the WattsEye app to view your full week of insights."

    why = [
        f"Aggregated from 7 days of NILM-disaggregated readings.",
        f"User feedback log: {accepted} accepted, {dismissed} dismissed, "
        f"{actions['snooze']} snoozed, {actions['question']} questions.",
        f"Cost projection based on TNB RP4 marginal rate at your usage band.",
    ]
    math = [
        f"week_kwh = last_3mo_avg_kwh × 7/30 = {snap.last_3mo_avg_kwh:.0f} × 7/30 = {week_kwh:.1f}",
        f"week_rm ≈ {week_kwh:.1f} × RM 0.34 effective ≈ RM {week_rm_est:.2f}",
    ]

    return Card(
        archetype_id=13,
        archetype_key="weekly_digest",
        family="forecast",
        severity="low",
        appliance=None,
        timestamp=now,
        headline=headline,
        impact_text=impact,
        action_text=action,
        saving_text=f"Saved this week: RM {assumed_saved_rm:.2f}",
        effort_text="—",
        confidence_label="High confidence",
        why_lines=why,
        math_lines=math,
        impact_rm_monthly=0.0,
        confidence=0.95,
        score=999.0,            # always surfaces first if pushed
        rank=0,
        surfaced=True,
    )
