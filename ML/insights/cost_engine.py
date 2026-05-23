from __future__ import annotations

try:
    from .models import ApplianceEvent, EngineResult
    from .tnb_tariff import (
        CURRENT_AFA_SEN_PER_KWH,
        calculate_standard_bill,
        marginal_cost_rm,
    )
except ImportError:
    from models import ApplianceEvent, EngineResult
    from tnb_tariff import (
        CURRENT_AFA_SEN_PER_KWH,
        calculate_standard_bill,
        marginal_cost_rm,
    )


# Default projected monthly usage for a typical Malaysian household. The
# effective sen/kWh varies by band, so we anchor cost estimates to this
# projection. Override per-call once we know the user's actual usage.
DEFAULT_PROJECTED_MONTHLY_KWH = 350.0


def effective_tariff_rm_per_kwh(
    projected_monthly_kwh: float = DEFAULT_PROJECTED_MONTHLY_KWH,
    afa_sen_per_kwh: float = CURRENT_AFA_SEN_PER_KWH,
) -> float:
    """Return the effective sen/kWh converted to RM/kWh at the given monthly band."""
    bill = calculate_standard_bill(projected_monthly_kwh, afa_sen_per_kwh)
    return bill.effective_sen_per_kwh / 100.0


def estimate_event_cost(
    event: ApplianceEvent,
    projected_monthly_kwh: float = DEFAULT_PROJECTED_MONTHLY_KWH,
    afa_sen_per_kwh: float = CURRENT_AFA_SEN_PER_KWH,
) -> float:
    """Cost of one appliance event in RM, using TNB RP4 marginal pricing."""
    return round(
        marginal_cost_rm(
            event_kwh=event.energy_kwh,
            current_monthly_kwh=projected_monthly_kwh,
            tariff="standard",
            afa_sen_per_kwh=afa_sen_per_kwh,
        ),
        2,
    )


def estimate_monthly_repeat_cost(
    event: ApplianceEvent,
    projected_monthly_kwh: float = DEFAULT_PROJECTED_MONTHLY_KWH,
    afa_sen_per_kwh: float = CURRENT_AFA_SEN_PER_KWH,
    repeat_days: int = 30,
) -> float:
    return round(
        estimate_event_cost(event, projected_monthly_kwh, afa_sen_per_kwh) * repeat_days,
        2,
    )


def analyze_cost(
    event: ApplianceEvent,
    projected_monthly_kwh: float = DEFAULT_PROJECTED_MONTHLY_KWH,
    afa_sen_per_kwh: float = CURRENT_AFA_SEN_PER_KWH,
    repeat_days: int = 30,
) -> EngineResult:
    event_cost = estimate_event_cost(event, projected_monthly_kwh, afa_sen_per_kwh)
    monthly_cost = estimate_monthly_repeat_cost(
        event, projected_monthly_kwh, afa_sen_per_kwh, repeat_days
    )
    effective_rm_kwh = effective_tariff_rm_per_kwh(projected_monthly_kwh, afa_sen_per_kwh)

    if monthly_cost >= 15:
        priority = "high"
        status = "costly"
    elif monthly_cost >= 5:
        priority = "medium"
        status = "watch"
    else:
        priority = "low"
        status = "normal"

    reasons = [
        f"This event costs about RM{event_cost:.2f}.",
        f"If repeated daily, it is about RM{monthly_cost:.2f}/month.",
        f"Priced against TNB RP4 standard tariff at {effective_rm_kwh * 100:.2f} sen/kWh "
        f"(home projected at {projected_monthly_kwh:.0f} kWh/month).",
    ]

    return EngineResult(
        engine="cost",
        status=status,
        priority=priority,
        reasons=reasons,
        metrics={
            "event_cost_rm": event_cost,
            "monthly_repeat_cost_rm": monthly_cost,
            "effective_rm_per_kwh": round(effective_rm_kwh, 4),
            "projected_monthly_kwh": projected_monthly_kwh,
            "afa_sen_per_kwh": afa_sen_per_kwh,
            "tariff_schedule": "TNB RP4 Domestic (1 July 2025 - 31 December 2027)",
        },
    )
