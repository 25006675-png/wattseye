"""Lookup helper for the ST efficiency registry CSV.

The CSV is hand-derived from Malaysia's MEPS 2026 revision thresholds
(refrigerator and air-conditioner categories). Numbers are conservative
class averages, not per-model lookups.

Sources:
  - Suruhanjaya Tenaga MEPS guidelines (https://www.st.gov.my/eng/microsites/index/19/110)
  - ST EDIK certification database (https://edik.st.gov.my/publicenquiry/search.aspx)
  - United for Efficiency, "Advancing Energy Efficiency in Malaysia: MEPS
    Revision for Air Conditioners" (united4efficiency.org, 2026 update)
  - Sifu Engineering, "Energy Efficiency Labels Malaysia" basic guide

CSPF derivation: avg_rated_watts = rated_cooling_kW * 1000 / CSPF.
EER not used for inverter models — CSPF reflects seasonal performance.

Refresh: ST publishes MEPS revisions on a multi-year cadence. The 2026
revision is the current target as of this writing; re-run the source review
when ST announces the next regulatory period.
"""

from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path

CSV_PATH = Path(__file__).resolve().parent / "efficiency_registry.csv"

REGISTRY_URL = "https://edik.st.gov.my/publicenquiry/search.aspx"
MEPS_GUIDE_URL = "https://www.st.gov.my/eng/microsites/index/19/110"


@dataclass(frozen=True)
class EfficiencyEntry:
    appliance: str
    size_band: str
    size_label: str
    star_rating: int
    avg_rated_watts: int
    notes: str


def _load() -> list[EfficiencyEntry]:
    rows: list[EfficiencyEntry] = []
    with CSV_PATH.open() as f:
        for r in csv.DictReader(f):
            rows.append(EfficiencyEntry(
                appliance=r["appliance"],
                size_band=r["size_band"],
                size_label=r["size_label"],
                star_rating=int(r["star_rating"]),
                avg_rated_watts=int(r["avg_rated_watts"]),
                notes=r.get("notes", ""),
            ))
    return rows


_CACHE: list[EfficiencyEntry] | None = None


def all_entries() -> list[EfficiencyEntry]:
    global _CACHE
    if _CACHE is None:
        _CACHE = _load()
    return _CACHE


def class_average(appliance: str, size_band: str, star_rating: int) -> int | None:
    """Return avg watts for (appliance, size_band, star_rating). None if unknown."""
    for e in all_entries():
        if e.appliance == appliance and e.size_band == size_band and e.star_rating == star_rating:
            return e.avg_rated_watts
    return None


def best_in_class(appliance: str, size_band: str) -> EfficiencyEntry | None:
    """Return the 5-star (or highest available) entry for the size band."""
    candidates = [e for e in all_entries()
                  if e.appliance == appliance and e.size_band == size_band]
    if not candidates:
        return None
    return max(candidates, key=lambda e: e.star_rating)


def compare_to_best(appliance: str, size_band: str, current_watts: float) -> dict | None:
    """Compare a measured wattage to the best-in-class for its size band.

    Returns a dict the Coach correlator (archetype #12) consumes directly:
        {
          'appliance': 'fridge',
          'current_w': 180,
          'efficient_class_w': 55,
          'efficient_class_label': '5-star, 250-400L',
          'replacement_rm': estimated MYR for a typical replacement model,
          'registry_url': ST EDIK search URL,
        }
    """
    best = best_in_class(appliance, size_band)
    if best is None:
        return None
    if current_watts <= best.avg_rated_watts * 1.3:
        return None  # already efficient enough
    # Rough MYR for a typical 5-star replacement in this band
    replacement_rm = _typical_replacement_rm(appliance, size_band)
    return {
        "appliance": appliance,
        "current_w": current_watts,
        "efficient_class_w": best.avg_rated_watts,
        "efficient_class_label": f"{best.star_rating}-star, {best.size_label}",
        "replacement_rm": replacement_rm,
        "registry_url": REGISTRY_URL,
    }


def _typical_replacement_rm(appliance: str, size_band: str) -> int:
    """Ballpark new-purchase price in MYR for a 5-star model in that band.

    Sourced from typical Lazada/Senheng prices in 2026; refresh occasionally.
    These are display values only — the user clicks through to the ST registry
    to pick an actual model.
    """
    table = {
        ("refrigerator", "small"):     1200,
        ("refrigerator", "medium"):    1800,
        ("refrigerator", "large"):     2800,
        ("ac_inverter", "1.0HP"):      1500,
        ("ac_inverter", "1.5HP"):      1900,
        ("ac_inverter", "2.0HP"):      2500,
        ("ac_inverter", "2.5HP"):      3200,
        ("water_heater", "small"):      450,
        ("water_heater", "medium"):     650,
        ("water_heater", "large"):      900,
        ("washing_machine", "top_load"):    1300,
        ("washing_machine", "front_load"):  1900,
        ("ceiling_fan", "standard"):   350,
    }
    return table.get((appliance, size_band), 2000)


if __name__ == "__main__":
    # Smoke test
    print(f"Loaded {len(all_entries())} entries from {CSV_PATH.name}\n")
    print("Best fridge (medium):", best_in_class("refrigerator", "medium"))
    print("Best AC (1.5HP):    ", best_in_class("ac_inverter", "1.5HP"))
    print()
    # Demo upgrade card data
    result = compare_to_best("refrigerator", "medium", current_watts=180)
    print("Upgrade card for inefficient fridge:")
    for k, v in (result or {}).items():
        print(f"  {k}: {v}")
