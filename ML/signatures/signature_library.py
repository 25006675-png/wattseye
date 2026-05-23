"""Signature library for user-labeled appliances beyond the NILM model set.

When the residual power channel (everything except AC and the 5 NILM-modeled
appliances) shows a power-on event, this module:

1. Extracts a feature vector — peak_w, mean_w, duration_min, hour_of_day, dayofweek.
2. Looks for a match in the household's signature library (SQLite store).
3. If a match is found within tolerance, returns the user's label
   (e.g. "rice cooker", "TV").
4. If no match, returns "unknown" and offers the event for user labelling.

After the user confirms a label once via the UI, that signature becomes a
first-class appliance for routine, history, anomaly, and bill calculation —
the same way NILM appliances are. The library grows as the user labels.

This is intentionally NOT a trained ML model. It is a small few-shot matcher
using simple Euclidean distance in feature space. New appliances can be added
in one tap, which is the whole point of the architecture.
"""

from __future__ import annotations

import argparse
import math
import sqlite3
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Iterable

DEFAULT_LIB = Path(__file__).resolve().parent / "signature_library.sqlite"
DEFAULT_HISTORY_DB = Path(__file__).resolve().parents[1] / "sensing" / "synthetic_history.sqlite"

UNKNOWN_ON_THRESHOLD_W = 60   # residual events below this are noise
MIN_EVENT_DURATION_MIN = 2
MATCH_DISTANCE_THRESHOLD = 0.40  # Euclidean distance in normalised feature space


@dataclass(frozen=True)
class EventFeatures:
    peak_w: float
    mean_w: float
    duration_min: float
    hour_of_day: int
    day_of_week: int


@dataclass(frozen=True)
class Signature:
    signature_id: int
    label: str
    peak_w: float
    mean_w: float
    duration_min: float
    typical_hours: str  # comma-separated for SQLite simplicity
    confirmed_count: int
    created_at: str

    def distance_to(self, ev: EventFeatures) -> float:
        # Normalise each feature so they contribute roughly equally
        df_peak = (ev.peak_w - self.peak_w) / max(self.peak_w, 1.0)
        df_dur = (ev.duration_min - self.duration_min) / max(self.duration_min, 1.0)
        typical = {int(h) for h in self.typical_hours.split(",") if h}
        df_hour = 0.0 if ev.hour_of_day in typical else 0.5
        return math.sqrt(df_peak ** 2 + df_dur ** 2 + df_hour ** 2)


# --- SQLite store -----------------------------------------------------------


def _ensure_schema(lib_path: Path) -> None:
    conn = sqlite3.connect(lib_path)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS signatures (
            signature_id INTEGER PRIMARY KEY AUTOINCREMENT,
            label TEXT NOT NULL,
            peak_w REAL NOT NULL,
            mean_w REAL NOT NULL,
            duration_min REAL NOT NULL,
            typical_hours TEXT NOT NULL,
            confirmed_count INTEGER NOT NULL DEFAULT 1,
            created_at TEXT NOT NULL
        )
    """)
    conn.commit()
    conn.close()


def _load_all(lib_path: Path) -> list[Signature]:
    _ensure_schema(lib_path)
    conn = sqlite3.connect(lib_path)
    rows = conn.execute(
        "SELECT signature_id, label, peak_w, mean_w, duration_min, "
        "typical_hours, confirmed_count, created_at FROM signatures"
    ).fetchall()
    conn.close()
    return [Signature(*row) for row in rows]


def add_signature(label: str, peak_w: float, mean_w: float, duration_min: float,
                  typical_hours: Iterable[int], lib_path: Path = DEFAULT_LIB) -> int:
    _ensure_schema(lib_path)
    conn = sqlite3.connect(lib_path)
    cur = conn.execute(
        "INSERT INTO signatures (label, peak_w, mean_w, duration_min, typical_hours, created_at) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (label, peak_w, mean_w, duration_min,
         ",".join(str(int(h)) for h in typical_hours),
         datetime.now().isoformat(timespec="seconds")),
    )
    sig_id = cur.lastrowid
    conn.commit()
    conn.close()
    return sig_id


def confirm_signature(sig_id: int, lib_path: Path = DEFAULT_LIB) -> None:
    conn = sqlite3.connect(lib_path)
    conn.execute(
        "UPDATE signatures SET confirmed_count = confirmed_count + 1 WHERE signature_id = ?",
        (sig_id,),
    )
    conn.commit()
    conn.close()


# --- Event detection on residual signal ------------------------------------


def detect_unknown_events(history_db: Path = DEFAULT_HISTORY_DB,
                          start: datetime | None = None,
                          end: datetime | None = None) -> list[tuple[datetime, EventFeatures]]:
    """Scan the *effective* residual signal — what the live system would see
    after subtracting AC (dedicated clamp) and the 5 NILM-modeled appliances.

    In the synthetic data, rice_cooker_w, tv_w, microwave_w, computer_w, fan_w
    are stored as separate ground-truth columns for evaluation, but in production
    they would all be lumped into the residual because there is no NILM model
    for them yet. We reconstruct that production view here.
    """
    conn = sqlite3.connect(history_db)
    q = (
        "SELECT timestamp, "
        "unknown_w + rice_cooker_w + tv_w + microwave_w + computer_w + fan_w "
        "AS residual_w FROM readings"
    )
    params: list = []
    if start and end:
        q += " WHERE timestamp BETWEEN ? AND ?"
        params = [start.isoformat(), end.isoformat()]
    q += " ORDER BY timestamp"
    rows = conn.execute(q, params).fetchall()
    conn.close()

    events: list[tuple[datetime, EventFeatures]] = []
    active = False
    start_ts: datetime | None = None
    peak = 0.0
    total = 0.0
    count = 0
    for ts_str, w in rows:
        ts = datetime.fromisoformat(ts_str)
        w = float(w)
        if w >= UNKNOWN_ON_THRESHOLD_W:
            if not active:
                active = True
                start_ts = ts
                peak = w
                total = w
                count = 1
            else:
                peak = max(peak, w)
                total += w
                count += 1
        elif active:
            assert start_ts is not None
            duration = (ts - start_ts).total_seconds() / 60
            if duration >= MIN_EVENT_DURATION_MIN:
                features = EventFeatures(
                    peak_w=peak,
                    mean_w=total / count if count else 0,
                    duration_min=duration,
                    hour_of_day=start_ts.hour,
                    day_of_week=start_ts.weekday(),
                )
                events.append((start_ts, features))
            active = False
            start_ts = None
    return events


# --- Matching ---------------------------------------------------------------


def match_event(ev: EventFeatures, lib_path: Path = DEFAULT_LIB) -> dict:
    library = _load_all(lib_path)
    if not library:
        return {"matched": False, "label": "unknown", "candidates": []}

    distances = [(sig, sig.distance_to(ev)) for sig in library]
    distances.sort(key=lambda x: x[1])
    best, best_dist = distances[0]
    matched = best_dist <= MATCH_DISTANCE_THRESHOLD
    return {
        "matched": matched,
        "label": best.label if matched else "unknown",
        "matched_signature_id": best.signature_id if matched else None,
        "distance": round(best_dist, 4),
        "candidates": [
            {"label": s.label, "distance": round(d, 4)} for s, d in distances[:3]
        ],
    }


# --- Auto-cluster proposal: group unlabeled events for the user ------------


def propose_clusters(events: list[EventFeatures], k: int = 5) -> list[dict]:
    """Group unlabeled events into k clusters by (peak_w, duration_min) so the
    UI can present one labelling prompt per cluster instead of per event."""
    if not events or k < 1:
        return []
    from sklearn.cluster import KMeans
    import numpy as np

    X = np.array([[e.peak_w, e.duration_min] for e in events])
    k = min(k, len(events))
    km = KMeans(n_clusters=k, random_state=42, n_init=10).fit(X)
    proposals: list[dict] = []
    for cid in range(k):
        members = [events[i] for i in range(len(events)) if km.labels_[i] == cid]
        if not members:
            continue
        peak_mean = float(sum(e.peak_w for e in members) / len(members))
        dur_mean = float(sum(e.duration_min for e in members) / len(members))
        hours = sorted({e.hour_of_day for e in members})
        proposals.append({
            "proposal_id": cid,
            "event_count": len(members),
            "peak_w_avg": round(peak_mean, 0),
            "duration_min_avg": round(dur_mean, 1),
            "typical_hours": hours,
            "example_label_guesses": _guess_labels(peak_mean, dur_mean, hours),
        })
    proposals.sort(key=lambda p: p["event_count"], reverse=True)
    return proposals


def _guess_labels(peak_w: float, dur_min: float, hours: list[int]) -> list[str]:
    guesses: list[str] = []
    dinner_window = any(17 <= h <= 19 for h in hours)
    evening = any(19 <= h <= 23 for h in hours)
    if 500 < peak_w < 800 and 25 < dur_min < 55 and dinner_window:
        guesses.append("rice cooker")
    if 70 < peak_w < 150 and dur_min > 60 and evening:
        guesses.append("TV")
    if 900 < peak_w < 1400 and dur_min < 5:
        guesses.append("microwave")
    if 100 < peak_w < 250 and dur_min > 120:
        guesses.append("computer setup")
    if 50 < peak_w < 120 and any(h >= 19 or h < 7 for h in hours):
        guesses.append("ceiling fan")
    if not guesses:
        guesses.append("(no confident guess)")
    return guesses


# --- CLI -------------------------------------------------------------------


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--scan", action="store_true", help="Detect unknown events in history.")
    parser.add_argument("--propose", action="store_true",
                        help="Cluster unknown events and propose labels for the user.")
    parser.add_argument("--match", nargs=5, metavar=("PEAK_W", "MEAN_W", "DUR_MIN", "HOUR", "DOW"),
                        help="Test match against existing library.")
    parser.add_argument("--add", nargs="+",
                        help="Add a labeled signature: LABEL PEAK_W MEAN_W DUR_MIN H1,H2,...")
    parser.add_argument("--list", action="store_true", help="List all stored signatures.")
    parser.add_argument("--history-db", type=Path, default=DEFAULT_HISTORY_DB)
    parser.add_argument("--lib", type=Path, default=DEFAULT_LIB)
    args = parser.parse_args()

    if args.list:
        for sig in _load_all(args.lib):
            print(sig)
        return

    if args.add:
        if len(args.add) < 5:
            raise SystemExit("Usage: --add LABEL PEAK_W MEAN_W DUR_MIN H1,H2,...")
        label, peak, mean, dur, hours_csv = args.add[0], float(args.add[1]), float(args.add[2]), float(args.add[3]), args.add[4]
        hours = [int(h) for h in hours_csv.split(",")]
        sig_id = add_signature(label, peak, mean, dur, hours, args.lib)
        print(f"Added signature #{sig_id}: {label}")
        return

    if args.match:
        peak, mean, dur, hr, dow = (float(args.match[0]), float(args.match[1]),
                                     float(args.match[2]), int(args.match[3]), int(args.match[4]))
        ev = EventFeatures(peak_w=peak, mean_w=mean, duration_min=dur,
                           hour_of_day=hr, day_of_week=dow)
        print(match_event(ev, args.lib))
        return

    if args.propose:
        events = detect_unknown_events(args.history_db)
        features = [ev for _, ev in events]
        print(f"Detected {len(events)} unknown-channel events in {args.history_db.name}")
        proposals = propose_clusters(features, k=6)
        for p in proposals:
            print(f"\nProposal #{p['proposal_id']}: {p['event_count']} events")
            print(f"  Peak {p['peak_w_avg']}W, ~{p['duration_min_avg']}min, hours {p['typical_hours']}")
            print(f"  Likely: {', '.join(p['example_label_guesses'])}")
        return

    if args.scan or True:
        events = detect_unknown_events(args.history_db)
        print(f"Detected {len(events)} unknown-channel events.")
        for ts, ev in events[:10]:
            print(f"  {ts:%Y-%m-%d %a %H:%M}  peak={ev.peak_w:>5.0f}W  dur={ev.duration_min:>4.0f}min")


if __name__ == "__main__":
    main()
