"""
Routine-aware insight engine for the WattsEye prototype.

This is intentionally explainable rather than a deep learning model. NILM detects
the appliance; this layer compares that detected event with household routine
history and produces structured facts for the dashboard or an LLM wording layer.
"""

from __future__ import annotations

import argparse
import csv
import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from statistics import mean


HISTORY_PATH = Path(__file__).resolve().parent / "demo_history.csv"
HIGH_POWER_WATTS = 700.0
EMPTY_ROOM_MINUTES = 10.0


@dataclass(frozen=True)
class RoutineEvent:
    timestamp: datetime
    appliance: str
    power_watts: float
    duration_minutes: float
    occupied: bool
    cost_rm: float = 0.0


def parse_bool(value: str | bool) -> bool:
    if isinstance(value, bool):
        return value
    normalized = value.strip().lower()
    if normalized in {"true", "1", "yes", "y", "occupied"}:
        return True
    if normalized in {"false", "0", "no", "n", "empty"}:
        return False
    raise ValueError(f"Cannot parse boolean value: {value!r}")


def parse_timestamp(value: str) -> datetime:
    for fmt in ("%Y-%m-%d %H:%M", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%dT%H:%M"):
        try:
            return datetime.strptime(value, fmt)
        except ValueError:
            pass
    raise ValueError("Timestamp must look like '2026-05-20 07:10'")


def load_history(path: Path) -> list[RoutineEvent]:
    events: list[RoutineEvent] = []
    with path.open("r", newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            events.append(
                RoutineEvent(
                    timestamp=parse_timestamp(row["timestamp"]),
                    appliance=row["appliance"].strip().lower(),
                    power_watts=float(row["power_watts"]),
                    duration_minutes=float(row["duration_minutes"]),
                    occupied=parse_bool(row["occupied"]),
                    cost_rm=float(row.get("cost_rm") or 0.0),
                )
            )
    return events


def circular_hour_distance(a: int, b: int) -> int:
    diff = abs(a - b)
    return min(diff, 24 - diff)


def appliance_history(history: list[RoutineEvent], appliance: str) -> list[RoutineEvent]:
    return [event for event in history if event.appliance == appliance]


def baseline_for(events: list[RoutineEvent]) -> dict[str, object]:
    if not events:
        return {
            "sample_count": 0,
            "usual_hours": [],
            "avg_power_watts": None,
            "avg_duration_minutes": None,
            "usually_occupied": None,
        }

    occupied_count = sum(1 for event in events if event.occupied)
    return {
        "sample_count": len(events),
        "usual_hours": sorted({event.timestamp.hour for event in events}),
        "avg_power_watts": round(mean(event.power_watts for event in events), 2),
        "avg_duration_minutes": round(mean(event.duration_minutes for event in events), 2),
        "usually_occupied": occupied_count >= (len(events) / 2),
    }


def score_event(event: RoutineEvent, history: list[RoutineEvent]) -> dict[str, object]:
    matched = appliance_history(history, event.appliance)
    baseline = baseline_for(matched)
    reasons: list[str] = []
    recommendations: list[str] = []
    severity_points = 0

    usual_hours = baseline["usual_hours"]
    if usual_hours:
        nearest_hour_gap = min(circular_hour_distance(event.timestamp.hour, hour) for hour in usual_hours)
        if nearest_hour_gap >= 3:
            severity_points += 2
            reasons.append(
                f"{event.appliance} is active at {event.timestamp.strftime('%H:%M')}, "
                f"outside the usual hours {usual_hours}."
            )
        elif nearest_hour_gap >= 2:
            severity_points += 1
            reasons.append(f"{event.appliance} usage is slightly outside the normal time window.")
    else:
        severity_points += 1
        reasons.append(f"No routine history exists yet for {event.appliance}.")

    avg_duration = baseline["avg_duration_minutes"]
    if isinstance(avg_duration, float) and avg_duration > 0:
        if event.duration_minutes > avg_duration * 1.8 and event.duration_minutes - avg_duration >= 10:
            severity_points += 2
            reasons.append(
                f"Duration is {event.duration_minutes:.0f} minutes, higher than the usual "
                f"{avg_duration:.0f} minutes."
            )

    avg_power = baseline["avg_power_watts"]
    if isinstance(avg_power, float) and avg_power > 0:
        if event.power_watts > avg_power * 1.35 and event.power_watts - avg_power >= 150:
            severity_points += 1
            reasons.append(
                f"Power is {event.power_watts:.0f}W, above the usual {avg_power:.0f}W for this appliance."
            )

    if not event.occupied and event.power_watts >= HIGH_POWER_WATTS and event.duration_minutes >= EMPTY_ROOM_MINUTES:
        severity_points += 3
        reasons.append("High power usage is active while the room is empty.")
        recommendations.append("Turn it off or enable auto-off control if nobody is using the room.")

    if event.appliance == "standby" and event.power_watts >= 120 and event.duration_minutes >= 180:
        severity_points += 2
        reasons.append("Standby load is high for several hours.")
        recommendations.append("Check always-on devices, chargers, and idle appliances.")

    if event.appliance == "fridge" and isinstance(avg_duration, float):
        if event.duration_minutes > avg_duration * 1.6:
            severity_points += 1
            reasons.append("Fridge cycle duration is longer than the seeded baseline.")
            recommendations.append("Check door seal, ventilation, or recent door-open time.")

    if not reasons:
        reasons.append(f"{event.appliance} usage matches the seeded household routine.")

    if not recommendations:
        if severity_points >= 2:
            recommendations.append("Review this event and confirm whether it should become part of the normal routine.")
        else:
            recommendations.append("Keep monitoring this routine change.")

    if severity_points >= 4:
        status = "unusual"
        priority = "high"
        title = "High-priority routine alert"
    elif severity_points >= 2:
        status = "unusual"
        priority = "medium"
        title = "Unusual routine detected"
    elif severity_points == 1:
        status = "watch"
        priority = "low"
        title = "Slight routine change"
    else:
        status = "normal"
        priority = "low"
        title = "Normal routine"

    return {
        "status": status,
        "priority": priority,
        "title": title,
        "appliance": event.appliance,
        "timestamp": event.timestamp.isoformat(timespec="minutes"),
        "power_watts": event.power_watts,
        "duration_minutes": event.duration_minutes,
        "occupied": event.occupied,
        "baseline": baseline,
        "reasons": reasons,
        "recommendation": recommendations[0],
        "llm_context": {
            "instruction": "Rewrite the structured insight as one short user-facing energy coach message.",
            "facts": reasons,
            "recommended_action": recommendations[0],
        },
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate a routine-aware WattsEye insight.")
    parser.add_argument("--history", type=Path, default=HISTORY_PATH)
    parser.add_argument("--timestamp", required=True, help="Example: '2026-05-20 07:10'")
    parser.add_argument("--appliance", required=True)
    parser.add_argument("--power-watts", type=float, required=True)
    parser.add_argument("--duration-minutes", type=float, required=True)
    parser.add_argument("--occupied", required=True, help="true/false")
    parser.add_argument("--cost-rm", type=float, default=0.0)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    history = load_history(args.history)
    event = RoutineEvent(
        timestamp=parse_timestamp(args.timestamp),
        appliance=args.appliance.strip().lower(),
        power_watts=args.power_watts,
        duration_minutes=args.duration_minutes,
        occupied=parse_bool(args.occupied),
        cost_rm=args.cost_rm,
    )
    print(json.dumps(score_event(event, history), indent=2))


if __name__ == "__main__":
    main()
