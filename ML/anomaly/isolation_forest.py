"""Isolation Forest anomaly detection on per-appliance events.

Pipeline:
1. Extract appliance "events" from synthetic_history.sqlite — each contiguous
   stretch where appliance power is above a small threshold is one event.
2. Featurize each event: peak_w, duration_min, hour_of_day, dayofweek, appliance.
3. Fit IsolationForest on the normal events (contamination=0.05).
4. Save model. At inference, score new events; high score = anomaly.

The model captures patterns like "kettle at 3 AM" (unusual hour), "fridge cycle
of 90 minutes" (unusual duration), or "hair dryer at 1500W" (unusual peak).
"""

from __future__ import annotations

import argparse
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path

import joblib
import numpy as np
from sklearn.ensemble import IsolationForest

DEFAULT_DB = Path(__file__).resolve().parents[1] / "sensing" / "synthetic_history.sqlite"
MODEL_PATH = Path(__file__).resolve().parent / "isolation_forest.joblib"

UKDALE_CACHE = Path("C:/Users/user/Documents/technothon/data/cache")
UKDALE_START = datetime(2012, 11, 9, 9, 0)
UKDALE_SAMPLE_SECONDS = 6
UKDALE_APPLIANCES = ["kettle", "fridge", "hair_dryer", "washing_machine", "microwave"]

# Per-appliance thresholds: minimum watts to count as "on"
ON_THRESHOLDS = {
    "kettle": 200,
    "fridge": 50,
    "hair_dryer": 300,
    "iron": 150,
    "washing_machine": 100,
    "rice_cooker": 200,
    "ac": 200,
    "microwave": 200,
}

# Mapping of CSV column -> appliance label
APPLIANCE_COLS = {
    "kettle_w": "kettle",
    "fridge_w": "fridge",
    "hair_dryer_w": "hair_dryer",
    "iron_w": "iron",
    "washing_machine_w": "washing_machine",
    "rice_cooker_w": "rice_cooker",
    "ac_w": "ac",
    "microwave_w": "microwave",
}

APPLIANCE_IDS = {name: i for i, name in enumerate(sorted(set(APPLIANCE_COLS.values())))}


@dataclass(frozen=True)
class ApplianceEvent:
    appliance: str
    start: datetime
    end: datetime
    peak_w: float
    mean_w: float
    duration_min: float

    @property
    def features(self) -> np.ndarray:
        return np.array([
            APPLIANCE_IDS[self.appliance],
            self.peak_w,
            self.duration_min,
            self.start.hour,
            self.start.weekday(),
        ], dtype=np.float64)


def _extract_events_ukdale(cache_dir: Path = UKDALE_CACHE,
                            max_events_per_appliance: int = 5000) -> list[ApplianceEvent]:
    """Detect appliance events directly from the UK-DALE 6-second npz cache.

    For each appliance we scan the `app` array for contiguous on-stretches
    above the threshold. Sub-sampling the final list keeps the model size
    manageable while preserving the distribution.
    """
    events: list[ApplianceEvent] = []
    for appliance in UKDALE_APPLIANCES:
        cache_file = cache_dir / f"house1_{appliance}.npz"
        if not cache_file.exists():
            continue
        threshold = ON_THRESHOLDS[appliance]
        app_data = np.load(cache_file)["app"].astype(np.float32)
        above = app_data > threshold
        # Find transitions: 0->1 = start, 1->0 = end
        padded = np.concatenate([[False], above, [False]])
        diff = np.diff(padded.astype(np.int8))
        starts = np.where(diff == 1)[0]
        ends = np.where(diff == -1)[0]

        app_events: list[ApplianceEvent] = []
        for s, e in zip(starts, ends):
            duration_samples = e - s
            duration_min = duration_samples * UKDALE_SAMPLE_SECONDS / 60
            if duration_min < 1:
                continue
            segment = app_data[s:e]
            start_ts = UKDALE_START + timedelta(seconds=int(s) * UKDALE_SAMPLE_SECONDS)
            app_events.append(ApplianceEvent(
                appliance=appliance,
                start=start_ts,
                end=UKDALE_START + timedelta(seconds=int(e) * UKDALE_SAMPLE_SECONDS),
                peak_w=float(segment.max()),
                mean_w=float(segment.mean()),
                duration_min=float(duration_min),
            ))
        # Cap per appliance to keep distribution balanced
        if len(app_events) > max_events_per_appliance:
            stride = len(app_events) // max_events_per_appliance
            app_events = app_events[::stride][:max_events_per_appliance]
        events.extend(app_events)
        print(f"  {appliance:<18s} {len(app_events):>5,} events extracted")
    return events


def _extract_events(db_path: Path) -> list[ApplianceEvent]:
    conn = sqlite3.connect(db_path)
    cols = ", ".join(["timestamp"] + list(APPLIANCE_COLS.keys()))
    rows = conn.execute(f"SELECT {cols} FROM readings ORDER BY timestamp").fetchall()
    conn.close()

    events: list[ApplianceEvent] = []
    for col_idx, (col, appliance) in enumerate(APPLIANCE_COLS.items(), start=1):
        threshold = ON_THRESHOLDS[appliance]
        active = False
        start: datetime | None = None
        peak: float = 0.0
        total: float = 0.0
        count: int = 0
        for row in rows:
            ts = datetime.fromisoformat(row[0])
            w = float(row[col_idx])
            if w >= threshold:
                if not active:
                    active = True
                    start = ts
                    peak = w
                    total = w
                    count = 1
                else:
                    peak = max(peak, w)
                    total += w
                    count += 1
            elif active:
                assert start is not None
                duration = (ts - start).total_seconds() / 60
                if duration >= 1:
                    events.append(ApplianceEvent(
                        appliance=appliance,
                        start=start,
                        end=ts,
                        peak_w=peak,
                        mean_w=total / count if count else 0,
                        duration_min=duration,
                    ))
                active = False
                start = None
    return events


def train(db_path: Path = DEFAULT_DB, source: str = "ukdale") -> IsolationForest:
    if source == "ukdale" and (UKDALE_CACHE / "house1_kettle.npz").exists():
        print("Extracting events from UK-DALE house 1 cache:")
        events = _extract_events_ukdale(UKDALE_CACHE)
    else:
        print(f"Extracting events from synthetic history at {db_path}")
        events = _extract_events(db_path)
    if not events:
        raise RuntimeError("No appliance events extracted from history.")
    X = np.stack([e.features for e in events])
    model = IsolationForest(
        n_estimators=200,
        contamination=0.05,
        random_state=42,
    ).fit(X)
    trained_classes = sorted({e.appliance for e in events})
    joblib.dump({
        "model": model,
        "appliance_ids": APPLIANCE_IDS,
        "trained_classes": trained_classes,
        "source": source,
    }, MODEL_PATH)

    # Summary
    by_app: dict[str, int] = {}
    for e in events:
        by_app[e.appliance] = by_app.get(e.appliance, 0) + 1
    print(f"Trained Isolation Forest on {len(events)} events from {len(by_app)} appliance classes:")
    for name in sorted(by_app):
        print(f"  {name:<18s} {by_app[name]} events")

    # Top-10 most anomalous events
    scores = -model.score_samples(X)
    top = np.argsort(scores)[-10:][::-1]
    print("\nTop-10 most anomalous events in the training set:")
    for idx in top:
        e = events[idx]
        print(f"  {e.appliance:<16s} {e.start.strftime('%Y-%m-%d %a %H:%M')}  "
              f"peak={e.peak_w:>6.0f}W dur={e.duration_min:>4.0f}min score={scores[idx]:.3f}")

    print(f"\nSaved -> {MODEL_PATH}")
    return model


def anomaly_score(appliance: str, peak_w: float, duration_min: float,
                  hour_of_day: int, day_of_week: int) -> dict:
    if not MODEL_PATH.exists():
        raise FileNotFoundError(f"Model not found at {MODEL_PATH}. Run --train first.")
    payload = joblib.load(MODEL_PATH)
    model: IsolationForest = payload["model"]
    ids = payload["appliance_ids"]
    trained = payload.get("trained_classes", list(ids.keys()))
    if appliance not in ids:
        raise ValueError(f"Unknown appliance {appliance!r}. Known: {sorted(ids)}")
    if appliance not in trained:
        raise ValueError(
            f"No training data for {appliance!r} in this model "
            f"(trained on {trained}). Cannot score reliably."
        )
    features = np.array([[ids[appliance], peak_w, duration_min, hour_of_day, day_of_week]],
                        dtype=np.float64)
    score = float(-model.score_samples(features)[0])
    is_anomaly = bool(model.predict(features)[0] == -1)
    return {"score": round(score, 4), "is_anomaly": is_anomaly}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--train", action="store_true")
    parser.add_argument("--score", nargs=5, metavar=("APPLIANCE", "PEAK_W", "DURATION_MIN", "HOUR", "DAYOFWEEK"))
    parser.add_argument("--db", type=Path, default=DEFAULT_DB)
    parser.add_argument("--source", choices=["ukdale", "synthetic"], default="ukdale")
    args = parser.parse_args()

    if args.train or not args.score:
        train(args.db, source=args.source)
    if args.score:
        appliance, peak, dur, hr, dow = args.score
        result = anomaly_score(appliance, float(peak), float(dur), int(hr), int(dow))
        print(f"{appliance} peak={peak}W dur={dur}min hr={hr} dow={dow} -> {result}")


if __name__ == "__main__":
    main()
