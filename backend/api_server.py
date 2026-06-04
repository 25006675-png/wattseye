"""Local WattsEye API bridge for the Flutter app.

Run from the repo root:

    python backend/api_server.py

The production Pi backend can replace this with FastAPI later, as long as it
keeps the same JSON contract documented in extra_info/FRONTEND_BRIEF.md.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import sys
from typing import Any
from urllib.parse import parse_qs, urlparse

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from ML.insights.coach.coach_engine import (  # noqa: E402
    _demo_snapshot,
    _peak_heavy_snapshot,
    cards_to_json,
    generate_cards,
)
from ML.insights.coach.whatsapp import (  # noqa: E402
    PUSH_ARCHETYPES,
    SETUP_ENV_VARS,
    MetaConfig,
    send_card_via_whatsapp,
)
from ML.insights.coach.whatsapp_webhook import record_user_action  # noqa: E402
from ML.insights.tnb_tariff import (  # noqa: E402
    RP4,
    calculate_standard_bill,
    calculate_tou_bill,
    marginal_cost_rm,
)
from backend.live_state import read_live_state  # noqa: E402

# Demo projection: a household coasting ~20 kWh under the RP4 1,500 kWh
# high-band cliff, so the Bill page tells the same near-cliff story as the
# rp4_tier_cliff coach card (instead of an unrelated 460 kWh fixture).
DEMO_PROJECTED_KWH = 1480.0
DEMO_PEAK_FRACTION = 0.35

# Forecast cost attribution. In live mode the AC share is measured directly by
# the dedicated clamp (exact); "other" is NILM-disaggregated; "unknown" is the
# unattributed residual. These demo fractions illustrate that split for the
# showcase forecast — the attribution bar is what no single-meter app can show.
DEMO_AC_COST_FRACTION = 0.45
DEMO_OTHER_COST_FRACTION = 0.38
DEMO_BASELINE_KWH = 1360.0  # prior month, drives the trend arrow on the forecast

# In-app action vocabulary -> learning-loop intent vocabulary.
# "none" means the user un-acted a card; we drop it from the loop log because
# the prior intent (if any) stands until explicitly overridden.
_APP_ACTION_TO_INTENT = {"do": "accept", "dismiss": "dismiss", "remind": "snooze"}

USER_ACTIONS: dict[str, str] = {}


def dashboard_payload() -> dict[str, Any]:
    # Live data wins when the Pi runtime (pi_bridge.py) is publishing a fresh
    # live_state.json; otherwise fall back to the built-in demo snapshot. The
    # app flips its "Demo data" / "Live Pi" chip purely on the JSON it sees.
    from datetime import datetime

    live = read_live_state()
    if live is not None:
        return live

    snap = _demo_snapshot()
    _std = calculate_standard_bill(DEMO_PROJECTED_KWH)
    # Month-to-date estimate from today's spend (= daily run-rate x days elapsed).
    # Honest extrapolation; a per-appliance accumulator can replace it later.
    days_elapsed = max(datetime.now().day, 1)
    return {
        "timestamp": snap.timestamp.isoformat(timespec="seconds"),
        "live_power_w": snap.live_power_w,
        "today_cost_rm": round(_std.total_rm / 30.0, 2),
        "projected_bill_rm": _std.total_rm,
        "occupancy_state": snap.occupancy_state,
        "occupancy_since": snap.occupancy_since.isoformat(timespec="seconds"),
        "active_appliances": [
            {
                "name": name,
                "watts": values.get("watts", 0),
                "today_kwh": 8.4 if name == "ac" else 2.6,
                "today_rm": (today_rm := 2.68 if name == "ac" else 0.83),
                "kind": "measured" if name == "ac" else "estimated",
                "month_cost_rm": round(today_rm * days_elapsed, 2),
            }
            for name, values in snap.active_appliances.items()
        ],
    }


def bill_payload() -> dict[str, Any]:
    """Real TNB RP4 bill for the demo projection, computed by tnb_tariff.

    Uses the same near-cliff kWh as the rp4_tier_cliff coach card so the Bill
    page and the Coach agree. Returns the itemised breakdown and the high-band
    cliff metadata the app needs to draw the 1,500 kWh gauge.
    """
    kwh = DEMO_PROJECTED_KWH
    std = calculate_standard_bill(kwh)
    peak = round(kwh * DEMO_PEAK_FRACTION, 1)
    off = round(kwh - peak, 1)
    tou = calculate_tou_bill(peak, off)
    threshold = RP4.high_band_threshold_kwh
    total = std.total_rm
    ac_rm = round(total * DEMO_AC_COST_FRACTION, 2)
    other_rm = round(total * DEMO_OTHER_COST_FRACTION, 2)
    unknown_rm = round(total - ac_rm - other_rm, 2)
    baseline_total = calculate_standard_bill(DEMO_BASELINE_KWH).total_rm
    return {
        "projected_total_rm": total,
        "projected_kwh": std.monthly_kwh,
        "effective_sen_per_kwh": std.effective_sen_per_kwh,
        "tou_projected_total_rm": tou.total_rm,
        "baseline_total_rm": round(baseline_total, 2),
        "attribution": [
            {"appliance": "Air-conditioning", "amount_rm": ac_rm, "kind": "measured"},
            {"appliance": "Other appliances", "amount_rm": other_rm, "kind": "estimated"},
            {"appliance": "Unknown / unlabelled", "amount_rm": unknown_rm, "kind": "unknown"},
        ],
        "high_band_threshold_kwh": threshold,
        "headroom_kwh": round(threshold - kwh, 1),
        "in_high_band": kwh > threshold,
        "low_band_gen_sen": RP4.standard.generation_low_band_sen,
        "high_band_gen_sen": RP4.standard.generation_high_band_sen,
        "lines": [
            {
                "label": line.label,
                "amount_rm": round(line.amount_rm, 2),
                "unit_detail": line.unit_detail,
            }
            for line in std.lines
        ],
        "notes": std.notes,
    }


# Forecast simulator levers. Consumption levers remove kWh (so the bill is
# recomputed once through the tariff engine — this is what makes cliff / EEI
# band crossings correct, which a flat per-card sum cannot capture). The two
# tariff levers change the plan instead and never stack (opposite premises).
FORECAST_CONSUMPTION_LEVERS = {
    "left_on_empty",
    "phantom_standby",
    "simultaneous_peak_load",
    "rp4_tier_cliff",
    "anomaly_with_action",
    "routine_shift",
    "inefficient_upgrade",
}
FORECAST_TARIFF_LEVERS = {"tou_switch", "peak_window_shift"}


def forecast_simulate_payload(body: dict[str, Any]) -> dict[str, Any]:
    """Recompute the projected bill for a chosen set of forecast levers.

    Composition is done through the tariff engine, not by summing per-card RM:
    consumption levers are converted to kWh removed and the bill is recomputed
    once at the new usage, so a combination that drops the home back under the
    1,500 kWh cliff sees the full rate reduction on every unit.
    """
    mode = body.get("mode", "showcase")
    selected = {str(k) for k in body.get("selected", [])}
    cards, _ = _coach_cards(mode)
    impact_by_key = {c.archetype_key: c.impact_rm_monthly for c in cards}

    proj = DEMO_PROJECTED_KWH
    baseline_total = calculate_standard_bill(proj).total_rm
    # RM per kWh at the current margin (reflects whichever band proj sits in).
    marginal_rate = marginal_cost_rm(1.0, proj - 1.0)
    if marginal_rate <= 0:
        marginal_rate = RP4.standard.generation_low_band_sen / 100.0

    # 1) Consumption levers -> kWh removed -> single bill recompute.
    kwh_saved = 0.0
    for key in selected & FORECAST_CONSUMPTION_LEVERS:
        kwh_saved += impact_by_key.get(key, 0.0) / marginal_rate
    new_kwh = max(proj - kwh_saved, 0.0)
    bill_after = calculate_standard_bill(new_kwh).total_rm
    consumption_saving = baseline_total - bill_after

    # 2) Tariff levers stack on top, but only the larger of the mutually
    #    exclusive pair counts.
    tariff_candidates: list[float] = []
    if "tou_switch" in selected:
        peak = new_kwh * DEMO_PEAK_FRACTION
        off = new_kwh - peak
        tou_total = calculate_tou_bill(peak, off).total_rm
        tariff_candidates.append(max(bill_after - tou_total, 0.0))
    if "peak_window_shift" in selected:
        tariff_candidates.append(impact_by_key.get("peak_window_shift", 0.0))
    tariff_saving = max(tariff_candidates) if tariff_candidates else 0.0

    total_saving = round(consumption_saving + tariff_saving, 2)
    composed_total = round(baseline_total - total_saving, 2)
    return {
        "projected_total_rm": round(baseline_total, 2),
        "composed_total_rm": composed_total,
        "saving_rm": total_saving,
        "new_kwh": round(new_kwh, 1),
        "selected": sorted(selected),
    }


def coach_cards_payload(mode: str = "showcase") -> list[dict[str, Any]]:
    cards, source = _coach_cards(mode)
    payload = cards_to_json(cards)
    for card in payload:
        card["data_source"] = source
        # Authoritative WhatsApp-push subset (see extra_info/whatsapp.md): only
        # these archetypes earn a phone buzz; the rest stay in-app only.
        card["push_eligible"] = card["archetype_key"] in PUSH_ARCHETYPES
        action = USER_ACTIONS.get(card["archetype_key"])
        if action is not None:
            card["user_action"] = action
    return payload


def _select_coach_snapshot(mode: str):
    """Return (snapshot, source_label).

    showcase -> the hand-built demo literal that trips all 12 archetypes.
    live     -> the Pi's live_state if fresh, else the bench-log history, else
                (no data) the demo literal so the tab never renders empty.
    """
    if mode != "live":
        return _demo_snapshot(), "showcase"
    from backend.snapshot_builder import (
        IAWE_COORDS, IAWE_HISTORY_DB, from_history, from_live_state,
    )

    snap = from_live_state()
    if snap is not None:
        return snap, "live"
    # Real sub-metered home (iAWE) is the primary replay source; fall back to the
    # synthetic Malaysian fixture, then to the demo literal so the tab never empties.
    snap = from_history(IAWE_HISTORY_DB, lat=IAWE_COORDS[0], lon=IAWE_COORDS[1])
    if snap is not None:
        return snap, "replay"
    snap = from_history()
    if snap is not None:
        return snap, "replay"
    return _demo_snapshot(), "showcase"


def _coach_cards(mode: str = "showcase"):
    if mode == "live":
        snap, source = _select_coach_snapshot("live")
        return generate_cards(snap, surface_count=2, include_weather=True), source

    # showcase: assemble the full 12-archetype catalog (one card each) by running
    # the real engine on the demo snapshot (10) + the peak-heavy companion (#3, #6).
    # This is an explicit catalog, not a single real home — see _peak_heavy_snapshot.
    by_key: dict[str, Any] = {}
    for snap in (_demo_snapshot(), _peak_heavy_snapshot()):
        for card in generate_cards(snap, surface_count=2, include_weather=True, apply_feedback=False):
            by_key.setdefault(card.archetype_key, card)
    cards = sorted(by_key.values(), key=lambda c: c.archetype_id)
    return cards, "showcase"


def integrations_status_payload() -> dict[str, Any]:
    model_files = sorted((ROOT / "ML" / "NILM").glob("*.pth"))
    joblib_files = sorted((ROOT / "ML").glob("**/*.joblib"))
    return {
        "pdf": {
            "available": importlib.util.find_spec("reportlab") is not None,
            "endpoint": "/api/report/monthly",
        },
        "weather": {
            "available": True,
            "source": "open-meteo",
            "endpoint": "/api/weather?city=Kuala%20Lumpur",
        },
        "ml": {
            "nilm_model_count": len(model_files),
            "nilm_models": [path.name for path in model_files],
            "torch_available": importlib.util.find_spec("torch") is not None,
            "joblib_model_count": len(joblib_files),
            "joblib_models": [str(path.relative_to(ROOT)) for path in joblib_files],
            "status_endpoint": "/api/ml/status",
            "inference_endpoint": "/api/ml/nilm/infer",
        },
    }


def weather_payload(city: str) -> dict[str, Any]:
    from ML.insights.coach.weather import get_forecast_safe

    forecast = get_forecast_safe(city)
    if forecast is None:
        return {
            "available": False,
            "city": city,
            "source": "open-meteo",
            "reason": "forecast unavailable; backend may be offline",
        }
    return {
        "available": True,
        "city": forecast.city,
        "current_temp_c": forecast.current_temp_c,
        "today_max_c": forecast.today_max_c,
        "daily_max_c": forecast.daily_max_c,
        "hot_days_over_33c": forecast.hot_days_over_33c,
        "fetched_at": forecast.fetched_at.isoformat(),
        "source": forecast.source,
    }


def monthly_report_bytes(mode: str) -> tuple[bytes | None, dict[str, Any] | None]:
    if importlib.util.find_spec("reportlab") is None:
        return None, {
            "error": "reportlab not installed",
            "install": "python -m pip install reportlab",
        }

    from ML.insights.coach.pdf_report import generate_monthly_report

    mode = mode if mode in {"summary", "detailed"} else "summary"
    out_path = ROOT / "backend" / "generated" / f"wattseye_report_{mode}.pdf"
    path = generate_monthly_report(_demo_snapshot(), out_path, mode=mode)
    return path.read_bytes(), None


def ml_status_payload() -> dict[str, Any]:
    return integrations_status_payload()["ml"]


def nilm_infer_payload(body: dict[str, Any]) -> dict[str, Any]:
    if importlib.util.find_spec("torch") is None:
        return {
            "available": False,
            "reason": "PyTorch is not installed",
            "install": "python -m pip install torch",
        }

    from argparse import Namespace
    import torch
    from ML.NILM.test_nilm_inference import (
        MODEL_DIR,
        run_one,
        synthetic_window,
    )

    window = body.get("power_window")
    if not isinstance(window, list) or not window:
        window = synthetic_window(240)
    window = [float(value) for value in window][-240:]
    if len(window) < 240:
        window = [window[0]] * (240 - len(window)) + window

    requested = body.get("models")
    if requested == "all":
        model_paths = sorted(MODEL_DIR.glob("*.pth"))
    elif isinstance(requested, list) and requested:
        model_paths = [MODEL_DIR / str(name) for name in requested]
    else:
        model_paths = [MODEL_DIR / "kettle.pth"]

    args = Namespace(
        input_mean=float(body.get("input_mean", 0.0)),
        input_std=float(body.get("input_std", 1.0)),
        output_mean=float(body.get("output_mean", 0.0)),
        output_std=float(body.get("output_std", 1.0)),
        warmup=int(body.get("warmup", 1)),
    )
    rows = [run_one(path, window, torch.device("cpu"), args) for path in model_paths]
    return {"available": True, "window_size": len(window), "predictions": rows}


def whatsapp_status_payload() -> dict[str, Any]:
    configured = MetaConfig.from_env() is not None
    missing = [name for name in SETUP_ENV_VARS if not os.environ.get(name)]
    return {
        "configured": configured,
        "missing": missing,
        "setup_needed": SETUP_ENV_VARS,
    }


def send_whatsapp_payload(body: dict[str, Any]) -> dict[str, Any]:
    archetype_key = str(body.get("archetype_key") or "")
    dry_run = bool(body.get("dry_run", False))
    use_llm = bool(body.get("use_llm", True))

    cards, _source = _coach_cards("showcase")
    card = next((item for item in cards if item.archetype_key == archetype_key), None)
    if card is None:
        return {
            "sent": False,
            "reason": f"unknown archetype_key: {archetype_key}",
            "setup_needed": SETUP_ENV_VARS,
        }

    return send_card_via_whatsapp(card, use_llm=use_llm, dry_run=dry_run)


def reminders_create_payload(body: dict[str, Any]) -> dict[str, Any]:
    """Schedule a WhatsApp reminder for a coach card, N seconds from now.

    The scheduler thread (started in main) fires it via the same Meta WhatsApp
    path as the manual nudge — so it no-ops cleanly until the token is set.
    """
    from datetime import datetime, timedelta

    from backend import reminders

    key = str(body.get("archetype_key") or "")
    if not key:
        return {"ok": False, "reason": "archetype_key required"}
    delay = float(body.get("fire_in_seconds", 0) or 0)
    fire_at = datetime.now().astimezone() + timedelta(seconds=delay)
    item = reminders.schedule(key, fire_at, str(body.get("headline") or ""))
    return {"ok": True, "reminder": item}


def ac_cutoff_payload(body: dict[str, Any]) -> dict[str, Any]:
    """Publish the AC 'off' command to MQTT for pi_bridge -> ESP32 (IR + relay).

    Degrades honestly: if paho-mqtt isn't installed (dev laptop) or the broker is
    unreachable, returns sent=False with a reason instead of pretending. The
    command shape matches pi_bridge's AC_COMMAND_TOPIC contract.
    """
    from datetime import datetime

    command = {
        "command": "off",
        "reason": str(body.get("reason") or "app_manual"),
        "ts": datetime.now().isoformat(timespec="seconds"),
    }
    broker = os.environ.get("MQTT_BROKER", "127.0.0.1")
    port = int(os.environ.get("MQTT_PORT", "1883"))
    try:
        import paho.mqtt.publish as publish
    except ModuleNotFoundError:
        return {"sent": False, "reason": "paho-mqtt not installed (Pi-only)", "command": command}
    try:
        publish.single("wattseye/ac/command", json.dumps(command),
                       hostname=broker, port=port, qos=1)
    except Exception as exc:  # broker down / network — be honest, don't fake success
        return {"sent": False, "reason": f"MQTT publish failed: {exc}", "command": command}
    return {"sent": True, "topic": "wattseye/ac/command", "command": command}


def ac_rule_get_payload() -> dict[str, Any]:
    """Current AC smart rule (enabled / empty_minutes / mode)."""
    from backend import smart_rules

    return {"ok": True, "rule": smart_rules.load_rule()}


def ac_rule_set_payload(body: dict[str, Any]) -> dict[str, Any]:
    """Persist the AC smart rule. Values are clamped/validated, not rejected.

    The persisted rule is what pi_bridge reads each tick to decide whether an
    empty-room AC episode should auto-cut or just remind.
    """
    from backend import smart_rules

    stored = smart_rules.save_rule(body or {})
    return {"ok": True, "rule": stored}


APPLIANCE_LABELS_PATH = ROOT / "backend" / "_appliance_labels.json"


def appliance_label_payload(body: dict[str, Any]) -> dict[str, Any]:
    """Persist a user label/correction for an appliance signature.

    Appends to a JSON log the future signature-matcher can consume as ground
    truth. kind is 'device' | 'multiple' | 'unsure'; 'device' carries the typed
    appliance name. Degrades honestly: a malformed kind is rejected.
    """
    from datetime import datetime

    appliance = str(body.get("appliance") or "").strip()
    kind = str(body.get("kind") or "").strip()
    if kind not in {"device", "multiple", "unsure"}:
        return {"ok": False, "reason": "invalid kind"}

    record = {
        "appliance": appliance,
        "kind": kind,
        "device": (str(body.get("device")).strip() if body.get("device") else None),
        "ts": datetime.now().isoformat(timespec="seconds"),
    }
    try:
        existing: list[Any] = []
        if APPLIANCE_LABELS_PATH.exists():
            existing = json.loads(APPLIANCE_LABELS_PATH.read_text("utf-8")) or []
        existing.append(record)
        APPLIANCE_LABELS_PATH.write_text(json.dumps(existing, indent=2), "utf-8")
    except Exception as exc:  # disk/permissions — be honest, don't fake success
        return {"ok": False, "reason": f"could not persist: {exc}", "record": record}
    return {"ok": True, "stored": record}


class Handler(BaseHTTPRequestHandler):
    server_version = "WattsEyeApi/0.1"

    def do_OPTIONS(self) -> None:
        self._send_json({"ok": True})

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        path = parsed.path
        query = parse_qs(parsed.query)
        if path == "/api/dashboard":
            self._send_json(dashboard_payload())
        elif path == "/api/coach/cards":
            mode = query.get("mode", ["showcase"])[0]
            self._send_json(coach_cards_payload(mode))
        elif path == "/api/integrations/status":
            self._send_json(integrations_status_payload())
        elif path == "/api/weather":
            city = query.get("city", ["Kuala Lumpur"])[0]
            self._send_json(weather_payload(city))
        elif path == "/api/ml/status":
            self._send_json(ml_status_payload())
        elif path == "/api/report/monthly":
            mode = query.get("mode", ["summary"])[0]
            content, error = monthly_report_bytes(mode)
            if error is not None:
                self._send_json(error, HTTPStatus.SERVICE_UNAVAILABLE)
            else:
                self._send_bytes(
                    content or b"",
                    "application/pdf",
                    f'wattseye_report_{mode}.pdf',
                )
        elif path == "/api/whatsapp/status":
            self._send_json(whatsapp_status_payload())
        elif path == "/api/ac/rule":
            self._send_json(ac_rule_get_payload())
        elif path == "/api/bill":
            self._send_json(bill_payload())
        elif path == "/api/history":
            self._send_json(
                {
                    "days": [
                        {"date": "2026-05-18", "cost_rm": 10.9},
                        {"date": "2026-05-19", "cost_rm": 11.8},
                        {"date": "2026-05-20", "cost_rm": 12.2},
                        {"date": "2026-05-21", "cost_rm": 11.1},
                        {"date": "2026-05-22", "cost_rm": 13.4},
                    ]
                }
            )
        else:
            self._send_json({"error": "not found"}, HTTPStatus.NOT_FOUND)

    def do_POST(self) -> None:
        path = urlparse(self.path).path
        prefix = "/api/coach/cards/"
        suffix = "/action"
        if not path.startswith(prefix) or not path.endswith(suffix):
            if path == "/api/whatsapp/send":
                self._send_json(send_whatsapp_payload(self._read_json()))
                return
            if path == "/api/ml/nilm/infer":
                self._send_json(nilm_infer_payload(self._read_json()))
                return
            if path == "/api/ac/cutoff":
                self._send_json(ac_cutoff_payload(self._read_json()))
                return
            if path == "/api/ac/rule":
                self._send_json(ac_rule_set_payload(self._read_json()))
                return
            if path == "/api/appliance/label":
                self._send_json(appliance_label_payload(self._read_json()))
                return
            if path == "/api/forecast/simulate":
                self._send_json(forecast_simulate_payload(self._read_json()))
                return
            if path == "/api/reminders":
                self._send_json(reminders_create_payload(self._read_json()))
                return
            self._send_json({"error": "not found"}, HTTPStatus.NOT_FOUND)
            return

        archetype_key = path[len(prefix) : -len(suffix)]
        body = self._read_json()
        action = body.get("action")
        if action not in {"do", "remind", "dismiss", "none"}:
            self._send_json({"error": "invalid action"}, HTTPStatus.BAD_REQUEST)
            return

        USER_ACTIONS[archetype_key] = action

        # Persist into the same log the WhatsApp webhook writes, so the
        # feedback_loader pipes in-app dismisses/accepts into the ranker too.
        intent = _APP_ACTION_TO_INTENT.get(action)
        if intent is not None:
            record_user_action(
                archetype_key=archetype_key,
                classification={"intent": intent, "confidence": 1.0, "stage": "app"},
                raw_reply=action,
                from_number="app",
            )
        self._send_json({"ok": True})

    def log_message(self, fmt: str, *args: Any) -> None:
        print(f"{self.address_string()} - {fmt % args}")

    def _read_json(self) -> dict[str, Any]:
        length = int(self.headers.get("Content-Length", "0"))
        if length == 0:
            return {}
        raw = self.rfile.read(length).decode("utf-8")
        data = json.loads(raw)
        return data if isinstance(data, dict) else {}

    def _send_json(
        self,
        payload: Any,
        status: HTTPStatus = HTTPStatus.OK,
    ) -> None:
        raw = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(raw)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.end_headers()
        self.wfile.write(raw)

    def _send_bytes(
        self,
        payload: bytes,
        content_type: str,
        filename: str | None = None,
    ) -> None:
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(payload)))
        self.send_header("Access-Control-Allow-Origin", "*")
        if filename:
            self.send_header(
                "Content-Disposition",
                f'attachment; filename="{filename}"',
            )
        self.end_headers()
        self.wfile.write(payload)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the WattsEye local API.")
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=8080)
    args = parser.parse_args()

    from backend import reminders

    reminders.start(lambda key: send_whatsapp_payload({"archetype_key": key}))

    server = ThreadingHTTPServer((args.host, args.port), Handler)
    print(f"WattsEye API listening on http://{args.host}:{args.port}")
    server.serve_forever()


if __name__ == "__main__":
    main()
