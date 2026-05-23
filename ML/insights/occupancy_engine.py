from __future__ import annotations

try:
    from .models import ApplianceEvent, EngineResult
except ImportError:
    from models import ApplianceEvent, EngineResult


HIGH_POWER_WATTS = 700.0
EMPTY_ROOM_MINUTES = 10.0


def analyze_occupancy(event: ApplianceEvent) -> EngineResult:
    reasons: list[str] = []
    metrics = {
        "occupied": event.occupied,
        "empty_room_minutes": 0 if event.occupied else event.duration_minutes,
        "high_power_threshold_watts": HIGH_POWER_WATTS,
    }

    if not event.occupied and event.power_watts >= HIGH_POWER_WATTS and event.duration_minutes >= EMPTY_ROOM_MINUTES:
        reasons.append(
            f"{event.appliance} is using {event.power_watts:.0f}W while the room appears empty "
            f"for {event.duration_minutes:.0f} minutes."
        )
        return EngineResult(
            engine="occupancy",
            status="empty_room_waste",
            priority="high",
            reasons=reasons,
            metrics=metrics,
        )

    if not event.occupied and event.power_watts >= HIGH_POWER_WATTS:
        reasons.append(f"{event.appliance} is high power, but the empty-room duration is still short.")
        return EngineResult(
            engine="occupancy",
            status="watch",
            priority="medium",
            reasons=reasons,
            metrics=metrics,
        )

    reasons.append("No empty-room waste condition detected.")
    return EngineResult(
        engine="occupancy",
        status="normal",
        priority="low",
        reasons=reasons,
        metrics=metrics,
    )
