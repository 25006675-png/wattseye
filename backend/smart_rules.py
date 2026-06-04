"""Persisted AC smart rule + its evaluator.

One user-configurable rule sits on top of the two things WattsEye already does
for real: occupancy empty-room detection (ML/insights/occupancy_engine.py) and
the AC IR/relay cutoff (pi_bridge -> ESP32). The rule decides whether an
empty-room-while-AC-on episode should *remind* the user or *auto turn off* the
AC, and after how many empty minutes.

Shape (also the /api/ac/rule JSON contract):
    {"enabled": bool, "empty_minutes": float, "mode": "remind" | "auto_off"}

Stored at backend/_smart_rule.json. Degrades honestly: a missing/corrupt file
falls back to DEFAULT_RULE; an out-of-range value is clamped, not rejected
silently.
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from ML.insights.models import ApplianceEvent
from ML.insights.occupancy_engine import HIGH_POWER_WATTS, analyze_occupancy

RULE_PATH = Path(__file__).resolve().parent / "_smart_rule.json"

# The occupancy engine only calls an episode "waste" at >= EMPTY_ROOM_MINUTES
# (10 min), so the rule threshold can't meaningfully go below that.
MIN_EMPTY_MINUTES = 10.0
MAX_EMPTY_MINUTES = 60.0
MODES = ("remind", "auto_off")

# Default matches the slide: "If AC is running and room is empty for 15 minutes,
# then remind the user or auto-turn off if enabled."
DEFAULT_RULE: dict[str, Any] = {"enabled": True, "empty_minutes": 15.0, "mode": "auto_off"}


def _coerce(rule: dict[str, Any]) -> dict[str, Any]:
    """Merge over defaults, clamp/validate. Never raises on bad input."""
    out = dict(DEFAULT_RULE)
    out["enabled"] = bool(rule.get("enabled", out["enabled"]))
    try:
        minutes = float(rule.get("empty_minutes", out["empty_minutes"]))
    except (TypeError, ValueError):
        minutes = out["empty_minutes"]
    out["empty_minutes"] = max(MIN_EMPTY_MINUTES, min(MAX_EMPTY_MINUTES, minutes))
    mode = str(rule.get("mode", out["mode"]))
    out["mode"] = mode if mode in MODES else out["mode"]
    return out


def default_rule() -> dict[str, Any]:
    return dict(DEFAULT_RULE)


def load_rule() -> dict[str, Any]:
    try:
        return _coerce(json.loads(RULE_PATH.read_text("utf-8")))
    except (FileNotFoundError, ValueError, OSError):
        return default_rule()


def save_rule(rule: dict[str, Any]) -> dict[str, Any]:
    stored = _coerce(rule)
    RULE_PATH.write_text(json.dumps(stored, indent=2), "utf-8")
    return stored


def evaluate(ac_watts: float, empty_minutes: float, occupied: bool,
             rule: dict[str, Any] | None = None) -> dict[str, Any] | None:
    """Return a decision dict if the rule fires this tick, else None.

    Reuses analyze_occupancy for the waste definition (high power + empty), then
    applies the rule's own enabled flag and minute threshold on top. The caller
    (pi_bridge) acts on decision["action"]: "auto_off" publishes the cutoff,
    "remind" raises a reminder instead of touching the AC.
    """
    rule = _coerce(rule) if rule is not None else load_rule()
    if not rule["enabled"] or occupied:
        return None

    event = ApplianceEvent(
        timestamp=datetime.now(),
        appliance="inverter_ac",
        power_watts=ac_watts,
        duration_minutes=empty_minutes,
        occupied=occupied,
        source="live",
        confidence=0.99,
    )
    result = analyze_occupancy(event)
    if result.status != "empty_room_waste":
        return None
    if empty_minutes < rule["empty_minutes"]:
        return None

    return {
        "action": rule["mode"],            # "auto_off" | "remind"
        "reason": "empty_room_waste",
        "empty_minutes": round(empty_minutes, 1),
        "ac_watts": round(ac_watts, 1),
        "threshold_minutes": rule["empty_minutes"],
        "high_power_threshold_watts": HIGH_POWER_WATTS,
    }
