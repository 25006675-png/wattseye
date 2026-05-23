"""TNB domestic electricity tariff model — RP4 (1 July 2025 – 31 December 2027).

WattsEye uses this module to convert kWh into RM in a way that matches a real
TNB bill, not a flat-rate estimate. It implements three things:

1. The standard Domestic Tariff (Tariff A) as restructured under Regulatory
   Period 4 (RP4) — component-based, with the Energy Efficiency Incentive
   (EEI) rebate, Automatic Fuel Adjustment (AFA), and the retail charge waiver.
2. The optional Time-of-Use (ToU) tariff — peak 2pm-10pm weekdays, off-peak
   otherwise.
3. A side-by-side comparison so the dashboard can tell the user whether
   switching to ToU would save them money given their actual usage pattern.

There is no public TNB tariff API. The schedule is hardcoded from TNB's
published RP4 documentation and verified against multiple secondary sources.
When TNB publishes a new AFA value (monthly) or a new RP, update the constants
at the top of this file.

Sources (verified 2026-05-20):
- TNB myTNB official tariff page:
    https://www.mytnb.com.my/tariff
- TNB press release: "TNB insulated as new electricity tariff kicks in from July":
    https://www.tnb.com.my/assets/newsclip/30062025a.pdf
- TNB new electricity schedule (PDF, June 2025):
    https://www.tnb.com.my/assets/newsclip/23062025a.pdf
- SEDA NEM calculator tariff reference (PDF):
    https://services.seda.gov.my/nemcalculator/tnb-tariff-rates.pdf
- Soyacincau, "TNB Electricity Bill changes starting July 2025" (2025-06-21):
    https://soyacincau.com/2025/06/21/tnb-domestic-electricity-tariff-structure-july-2025-impact-changes/
- paultan.org, "TNB new electricity tariff calculation from July 2025" (2025-06-21):
    https://paultan.org/2025/06/21/tnb-new-electricity-tariff-calculation-from-july-2025/
- SolarSunYield, "TNB Tariffs Decoded: 2026 Guide to Normal vs Time of Use Plans" (EEI rebate table):
    https://www.solarsunyield.com/latestnews/nid/169869/
- Sunview, "Homeowner's Guide to TNB's New Electricity Tariff (Effective 1 July 2025)":
    https://www.sunview.com.my/r/your-complete-homeowners-guide-to-tnbs-new-electricity-tariff-effective-1-july-2025
- Solaroo, "TNB's New Electricity Tariff (Effective 1 July 2025)":
    https://solaroo.com/tnbs-new-electricity-tariff-effective-1-july-2025/
- Soyacincau, "Off-peak electricity rates: How to apply for TNB ToU" (2025-07-05):
    https://soyacincau.com/2025/07/05/tnb-time-of-use-off-peak-electricity-tariff-scheme-how-to-apply/
- Malay Mail, "Is TNB's Time of Use plan right for you?" (2025-07-15):
    https://www.malaymail.com/news/malaysia/2025/07/15/is-tnbs-time-of-use-plan-right-for-you-it-depends-on-when-you-use-power/183461
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, time
from typing import Iterable, Literal


SEN_PER_RM = 100.0


@dataclass(frozen=True)
class ComponentRates:
    """All rates are in sen/kWh except retail_monthly_rm."""

    generation_low_band_sen: float
    generation_high_band_sen: float
    capacity_sen: float
    network_sen: float
    retail_monthly_rm: float


@dataclass(frozen=True)
class TariffSchedule:
    name: str
    effective_from: date
    effective_to: date
    standard: ComponentRates
    tou_offpeak: ComponentRates
    tou_peak: ComponentRates
    retail_waiver_threshold_kwh: int
    afa_waiver_threshold_kwh: int
    high_band_threshold_kwh: int


# --- RP4 schedule (1 July 2025 - 31 December 2027) ---------------------------

RP4 = TariffSchedule(
    name="RP4 Domestic",
    effective_from=date(2025, 7, 1),
    effective_to=date(2027, 12, 31),
    standard=ComponentRates(
        generation_low_band_sen=27.03,
        generation_high_band_sen=37.03,
        capacity_sen=4.55,
        network_sen=12.85,
        retail_monthly_rm=10.00,
    ),
    tou_offpeak=ComponentRates(
        generation_low_band_sen=24.43,
        generation_high_band_sen=34.43,
        capacity_sen=4.55,
        network_sen=12.85,
        retail_monthly_rm=10.00,
    ),
    tou_peak=ComponentRates(
        generation_low_band_sen=28.52,
        generation_high_band_sen=38.52,
        capacity_sen=4.55,
        network_sen=12.85,
        retail_monthly_rm=10.00,
    ),
    retail_waiver_threshold_kwh=600,
    afa_waiver_threshold_kwh=600,
    high_band_threshold_kwh=1500,
)


# Energy Efficiency Incentive rebate, sen/kWh, applied to the *whole* monthly
# usage if it lands in that band. Verified from TNB RP4 schedule.
EEI_REBATE_TABLE: list[tuple[int, int, float]] = [
    (1, 200, 25.00),
    (201, 250, 24.50),
    (251, 300, 22.50),
    (301, 350, 21.00),
    (351, 400, 17.00),
    (401, 450, 14.50),
    (451, 500, 12.00),
    (501, 550, 10.50),
    (551, 600, 9.00),
    (601, 650, 7.50),
    (651, 700, 5.50),
    (701, 750, 4.50),
    (751, 800, 4.00),
    (801, 850, 2.50),
    (851, 900, 1.00),
    (901, 1000, 0.50),
]


def eei_rebate_sen_per_kwh(monthly_kwh: float) -> float:
    """Return the EEI rebate in sen/kWh for a given monthly consumption."""
    rounded = int(monthly_kwh)
    if rounded < 1:
        return 0.0
    for low, high, rebate in EEI_REBATE_TABLE:
        if low <= rounded <= high:
            return rebate
    return 0.0


# AFA (Automatic Fuel Adjustment) — replaces the legacy ICPT under RP4.
# Published monthly by TNB. Update this value each billing cycle, or pass it
# explicitly to the calculator. Positive value = surcharge, negative = rebate.
CURRENT_AFA_SEN_PER_KWH: float = 0.0  # update from tnb.com.my each month


# --- Bill calculation -------------------------------------------------------


@dataclass(frozen=True)
class BillLine:
    label: str
    amount_rm: float
    unit_detail: str = ""


@dataclass(frozen=True)
class BillBreakdown:
    tariff_name: str  # "standard" or "tou"
    monthly_kwh: float
    lines: list[BillLine]
    total_rm: float
    effective_sen_per_kwh: float
    notes: list[str] = field(default_factory=list)


def _energy_rate_sen(rates: ComponentRates, in_high_band: bool) -> float:
    gen = rates.generation_high_band_sen if in_high_band else rates.generation_low_band_sen
    return gen + rates.capacity_sen + rates.network_sen


def calculate_standard_bill(
    monthly_kwh: float,
    afa_sen_per_kwh: float = CURRENT_AFA_SEN_PER_KWH,
    schedule: TariffSchedule = RP4,
) -> BillBreakdown:
    if monthly_kwh < 0:
        raise ValueError("monthly_kwh must be non-negative")

    in_high_band = monthly_kwh > schedule.high_band_threshold_kwh
    rates = schedule.standard
    energy_sen = _energy_rate_sen(rates, in_high_band)

    eei_sen = eei_rebate_sen_per_kwh(monthly_kwh)
    net_sen = energy_sen - eei_sen

    energy_rm = monthly_kwh * net_sen / SEN_PER_RM

    retail_waived = monthly_kwh <= schedule.retail_waiver_threshold_kwh
    afa_waived = monthly_kwh <= schedule.afa_waiver_threshold_kwh

    retail_rm = 0.0 if retail_waived else rates.retail_monthly_rm
    afa_rm = 0.0 if afa_waived else monthly_kwh * afa_sen_per_kwh / SEN_PER_RM

    lines = [
        BillLine(
            label="Generation",
            amount_rm=monthly_kwh * (rates.generation_high_band_sen if in_high_band else rates.generation_low_band_sen) / SEN_PER_RM,
            unit_detail=f"{rates.generation_high_band_sen if in_high_band else rates.generation_low_band_sen:.2f} sen/kWh",
        ),
        BillLine(
            label="Capacity",
            amount_rm=monthly_kwh * rates.capacity_sen / SEN_PER_RM,
            unit_detail=f"{rates.capacity_sen:.2f} sen/kWh",
        ),
        BillLine(
            label="Network",
            amount_rm=monthly_kwh * rates.network_sen / SEN_PER_RM,
            unit_detail=f"{rates.network_sen:.2f} sen/kWh",
        ),
        BillLine(
            label="Energy Efficiency Incentive (rebate)",
            amount_rm=-monthly_kwh * eei_sen / SEN_PER_RM,
            unit_detail=f"-{eei_sen:.2f} sen/kWh (band {_eei_band_label(monthly_kwh)})",
        ),
        BillLine(
            label="AFA (Automatic Fuel Adjustment)",
            amount_rm=afa_rm,
            unit_detail=(
                f"waived (usage <= {schedule.afa_waiver_threshold_kwh} kWh)"
                if afa_waived
                else f"{afa_sen_per_kwh:+.2f} sen/kWh"
            ),
        ),
        BillLine(
            label="Retail charge",
            amount_rm=retail_rm,
            unit_detail=(
                f"waived (usage <= {schedule.retail_waiver_threshold_kwh} kWh)"
                if retail_waived
                else f"RM{rates.retail_monthly_rm:.2f}/month"
            ),
        ),
    ]

    total_rm = energy_rm + retail_rm + afa_rm
    effective_sen = (total_rm / monthly_kwh * SEN_PER_RM) if monthly_kwh > 0 else 0.0

    notes = []
    if in_high_band:
        notes.append(
            f"Usage exceeds {schedule.high_band_threshold_kwh} kWh — entire month billed at high-band rate."
        )
    if eei_sen > 0:
        notes.append(f"EEI rebate applied at {eei_sen:.2f} sen/kWh.")
    if retail_waived:
        notes.append("Retail charge and AFA waived (low-usage household).")

    return BillBreakdown(
        tariff_name="standard",
        monthly_kwh=round(monthly_kwh, 2),
        lines=lines,
        total_rm=round(total_rm, 2),
        effective_sen_per_kwh=round(effective_sen, 2),
        notes=notes,
    )


def calculate_tou_bill(
    peak_kwh: float,
    offpeak_kwh: float,
    afa_sen_per_kwh: float = CURRENT_AFA_SEN_PER_KWH,
    schedule: TariffSchedule = RP4,
) -> BillBreakdown:
    if peak_kwh < 0 or offpeak_kwh < 0:
        raise ValueError("kWh values must be non-negative")

    monthly_kwh = peak_kwh + offpeak_kwh
    in_high_band = monthly_kwh > schedule.high_band_threshold_kwh

    peak_rates = schedule.tou_peak
    off_rates = schedule.tou_offpeak

    peak_gen = peak_rates.generation_high_band_sen if in_high_band else peak_rates.generation_low_band_sen
    off_gen = off_rates.generation_high_band_sen if in_high_band else off_rates.generation_low_band_sen

    peak_energy_sen = peak_gen + peak_rates.capacity_sen + peak_rates.network_sen
    off_energy_sen = off_gen + off_rates.capacity_sen + off_rates.network_sen

    eei_sen = eei_rebate_sen_per_kwh(monthly_kwh)

    peak_energy_rm = peak_kwh * (peak_energy_sen - eei_sen) / SEN_PER_RM
    off_energy_rm = offpeak_kwh * (off_energy_sen - eei_sen) / SEN_PER_RM

    retail_waived = monthly_kwh <= schedule.retail_waiver_threshold_kwh
    afa_waived = monthly_kwh <= schedule.afa_waiver_threshold_kwh
    retail_rm = 0.0 if retail_waived else peak_rates.retail_monthly_rm
    afa_rm = 0.0 if afa_waived else monthly_kwh * afa_sen_per_kwh / SEN_PER_RM

    lines = [
        BillLine(
            label="Peak energy (gen+cap+net)",
            amount_rm=peak_kwh * peak_energy_sen / SEN_PER_RM,
            unit_detail=f"{peak_kwh:.1f} kWh × {peak_energy_sen:.2f} sen/kWh",
        ),
        BillLine(
            label="Off-peak energy (gen+cap+net)",
            amount_rm=offpeak_kwh * off_energy_sen / SEN_PER_RM,
            unit_detail=f"{offpeak_kwh:.1f} kWh × {off_energy_sen:.2f} sen/kWh",
        ),
        BillLine(
            label="Energy Efficiency Incentive (rebate)",
            amount_rm=-monthly_kwh * eei_sen / SEN_PER_RM,
            unit_detail=f"-{eei_sen:.2f} sen/kWh (band {_eei_band_label(monthly_kwh)})",
        ),
        BillLine(
            label="AFA (Automatic Fuel Adjustment)",
            amount_rm=afa_rm,
            unit_detail=(
                f"waived (usage <= {schedule.afa_waiver_threshold_kwh} kWh)"
                if afa_waived
                else f"{afa_sen_per_kwh:+.2f} sen/kWh"
            ),
        ),
        BillLine(
            label="Retail charge",
            amount_rm=retail_rm,
            unit_detail=(
                f"waived (usage <= {schedule.retail_waiver_threshold_kwh} kWh)"
                if retail_waived
                else f"RM{peak_rates.retail_monthly_rm:.2f}/month"
            ),
        ),
    ]

    total_rm = peak_energy_rm + off_energy_rm + retail_rm + afa_rm
    effective_sen = (total_rm / monthly_kwh * SEN_PER_RM) if monthly_kwh > 0 else 0.0

    notes = []
    if in_high_band:
        notes.append(
            f"Usage exceeds {schedule.high_band_threshold_kwh} kWh — high-band ToU rates applied."
        )
    notes.append(
        f"Split: {peak_kwh / monthly_kwh * 100:.0f}% peak / {offpeak_kwh / monthly_kwh * 100:.0f}% off-peak"
        if monthly_kwh > 0
        else "No usage in period."
    )

    return BillBreakdown(
        tariff_name="tou",
        monthly_kwh=round(monthly_kwh, 2),
        lines=lines,
        total_rm=round(total_rm, 2),
        effective_sen_per_kwh=round(effective_sen, 2),
        notes=notes,
    )


def _eei_band_label(monthly_kwh: float) -> str:
    rounded = int(monthly_kwh)
    for low, high, _ in EEI_REBATE_TABLE:
        if low <= rounded <= high:
            return f"{low}-{high} kWh"
    if rounded > 1000:
        return ">1000 kWh"
    return "n/a"


# --- ToU classifier ---------------------------------------------------------

PEAK_START = time(14, 0)
PEAK_END = time(22, 0)


def is_peak(ts: datetime) -> bool:
    """ToU peak: Monday-Friday, 14:00-21:59. Off-peak otherwise (weekends 24h)."""
    if ts.weekday() >= 5:
        return False
    return PEAK_START <= ts.time() < PEAK_END


def split_peak_offpeak(
    readings: Iterable[tuple[datetime, float]],
) -> tuple[float, float]:
    """Sum kWh into (peak_kwh, offpeak_kwh) from (timestamp, kwh) pairs."""
    peak = 0.0
    off = 0.0
    for ts, kwh in readings:
        if is_peak(ts):
            peak += kwh
        else:
            off += kwh
    return peak, off


# --- Tariff comparison ------------------------------------------------------


@dataclass(frozen=True)
class TariffComparison:
    standard: BillBreakdown
    tou: BillBreakdown
    cheaper: Literal["standard", "tou", "tie"]
    monthly_saving_rm: float
    recommendation: str


def compare_tariffs(
    readings: Iterable[tuple[datetime, float]],
    afa_sen_per_kwh: float = CURRENT_AFA_SEN_PER_KWH,
    schedule: TariffSchedule = RP4,
) -> TariffComparison:
    peak_kwh, off_kwh = split_peak_offpeak(readings)
    total_kwh = peak_kwh + off_kwh

    std = calculate_standard_bill(total_kwh, afa_sen_per_kwh, schedule)
    tou = calculate_tou_bill(peak_kwh, off_kwh, afa_sen_per_kwh, schedule)

    diff = std.total_rm - tou.total_rm
    if abs(diff) < 0.50:
        cheaper: Literal["standard", "tou", "tie"] = "tie"
        rec = "Either plan costs about the same for this usage pattern."
    elif diff > 0:
        cheaper = "tou"
        rec = (
            f"Switching to ToU would save about RM{diff:.2f}/month "
            f"({diff / std.total_rm * 100:.1f}% of the bill). "
            f"This relies on shifting load to off-peak hours (before 2pm or after 10pm weekdays, all day weekends)."
        )
    else:
        cheaper = "standard"
        rec = (
            f"Standard tariff is cheaper by RM{-diff:.2f}/month for this household. "
            f"ToU would only pay off if more usage moved into off-peak hours."
        )

    return TariffComparison(
        standard=std,
        tou=tou,
        cheaper=cheaper,
        monthly_saving_rm=round(abs(diff), 2),
        recommendation=rec,
    )


# --- Marginal cost helper for per-event pricing -----------------------------


def marginal_cost_rm(
    event_kwh: float,
    current_monthly_kwh: float,
    tariff: Literal["standard", "tou"] = "standard",
    event_time: datetime | None = None,
    afa_sen_per_kwh: float = CURRENT_AFA_SEN_PER_KWH,
    schedule: TariffSchedule = RP4,
) -> float:
    """Return the cost of adding event_kwh to a month already at current_monthly_kwh.

    Handles band crossings (EEI bands and the 1500 kWh high-band cliff) by
    computing bill(before) and bill(after) and returning the difference.
    """
    if tariff == "standard":
        before = calculate_standard_bill(current_monthly_kwh, afa_sen_per_kwh, schedule)
        after = calculate_standard_bill(current_monthly_kwh + event_kwh, afa_sen_per_kwh, schedule)
        return round(after.total_rm - before.total_rm, 4)

    if event_time is None:
        raise ValueError("ToU marginal cost needs event_time")
    peak_now = is_peak(event_time)
    # Assume the rest of the month splits 50/50 between bands for the "before" snapshot.
    # For accuracy, callers should track running peak/off-peak totals and pass them.
    before_peak = current_monthly_kwh * 0.3
    before_off = current_monthly_kwh - before_peak
    after_peak = before_peak + (event_kwh if peak_now else 0)
    after_off = before_off + (0 if peak_now else event_kwh)
    before = calculate_tou_bill(before_peak, before_off, afa_sen_per_kwh, schedule)
    after = calculate_tou_bill(after_peak, after_off, afa_sen_per_kwh, schedule)
    return round(after.total_rm - before.total_rm, 4)


# --- CLI demo ---------------------------------------------------------------


def _format_breakdown(b: BillBreakdown) -> str:
    out = [f"{b.tariff_name.upper()} TARIFF — {b.monthly_kwh:.1f} kWh"]
    for line in b.lines:
        out.append(f"  {line.label:<42s}  RM{line.amount_rm:>8.2f}   {line.unit_detail}")
    out.append(f"  {'TOTAL':<42s}  RM{b.total_rm:>8.2f}   (effective {b.effective_sen_per_kwh:.2f} sen/kWh)")
    for note in b.notes:
        out.append(f"  note: {note}")
    return "\n".join(out)


def _demo() -> None:
    print("=" * 78)
    print("TNB RP4 Domestic Tariff — WattsEye calculator demo")
    print(f"Schedule: {RP4.name}, effective {RP4.effective_from} to {RP4.effective_to}")
    print("=" * 78)

    for monthly_kwh in (180, 350, 650, 1200, 1800):
        print()
        bill = calculate_standard_bill(monthly_kwh)
        print(_format_breakdown(bill))

    print()
    print("-" * 78)
    print("ToU comparison for a 350 kWh/month home that uses 35% of energy at peak:")
    print("-" * 78)
    peak_kwh = 350 * 0.35
    off_kwh = 350 - peak_kwh
    std = calculate_standard_bill(350)
    tou = calculate_tou_bill(peak_kwh, off_kwh)
    print(_format_breakdown(std))
    print()
    print(_format_breakdown(tou))
    print()
    saving = std.total_rm - tou.total_rm
    print(f"Difference: RM{saving:+.2f}/month — ToU {'cheaper' if saving > 0 else 'more expensive'}")


if __name__ == "__main__":
    _demo()
