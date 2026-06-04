"""Build a real-home `readings` history from the iAWE dataset.

iAWE (Indian Apartment Wattage Energy) — a public, sub-metered dataset from a Delhi
home. We use it as the *real* replay source for the coach (vs the synthetic Malaysian
fixture in synthetic_history.py). It is the closest publicly available sub-metered AC
dataset; the in-home Malaysian pilot / live Pi remain the eventual ground truth.

Source : NILMTK HDF5 (`iawe.h5`, ~408 MB) — Zenodo record 13917372 (Processed NILM
         Datasets: IAWE, REDD, UKDALE). Download separately to `datasets/iawe.h5`
         (gitignored; not redistributed here). Original: https://iawe.github.io/
Output : ML/sensing/iawe_history.sqlite (small, committed) — same `readings` schema
         as synthetic_history, so from_history() consumes it unchanged.

Meter map (confirmed from power profiles + NILMTK metadata):
  1,2 = mains   3 = fridge   4,5 = AC1/AC2   6 = washing machine
  7 = laptop    8 = clothes iron   9 = kitchen   10 = TV   11 = water filter   12 = water motor
iAWE has no kettle / hair_dryer / rice_cooker / microwave / fan channels (left 0).

Read via PyTables directly (pandas 3.0 HDFStore reader is incompatible with this
older PyTables layout). 1 Hz -> 1-min mean, clipped to a 30-day window; sensor-gap
minutes (mains == 0) are dropped, not zero-filled, so standby/peak signals stay honest.

    python -m ML.sensing.build_iawe_history
"""
from __future__ import annotations

import sqlite3
from pathlib import Path

import pandas as pd
import tables

ROOT = Path(__file__).resolve().parents[2]
H5 = ROOT / "datasets" / "iawe.h5"
DST = Path(__file__).resolve().parent / "iawe_history.sqlite"

COLS = ["timestamp", "total_w", "ac_w", "kettle_w", "fridge_w", "hair_dryer_w",
        "iron_w", "washing_machine_w", "rice_cooker_w", "tv_w", "microwave_w",
        "computer_w", "fan_w", "unknown_w", "occupied"]


def _meter_series(h, i: int) -> pd.Series:
    t = h.get_node(f"/building1/elec/meter{i}/table")
    idx = pd.to_datetime(t.col("index"))         # int64 ns -> datetime
    power = t.col("values_block_0")[:, 0]         # active power (W)
    return pd.Series(power, index=idx).sort_index().resample("1min").mean()


def build() -> int:
    if not H5.exists():
        raise SystemExit(f"Missing {H5}. Download iawe.h5 (Zenodo 13917372) into datasets/ first.")
    h = tables.open_file(str(H5), "r")
    m = {i: _meter_series(h, i) for i in range(1, 13)}
    h.close()

    frame = pd.DataFrame({
        "total_w": m[1].add(m[2], fill_value=0),
        "ac_w": m[4].add(m[5], fill_value=0),
        "fridge_w": m[3],
        "washing_machine_w": m[6],
        "computer_w": m[7],
        "iron_w": m[8],
        "tv_w": m[10],
    }).fillna(0.0)

    start = pd.Timestamp("2013-06-07")            # window where the submeters are live
    frame = frame.loc[start:start + pd.Timedelta(days=59)]  # ~2 months -> enables month-over-month (#7)
    frame = frame[frame["total_w"] > 0]           # drop sensor-gap minutes (see module docstring)

    known = ["ac_w", "fridge_w", "washing_machine_w", "computer_w", "iron_w", "tv_w"]
    frame["unknown_w"] = (frame["total_w"] - frame[known].sum(axis=1)).clip(lower=0)
    for c in ["kettle_w", "hair_dryer_w", "rice_cooker_w", "microwave_w", "fan_w"]:
        frame[c] = 0.0
    frame["occupied"] = 1

    DST.unlink(missing_ok=True)
    conn = sqlite3.connect(str(DST))
    conn.execute(f"CREATE TABLE readings ({', '.join(c + ' REAL' for c in COLS)})")
    rows = [
        tuple([ts.isoformat()] + [round(float(r.get(c, 0.0)), 1) for c in COLS[1:]])
        for ts, r in frame.iterrows()
    ]
    conn.executemany(f"INSERT INTO readings VALUES ({','.join('?' * len(COLS))})", rows)
    conn.commit()
    conn.close()
    return len(rows)


if __name__ == "__main__":
    n = build()
    print(f"wrote {n} rows -> {DST}")
