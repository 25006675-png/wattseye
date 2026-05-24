"""Local WattsEye API bridge for the Flutter app.

Run from the repo root:

    python backend/api_server.py

The production Pi backend can replace this with FastAPI later, as long as it
keeps the same JSON contract documented in extra_info/FRONTEND_BRIEF.md.
"""

from __future__ import annotations

import argparse
import json
import os
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import sys
from typing import Any
from urllib.parse import urlparse

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
    cards = generate_cards(_demo_snapshot(), surface_count=2, include_weather=False)
    payload = cards_to_json(cards)
    for card in payload:
        action = USER_ACTIONS.get(card["archetype_key"])
        if action is not None:
            card["user_action"] = action
    return payload


def _coach_cards():
    return generate_cards(_demo_snapshot(), surface_count=2, include_weather=False)


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
        path = urlparse(self.path).path
        if path == "/api/dashboard":
            self._send_json(dashboard_payload())
        elif path == "/api/coach/cards":
            self._send_json(coach_cards_payload())
        elif path == "/api/whatsapp/status":
            self._send_json(whatsapp_status_payload())
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
