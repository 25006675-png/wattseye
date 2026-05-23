"""Linear Regression for refrigerator efficiency drift detection.

Predicts the expected per-hour fridge duty cycle (fraction of the hour the
compressor runs) from time features, and flags hours where the actual duty
cycle exceeds the predicted value by more than a learned threshold.

A degrading fridge (door seal, dirty coil, refrigerant) cycles more often
to maintain temperature -- duty cycle drifts upward without a corresponding
load change. This is exactly what the regression catches.

Two data sources are supported:

1. UK-DALE house 1 fridge submeter (recommended). 4+ years of real fridge
   data at 6-second resolution from the technothon UKDALE cache.
2. Synthetic history (fallback). Useful when UK-DALE is unavailable; produces
   near-zero R^2 because the synthetic fridge is timer-driven.

Pipeline (UK-DALE mode):
1. Load house1_fridge.npz from the technothon cache.
2. Reshape into hour-buckets (600 samples per hour @ 6s).
3. duty_cycle per hour = fraction of samples where app > 50W.
4. Hour-of-day derived from sample index assuming start at UK-DALE house 1
   start time 2012-11-09 09:00 UTC (the time-of-day periodicity is what
   the regression learns; the absolute date does not matter).
5. Train LinearRegression on (hour_sin, hour_cos, dayofweek, weekend_flag).
6. Evaluate on held-out final 15% of data.

Production note: in a real home this model is fine-tuned on the home's own
first 30 days of recorded fridge data as the personal healthy baseline.
"""

from __future__ import annotations

import argparse
import math
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path

import joblib
import numpy as np
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_absolute_error, r2_score

DEFAULT_DB = Path(__file__).resolve().parents[1] / "sensing" / "synthetic_history.sqlite"
MODEL_PATH = Path(__file__).resolve().parent / "fridge_health.joblib"

UKDALE_CACHE = Path("C:/Users/user/Documents/technothon/data/cache/house1_fridge.npz")
UKDALE_START = datetime(2012, 11, 9, 9, 0)  # UK-DALE house 1 mains start
UKDALE_SAMPLE_SECONDS = 6
SAMPLES_PER_HOUR = 3600 // UKDALE_SAMPLE_SECONDS  # 600

FRIDGE_ON_THRESHOLD_W = 50
DRIFT_Z_THRESHOLD = 2.5  # residual std-deviations beyond which an hour is flagged


@dataclass(frozen=True)
class HealthModel:
    regression: LinearRegression
    train_mae: float
    train_r2: float
    flag_ratio: float


def _features(hour: int, day_of_week: int, month: int = 6) -> np.ndarray:
    """Time-based feature vector for fridge duty cycle regression.

    Includes hour-of-day (cyclic), weekday/weekend, and month-of-year (cyclic).
    Month captures the seasonal swing — fridge works harder when ambient is hot.
    """
    return np.array([
        math.sin(2 * math.pi * hour / 24),
        math.cos(2 * math.pi * hour / 24),
        day_of_week / 6.0,
        1.0 if day_of_week >= 5 else 0.0,
        math.sin(2 * math.pi * (month - 1) / 12),
        math.cos(2 * math.pi * (month - 1) / 12),
    ], dtype=np.float64)


def _aggregate_hourly_ukdale(cache_path: Path) -> tuple[np.ndarray, np.ndarray, list[datetime]]:
    """Compute per-hour duty cycle from the UK-DALE house 1 fridge cache.

    The cache is contiguous 6-second-resampled fridge power. We reshape into
    hour-buckets (600 samples each) and compute the fraction of samples above
    the 'on' threshold per bucket.
    """
    payload = np.load(cache_path)
    app = payload["app"].astype(np.float32)

    n_full_hours = len(app) // SAMPLES_PER_HOUR
    app = app[: n_full_hours * SAMPLES_PER_HOUR].reshape(n_full_hours, SAMPLES_PER_HOUR)
    duty_cycle = (app > FRIDGE_ON_THRESHOLD_W).mean(axis=1).astype(np.float32)

    timestamps = [UKDALE_START + timedelta(hours=i) for i in range(n_full_hours)]
    X = np.stack([_features(t.hour, t.weekday(), t.month) for t in timestamps])
    return X, duty_cycle, timestamps


def _aggregate_hourly(db_path: Path) -> tuple[np.ndarray, np.ndarray, list[datetime]]:
    conn = sqlite3.connect(db_path)
    rows = conn.execute(
        "SELECT timestamp, fridge_w FROM readings ORDER BY timestamp"
    ).fetchall()
    conn.close()

    buckets: dict[datetime, list[float]] = {}
    for ts_str, fridge_w in rows:
        ts = datetime.fromisoformat(ts_str)
        key = ts.replace(minute=0, second=0, microsecond=0)
        buckets.setdefault(key, []).append(float(fridge_w))

    keys = sorted(buckets.keys())
    X = np.stack([_features(k.hour, k.weekday(), k.month) for k in keys])
    y = np.array([
        sum(1 for w in buckets[k] if w >= FRIDGE_ON_THRESHOLD_W) / len(buckets[k])
        for k in keys
    ])
    return X, y, keys


def train(db_path: Path = DEFAULT_DB, source: str = "ukdale") -> dict:
    if source == "ukdale" and UKDALE_CACHE.exists():
        print(f"Training on UK-DALE house 1 fridge submeter (4+ years @ 6s)")
        X, y, keys = _aggregate_hourly_ukdale(UKDALE_CACHE)
    else:
        print(f"Training on synthetic history at {db_path}")
        X, y, keys = _aggregate_hourly(db_path)

    n_total = len(X)
    n_train = int(n_total * 0.85)

    X_train, y_train = X[:n_train], y[:n_train]
    X_eval, y_eval = X[n_train:], y[n_train:]
    eval_keys = keys[n_train:]

    reg = LinearRegression().fit(X_train, y_train)
    y_pred_train = reg.predict(X_train)
    train_mae = float(mean_absolute_error(y_train, y_pred_train))
    train_r2 = float(r2_score(y_train, y_pred_train))

    eval_pred = reg.predict(X_eval)
    eval_mae = float(mean_absolute_error(y_eval, eval_pred))
    eval_r2 = float(r2_score(y_eval, eval_pred))

    train_residual = y_train - y_pred_train
    residual_std = float(np.std(train_residual))

    print(f"Trained on {n_train:,} hourly buckets; evaluated on held-out {len(X_eval):,}.")
    print(f"  Training MAE = {train_mae:.4f}   R^2 = {train_r2:.4f}")
    print(f"  Held-out MAE = {eval_mae:.4f}   R^2 = {eval_r2:.4f}")
    print(f"  Residual std on train = {residual_std:.4f} duty-cycle units")
    print(f"  Anomaly threshold = +/- {DRIFT_Z_THRESHOLD:.1f} sigma "
          f"(= +/- {DRIFT_Z_THRESHOLD * residual_std:.3f} duty-cycle units)")

    eval_residual = y_eval - eval_pred
    z_scores = eval_residual / max(residual_std, 1e-6)
    flagged = np.where(np.abs(z_scores) > DRIFT_Z_THRESHOLD)[0]

    print(f"\nEvaluated {len(eval_keys):,} hours.")
    print(f"  {len(flagged)} hours flagged ({len(flagged) / len(eval_keys) * 100:.1f}%).")
    if len(flagged):
        print("  Top 10 most extreme flagged hours:")
        top = sorted(flagged, key=lambda i: -abs(z_scores[i]))[:10]
        for idx in top:
            print(f"    {eval_keys[idx]:%Y-%m-%d %a %H:00}  "
                  f"actual={y_eval[idx]:.2f}  predicted={eval_pred[idx]:.2f}  "
                  f"z={z_scores[idx]:+.2f}")

    payload = {
        "regression": reg,
        "train_mae": train_mae,
        "train_r2": train_r2,
        "residual_std": residual_std,
        "z_threshold": DRIFT_Z_THRESHOLD,
    }
    joblib.dump(payload, MODEL_PATH)
    print(f"\nSaved -> {MODEL_PATH}")
    return payload


def health_check(actual_duty_cycle: float, hour: int, day_of_week: int, month: int = 6) -> dict:
    if not MODEL_PATH.exists():
        raise FileNotFoundError(f"Model not found at {MODEL_PATH}. Run --train first.")
    payload = joblib.load(MODEL_PATH)
    features = _features(hour, day_of_week, month).reshape(1, -1)
    predicted = float(payload["regression"].predict(features)[0])
    residual = actual_duty_cycle - predicted
    z = residual / max(payload["residual_std"], 1e-6)
    flagged = abs(z) > payload["z_threshold"]

    if flagged and z > 0:
        status = "elevated_duty_cycle"
        priority = "high" if abs(z) > 3.5 else "medium"
    elif flagged:
        status = "lower_than_expected"
        priority = "low"
    else:
        status = "normal"
        priority = "low"

    drift_percent = (residual / predicted * 100) if predicted > 0.01 else 0.0
    return {
        "actual": round(actual_duty_cycle, 4),
        "predicted": round(predicted, 4),
        "residual": round(residual, 4),
        "z_score": round(z, 2),
        "drift_percent": round(drift_percent, 1),
        "flagged": flagged,
        "status": status,
        "priority": priority,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--train", action="store_true")
    parser.add_argument("--check", nargs=3, metavar=("DUTY_CYCLE", "HOUR", "DAYOFWEEK"))
    parser.add_argument("--db", type=Path, default=DEFAULT_DB)
    parser.add_argument("--source", choices=["ukdale", "synthetic"], default="ukdale")
    args = parser.parse_args()

    if args.train or not args.check:
        train(args.db, source=args.source)
    if args.check:
        d, h, dow = float(args.check[0]), int(args.check[1]), int(args.check[2])
        print(health_check(d, h, dow))


if __name__ == "__main__":
    main()
