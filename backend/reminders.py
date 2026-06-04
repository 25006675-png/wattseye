"""Tiny reminder scheduler: persist pending reminders, fire a callback when due.

Demo-grade — a daemon thread polls a JSON file every few seconds and invokes a
send callback (WhatsApp) for any reminder whose time has come. On the Pi (runs
24/7) this is the right home for it; it is not built for HA / multi-process.
"""

from __future__ import annotations

import json
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

_STORE = Path(__file__).resolve().parent / "reminders.json"
_LOCK = threading.Lock()


def _load() -> list[dict[str, Any]]:
    if not _STORE.exists():
        return []
    try:
        return json.loads(_STORE.read_text("utf-8"))
    except (json.JSONDecodeError, OSError):
        return []


def _save(items: list[dict[str, Any]]) -> None:
    _STORE.write_text(json.dumps(items, indent=2), "utf-8")


def schedule(archetype_key: str, fire_at: datetime, headline: str = "") -> dict[str, Any]:
    """Persist a pending reminder. fire_at may be naive (local) or tz-aware."""
    item = {
        "id": f"{archetype_key}-{int(fire_at.timestamp())}",
        "archetype_key": archetype_key,
        "headline": headline,
        "fire_at": fire_at.astimezone(timezone.utc).isoformat(),
        "status": "pending",
    }
    with _LOCK:
        items = _load()
        items.append(item)
        _save(items)
    return item


def list_all() -> list[dict[str, Any]]:
    with _LOCK:
        return _load()


def start(send: Callable[[str], Any], poll_seconds: float = 5.0) -> threading.Thread:
    """Start the daemon scheduler. `send(archetype_key)` should return the send
    result dict; a falsy `sent` marks the reminder errored (not lost)."""

    def loop() -> None:
        while True:
            now = datetime.now(timezone.utc)
            with _LOCK:
                due = [
                    i
                    for i in _load()
                    if i["status"] == "pending"
                    and datetime.fromisoformat(i["fire_at"]) <= now
                ]
            results: dict[str, tuple[str, str | None]] = {}
            for item in due:
                try:
                    res = send(item["archetype_key"])
                    if isinstance(res, dict) and res.get("sent") is False:
                        results[item["id"]] = ("error", str(res.get("reason") or "send failed"))
                    else:
                        results[item["id"]] = ("sent", None)
                except Exception as exc:  # noqa: BLE001 — never let one send kill the loop
                    results[item["id"]] = ("error", str(exc))
            if results:
                with _LOCK:
                    items = _load()
                    for it in items:
                        if it["id"] in results:
                            status, err = results[it["id"]]
                            it["status"] = status
                            if err:
                                it["error"] = err
                    _save(items)
            time.sleep(poll_seconds)

    thread = threading.Thread(target=loop, daemon=True, name="reminder-scheduler")
    thread.start()
    return thread
