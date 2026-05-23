"""K-Means clustering of household activity into daily phases.

Discovers ~4 natural phases per day (e.g. sleep / morning / work / evening)
from the synthetic history. The existing `routine_engine.py` then fills in
per-phase appliance statistics.

Pipeline:
1. Read synthetic_history.sqlite (or any DB with the same schema).
2. Aggregate readings by (day_of_week, hour) -> mean total_w, occupancy fraction.
3. Featurize each (day_of_week, hour) point.
4. Fit KMeans(k=4) on the features.
5. Label clusters by inspecting cluster centroids (lowest activity = sleep, etc.).
6. Save the trained model + label map as kmeans_phases.joblib.

Run:
    python ML/routine/kmeans_phases.py --train
    python ML/routine/kmeans_phases.py --classify "2026-05-20 14:20"
"""

from __future__ import annotations

import argparse
import math
import sqlite3
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import joblib
import numpy as np
from sklearn.cluster import KMeans

DEFAULT_DB = Path(__file__).resolve().parents[1] / "sensing" / "synthetic_history.sqlite"
MODEL_PATH = Path(__file__).resolve().parent / "kmeans_phases.joblib"

K = 4


@dataclass(frozen=True)
class PhaseModel:
    kmeans: KMeans
    label_map: dict[int, str]
    feature_means: np.ndarray
    feature_stds: np.ndarray

    def classify(self, hour: int, day_of_week: int, recent_total_w: float, recent_occupied: float) -> dict:
        features = _featurize(hour, day_of_week, recent_total_w, recent_occupied)
        scaled = (features - self.feature_means) / self.feature_stds
        cluster_id = int(self.kmeans.predict(scaled.reshape(1, -1))[0])
        return {
            "phase": self.label_map[cluster_id],
            "cluster_id": cluster_id,
        }


def _featurize(hour: int, day_of_week: int, total_w: float, occupied_frac: float) -> np.ndarray:
    # Cyclic encoding for hour-of-day so 23 and 0 are close.
    hour_sin = math.sin(2 * math.pi * hour / 24)
    hour_cos = math.cos(2 * math.pi * hour / 24)
    is_weekend = 1.0 if day_of_week >= 5 else 0.0
    return np.array([hour_sin, hour_cos, is_weekend, total_w, occupied_frac], dtype=np.float64)


def _load_aggregated(db_path: Path) -> tuple[np.ndarray, list[tuple[int, int]]]:
    conn = sqlite3.connect(db_path)
    rows = conn.execute("SELECT timestamp, total_w, occupied FROM readings").fetchall()
    conn.close()

    buckets: dict[tuple[int, int], list[tuple[float, int]]] = {}
    for ts_str, total_w, occupied in rows:
        ts = datetime.fromisoformat(ts_str)
        key = (ts.weekday(), ts.hour)
        buckets.setdefault(key, []).append((total_w, occupied))

    keys = sorted(buckets.keys())
    features = []
    for (dow, hour) in keys:
        samples = buckets[(dow, hour)]
        mean_total = float(np.mean([s[0] for s in samples]))
        occ_frac = float(np.mean([s[1] for s in samples]))
        features.append(_featurize(hour, dow, mean_total, occ_frac))

    return np.array(features), keys


def _label_clusters(kmeans: KMeans, raw_features: np.ndarray, keys: list[tuple[int, int]]) -> dict[int, str]:
    """Assign human-readable names to cluster IDs by inspecting which hours
    landed in each cluster (circular-mean hour) and the cluster's mean activity.

    Phase names follow a simple time-of-day partition rather than activity rank,
    because "low activity" can legitimately mean either sleep (night) or empty
    home (weekday daytime) and we want both to be distinguishable.
    """
    labels = kmeans.labels_
    summaries: dict[int, tuple[float, float, float]] = {}
    for cluster_id in range(kmeans.n_clusters):
        mask = labels == cluster_id
        cluster_keys = [keys[i] for i in range(len(keys)) if mask[i]]
        if not cluster_keys:
            summaries[cluster_id] = (12.0, 0.0, 0.0)
            continue
        hours = [h for (_, h) in cluster_keys]
        hours_rad = np.array([h * 2 * math.pi / 24 for h in hours])
        circ_mean = math.atan2(float(np.mean(np.sin(hours_rad))), float(np.mean(np.cos(hours_rad))))
        mean_hour = (circ_mean * 24 / (2 * math.pi)) % 24
        cluster_total = float(np.mean(raw_features[mask, 3]))
        cluster_occ = float(np.mean(raw_features[mask, 4]))
        summaries[cluster_id] = (mean_hour, cluster_total, cluster_occ)

    def label_for(hour: float, occ: float) -> str:
        if hour < 6 or hour >= 23:
            return "sleep"
        if hour < 11:
            return "morning"
        if hour < 17:
            return "midday_away" if occ < 0.4 else "midday_home"
        return "evening"

    label_map: dict[int, str] = {}
    used: dict[str, int] = {}
    for cluster_id, (mean_hour, _, occ) in summaries.items():
        base = label_for(mean_hour, occ)
        if base in used:
            base = f"{base}_{used[base] + 1}"
        used[base] = used.get(base.rstrip("_0123456789"), 0) + 1
        label_map[cluster_id] = base
    return label_map


def train(db_path: Path = DEFAULT_DB, k: int = K) -> dict:
    raw_features, keys = _load_aggregated(db_path)
    means = raw_features.mean(axis=0)
    stds = raw_features.std(axis=0)
    stds = np.where(stds == 0, 1.0, stds)
    scaled = (raw_features - means) / stds

    kmeans = KMeans(n_clusters=k, random_state=42, n_init=10).fit(scaled)
    label_map = _label_clusters(kmeans, raw_features, keys)
    payload = {
        "kmeans": kmeans,
        "label_map": label_map,
        "feature_means": means,
        "feature_stds": stds,
    }
    joblib.dump(payload, MODEL_PATH)
    print(f"Trained on {len(raw_features)} (day_of_week, hour) buckets")
    print(f"Cluster labels: {label_map}")
    _print_phase_assignments(label_map, keys, kmeans.labels_)
    print(f"\nSaved model -> {MODEL_PATH}")
    return payload


def _print_phase_assignments(label_map: dict[int, str], keys, cluster_ids) -> None:
    day_names = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    print("\nDay/Hour assignment (M=morning, W=work, E=evening, S=sleep):")
    code = {"morning": "M", "midday_away": "A", "midday_home": "H", "evening": "E", "sleep": "S"}
    rows = {dow: ["?"] * 24 for dow in range(7)}
    for (dow, hour), cid in zip(keys, cluster_ids):
        rows[dow][hour] = code.get(label_map.get(int(cid), ""), "?")
    print("       " + " ".join(f"{h:>2d}" for h in range(24)))
    for dow in range(7):
        print(f"  {day_names[dow]}  " + "  ".join(rows[dow]))


def classify(ts: datetime, db_path: Path = DEFAULT_DB) -> dict:
    if not MODEL_PATH.exists():
        raise FileNotFoundError(f"Model not found at {MODEL_PATH}. Run --train first.")
    payload = joblib.load(MODEL_PATH)

    conn = sqlite3.connect(db_path)
    rows = conn.execute(
        "SELECT total_w, occupied FROM readings WHERE timestamp LIKE ?",
        (f"%T{ts.hour:02d}:%",),
    ).fetchall()
    conn.close()
    if rows:
        recent_total = float(np.mean([r[0] for r in rows]))
        recent_occ = float(np.mean([r[1] for r in rows]))
    else:
        recent_total = 200.0
        recent_occ = 0.5

    features = _featurize(ts.hour, ts.weekday(), recent_total, recent_occ)
    scaled = (features - payload["feature_means"]) / payload["feature_stds"]
    cluster_id = int(payload["kmeans"].predict(scaled.reshape(1, -1))[0])
    return {
        "phase": payload["label_map"][cluster_id],
        "cluster_id": cluster_id,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--train", action="store_true")
    parser.add_argument("--classify", type=str, help="Timestamp like '2026-05-20 14:20'")
    parser.add_argument("--db", type=Path, default=DEFAULT_DB)
    args = parser.parse_args()

    if args.train or not args.classify:
        train(args.db)
    if args.classify:
        ts = datetime.fromisoformat(args.classify.replace(" ", "T"))
        result = classify(ts, args.db)
        print(f"{ts.isoformat()} -> {result}")


if __name__ == "__main__":
    main()
