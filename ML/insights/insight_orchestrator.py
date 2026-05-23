from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path

try:
    from .cost_engine import analyze_cost
    from .health_engine import analyze_health
    from .models import ApplianceEvent, EngineResult, priority_rank
    from .occupancy_engine import analyze_occupancy
except ImportError:  # Allows direct script execution: python ML/insights/insight_orchestrator.py
    from cost_engine import analyze_cost
    from health_engine import analyze_health
    from models import ApplianceEvent, EngineResult, priority_rank
    from occupancy_engine import analyze_occupancy

# Optional ML engine wrappers — gracefully no-op if model files are missing.
import sys
_ML_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_ML_ROOT))

try:
    from anomaly.isolation_forest import anomaly_score as _if_score
except Exception:
    _if_score = None

try:
    from anomaly.appliance_health_regression import health_check as _fridge_health
except Exception:
    _fridge_health = None

try:
    from routine.kmeans_phases import classify as _classify_phase
except Exception:
    _classify_phase = None

try:
    from signatures.signature_library import match_event as _match_signature
    from signatures.signature_library import EventFeatures as _SigEvent
except Exception:
    _match_signature = None
    _SigEvent = None


def analyze_anomaly(event: ApplianceEvent) -> EngineResult:
    if _if_score is None:
        return EngineResult(
            engine="anomaly", status="unavailable", priority="low",
            reasons=[], metrics={"reason": "isolation_forest.joblib not loaded"},
        )
    try:
        result = _if_score(
            appliance=event.appliance,
            peak_w=event.power_watts,
            duration_min=event.duration_minutes,
            hour_of_day=event.timestamp.hour,
            day_of_week=event.timestamp.weekday(),
        )
    except ValueError:
        return EngineResult(
            engine="anomaly", status="not_applicable", priority="low",
            reasons=[], metrics={"reason": f"no IF model for {event.appliance}"},
        )
    is_anom = result["is_anomaly"]
    return EngineResult(
        engine="anomaly",
        status="anomalous" if is_anom else "normal",
        priority="high" if is_anom else "low",
        reasons=[
            f"{event.appliance} event signature is {'unusual' if is_anom else 'consistent'} "
            f"compared with learned baseline (IF score {result['score']:.2f})."
        ] if is_anom else [],
        metrics=result,
    )


def analyze_fridge_drift(event: ApplianceEvent, fridge_duty_cycle: float | None) -> EngineResult:
    if event.appliance != "fridge" or _fridge_health is None or fridge_duty_cycle is None:
        return EngineResult(
            engine="fridge_health", status="not_applicable", priority="low",
            reasons=[], metrics={},
        )
    result = _fridge_health(
        actual_duty_cycle=fridge_duty_cycle,
        hour=event.timestamp.hour,
        day_of_week=event.timestamp.weekday(),
        month=event.timestamp.month,
    )
    reasons = []
    if result["flagged"]:
        reasons.append(
            f"Fridge duty cycle is {result['drift_percent']:+.0f}% off the learned baseline "
            f"for this hour (z={result['z_score']:+.1f} sigma; "
            f"actual {result['actual']:.2f} vs expected {result['predicted']:.2f})."
        )
    return EngineResult(
        engine="fridge_health",
        status=result["status"],
        priority=result["priority"],
        reasons=reasons,
        metrics=result,
    )


def analyze_phase(event: ApplianceEvent) -> EngineResult:
    if _classify_phase is None:
        return EngineResult(
            engine="phase", status="unavailable", priority="low",
            reasons=[], metrics={},
        )
    try:
        result = _classify_phase(event.timestamp)
    except FileNotFoundError:
        return EngineResult(
            engine="phase", status="unavailable", priority="low",
            reasons=[], metrics={"reason": "kmeans_phases.joblib not trained"},
        )
    return EngineResult(
        engine="phase", status="learned", priority="low",
        reasons=[f"Current phase classified as '{result['phase']}'."],
        metrics=result,
    )


def analyze_signature(event: ApplianceEvent) -> EngineResult:
    if event.appliance != "unknown" or _match_signature is None or _SigEvent is None:
        return EngineResult(
            engine="signature", status="not_applicable", priority="low",
            reasons=[], metrics={},
        )
    ev = _SigEvent(
        peak_w=event.power_watts,
        mean_w=event.power_watts,
        duration_min=event.duration_minutes,
        hour_of_day=event.timestamp.hour,
        day_of_week=event.timestamp.weekday(),
    )
    result = _match_signature(ev)
    if result["matched"]:
        return EngineResult(
            engine="signature", status="matched", priority="low",
            reasons=[f"Matched user-labelled signature: {result['label']} "
                     f"(distance {result['distance']:.2f})."],
            metrics=result,
        )
    return EngineResult(
        engine="signature", status="needs_label", priority="medium",
        reasons=["Unlabelled load detected. Confirm the appliance to improve future tracking."],
        metrics=result,
    )


ROUTINE_DIR = Path(__file__).resolve().parents[1] / "routine"
DEFAULT_HISTORY = ROUTINE_DIR / "demo_history.csv"


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
    raise ValueError("Timestamp must look like '2026-05-20 14:20'")


def load_routine_result(event: ApplianceEvent, history_path: Path) -> EngineResult:
    import sys

    sys.path.insert(0, str(ROUTINE_DIR))
    from routine_engine import load_history, score_event
    from routine_engine import RoutineEvent as RoutineEngineEvent

    routine_event = RoutineEngineEvent(
        timestamp=event.timestamp,
        appliance=event.appliance,
        power_watts=event.power_watts,
        duration_minutes=event.duration_minutes,
        occupied=event.occupied,
    )
    result = score_event(routine_event, load_history(history_path))
    return EngineResult(
        engine="routine",
        status=str(result["status"]),
        priority=str(result["priority"]),
        reasons=list(result["reasons"]),
        metrics={"baseline": result["baseline"]},
    )


def choose_title(event: ApplianceEvent, results: list[EngineResult]) -> str:
    statuses = {result.status for result in results}
    if "empty_room_waste" in statuses:
        return f"{event.appliance.upper()} running in an empty room"
    if "health_warning" in statuses or any(result.engine == "health" and result.status == "watch" for result in results):
        return f"{event.appliance.replace('_', ' ').title()} health watch"
    if any(result.engine == "cost" and result.status == "costly" for result in results):
        return f"{event.appliance.replace('_', ' ').title()} cost is trending high"
    if any(result.engine == "routine" and result.status == "unusual" for result in results):
        return f"Unusual {event.appliance.replace('_', ' ')} routine"
    return f"{event.appliance.replace('_', ' ').title()} usage looks normal"


def choose_action(event: ApplianceEvent, results: list[EngineResult]) -> str:
    statuses = {result.status for result in results}
    if "empty_room_waste" in statuses:
        return "Turn it off or enable auto-off control if nobody is using the room."
    if "health_warning" in statuses or any(result.engine == "health" and result.status == "watch" for result in results):
        return "Check whether this pattern continues before treating it as a fault."
    if any(result.engine == "routine" and result.status in {"unusual", "watch"} for result in results):
        return "Mark as normal if this usage is intentional."
    return "No action needed."


def orchestrate_insight(
    event: ApplianceEvent,
    history_path: Path = DEFAULT_HISTORY,
    projected_monthly_kwh: float = 350.0,
    afa_sen_per_kwh: float = 0.0,
    fridge_duty_cycle: float | None = None,
) -> dict[str, object]:
    routine_result = load_routine_result(event, history_path)
    baseline = routine_result.metrics.get("baseline")
    results = [
        routine_result,
        analyze_cost(
            event,
            projected_monthly_kwh=projected_monthly_kwh,
            afa_sen_per_kwh=afa_sen_per_kwh,
        ),
        analyze_occupancy(event),
        analyze_health(event, baseline if isinstance(baseline, dict) else None),
        analyze_anomaly(event),
        analyze_fridge_drift(event, fridge_duty_cycle),
        analyze_phase(event),
        analyze_signature(event),
    ]

    highest_priority = max((result.priority for result in results), key=priority_rank)
    top_reasons: list[str] = []
    for result in sorted(results, key=lambda item: priority_rank(item.priority), reverse=True):
        for reason in result.reasons:
            if reason not in top_reasons and len(top_reasons) < 4:
                top_reasons.append(reason)

    cost_metrics = next(result.metrics for result in results if result.engine == "cost")
    return {
        "type": "energy_insight",
        "title": choose_title(event, results),
        "priority": highest_priority,
        "device": event.appliance,
        "source": event.source,
        "appliance_confidence_label": confidence_label(event.confidence),
        "timestamp": event.timestamp.isoformat(timespec="minutes"),
        "power_watts": event.power_watts,
        "duration_minutes": event.duration_minutes,
        "estimated_cost_rm": cost_metrics["event_cost_rm"],
        "monthly_projection_rm": cost_metrics["monthly_repeat_cost_rm"],
        "reasons": top_reasons,
        "recommended_action": choose_action(event, results),
        "engine_results": [
            {
                "engine": result.engine,
                "status": result.status,
                "priority": result.priority,
                "metrics": result.metrics,
            }
            for result in results
        ],
        "llm_context": {
            "instruction": "Write one short, non-accusatory energy-saving message for a mobile app.",
            "facts": top_reasons,
            "recommended_action": choose_action(event, results),
        },
    }


def confidence_label(confidence: float) -> str:
    if confidence >= 0.85:
        return "confirmed" if confidence >= 0.98 else "likely"
    if confidence >= 0.6:
        return "possible"
    return "unknown"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Combine WattsEye engines into one dashboard insight.")
    parser.add_argument("--history", type=Path, default=DEFAULT_HISTORY)
    parser.add_argument("--timestamp", required=True)
    parser.add_argument("--appliance", required=True)
    parser.add_argument("--power-watts", type=float, required=True)
    parser.add_argument("--duration-minutes", type=float, required=True)
    parser.add_argument("--occupied", required=True)
    parser.add_argument("--source", default="nilm")
    parser.add_argument("--confidence", type=float, default=0.7)
    parser.add_argument(
        "--projected-monthly-kwh",
        type=float,
        default=350.0,
        help="Projected monthly home usage; sets the TNB RP4 tariff band for pricing.",
    )
    parser.add_argument(
        "--afa-sen-per-kwh",
        type=float,
        default=0.0,
        help="Current TNB AFA surcharge/rebate. Update from tnb.com.my monthly.",
    )
    parser.add_argument(
        "--fridge-duty-cycle",
        type=float,
        default=None,
        help="Optional: fridge duty cycle this hour (0-1) for health regression.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    event = ApplianceEvent(
        timestamp=parse_timestamp(args.timestamp),
        appliance=args.appliance.strip().lower(),
        power_watts=args.power_watts,
        duration_minutes=args.duration_minutes,
        occupied=parse_bool(args.occupied),
        source=args.source,
        confidence=args.confidence,
    )
    print(
        json.dumps(
            orchestrate_insight(
                event,
                args.history,
                projected_monthly_kwh=args.projected_monthly_kwh,
                afa_sen_per_kwh=args.afa_sen_per_kwh,
                fridge_duty_cycle=args.fridge_duty_cycle,
            ),
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
