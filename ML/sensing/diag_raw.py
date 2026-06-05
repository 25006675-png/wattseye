"""Raw ADS1115 front-end diagnostic — NO scaling, NO RMS, NO calibration.

Prints the raw pin voltage on each channel so you can tell a *working* input
from a *floating* one before trusting any watt value. This exists because
calibration only works once the sensor actually tracks the load; if a CT/ZMPT
input is floating or unbiased, scaling just amplifies noise.

How to read the output, per channel:
  * mean ~1.65 V                  -> input is biased to the midpoint (good).
  * mean near 0 V or 3.3 V, drifting, or far from 1.65 V  -> likely floating /
    unbiased (bad — this is the phantom-current culprit).
  * Vpp (peak-to-peak) GROWS when you switch the load on  -> the sensor is
    really seeing current/voltage (good).
  * Vpp barely changes between load-off and load-on       -> the sensor is NOT
    sensing the conductor (clamp on wrong wire / both conductors / not seated).

Channels (HARDWARE_CONNECTION.md §6-8):
  A3 = main feeder current (SCT-013 #1)
  A1 = mains voltage       (ZMPT101B OUT)
  A2 = dedicated AC current(SCT-013 #2)

Run on the Pi:
  python -m ML.sensing.diag_raw                 # forever, 1 s windows
  python -m ML.sensing.diag_raw --count 5       # 5 windows then stop
Compare a load-OFF run against a load-ON run (e.g. kettle).
"""

from __future__ import annotations

import argparse
import time

CHANNELS = {3: "A3 main-I", 1: "A1 voltage", 2: "A2 ac-I"}
MIDPOINT_V = 1.65  # expected DC bias for a 3.3 V single-supply front end


def _read_raw_window(duration_s: float = 1.0):
    """Collect raw pin voltages (volts at the ADC, unscaled) for each channel."""
    import board  # type: ignore
    import busio  # type: ignore
    import adafruit_ads1x15.ads1115 as ADS  # type: ignore
    from adafruit_ads1x15.analog_in import AnalogIn  # type: ignore

    i2c = busio.I2C(board.SCL, board.SDA)
    ads = ADS.ADS1115(i2c, address=0x48)
    ads.data_rate = 860
    pins = {idx: AnalogIn(ads, getattr(ADS, f"P{idx}", idx)) for idx in CHANNELS}

    buffers: dict[int, list[float]] = {idx: [] for idx in CHANNELS}
    t_end = time.time() + duration_s
    while time.time() < t_end:
        for idx, pin in pins.items():
            buffers[idx].append(pin.voltage)
    return buffers


def _summarise(samples: list[float]) -> dict[str, float]:
    if not samples:
        return {"n": 0, "mean": 0.0, "min": 0.0, "max": 0.0, "vpp": 0.0}
    lo, hi = min(samples), max(samples)
    return {
        "n": len(samples),
        "mean": sum(samples) / len(samples),
        "min": lo,
        "max": hi,
        "vpp": hi - lo,
    }


def _verdict(s: dict[str, float]) -> str:
    """One-word read on whether this channel looks alive or floating."""
    if s["n"] == 0:
        return "NO SAMPLES"
    bias_ok = abs(s["mean"] - MIDPOINT_V) < 0.3
    moving = s["vpp"] > 0.02  # >~20 mV swing => some signal present
    if not bias_ok:
        return f"BIAS OFF (mean {s['mean']:.2f}V, want ~{MIDPOINT_V}V) -> likely floating/unbiased"
    if not moving:
        return "biased but FLAT (Vpp tiny) -> no signal on this input"
    return "biased + signal present"


def main() -> None:
    parser = argparse.ArgumentParser(description="Raw ADS1115 front-end diagnostic.")
    parser.add_argument("--count", type=int, default=0, help="Stop after N windows (0 = forever).")
    parser.add_argument("--window", type=float, default=1.0, help="Seconds per window (default 1.0).")
    args = parser.parse_args()

    print("Raw ADS1115 readings (volts at the pin, UNSCALED). Ctrl-C to stop.")
    print("Compare load-OFF vs load-ON: a real sensor's Vpp grows under load.\n")

    n = 0
    while True:
        buffers = _read_raw_window(args.window)
        ts = time.strftime("%H:%M:%S")
        for idx, name in CHANNELS.items():
            s = _summarise(buffers[idx])
            print(f"[{ts}] {name:11s} n={s['n']:4d}  "
                  f"mean={s['mean']:5.3f}V  min={s['min']:5.3f}  max={s['max']:5.3f}  "
                  f"Vpp={s['vpp']:5.3f}V  | {_verdict(s)}")
        print()
        n += 1
        if args.count and n >= args.count:
            break


if __name__ == "__main__":
    main()
