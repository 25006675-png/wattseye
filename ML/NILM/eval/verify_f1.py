"""Recompute NILM test-house F1/MAE from saved predictions — reproduces RESULTS.md.

The reported WattsEye NILM accuracy (eval/RESULTS.md) is produced on the UK-DALE
unseen-house test split (House 2). The training repo saves the held-out
predictions per appliance as `test_result.json` ({"gt": [...], "pred": [...]} in
watts). This script recomputes the metrics from those files using the exact
status logic from the training code, so the numbers are auditable without a GPU
or the training pipeline.

Usage:
    # point at a directory holding <appliance>/test_result.json files
    python ML/NILM/eval/verify_f1.py --pred-root /path/to/checkpoints_electricity/uk_dale

    # or a single file
    python ML/NILM/eval/verify_f1.py --file kettle/test_result.json --appliance kettle

Status logic (matches training repo metrics.py + Trainer):
    gt_status   = compute_status(gt, threshold, min_on, min_off)   # smoothed
    pred_status = pred >= threshold                                # simple
    F1          = f1(gt_status, pred_status)

Dependencies: numpy, scikit-learn.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
from sklearn.metrics import accuracy_score, f1_score, precision_score, recall_score

# UK-DALE preprocessing constants (from the training repo config.py, dataset_code='uk_dale').
THRESHOLD = {"kettle": 2000, "fridge": 50, "washing_machine": 20, "hair_dryer": 800, "iron": 1000}
MIN_ON = {"kettle": 2, "fridge": 10, "washing_machine": 300, "hair_dryer": 2, "iron": 2}
MIN_OFF = {"kettle": 0, "fridge": 2, "washing_machine": 26, "hair_dryer": 0, "iron": 0}
CLAIMED_F1 = {"kettle": 0.960, "fridge": 0.858, "washing_machine": 0.802, "hair_dryer": 0.762, "iron": 0.675}


def compute_status(data: np.ndarray, threshold: float, min_on: int, min_off: int) -> np.ndarray:
    """Ported verbatim from the training repo metrics.compute_status (single channel)."""
    data = data.reshape(-1, 1)
    initial_status = data[:, 0] >= threshold
    status_diff = np.diff(initial_status)
    events_idx = np.array(status_diff.nonzero()).squeeze()
    events_idx = np.atleast_1d(events_idx) + 1
    if initial_status[0]:
        events_idx = np.insert(events_idx, 0, 0)
    if initial_status[-1]:
        events_idx = np.insert(events_idx, events_idx.size, initial_status.size)
    events_idx = events_idx.reshape((-1, 2))
    on_events, off_events = events_idx[:, 0].copy(), events_idx[:, 1].copy()
    if len(on_events) > 0:
        off_duration = on_events[1:] - off_events[:-1]
        off_duration = np.insert(off_duration, 0, 1000)
        on_events = on_events[off_duration > min_off]
        off_events = off_events[np.roll(off_duration, -1) > min_off]
        on_duration = off_events - on_events
        on_events = on_events[on_duration >= min_on]
        off_events = off_events[on_duration >= min_on]
    status = np.zeros(data.shape[0])
    for on, off in zip(on_events, off_events):
        status[on:off] = 1
    return status


def evaluate(pred_file: Path, appliance: str) -> dict:
    d = json.loads(pred_file.read_text())
    gt = np.array(d["gt"], dtype=float).ravel()
    pred = np.clip(np.array(d["pred"], dtype=float).ravel(), 0, None)
    gt_status = compute_status(gt, THRESHOLD[appliance], MIN_ON[appliance], MIN_OFF[appliance])
    pred_status = (pred >= THRESHOLD[appliance]).astype(int)
    return {
        "appliance": appliance,
        "n_test": int(len(gt)),
        "f1": round(float(f1_score(gt_status, pred_status, zero_division=0)), 4),
        "precision": round(float(precision_score(gt_status, pred_status, zero_division=0)), 4),
        "recall": round(float(recall_score(gt_status, pred_status, zero_division=0)), 4),
        "accuracy": round(float(accuracy_score(gt_status, pred_status)), 4),
        "mae_watts": round(float(np.mean(np.abs(gt - pred))), 2),
    }


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--pred-root", type=Path, help="Dir holding <appliance>/test_result.json")
    ap.add_argument("--file", type=Path, help="A single test_result.json")
    ap.add_argument("--appliance", help="Appliance name (required with --file)")
    args = ap.parse_args()

    rows = []
    if args.file:
        if not args.appliance:
            ap.error("--appliance is required with --file")
        rows.append(evaluate(args.file, args.appliance))
    elif args.pred_root:
        for appliance in THRESHOLD:
            f = args.pred_root / appliance / "test_result.json"
            if f.exists():
                rows.append(evaluate(f, appliance))
        if not rows:
            ap.error(f"No <appliance>/test_result.json under {args.pred_root}")
    else:
        ap.error("Pass --pred-root or --file")

    print(f"{'appliance':16s}{'n_test':>10s}{'F1':>8s}{'claimed':>9s}{'prec':>7s}{'recall':>8s}{'MAE_W':>8s}")
    for r in rows:
        claim = CLAIMED_F1.get(r["appliance"])
        flag = "" if claim is None else ("  OK" if abs(r["f1"] - claim) <= 0.005 else "  DIFF")
        claim_s = "-" if claim is None else f"{claim:.3f}"
        print(f"{r['appliance']:16s}{r['n_test']:>10d}{r['f1']:>8.3f}{claim_s:>9s}"
              f"{r['precision']:>7.3f}{r['recall']:>8.3f}{r['mae_watts']:>8.1f}{flag}")


if __name__ == "__main__":
    main()
