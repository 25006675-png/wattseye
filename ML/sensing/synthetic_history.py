"""Synthetic Malaysian household electricity history generator.

Produces realistic 30-day, 1-minute-resolution data with three appliance layers:

1. NILM-modeled appliances (5 named channels — match the .pth models in ML/NILM/)
2. Signature-labelable appliances (5 named channels — discoverable via signature library)
3. Residual noise (lumped into unknown_w — lights, chargers, ambient standby)

Also includes:
- AC channel (dedicated CT clamp ground truth)
- Occupancy (mmWave ground truth)
- Two seeded anomalies (empty-room AC events, one extended fridge cycle)

Output formats:
- CSV: ML/sensing/synthetic_history.csv (human-readable, ~6 MB)
- SQLite: ML/sensing/synthetic_history.sqlite (queryable, indexed)

This is the canonical training/demo data for the downstream ML models:
- ML/routine/kmeans_phases.py
- ML/anomaly/isolation_forest.py
- ML/anomaly/appliance_health_regression.py
- ML/signatures/signature_library.py
"""

from __future__ import annotations

import csv
import math
import random
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Callable

OUT_DIR = Path(__file__).resolve().parent
CSV_PATH = OUT_DIR / "synthetic_history.csv"
SQLITE_PATH = OUT_DIR / "synthetic_history.sqlite"

START = datetime(2026, 4, 21, 0, 0)  # 30 days ending the day before the demo
DAYS = 30
MINUTES_PER_DAY = 24 * 60
TOTAL_MINUTES = DAYS * MINUTES_PER_DAY

SEED = 20260520
random.seed(SEED)


@dataclass
class Appliance:
    name: str
    layer: str  # "nilm", "signature", "residual"
    sample: Callable[[datetime, bool], float]


# --- Per-appliance generators -------------------------------------------------


def _bernoulli(p: float) -> bool:
    return random.random() < p


def _gauss(mean: float, sigma: float, low: float = 0.0) -> float:
    return max(low, random.gauss(mean, sigma))


# Helpers stateful across the timeline. We avoid global mutation by closures.

def make_kettle():
    state = {"on_until": None}

    def sample(ts: datetime, occupied: bool) -> float:
        if state["on_until"] and ts < state["on_until"]:
            return _gauss(1800, 30)
        state["on_until"] = None
        # Most boils between 6-8 AM, occasional afternoon and evening
        hour = ts.hour
        p = 0.0
        if 6 <= hour < 9 and occupied:
            p = 0.04  # ~2 events in this 3-hour window
        elif 13 <= hour < 14 and occupied:
            p = 0.01
        elif 19 <= hour < 21 and occupied:
            p = 0.015
        if _bernoulli(p):
            state["on_until"] = ts + timedelta(minutes=random.randint(3, 5))
            return _gauss(1800, 30)
        return 0.0

    return sample


def make_fridge(anomaly_window: tuple[datetime, datetime] | None = None):
    state = {"phase_min": 0, "on": False}

    def sample(ts: datetime, occupied: bool) -> float:
        in_anomaly = anomaly_window and anomaly_window[0] <= ts < anomaly_window[1]
        cycle_on = 20 if not in_anomaly else 35
        cycle_off = 30
        period = cycle_on + cycle_off
        state["phase_min"] = (state["phase_min"] + 1) % period
        if state["phase_min"] < cycle_on:
            return _gauss(120, 4)
        return _gauss(4, 1)  # tiny standby during off-cycle

    return sample


def make_hair_dryer():
    state = {"on_until": None}

    def sample(ts: datetime, occupied: bool) -> float:
        if state["on_until"] and ts < state["on_until"]:
            return _gauss(1200, 25)
        state["on_until"] = None
        # 3 times per week, morning or evening, when occupied
        if occupied and ts.weekday() in (1, 3, 5) and ts.hour in (7, 20):
            if _bernoulli(0.05):
                state["on_until"] = ts + timedelta(minutes=random.randint(4, 7))
                return _gauss(1200, 25)
        return 0.0

    return sample


def make_iron():
    state = {"on_until": None}

    def sample(ts: datetime, occupied: bool) -> float:
        if state["on_until"] and ts < state["on_until"]:
            # Iron has a thermal cycle: alternating heating bursts
            return _gauss(1000, 50) if random.random() < 0.6 else _gauss(50, 10)
        state["on_until"] = None
        # Once a week, Sunday afternoon, when occupied
        if occupied and ts.weekday() == 6 and ts.hour in (14, 15) and _bernoulli(0.02):
            state["on_until"] = ts + timedelta(minutes=random.randint(15, 25))
            return _gauss(1000, 50)
        return 0.0

    return sample


def make_washing_machine():
    state = {"stage": None, "stage_until": None}

    def sample(ts: datetime, occupied: bool) -> float:
        if state["stage"] and ts < state["stage_until"]:
            if state["stage"] == "fill":
                return _gauss(200, 10)
            if state["stage"] == "wash":
                return _gauss(500, 40)
            if state["stage"] == "rinse":
                return _gauss(300, 20)
            if state["stage"] == "spin":
                return _gauss(450, 30)
        if state["stage"]:
            order = ["fill", "wash", "rinse", "spin", None]
            durations = {"fill": 5, "wash": 25, "rinse": 10, "spin": 15}
            idx = order.index(state["stage"])
            nxt = order[idx + 1]
            state["stage"] = nxt
            if nxt:
                state["stage_until"] = ts + timedelta(minutes=durations[nxt])
                return sample(ts, occupied)
            return 0.0
        # Twice a week, Saturday/Wednesday morning
        if occupied and ts.weekday() in (2, 5) and ts.hour == 10 and _bernoulli(0.04):
            state["stage"] = "fill"
            state["stage_until"] = ts + timedelta(minutes=5)
            return _gauss(200, 10)
        return 0.0

    return sample


def make_ac(empty_room_events: list[tuple[datetime, datetime]] | None = None):
    state = {"on_until": None}
    empty_room_events = empty_room_events or []

    def sample(ts: datetime, occupied: bool) -> float:
        # Forced empty-room AC anomaly: AC stays on even though room is empty
        for start, end in empty_room_events:
            if start <= ts < end:
                return _gauss(900, 30)
        if state["on_until"] and ts < state["on_until"]:
            return _gauss(900, 30) if occupied or random.random() < 0.7 else 0.0
        state["on_until"] = None
        # AC normally runs evening 8-11 PM weekdays, 6 PM - midnight weekends, only when occupied
        hour = ts.hour
        weekday = ts.weekday() < 5
        evening_start = 20 if weekday else 18
        evening_end = 23 if weekday else 24
        if occupied and evening_start <= hour < evening_end and _bernoulli(0.02):
            state["on_until"] = ts + timedelta(minutes=random.randint(40, 90))
            return _gauss(900, 30)
        return 0.0

    return sample


def make_rice_cooker():
    state = {"on_until": None}

    def sample(ts: datetime, occupied: bool) -> float:
        if state["on_until"] and ts < state["on_until"]:
            # Cooking burst then warming
            elapsed = (state["on_until"] - ts).total_seconds() / 60
            return _gauss(620, 15) if elapsed > 15 else _gauss(60, 5)
        state["on_until"] = None
        if occupied and ts.hour == 18 and _bernoulli(0.08):
            state["on_until"] = ts + timedelta(minutes=random.randint(35, 45))
            return _gauss(620, 15)
        return 0.0

    return sample


def make_tv():
    state = {"on_until": None}

    def sample(ts: datetime, occupied: bool) -> float:
        if state["on_until"] and ts < state["on_until"]:
            return _gauss(90, 4)
        state["on_until"] = None
        # Evening 7-10 PM, 3-4 hours
        if occupied and ts.hour in (19, 20) and _bernoulli(0.03):
            state["on_until"] = ts + timedelta(minutes=random.randint(120, 240))
            return _gauss(90, 4)
        return 0.0

    return sample


def make_microwave():
    state = {"on_until": None}

    def sample(ts: datetime, occupied: bool) -> float:
        if state["on_until"] and ts < state["on_until"]:
            return _gauss(1100, 30)
        state["on_until"] = None
        if occupied and ts.hour in (8, 12, 19) and _bernoulli(0.015):
            state["on_until"] = ts + timedelta(minutes=random.randint(1, 3))
            return _gauss(1100, 30)
        return 0.0

    return sample


def make_computer():
    def sample(ts: datetime, occupied: bool) -> float:
        # Office hours weekday, when occupied (work-from-home)
        if ts.weekday() < 5 and 9 <= ts.hour < 18 and occupied:
            return _gauss(150, 12)
        return 0.0

    return sample


def make_ceiling_fan():
    def sample(ts: datetime, occupied: bool) -> float:
        # Evening + night when occupied
        if occupied and (ts.hour >= 19 or ts.hour < 7):
            return _gauss(75, 5)
        return 0.0

    return sample


def make_lights():
    def sample(ts: datetime, occupied: bool) -> float:
        if not occupied:
            return _gauss(2, 1)  # security light
        if ts.hour < 6 or ts.hour >= 19:
            return _gauss(45, 8)
        return _gauss(8, 3)

    return sample


def make_chargers():
    def sample(ts: datetime, occupied: bool) -> float:
        # Mostly overnight
        if ts.hour >= 22 or ts.hour < 7:
            return _gauss(20, 3)
        return _gauss(5, 2)

    return sample


def make_ambient_standby():
    def sample(ts: datetime, occupied: bool) -> float:
        # Always-on baseline
        return _gauss(30, 2)

    return sample


# --- Occupancy ----------------------------------------------------------------


def occupied_at(ts: datetime, empty_room_events: list[tuple[datetime, datetime]]) -> bool:
    """Return True if the room is occupied.

    Note: during empty_room_events the AC stays on but the room is empty
    (that is the anomaly we want the system to catch).
    """
    for start, end in empty_room_events:
        if start <= ts < end:
            return False

    weekday = ts.weekday() < 5
    hour = ts.hour
    if weekday:
        # Home morning 6-8, away 9-17, home 18-23, sleep 0-5 (still home)
        if 9 <= hour < 18:
            return _bernoulli(0.05)  # rarely home during work hours
        return _bernoulli(0.92)
    # Weekends — home most of the day
    if 12 <= hour < 16:
        return _bernoulli(0.70)
    return _bernoulli(0.90)


# --- Driver -------------------------------------------------------------------


@dataclass
class Row:
    timestamp: str
    total_w: float
    ac_w: float
    kettle_w: float
    fridge_w: float
    hair_dryer_w: float
    iron_w: float
    washing_machine_w: float
    rice_cooker_w: float
    tv_w: float
    microwave_w: float
    computer_w: float
    fan_w: float
    unknown_w: float
    occupied: int


def generate() -> list[Row]:
    # Seed two empty-room AC anomalies
    empty_room_events = [
        (START + timedelta(days=10, hours=14, minutes=20),
         START + timedelta(days=10, hours=15, minutes=10)),
        (START + timedelta(days=20, hours=15, minutes=5),
         START + timedelta(days=20, hours=15, minutes=55)),
    ]
    # Seed one extended fridge cycle window (day 25 ~ 4 hours of degraded cycling)
    fridge_anomaly = (
        START + timedelta(days=25, hours=14),
        START + timedelta(days=25, hours=18),
    )

    sampler_kettle = make_kettle()
    sampler_fridge = make_fridge(anomaly_window=fridge_anomaly)
    sampler_hair = make_hair_dryer()
    sampler_iron = make_iron()
    sampler_wash = make_washing_machine()
    sampler_ac = make_ac(empty_room_events=empty_room_events)
    sampler_rice = make_rice_cooker()
    sampler_tv = make_tv()
    sampler_micro = make_microwave()
    sampler_comp = make_computer()
    sampler_fan = make_ceiling_fan()
    sampler_lights = make_lights()
    sampler_chargers = make_chargers()
    sampler_ambient = make_ambient_standby()

    rows: list[Row] = []
    for minute in range(TOTAL_MINUTES):
        ts = START + timedelta(minutes=minute)
        occupied = occupied_at(ts, empty_room_events)

        kettle = sampler_kettle(ts, occupied)
        fridge = sampler_fridge(ts, occupied)
        hair = sampler_hair(ts, occupied)
        iron = sampler_iron(ts, occupied)
        wash = sampler_wash(ts, occupied)
        ac = sampler_ac(ts, occupied)
        rice = sampler_rice(ts, occupied)
        tv = sampler_tv(ts, occupied)
        micro = sampler_micro(ts, occupied)
        comp = sampler_comp(ts, occupied)
        fan = sampler_fan(ts, occupied)
        lights = sampler_lights(ts, occupied)
        chargers = sampler_chargers(ts, occupied)
        ambient = sampler_ambient(ts, occupied)

        unknown = lights + chargers + ambient
        total = kettle + fridge + hair + iron + wash + ac + rice + tv + micro + comp + fan + unknown
        # Sensor noise on total reading
        total += _gauss(0, 3, low=-9999)

        rows.append(Row(
            timestamp=ts.isoformat(timespec="minutes"),
            total_w=round(max(0.0, total), 2),
            ac_w=round(ac, 2),
            kettle_w=round(kettle, 2),
            fridge_w=round(fridge, 2),
            hair_dryer_w=round(hair, 2),
            iron_w=round(iron, 2),
            washing_machine_w=round(wash, 2),
            rice_cooker_w=round(rice, 2),
            tv_w=round(tv, 2),
            microwave_w=round(micro, 2),
            computer_w=round(comp, 2),
            fan_w=round(fan, 2),
            unknown_w=round(unknown, 2),
            occupied=1 if occupied else 0,
        ))

    return rows


def write_csv(rows: list[Row], path: Path) -> None:
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([
            "timestamp", "total_w", "ac_w", "kettle_w", "fridge_w", "hair_dryer_w",
            "iron_w", "washing_machine_w", "rice_cooker_w", "tv_w", "microwave_w",
            "computer_w", "fan_w", "unknown_w", "occupied",
        ])
        for r in rows:
            writer.writerow([
                r.timestamp, r.total_w, r.ac_w, r.kettle_w, r.fridge_w, r.hair_dryer_w,
                r.iron_w, r.washing_machine_w, r.rice_cooker_w, r.tv_w, r.microwave_w,
                r.computer_w, r.fan_w, r.unknown_w, r.occupied,
            ])


def write_sqlite(rows: list[Row], path: Path) -> None:
    if path.exists():
        path.unlink()
    conn = sqlite3.connect(path)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE readings (
            timestamp TEXT PRIMARY KEY,
            total_w REAL, ac_w REAL,
            kettle_w REAL, fridge_w REAL, hair_dryer_w REAL,
            iron_w REAL, washing_machine_w REAL,
            rice_cooker_w REAL, tv_w REAL, microwave_w REAL,
            computer_w REAL, fan_w REAL,
            unknown_w REAL, occupied INTEGER
        )
    """)
    c.executemany("""
        INSERT INTO readings VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, [
        (r.timestamp, r.total_w, r.ac_w, r.kettle_w, r.fridge_w, r.hair_dryer_w,
         r.iron_w, r.washing_machine_w, r.rice_cooker_w, r.tv_w, r.microwave_w,
         r.computer_w, r.fan_w, r.unknown_w, r.occupied)
        for r in rows
    ])
    c.execute("CREATE INDEX idx_ts ON readings(timestamp)")
    conn.commit()
    conn.close()


def summary(rows: list[Row]) -> None:
    days = DAYS
    total_kwh = sum(r.total_w for r in rows) / 60 / 1000
    ac_kwh = sum(r.ac_w for r in rows) / 60 / 1000
    kettle_kwh = sum(r.kettle_w for r in rows) / 60 / 1000
    fridge_kwh = sum(r.fridge_w for r in rows) / 60 / 1000
    unknown_kwh = sum(r.unknown_w for r in rows) / 60 / 1000
    occupied_min = sum(r.occupied for r in rows)
    print(f"Generated {len(rows)} rows over {days} days ({START.isoformat()} -> {(START + timedelta(days=days)).isoformat()})")
    print(f"  Total energy:    {total_kwh:.1f} kWh   ({total_kwh / days:.1f} kWh/day)")
    print(f"  AC:              {ac_kwh:.1f} kWh   ({ac_kwh / total_kwh * 100:.0f}%)")
    print(f"  Kettle:          {kettle_kwh:.2f} kWh ({kettle_kwh / total_kwh * 100:.0f}%)")
    print(f"  Fridge:          {fridge_kwh:.1f} kWh  ({fridge_kwh / total_kwh * 100:.0f}%)")
    print(f"  Residual unknown:{unknown_kwh:.1f} kWh ({unknown_kwh / total_kwh * 100:.0f}%)")
    print(f"  Occupied:        {occupied_min / len(rows) * 100:.0f}% of minutes")


def main() -> None:
    print(f"Synthetic history generator — seed={SEED}")
    rows = generate()
    write_csv(rows, CSV_PATH)
    write_sqlite(rows, SQLITE_PATH)
    summary(rows)
    print(f"\nWrote {CSV_PATH}")
    print(f"Wrote {SQLITE_PATH}")


if __name__ == "__main__":
    main()
