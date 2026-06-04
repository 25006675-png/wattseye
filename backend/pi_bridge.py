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

from backend import reminders, smart_rules  # noqa: E402
from backend.live_state import write_live_state  # noqa: E402

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
    # Optional live NILM disaggregation (off unless WATTSEYE_NILM is set).
    nilm: object | None = None
    _last_nilm_ts: float = 0.0
    _nilm_result: dict = field(default_factory=dict)

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


def decide_ac_action(state: BridgeState, rule: dict | None = None) -> dict | None:
    """Return the smart-rule decision if it fires this tick, else None.

    Delegates the waste detection + threshold/mode logic to backend.smart_rules
    (which reuses occupancy_engine). Debounced via state.cutoff_sent so one empty
    episode acts at most once. The decision's "action" is "auto_off" or "remind";
    the caller decides whether to drive the AC or just nudge the user.
    """
    if state.cutoff_sent:
        return None
    decision = smart_rules.evaluate(
        state.ac_watts, state.empty_minutes, state.occupied, rule
    )
    if decision is not None:
        state.cutoff_sent = True
    return decision


def build_dashboard_payload(state: BridgeState) -> dict:
    """Shape the live state into the exact dashboard JSON contract (live_state.py)."""
    kwh_today = state.wh_today / 1000.0
    today_cost = round(kwh_today * RM_PER_KWH, 2)
    now = datetime.now()
    # Steady-state month projection from the current draw: treat the present
    # power as the average rate for a 30-day month. Stable (unlike extrapolating
    # a partial day, which explodes near midnight) and easy to read.
    projected_bill = round((state.main_watts / 1000.0) * 24 * 30 * RM_PER_KWH, 2)

    def _entry(name: str, watts: float) -> dict:
        share = watts / max(1.0, state.main_watts)
        return {
            "name": name,
            "watts": round(watts, 1),
            "today_kwh": round(kwh_today * share, 2),
            "today_rm": round(today_cost * share, 2),
        }

    appliances = []
    if state.ac_watts > 5:
        appliances.append(_entry("ac", state.ac_watts))

    # If live NILM is enabled and labelled the residual, show per-appliance tiles;
    # otherwise fall back to the single aggregate "other" bucket.
    nilm_on = {n: r for n, r in state._nilm_result.items() if r.get("on")}
    if nilm_on:
        for name, r in nilm_on.items():
            appliances.append(_entry(name, r["watts"]))
    elif state.residual_watts > 5:
        appliances.append(_entry("other", state.residual_watts))

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
    if state.nilm is not None:
        state.nilm.add_sample(state.residual_watts, time.time())


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
    if os.environ.get("WATTSEYE_NILM", "").lower() in ("1", "true", "yes"):
        from backend.nilm_runtime import try_build_runner
        state.nilm = try_build_runner()
        print("NILM live disaggregation:",
              "ON" if state.nilm else "unavailable (torch/checkpoints missing) -> 'other' bucket")

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
            if state.nilm is not None and (time.time() - state._last_nilm_ts) >= 6.0:
                try:
                    state._nilm_result = state.nilm.infer()
                except Exception:
                    state._nilm_result = {}
                state._last_nilm_ts = time.time()
            # Re-read the rule each tick so a change made in the app (POST
            # /api/ac/rule) takes effect within ~1s without restarting the bridge.
            decision = decide_ac_action(state, smart_rules.load_rule())
            if decision is not None:
                if decision["action"] == "auto_off":
                    command = {
                        "command": "off",
                        "reason": decision["reason"],
                        "ts": datetime.now().isoformat(timespec="seconds"),
                    }
                    client.publish(AC_COMMAND_TOPIC, json.dumps(command), qos=1)
                    print(f"--> AC auto-off published (smart rule): {command}")
                else:  # "remind": nudge the user via WhatsApp, don't touch the AC
                    # Schedule an immediately-due reminder; the daemon running in
                    # api_server (reminders.start) picks it up within ~5s and pushes
                    # the left_on_empty card over WhatsApp. Debounced once/episode by
                    # state.cutoff_sent, so it can't spam.
                    reminders.schedule(
                        "left_on_empty",
                        datetime.now(),
                        headline=(f"AC drawing {decision['ac_watts']:.0f}W in an empty "
                                  f"room ({decision['empty_minutes']:.0f} min)."),
                    )
                    print(f"--> Smart rule REMIND -> WhatsApp queued: AC "
                          f"{decision['ac_watts']}W, room empty {decision['empty_minutes']} min")
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
    # Explicit rule (10-min threshold, auto-off) so the test is deterministic and
    # independent of any _smart_rule.json on disk.
    auto_rule = {"enabled": True, "empty_minutes": 10.0, "mode": "auto_off"}

    # 1) Occupied, AC running hard -> no action.
    apply_power_message(state, {"main_watts": 1800, "ac_watts": 1200, "residual_watts": 600, "vrms": 240})
    apply_occupancy_message(state, {"occupied": True})
    assert decide_ac_action(state, auto_rule) is None, "should not act while occupied"

    # 2) Room goes empty, but only just now -> still nothing (under threshold).
    apply_occupancy_message(state, {"occupied": False})
    assert decide_ac_action(state, auto_rule) is None, "should not act before the threshold"

    # 3) Backdate the empty timestamp past the threshold -> auto-off fires once.
    state.occupancy_since = datetime.now() - timedelta(minutes=12)
    decision = decide_ac_action(state, auto_rule)
    assert decision is not None and decision["action"] == "auto_off", \
        "auto-off should fire after 12 min empty + high AC"
    commands.append(decision)

    # 4) Debounce: a second evaluation in the same episode does NOT re-fire.
    assert decide_ac_action(state, auto_rule) is None, "must not repeat within one empty episode"

    # 5) Re-occupied then empty again -> re-arms and can fire once more.
    apply_occupancy_message(state, {"occupied": True})
    apply_occupancy_message(state, {"occupied": False})
    state.occupancy_since = datetime.now() - timedelta(minutes=15)
    assert decide_ac_action(state, auto_rule) is not None, "should re-arm after re-occupancy"

    # 6) Disabled rule -> never acts, even with a long empty episode.
    apply_occupancy_message(state, {"occupied": True})
    apply_occupancy_message(state, {"occupied": False})
    state.occupancy_since = datetime.now() - timedelta(minutes=30)
    assert decide_ac_action(state, {"enabled": False, "empty_minutes": 10.0, "mode": "auto_off"}) is None, \
        "disabled rule must never act"

    # 7) Remind mode -> fires with action='remind' (nudge, not a cutoff).
    apply_occupancy_message(state, {"occupied": True})
    apply_occupancy_message(state, {"occupied": False})
    state.occupancy_since = datetime.now() - timedelta(minutes=20)
    remind = decide_ac_action(state, {"enabled": True, "empty_minutes": 15.0, "mode": "remind"})
    assert remind is not None and remind["action"] == "remind", "remind mode should produce a remind decision"

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
