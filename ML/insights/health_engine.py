from __future__ import annotations

try:
    from .models import ApplianceEvent, EngineResult
except ImportError:
    from models import ApplianceEvent, EngineResult


HEALTH_APPLIANCES = {"fridge", "washing_machine", "ac"}


def analyze_health(event: ApplianceEvent, baseline: dict[str, object] | None = None) -> EngineResult:
    baseline = baseline or {}
    avg_duration = baseline.get("avg_duration_minutes")
    avg_power = baseline.get("avg_power_watts")
    reasons: list[str] = []
    health_score = 100

    if event.appliance not in HEALTH_APPLIANCES:
        return EngineResult(
            engine="health",
            status="not_applicable",
            priority="low",
            reasons=[f"No health rule is configured for {event.appliance}."],
            metrics={"health_score": None},
        )

    if isinstance(avg_duration, (int, float)) and avg_duration > 0:
        if event.duration_minutes > avg_duration * 1.6:
            health_score -= 20
            reasons.append(
                f"Runtime is {event.duration_minutes:.0f} minutes, longer than the usual "
                f"{avg_duration:.0f} minutes."
            )

    if isinstance(avg_power, (int, float)) and avg_power > 0:
        if event.power_watts > avg_power * 1.35 and event.power_watts - avg_power >= 150:
            health_score -= 15
            reasons.append(
                f"Power is {event.power_watts:.0f}W, above the usual {avg_power:.0f}W."
            )

    health_score = max(0, health_score)
    if health_score <= 70:
        status = "health_warning"
        priority = "medium"
    elif health_score < 100:
        status = "watch"
        priority = "low"
    else:
        status = "normal"
        priority = "low"
        reasons.append(f"{event.appliance} behavior is within the seeded health baseline.")

    return EngineResult(
        engine="health",
        status=status,
        priority=priority,
        reasons=reasons,
        metrics={"health_score": health_score},
    )
