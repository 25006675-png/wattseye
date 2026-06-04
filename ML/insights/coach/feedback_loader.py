"""Feedback loader — closes the Coach engine learn -> surface loop.

The webhook writes `_user_actions.json` whenever the user replies (accept /
dismiss / snooze). The WhatsApp pusher writes `_whatsapp_sent.json` whenever
a card is sent. This module bridges both logs back into a HomeSnapshot so the
ranker's dismiss_decay and novelty terms actually fire.

Without this bridge, both fields stay empty dicts and ranker.py collapses to
score = sqrt(impact) * confidence * severity — i.e. no learning effect.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime
from pathlib import Path

from .situations import HomeSnapshot

log = logging.getLogger("wattseye.coach.feedback")

_HERE = Path(__file__).resolve().parent
USER_ACTIONS_PATH = _HERE / "_user_actions.json"
WHATSAPP_SENT_PATH = _HERE / "_whatsapp_sent.json"


def _read_json(path: Path):
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text())
    except (OSError, json.JSONDecodeError) as e:
        log.warning("Could not read %s: %s", path.name, e)
        return None


def load_dismissed_archetypes(path: Path = USER_ACTIONS_PATH) -> dict[str, datetime]:
    """Most-recent dismiss timestamp per archetype_key, read from the webhook log."""
    data = _read_json(path)
    if not isinstance(data, list):
        return {}
    out: dict[str, datetime] = {}
    for entry in data:
        if not isinstance(entry, dict):
            continue
        if entry.get("intent") != "dismiss":
            continue
        key = entry.get("archetype_key")
        ts_raw = entry.get("timestamp")
        if not isinstance(key, str) or not isinstance(ts_raw, str):
            continue
        try:
            ts = datetime.fromisoformat(ts_raw)
        except ValueError:
            continue
        prev = out.get(key)
        if prev is None or ts > prev:
            out[key] = ts
    return out


def load_recently_shown(path: Path = WHATSAPP_SENT_PATH) -> dict[str, datetime]:
    """Last push timestamp per archetype_key, read from the WhatsApp sent log."""
    data = _read_json(path)
    if not isinstance(data, dict):
        return {}
    out: dict[str, datetime] = {}
    for key, ts_raw in data.items():
        if key == "__last_any__" or not isinstance(ts_raw, str):
            continue
        try:
            out[key] = datetime.fromisoformat(ts_raw)
        except ValueError:
            continue
    return out


def apply_feedback_to_snapshot(snap: HomeSnapshot) -> HomeSnapshot:
    """Populate dismiss/show history on snap from disk. Mutates and returns.

    Only fills fields the caller left empty, so tests and demo fixtures that
    pre-populate either dict keep full control.
    """
    if not snap.dismissed_archetypes:
        snap.dismissed_archetypes = load_dismissed_archetypes()
    if not snap.recently_shown:
        snap.recently_shown = load_recently_shown()
    return snap


if __name__ == "__main__":
    d = load_dismissed_archetypes()
    s = load_recently_shown()
    print(f"Dismissed archetypes ({len(d)}):")
    for k, v in sorted(d.items()):
        print(f"  {k:24s}  last dismissed {v.isoformat(timespec='minutes')}")
    print(f"\nRecently shown ({len(s)}):")
    for k, v in sorted(s.items()):
        print(f"  {k:24s}  last shown     {v.isoformat(timespec='minutes')}")
