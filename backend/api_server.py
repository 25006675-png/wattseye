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
import secrets
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
    cards_to_json,
    generate_cards,
)
from ML.insights.coach.whatsapp import (  # noqa: E402
    SETUP_ENV_VARS,
    TwilioConfig,
    send_card_via_whatsapp,
)

USER_ACTIONS: dict[str, str] = {}
PHONE_REGISTRY_PATH = ROOT / "backend" / "generated" / "paired_phones.json"
PAIRING_CODE = f"{secrets.randbelow(900000) + 100000}"


def dashboard_payload() -> dict[str, Any]:
    snap = _demo_snapshot()
    return {
        "timestamp": snap.timestamp.isoformat(timespec="seconds"),
        "live_power_w": snap.live_power_w,
        "today_cost_rm": 4.97,
        "projected_bill_rm": 149.18,
        "occupancy_state": snap.occupancy_state,
        "occupancy_since": snap.occupancy_since.isoformat(timespec="seconds"),
        "active_appliances": [
            {
                "name": name,
                "watts": values.get("watts", 0),
                "today_kwh": 8.4 if name == "ac" else 2.6,
                "today_rm": 2.68 if name == "ac" else 0.83,
            }
            for name, values in snap.active_appliances.items()
        ],
    }


def coach_cards_payload() -> list[dict[str, Any]]:
    cards = _coach_cards()
    payload = cards_to_json(cards)
    for card in payload:
        action = USER_ACTIONS.get(card["archetype_key"])
        if action is not None:
            card["user_action"] = action
    return payload


def _coach_cards():
    return generate_cards(_demo_snapshot(), surface_count=2, include_weather=True)


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


def phones_payload() -> dict[str, Any]:
    return {
        "pairing_code": PAIRING_CODE,
        "pairing_code_hint": "Enter this 6-digit code on the new phone.",
        "pairing_url": "/api/phones/pair",
        "phones": _load_paired_phones(),
    }


def pair_phone_payload(body: dict[str, Any]) -> tuple[dict[str, Any], HTTPStatus]:
    if str(body.get("code", "")).strip() != PAIRING_CODE:
        return {"paired": False, "error": "Invalid pairing code"}, HTTPStatus.BAD_REQUEST

    phone_name = str(body.get("phone_name") or "New phone").strip()[:48]
    platform = str(body.get("platform") or "mobile").strip()[:24]
    phone_id = str(body.get("phone_id") or secrets.token_hex(8)).strip()[:48]
    phones = [
        phone for phone in _load_paired_phones()
        if phone.get("phone_id") != phone_id
    ]
    phones.append(
        {
            "phone_id": phone_id,
            "phone_name": phone_name,
            "platform": platform,
            "paired_at": _now_iso(),
            "last_seen": _now_iso(),
        }
    )
    _save_paired_phones(phones)
    payload = phones_payload()
    payload["paired"] = True
    payload["phone_id"] = phone_id
    return payload, HTTPStatus.OK


def _load_paired_phones() -> list[dict[str, Any]]:
    if not PHONE_REGISTRY_PATH.exists():
        return [
            {
                "phone_id": "primary-demo",
                "phone_name": "Primary phone",
                "platform": "mobile",
                "paired_at": "2026-05-24T10:00:00",
                "last_seen": "2026-05-24T10:00:00",
            }
        ]
    try:
        data = json.loads(PHONE_REGISTRY_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    if not isinstance(data, list):
        return []
    return [dict(item) for item in data if isinstance(item, dict)]


def _save_paired_phones(phones: list[dict[str, Any]]) -> None:
    PHONE_REGISTRY_PATH.parent.mkdir(parents=True, exist_ok=True)
    PHONE_REGISTRY_PATH.write_text(
        json.dumps(phones, indent=2),
        encoding="utf-8",
    )


def _now_iso() -> str:
    from datetime import datetime

    return datetime.now().isoformat(timespec="seconds")


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
    configured = TwilioConfig.from_env() is not None
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

    cards = _coach_cards()
    card = next((item for item in cards if item.archetype_key == archetype_key), None)
    if card is None:
        return {
            "sent": False,
            "reason": f"unknown archetype_key: {archetype_key}",
            "setup_needed": SETUP_ENV_VARS,
        }

    return send_card_via_whatsapp(card, use_llm=use_llm, dry_run=dry_run)


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
            self._send_json(coach_cards_payload())
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
        elif path == "/api/phones":
            self._send_json(phones_payload())
        elif path == "/api/bill":
            self._send_json(
                {
                    "projected_total_rm": 149.18,
                    "projected_kwh": 460,
                    "effective_sen_per_kwh": 32.43,
                    "tou_projected_total_rm": 143.80,
                }
            )
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
            if path == "/api/phones/pair":
                payload, status = pair_phone_payload(self._read_json())
                self._send_json(payload, status)
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

    server = ThreadingHTTPServer((args.host, args.port), Handler)
    print(f"WattsEye API listening on http://{args.host}:{args.port}")
    server.serve_forever()


if __name__ == "__main__":
    main()
