"""The Pi brain: subscribe to live sensor MQTT, decide, and drive the demo.

This is the runtime glue the plan described but never shipped. It ties the
sensing process (`ML/sensing/ads1115_reader.py`) and the ESP32 firmware
together through MQTT, runs the empty-room decision through the existing
`occupancy_engine`, and writes the dashboard live-state file that
`backend/api_server.py` serves.

Data flow (see HARDWARE_CONNECTION.md §14):

    ads1115_reader  --(wattseye/power)-->     \
                                               pi_bridge --> live_state.json --> API
    ESP32 LD2410C   --(wattseye/occupancy)--> /     |
                                                     '--(wattseye/ac/command)--> ESP32
                                                            (IR + relay cutoff)

------------------------------------------------------------------------------
MQTT CONTRACT (this process is the hub)
------------------------------------------------------------------------------
SUBSCRIBES
  wattseye/power       (from ads1115_reader) — see that file for the schema
  wattseye/occupancy   (from ESP32):
      {"occupied": true|false, "room": "living", "ts": "..."}
  wattseye/ac/state    (from ESP32, optional ack):
      {"relay": "on"|"off", "ir_sent": true, "ts": "..."}
PUBLISHES
  wattseye/ac/command  (to ESP32):
      {"command": "off"|"on", "reason": "empty_room_waste", "ts": "..."}
------------------------------------------------------------------------------

Run modes:
    python -m backend.pi_bridge                 # connect to broker, run forever
    python -m backend.pi_bridge --self-test      # no broker; replay a synthetic
                                                 # empty-room scenario and assert
                                                 # the cutoff fires + state is written
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from backend.live_state import write_live_state  # noqa: E402
from ML.insights.models import ApplianceEvent  # noqa: E402
from ML.insights.occupancy_engine import analyze_occupancy  # noqa: E402

POWER_TOPIC = "wattseye/power"
OCCUPANCY_TOPIC = "wattseye/occupancy"
AC_STATE_TOPIC = "wattseye/ac/state"
AC_COMMAND_TOPIC = "wattseye/ac/command"

# Approximate flat energy price for live cost accounting. The exact RP4 banded
# tariff lives in ML/insights/tnb_tariff.py; this is a deliberately simple
# stand-in so the dashboard shows a moving RM figure. Refine if needed.
RM_PER_KWH = 0.45

# How often we recompute + write the dashboard payload.
TICK_INTERVAL_S = 1.0


@dataclass
class BridgeState:
    """Everything the bridge knows about the home right now."""

    # latest power reading
    main_watts: float = 0.0
    ac_watts: float = 0.0
    residual_watts: float = 0.0
    vrms: float = 0.0
    # occupancy
    occupied: bool = True
    occupancy_since: datetime = field(default_factory=datetime.now)
    # cutoff debounce — don't re-send "off" every tick of the same empty episode
    cutoff_sent: bool = False
    # energy accounting (Wh accumulated today)
    wh_today: float = 0.0
    day: int = field(default_factory=lambda: datetime.now().day)
    _last_energy_ts: float = field(default_factory=time.time)

    @property
    def occupancy_state(self) -> str:
        return "home" if self.occupied else "away"

    @property
    def empty_minutes(self) -> float:
        if self.occupied:
            return 0.0
        return (datetime.now() - self.occupancy_since).total_seconds() / 60.0


def _accumulate_energy(state: BridgeState) -> None:
    """Integrate main_watts over wall-clock time into Wh; reset at midnight."""
    now = time.time()
    dt_h = (now - state._last_energy_ts) / 3600.0
    state.wh_today += state.main_watts * dt_h
    state._last_energy_ts = now
    today = datetime.now().day
    if today != state.day:
        state.day = today
        state.wh_today = 0.0


def decide_ac_cutoff(state: BridgeState) -> dict | None:
    """Return an AC command dict if the empty-room rule fires, else None.

    Reuses the shipped occupancy_engine thresholds (HIGH_POWER_WATTS=700,
    EMPTY_ROOM_MINUTES=10) so the live behaviour matches the demo/insight path.
    """
    event = ApplianceEvent(
        timestamp=datetime.now(),
        appliance="inverter_ac",
        power_watts=state.ac_watts,
        duration_minutes=state.empty_minutes,
        occupied=state.occupied,
        source="live",
        confidence=0.99,
    )
    result = analyze_occupancy(event)
    if result.status == "empty_room_waste" and not state.cutoff_sent:
        state.cutoff_sent = True
        return {
            "command": "off",
            "reason": result.status,
            "ts": datetime.now().isoformat(timespec="seconds"),
        }
    return None


def build_dashboard_payload(state: BridgeState) -> dict:
    """Shape the live state into the exact dashboard JSON contract (live_state.py)."""
    kwh_today = state.wh_today / 1000.0
    today_cost = round(kwh_today * RM_PER_KWH, 2)
    now = datetime.now()
    # Steady-state month projection from the current draw: treat the present
    # power as the average rate for a 30-day month. Stable (unlike extrapolating
    # a partial day, which explodes near midnight) and easy to read.
    projected_bill = round((state.main_watts / 1000.0) * 24 * 30 * RM_PER_KWH, 2)

    appliances = []
    if state.ac_watts > 5:
        appliances.append({
            "name": "ac",
            "watts": round(state.ac_watts, 1),
            "today_kwh": round(kwh_today * (state.ac_watts / max(1.0, state.main_watts)), 2),
            "today_rm": round(today_cost * (state.ac_watts / max(1.0, state.main_watts)), 2),
        })
    if state.residual_watts > 5:
        appliances.append({
            "name": "other",
            "watts": round(state.residual_watts, 1),
            "today_kwh": round(kwh_today * (state.residual_watts / max(1.0, state.main_watts)), 2),
            "today_rm": round(today_cost * (state.residual_watts / max(1.0, state.main_watts)), 2),
        })

    return {
        "timestamp": now.isoformat(timespec="seconds"),
        "live_power_w": round(state.main_watts, 1),
        "today_cost_rm": today_cost,
        "projected_bill_rm": projected_bill,
        "occupancy_state": state.occupancy_state,
        "occupancy_since": state.occupancy_since.isoformat(timespec="seconds"),
        "active_appliances": appliances,
    }


# --- message handlers (pure: state in, state mutated) -----------------------


def apply_power_message(state: BridgeState, msg: dict) -> None:
    state.main_watts = float(msg.get("main_watts", 0.0))
    state.ac_watts = float(msg.get("ac_watts", 0.0))
    state.residual_watts = float(msg.get("residual_watts", 0.0))
    state.vrms = float(msg.get("vrms", 0.0))


def apply_occupancy_message(state: BridgeState, msg: dict) -> None:
    occupied = bool(msg.get("occupied", True))
    if occupied != state.occupied:
        state.occupied = occupied
        state.occupancy_since = datetime.now()
        if occupied:
            # Room re-occupied: arm the cutoff again for the next empty episode.
            state.cutoff_sent = False


# --- live (broker-connected) runtime ----------------------------------------


def run_live(broker: str, port: int) -> None:
    import paho.mqtt.client as mqtt  # type: ignore

    state = BridgeState()

    def on_connect(client, userdata, flags, rc):
        client.subscribe([(POWER_TOPIC, 0), (OCCUPANCY_TOPIC, 0), (AC_STATE_TOPIC, 0)])
        print(f"bridge connected to {broker}:{port}, subscribed power/occupancy/ac-state")

    def on_message(client, userdata, message):
        try:
            payload = json.loads(message.payload.decode())
        except (ValueError, UnicodeDecodeError):
            return
        if message.topic == POWER_TOPIC:
            apply_power_message(state, payload)
        elif message.topic == OCCUPANCY_TOPIC:
            apply_occupancy_message(state, payload)
        elif message.topic == AC_STATE_TOPIC:
            print(f"esp32 ac state: {payload}")

    client = mqtt.Client(client_id="wattseye-pi-bridge")
    client.on_connect = on_connect
    client.on_message = on_message
    client.connect(broker, port, keepalive=30)
    client.loop_start()

    try:
        while True:
            _accumulate_energy(state)
            command = decide_ac_cutoff(state)
            if command is not None:
                client.publish(AC_COMMAND_TOPIC, json.dumps(command), qos=1)
                print(f"--> AC cutoff command published: {command}")
            write_live_state(build_dashboard_payload(state))
            time.sleep(TICK_INTERVAL_S)
    except KeyboardInterrupt:
        pass
    finally:
        client.loop_stop()
        client.disconnect()


# --- self-test (no broker) ---------------------------------------------------


def run_self_test() -> int:
    """Replay an empty-room scenario without a broker; assert the cutoff fires.

    Returns a process exit code (0 = pass). Lets the decision + state-writing
    logic be verified on any machine before MQTT/hardware exist.
    """
    state = BridgeState()
    commands: list[dict] = []

    # 1) Occupied, AC running hard -> no cutoff.
    apply_power_message(state, {"main_watts": 1800, "ac_watts": 1200, "residual_watts": 600, "vrms": 240})
    apply_occupancy_message(state, {"occupied": True})
    assert decide_ac_cutoff(state) is None, "should not cut off while occupied"

    # 2) Room goes empty, but only just now -> still no cutoff (under 10 min).
    apply_occupancy_message(state, {"occupied": False})
    assert decide_ac_cutoff(state) is None, "should not cut off before EMPTY_ROOM_MINUTES"

    # 3) Backdate the empty timestamp past the threshold -> cutoff fires once.
    state.occupancy_since = datetime.now() - timedelta(minutes=12)
    cmd = decide_ac_cutoff(state)
    assert cmd is not None and cmd["command"] == "off", "cutoff should fire after 12 min empty + high AC"
    commands.append(cmd)

    # 4) Debounce: a second evaluation in the same episode does NOT re-fire.
    assert decide_ac_cutoff(state) is None, "cutoff must not repeat within one empty episode"

    # 5) Re-occupied then empty again -> re-arms and can fire once more.
    apply_occupancy_message(state, {"occupied": True})
    apply_occupancy_message(state, {"occupied": False})
    state.occupancy_since = datetime.now() - timedelta(minutes=15)
    assert decide_ac_cutoff(state) is not None, "should re-arm after re-occupancy"

    # 6) live_state.json is written in the exact dashboard shape.
    state.wh_today = 5200.0  # 5.2 kWh so far today
    payload = build_dashboard_payload(state)
    write_live_state(payload)
    required = {"timestamp", "live_power_w", "today_cost_rm", "projected_bill_rm",
                "occupancy_state", "occupancy_since", "active_appliances"}
    missing = required - set(payload)
    assert not missing, f"dashboard payload missing keys: {missing}"

    print("self-test PASSED")
    print(f"  cutoff commands fired: {len(commands)} (expected >=1)")
    print(f"  sample payload: {json.dumps(payload, indent=2)}")
    return 0


def main() -> None:
    parser = argparse.ArgumentParser(description="WattsEye Pi bridge (MQTT -> decision -> live state).")
    parser.add_argument("--broker", default=os.environ.get("MQTT_BROKER", "127.0.0.1"))
    parser.add_argument("--port", type=int, default=int(os.environ.get("MQTT_PORT", "1883")))
    parser.add_argument("--self-test", action="store_true",
                        help="Run the offline decision/state self-test and exit.")
    args = parser.parse_args()

    if args.self_test:
        raise SystemExit(run_self_test())
    run_live(args.broker, args.port)


if __name__ == "__main__":
    main()
