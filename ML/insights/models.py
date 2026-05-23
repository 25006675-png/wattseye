from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class ApplianceEvent:
    timestamp: datetime
    appliance: str
    power_watts: float
    duration_minutes: float
    occupied: bool
    source: str = "nilm"
    confidence: float = 0.7

    @property
    def energy_kwh(self) -> float:
        return self.power_watts * (self.duration_minutes / 60.0) / 1000.0


@dataclass(frozen=True)
class EngineResult:
    engine: str
    status: str
    priority: str
    reasons: list[str]
    metrics: dict[str, object]


def priority_rank(priority: str) -> int:
    return {"low": 1, "medium": 2, "high": 3, "critical": 4}.get(priority, 0)
