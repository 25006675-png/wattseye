# Sensing — Power Math

This folder owns the bridge between raw ADS1115 samples and the watt values that reach the dashboard.

```text
power_math.py
  RMS calculation, apparent-power computation (Vrms * Irms),
  per-appliance power-factor correction.
  Calibration constants and the APPLIANCE_POWER_FACTORS table live here.
```

## Why this exists

A naive `Power = Voltage * Current` is wrong for 50 Hz mains. The ADS1115 at ~250 SPS per channel (3 channels active) only gives ~5 samples per AC cycle — enough to compute RMS magnitudes, not enough to resolve the phase angle between voltage and current. So WattsEye computes:

```text
Apparent power S = Vrms * Irms      (units: VA, what the ADC can give us)
Real power     P = S * cos(phi)     (per-appliance PF correction at the insight layer)
```

For resistive demo loads (kettle, hair dryer, iron) `cos(phi) ≈ 1.00` so apparent ≈ real and the dashboard is accurate live. For inductive or switching loads (LED lamp, fridge, inverter AC) the PF table corrects the displayed watts.

See plan 02 §10a and plan 04 §5 for the full reasoning.

## Quick self-check

```powershell
python .\ML\sensing\power_math.py
```

This runs a synthetic 50 Hz simulation of a 2000 W kettle and a 1500 VA inverter AC, then prints the RMS calculation and the PF-corrected watts.

## Calibration workflow

1. Plug in a kettle alone. The kettle has PF ≈ 1.00 by physics, so any gap between WattsEye's apparent-power reading and the kettle's rated wattage is **sensor scale error**. Adjust `CalibrationConstants.main_current_scale` (and `voltage_scale` if needed) until the reading matches.
2. Plug in each non-resistive appliance and record `measured_VA / rated_W`. Store the result in `APPLIANCE_POWER_FACTORS`.
3. The insight layer (`ML/insights/insight_orchestrator.py`) calls `apparent_to_real_watts(va, appliance)` before showing values on the dashboard.

## Upgrade path

The ADS1115 is fine for the prototype demo (resistive appliances, no real inverter AC on stage). For production:

- **MCP3008 over SPI** (~200 kSPS): enough samples per cycle to compute true real power including PF in software. RM 10-25.
- **PZEM-004T / ADE7953**: dedicated energy-metering ICs that return V, I, W, PF, and accumulated energy directly. RM 30-60.

Neither is needed for the demo. The PF correction in this module is the honest middle ground.
