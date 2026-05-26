"""Read SCT-013 clamps + ZMPT101B via ADS1115 and publish a power reading once
per second over MQTT. This is the Pi-side live sensing process.

Wiring (see HARDWARE_CONNECTION.md §6-8):
    A0 = main feeder current  (SCT-013 #1, biased to 1.65 V)
    A1 = mains voltage        (ZMPT101B OUT, trimpot-tuned)
    A2 = dedicated AC current (SCT-013 #2, biased to 1.65 V)

It publishes JSON to MQTT topic `wattseye/power` (see the MQTT CONTRACT block
below). `pi_bridge.py` consumes that topic, decides on AC cutoff, and writes the
dashboard live-state file.

Run modes:
    python -m ML.sensing.ads1115_reader              # real hardware + MQTT
    python -m ML.sensing.ads1115_reader --simulate   # synthetic samples, no ADC
    python -m ML.sensing.ads1115_reader --no-mqtt     # print readings to stdout

`--simulate` needs neither the ADS1115 nor the adafruit/paho libraries, so the
whole pipeline can be exercised on a laptop before any hardware is wired.

------------------------------------------------------------------------------
MQTT CONTRACT — topic `wattseye/power`  (published ~1 Hz, QoS 0, not retained)
------------------------------------------------------------------------------
{
  "ts":            "2026-05-26T14:03:11",   # ISO local time
  "vrms":          239.8,                    # volts
  "main_watts":    1834.2,                   # real W, whole-home (PF-corrected)
  "ac_watts":      1180.5,                   # real W, dedicated AC branch
  "residual_watts":653.7,                    # main - ac (everything else)
  "irms_main":     7.92,
  "irms_ac":       5.10
}
------------------------------------------------------------------------------
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path

# Import power_math whether run as a module (-m) or as a direct script.
try:
    from .power_math import (
        CalibrationConstants,
        apparent_to_real_watts,
        compute_power_reading,
    )
except ImportError:  # direct: python ML/sensing/ads1115_reader.py
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from power_math import (  # type: ignore
        CalibrationConstants,
        apparent_to_real_watts,
        compute_power_reading,
    )

POWER_TOPIC = "wattseye/power"

# SCT-013 30A/1V: 30 A of primary current per 1 V at the jack (burden resistor
# is built in — see HARDWARE_CONNECTION.md §6.1, do NOT add an external one).
AMPS_PER_VOLT = 30.0

# ZMPT101B is trimpot-tuned (§7.3) so its OUT swings within 0-3.3 V. This maps
# 1 V at OUT to real mains volts; refine during calibration (§16).
VOLTS_PER_VOLT = 240.0  # placeholder — set during voltage calibration

# Calibrate once against a known kettle (§16). 1.00 == no correction.
CALIBRATION = CalibrationConstants(
    voltage_scale=1.00,
    main_current_scale=1.00,
    ac_current_scale=1.00,
)

# The branch on clamp #2 is the dedicated AC; PF-correct it as an inverter AC.
AC_APPLIANCE_CLASS = "inverter_ac"


# --- sample acquisition -----------------------------------------------------


def _read_hardware_window(duration_s: float = 1.0):
    """Collect ~1 s of (voltage, main_current, ac_current) samples from the ADS1115.

    Returns three lists already scaled to physical units (volts, amps). The
    1.65 V bias is left in — compute_power_reading()'s rms_centered() removes it.
    """
    import board  # type: ignore
    import busio  # type: ignore
    import adafruit_ads1x15.ads1115 as ADS  # type: ignore
    from adafruit_ads1x15.analog_in import AnalogIn  # type: ignore

    i2c = busio.I2C(board.SCL, board.SDA)
    ads = ADS.ADS1115(i2c, address=0x48)
    ads.data_rate = 860  # fastest; nets ~250 SPS/channel after the mux
    a_main = AnalogIn(ads, ADS.P0)
    a_volt = AnalogIn(ads, ADS.P1)
    a_ac = AnalogIn(ads, ADS.P2)

    v_buf, i_main_buf, i_ac_buf = [], [], []
    t_end = time.time() + duration_s
    while time.time() < t_end:
        v_buf.append(a_volt.voltage * VOLTS_PER_VOLT)
        i_main_buf.append(a_main.voltage * AMPS_PER_VOLT)
        i_ac_buf.append(a_ac.voltage * AMPS_PER_VOLT)
    return v_buf, i_main_buf, i_ac_buf


def _read_simulated_window(t: float):
    """Synthetic 50 Hz buffers so the pipeline runs with no hardware.

    Models a ~1.8 kW whole-home load with a ~1.2 kW AC branch, gently varying
    so the dashboard isn't static. The AC branch goes to ~0 after t>40 s to
    mimic a cutoff, which lets the bridge's decision logic be exercised too.
    """
    from math import pi, sin

    sps = 250
    vrms = 240.0
    main_w = 1800.0 + 150.0 * sin(t / 7.0)
    ac_w = 0.0 if (int(t) % 80) >= 40 else 1200.0 + 100.0 * sin(t / 5.0)

    i_main_rms = main_w / vrms
    i_ac_rms = ac_w / vrms
    v_amp = vrms * 1.41421
    im_amp = i_main_rms * 1.41421
    ia_amp = i_ac_rms * 1.41421

    v_buf = [v_amp * sin(2 * pi * 50 * (i / sps)) for i in range(sps)]
    i_main_buf = [im_amp * sin(2 * pi * 50 * (i / sps)) for i in range(sps)]
    i_ac_buf = [ia_amp * sin(2 * pi * 50 * (i / sps)) for i in range(sps)]
    return v_buf, i_main_buf, i_ac_buf


# --- reading assembly -------------------------------------------------------


def build_power_message(v_buf, i_main_buf, i_ac_buf) -> dict:
    """Turn raw sample buffers into the MQTT `wattseye/power` payload."""
    reading = compute_power_reading(v_buf, i_main_buf, i_ac_buf, CALIBRATION)
    # Whole-home: we don't know the appliance mix, so use the generic PF.
    main_watts = apparent_to_real_watts(reading.apparent_main_va, "unknown")
    ac_watts = apparent_to_real_watts(reading.apparent_ac_va, AC_APPLIANCE_CLASS)
    residual = max(0.0, round(main_watts - ac_watts, 2))
    return {
        "ts": datetime.now().isoformat(timespec="seconds"),
        "vrms": reading.vrms,
        "main_watts": main_watts,
        "ac_watts": ac_watts,
        "residual_watts": residual,
        "irms_main": reading.irms_main,
        "irms_ac": reading.irms_ac,
    }


# --- MQTT -------------------------------------------------------------------


def _make_mqtt_client(host: str, port: int):
    import paho.mqtt.client as mqtt  # type: ignore

    client = mqtt.Client(client_id="wattseye-ads1115-reader")
    client.connect(host, port, keepalive=30)
    client.loop_start()
    return client


def main() -> None:
    parser = argparse.ArgumentParser(description="WattsEye ADS1115 live power reader.")
    parser.add_argument("--simulate", action="store_true",
                        help="Generate synthetic samples (no ADS1115/adafruit libs needed).")
    parser.add_argument("--no-mqtt", action="store_true",
                        help="Print readings to stdout instead of publishing to MQTT.")
    parser.add_argument("--broker", default=os.environ.get("MQTT_BROKER", "127.0.0.1"))
    parser.add_argument("--port", type=int, default=int(os.environ.get("MQTT_PORT", "1883")))
    parser.add_argument("--interval", type=float, default=1.0,
                        help="Seconds between readings (default 1.0).")
    parser.add_argument("--count", type=int, default=0,
                        help="Stop after N readings (0 = run forever).")
    args = parser.parse_args()

    client = None
    if not args.no_mqtt:
        try:
            client = _make_mqtt_client(args.broker, args.port)
            print(f"connected to MQTT {args.broker}:{args.port}, publishing {POWER_TOPIC}")
        except Exception as e:
            print(f"MQTT connect failed ({e}); falling back to stdout", file=sys.stderr)

    start = time.time()
    n = 0
    while True:
        loop_start = time.time()
        if args.simulate:
            buffers = _read_simulated_window(loop_start - start)
        else:
            buffers = _read_hardware_window(args.interval)

        msg = build_power_message(*buffers)
        encoded = json.dumps(msg)
        if client is not None:
            client.publish(POWER_TOPIC, encoded, qos=0)
        else:
            print(encoded)

        n += 1
        if args.count and n >= args.count:
            break
        # Keep a steady cadence; hardware read already consumed ~interval seconds.
        sleep_for = args.interval - (time.time() - loop_start)
        if sleep_for > 0:
            time.sleep(sleep_for)

    if client is not None:
        client.loop_stop()
        client.disconnect()


if __name__ == "__main__":
    main()
