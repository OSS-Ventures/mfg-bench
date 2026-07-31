"""Quality economics generator.

Given a serial production process where each station scraps a fraction of the units it
receives (removed from the process) and reworks another fraction (repaired at a cost, then
continuing to the next station), computes:
- each station's First-Pass Yield (FPY) -- the fraction that passes with no rework at all,
- the average FPY across stations and the Rolled Throughput Yield (RTY, the product of the
  per-station FPYs -- the fraction of starting units that would pass every station right first
  time), and
- the Cost of Poor Quality (COPQ): total scrap cost + total rework cost.

All values are derived directly from each station's scrap rate, rework rate, and per-unit
scrap/rework cost -- correct by construction, never a model's opinion.
"""
from __future__ import annotations

import random
from datetime import datetime, timezone
from typing import Any

from generators.base import Generator


class QualityEconomicsGenerator(Generator):
    name = "quality_economics"

    def generate(self, seed: int, difficulty: str = "standard") -> dict[str, Any]:
        rng = random.Random(seed)

        num_stations = 3 if difficulty == "standard" else 4
        scrap_low, scrap_high = (1, 6) if difficulty == "standard" else (3, 12)
        rework_low, rework_high = (2, 10) if difficulty == "standard" else (5, 15)

        units_started = float(rng.randint(5, 20) * 100)
        stations = [
            {
                "scrap_pct": rng.randint(scrap_low, scrap_high),
                "rework_pct": rng.randint(rework_low, rework_high),
                "scrap_cost_per_unit": rng.randint(10, 60),
                "rework_cost_per_unit": rng.randint(5, 30),
            }
            for _ in range(num_stations)
        ]

        metrics = compute_quality_economics(units_started, stations)

        station_lines = "\n".join(
            f"Station {i + 1}: scrap rate = {s['scrap_pct']}%, rework rate = {s['rework_pct']}%, "
            f"scrap cost = ${s['scrap_cost_per_unit']}/unit scrapped, "
            f"rework cost = ${s['rework_cost_per_unit']}/unit reworked"
            for i, s in enumerate(stations)
        )

        prompt = (
            f"A production process has {num_stations} sequential stations. "
            f"{units_started:g} units enter station 1. At each station, a fraction of the units "
            "entering are scrapped (removed from the process for good) and another fraction are "
            "reworked (repaired at a cost, then continuing on to the next station); the "
            "remainder pass with no rework, right first time.\n\n"
            f"{station_lines}\n\n"
            "Formulas:\n"
            "- A station's First-Pass Yield (FPY) = 1 - scrap rate - rework rate (the fraction "
            "of units entering that station which pass with no rework at all).\n"
            "- Units entering the next station = units entering this station x (1 - scrap "
            "rate) -- reworked units continue on; only scrapped units leave the process.\n"
            "- Average FPY = the arithmetic mean of the per-station FPYs.\n"
            "- Rolled Throughput Yield (RTY) = the product of the per-station FPYs (the "
            "fraction of the units entering station 1 that would pass every station right "
            "first time, with no rework anywhere).\n"
            "- Total scrap cost = sum over stations of (units scrapped at that station x that "
            "station's scrap cost per unit).\n"
            "- Total rework cost = sum over stations of (units reworked at that station x that "
            "station's rework cost per unit).\n"
            "- Cost of Poor Quality (COPQ) = Total scrap cost + Total rework cost.\n\n"
            "Compute, in this order: (1) Average FPY as a percentage, (2) Rolled Throughput "
            "Yield as a percentage, (3) Total scrap cost in dollars, (4) Total rework cost in "
            "dollars, (5) COPQ in dollars. Round all values to 2 decimal places."
        )

        parts = [
            {"value": metrics["avg_fpy_pct"], "tolerance": 0.01, "tolerance_type": "relative"},
            {"value": metrics["rty_pct"], "tolerance": 0.01, "tolerance_type": "relative"},
            {"value": metrics["total_scrap_cost"], "tolerance": 0.01, "tolerance_type": "relative"},
            {"value": metrics["total_rework_cost"], "tolerance": 0.01, "tolerance_type": "relative"},
            {"value": metrics["copq"], "tolerance": 0.01, "tolerance_type": "relative"},
        ]

        return {
            "id": f"compute.quality_economics.{seed:06d}",
            "family": "computed",
            "domain": "cost_performance",
            "reasoning_tier": "L2",
            "answer_format": "numeric",
            "prompt": prompt,
            "context": {
                "units_started": units_started,
                "stations": stations,
            },
            "ground_truth": {"parts": parts},
            "scorer": "numeric",
            "generator": self.name,
            "seed": seed,
            "difficulty": difficulty,
            "source": None,
            "source_url": None,
            "created": datetime.now(timezone.utc).date().isoformat(),
            "public": True,
        }


def compute_quality_economics(
    units_started: float, stations: list[dict[str, Any]]
) -> dict[str, Any]:
    """Compute per-station FPY, average FPY, RTY, scrap/rework cost, and COPQ.

    Pure function of the starting unit count + each station's scrap/rework rates and unit
    costs -- no randomness, no model opinion. Shared by the generator and independently
    re-derived (not called) by the hand-verified tests.
    """
    units_in = units_started
    fpys = []
    total_scrap_cost = 0.0
    total_rework_cost = 0.0

    for station in stations:
        scrap_rate = station["scrap_pct"] / 100
        rework_rate = station["rework_pct"] / 100

        scrapped = units_in * scrap_rate
        reworked = units_in * rework_rate
        fpys.append(1 - scrap_rate - rework_rate)

        total_scrap_cost += scrapped * station["scrap_cost_per_unit"]
        total_rework_cost += reworked * station["rework_cost_per_unit"]

        units_in = units_in * (1 - scrap_rate)

    avg_fpy_pct = (sum(fpys) / len(fpys)) * 100
    rty = 1.0
    for fpy in fpys:
        rty *= fpy
    rty_pct = rty * 100

    return {
        "avg_fpy_pct": round(avg_fpy_pct, 2),
        "rty_pct": round(rty_pct, 2),
        "total_scrap_cost": round(total_scrap_cost, 2),
        "total_rework_cost": round(total_rework_cost, 2),
        "copq": round(total_scrap_cost + total_rework_cost, 2),
    }
