"""Power math for WattsEye's ADS1115 + CT clamp sensing chain.

This module is the honest middle layer between raw ADS1115 samples and the
watt values shown on the dashboard. It exists because a naive `V * I` is
wrong for AC mains, and our ADS1115 sample rate is too low to compute true
real power on its own.

What this module does:

1. Compute RMS values from a 1-second buffer of ADS1115 samples.
2. Compute apparent power S = Vrms * Irms in VA.
3. Apply a per-appliance power-factor correction to convert VA to W when
   the appliance class is known.

What this module does NOT do:

- Compute instantaneous v(t) * i(t) point-by-point real power. The ADS1115
  at ~250 SPS per channel only gives ~5 samples per 50 Hz cycle, which is
  not enough to resolve phase. Upgrade to MCP3008 or a dedicated energy-
  metering IC (PZEM-004T, ADE7953) if true real power is required.

See plan 02 §10a and plan 04 §5 for the full reasoning.
"""

from __future__ import annotations

from dataclasses import dataclass
from math import sqrt
from typing import Iterable, Sequence


MAINS_FREQUENCY_HZ = 50.0
NOMINAL_VRMS_MALAYSIA = 240.0


@dataclass(frozen=True)
class CalibrationConstants:
    """Per-channel scale corrections measured against a known resistive load.

    Apply by multiplying the raw RMS value by the constant. A constant of
    1.00 means no correction. Measure these once during commissioning by
    plugging in a calibrated reference (kettle with known rating, or a
    smart plug used as ground truth).
    """

    voltage_scale: float = 1.00
    main_current_scale: float = 1.00
    ac_current_scale: float = 1.00


DEFAULT_CALIBRATION = CalibrationConstants()


# Power factor reference table. Sources:
# - Manufacturer datasheets for typical Malaysian household appliances
# - EnergyStar appliance category guidelines
# - General industry consensus for resistive vs. inductive vs. SMPS loads
#
# These are starting estimates. Overwrite with values measured during
# commissioning (rated_W / measured_VA, with one appliance running alone).
APPLIANCE_POWER_FACTORS: dict[str, float] = {
    # Pure resistive (heating element only)
    "kettle": 1.00,
    "iron": 1.00,
    "water_heater": 1.00,
    "incandescent_lamp": 1.00,
    "toaster": 1.00,
    "rice_cooker": 1.00,
    # Resistive heating + small motor
    "hair_dryer": 0.95,
    "oven": 0.98,
    # Switching power supplies / LED drivers
    "led_lamp": 0.65,
    "phone_charger": 0.55,
    "laptop_charger": 0.65,
    "tv": 0.80,
    "computer": 0.70,
    # Inductive (motors, compressors)
    "fan": 0.85,
    "fridge": 0.70,
    "washing_machine": 0.75,
    "microwave": 0.95,
    # Variable inductive (inverter compressors — varies with load)
    "inverter_ac": 0.85,  # typical mid-load; ranges 0.60-0.95
    # Catch-all
    "unknown": 0.85,
}


# --- RMS calculation --------------------------------------------------------


def rms(samples: Sequence[float] | Iterable[float]) -> float:
    """Return the root-mean-square of a buffer of samples.

    Samples should be zero-centered. If the ADC reads with a DC offset
    (e.g. signal biased to 1.65 V midpoint for a 3.3 V system), subtract
    the mean first or use `rms_centered`.
    """
    values = list(samples)
    if not values:
        return 0.0
    return sqrt(sum(v * v for v in values) / len(values))


def rms_centered(samples: Sequence[float] | Iterable[float]) -> float:
    """RMS after removing the mean, for signals with a DC offset."""
    values = list(samples)
    if not values:
        return 0.0
    mean = sum(values) / len(values)
    return sqrt(sum((v - mean) ** 2 for v in values) / len(values))


# --- One-second power computation ------------------------------------------


@dataclass(frozen=True)
class PowerReading:
    """One second of computed power from the ADS1115 buffers."""

    vrms: float
    irms_main: float
    irms_ac: float
    apparent_main_va: float
    apparent_ac_va: float
    apparent_residual_va: float

    @property
    def is_dc_offset_suspicious(self) -> bool:
        """Vrms way off nominal is a clue the signal is not zero-centered."""
        return self.vrms < NOMINAL_VRMS_MALAYSIA * 0.5 or self.vrms > NOMINAL_VRMS_MALAYSIA * 1.2


def compute_power_reading(
    voltage_samples: Sequence[float],
    main_current_samples: Sequence[float],
    ac_current_samples: Sequence[float],
    calibration: CalibrationConstants = DEFAULT_CALIBRATION,
) -> PowerReading:
    """Convert one second of ADS1115 samples into RMS power values.

    All sample buffers are expected to be in the same physical units
    already (volts and amps), after the burden-resistor + voltage-divider
    conditioning. Apply `calibration` to correct per-channel scale error.
    """
    vrms = rms_centered(voltage_samples) * calibration.voltage_scale
    irms_main = rms_centered(main_current_samples) * calibration.main_current_scale
    irms_ac = rms_centered(ac_current_samples) * calibration.ac_current_scale

    s_main = vrms * irms_main
    s_ac = vrms * irms_ac
    s_residual = max(0.0, s_main - s_ac)

    return PowerReading(
        vrms=round(vrms, 2),
        irms_main=round(irms_main, 4),
        irms_ac=round(irms_ac, 4),
        apparent_main_va=round(s_main, 2),
        apparent_ac_va=round(s_ac, 2),
        apparent_residual_va=round(s_residual, 2),
    )


# --- Apparent-to-real power correction --------------------------------------


def power_factor_for(appliance: str) -> float:
    """Return the calibrated PF for an appliance, defaulting to 0.85."""
    return APPLIANCE_POWER_FACTORS.get(appliance.lower(), APPLIANCE_POWER_FACTORS["unknown"])


def apparent_to_real_watts(apparent_va: float, appliance: str) -> float:
    """Convert apparent power (VA) to a real-watts estimate using PF table.

    Use this at the insight layer once an appliance has been classified
    (by NILM or by being on the dedicated AC clamp). For unknown loads,
    a generic PF of 0.85 is used — flag the value as estimated in the UI.
    """
    return round(apparent_va * power_factor_for(appliance), 2)


def real_power_breakdown(
    reading: PowerReading,
    ac_appliance: str = "inverter_ac",
    residual_classifications: dict[str, float] | None = None,
) -> dict[str, float]:
    """Convert a PowerReading into a per-appliance real-watt breakdown.

    `residual_classifications` maps appliance name -> apparent VA share of
    the residual signal (typically output by NILM). The AC branch is
    always treated as the `ac_appliance` class (default: inverter AC).
    """
    breakdown: dict[str, float] = {
        ac_appliance: apparent_to_real_watts(reading.apparent_ac_va, ac_appliance),
    }
    if residual_classifications:
        for appliance, apparent_va in residual_classifications.items():
            breakdown[appliance] = apparent_to_real_watts(apparent_va, appliance)
    return breakdown


# --- Self-check demo --------------------------------------------------------


def _synthetic_50hz(amplitude: float, samples_per_second: int, duration_s: float = 1.0) -> list[float]:
    """Generate a clean 50 Hz sine wave for sanity-check / unit-test use."""
    from math import pi, sin

    total = int(samples_per_second * duration_s)
    return [amplitude * sin(2 * pi * MAINS_FREQUENCY_HZ * (i / samples_per_second)) for i in range(total)]


def _demo() -> None:
    # Simulate one second of clean samples for a 2000 W kettle on 240 V mains.
    # I_peak = 2000 / 240 * sqrt(2) = 11.78 A.
    v_samples = _synthetic_50hz(amplitude=240 * 1.41421, samples_per_second=250)
    i_samples = _synthetic_50hz(amplitude=2000 / 240 * 1.41421, samples_per_second=250)
    no_load = [0.0] * 250

    reading = compute_power_reading(v_samples, i_samples, no_load)
    print("Synthetic kettle on general branch (resistive, PF=1.00):")
    print(f"  Vrms              = {reading.vrms} V")
    print(f"  Irms_main         = {reading.irms_main} A")
    print(f"  Apparent main     = {reading.apparent_main_va} VA")
    print(f"  Apparent AC       = {reading.apparent_ac_va} VA")
    print(f"  Apparent residual = {reading.apparent_residual_va} VA")
    real = apparent_to_real_watts(reading.apparent_main_va, "kettle")
    print(f"  Real watts (PF-corrected for kettle) = {real} W")

    # Now simulate an inverter AC drawing 1500 VA at PF 0.85 → real ~1275 W.
    ac_amps_rms = 1500 / 240
    ac_samples = _synthetic_50hz(amplitude=ac_amps_rms * 1.41421, samples_per_second=250)
    reading_ac = compute_power_reading(v_samples, no_load, ac_samples)
    print()
    print("Synthetic AC on dedicated branch (apparent 1500 VA, PF=0.85):")
    print(f"  Apparent AC       = {reading_ac.apparent_ac_va} VA")
    real_ac = apparent_to_real_watts(reading_ac.apparent_ac_va, "inverter_ac")
    print(f"  Real watts (PF-corrected for inverter_ac) = {real_ac} W")
    print(f"  Reported on dashboard: {real_ac} W (was overstated by "
          f"{reading_ac.apparent_ac_va - real_ac:.0f} VA without correction)")


if __name__ == "__main__":
    _demo()
