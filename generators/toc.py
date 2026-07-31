"""Theory of Constraints (TOC) / bottleneck generator.

Given a serial production line of workstations, each with a per-unit processing time and a
number of identical parallel machines, computes:
- the bottleneck station (the one with the lowest capacity -- the system constraint),
- system throughput in units/hour (the bottleneck's own capacity, since a serial line can never
  produce faster than its slowest station), and
- expected output over one full work shift, assuming steady-state flow.

All three values are computed directly from each station's task_time_min and num_machines --
correct by construction, never a model's opinion.
"""
from __future__ import annotations

import random
from datetime import datetime, timezone
from typing import Any

from generators.base import Generator


class TOCGenerator(Generator):
    name = "toc"

    def generate(self, seed: int, difficulty: str = "standard") -> dict[str, Any]:
        rng = random.Random(seed)

        num_stations = 4 if difficulty == "standard" else 5
        time_low, time_high = (4, 20) if difficulty == "standard" else (3, 25)
        machines_high = 3 if difficulty == "standard" else 4
        hours_low, hours_high = (6, 10) if difficulty == "standard" else (6, 12)

        stations = [
            {
                "task_time_min": rng.randint(time_low, time_high),
                "num_machines": rng.randint(1, machines_high),
            }
            for _ in range(num_stations)
        ]
        hours_per_day = rng.randint(hours_low, hours_high)

        metrics = compute_toc_metrics(stations, hours_per_day)

        station_lines = "\n".join(
            f"Station {i + 1}: task time = {s['task_time_min']} min/unit, "
            f"{s['num_machines']} identical parallel machine(s)"
            for i, s in enumerate(stations)
        )

        prompt = (
            f"A production line has {num_stations} sequential workstations, each staffed with "
            "one or more identical parallel machines that all perform that station's task:\n\n"
            f"{station_lines}\n\n"
            f"The line runs {hours_per_day} hours per day.\n\n"
            "Each station's capacity (units/hour) = (number of parallel machines x 60) / "
            "(task time in minutes per unit). The line's system throughput is limited by its "
            "slowest (lowest-capacity) station -- the constraint, or bottleneck. If two "
            "stations tie for the lowest capacity, the bottleneck is the one earliest in the "
            "sequence.\n\n"
            "Compute: (1) the bottleneck station number, (2) the system throughput in "
            "units/hour (the bottleneck's own capacity), rounded to 2 decimal places, and "
            "(3) the expected output over one full day's shift (throughput x hours per day), "
            "rounded to 2 decimal places.\n\n"
            "Report 3 numbers in this order: bottleneck station number, system throughput "
            "(units/hour), shift output (units)."
        )

        parts = [
            {
                "value": float(metrics["bottleneck_station"]),
                "tolerance": 0.01,
                "tolerance_type": "absolute",
            },
            {
                "value": metrics["throughput_uph"],
                "tolerance": 0.01,
                "tolerance_type": "relative",
            },
            {
                "value": metrics["shift_output"],
                "tolerance": 0.01,
                "tolerance_type": "relative",
            },
        ]

        return {
            "id": f"compute.toc.{seed:06d}",
            "family": "computed",
            "domain": "production_scheduling",
            "reasoning_tier": "L3",
            "answer_format": "numeric",
            "prompt": prompt,
            "context": {
                "stations": stations,
                "hours_per_day": hours_per_day,
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


def compute_toc_metrics(stations: list[dict[str, Any]], hours_per_day: float) -> dict[str, Any]:
    """Compute the bottleneck station, system throughput, and shift output.

    Pure function of station task times/machine counts + shift length -- no randomness, no
    model opinion. Shared by the generator and independently re-derived (not called) by the
    hand-verified tests.
    """
    capacities = [(s["num_machines"] * 60) / s["task_time_min"] for s in stations]
    bottleneck_index = min(range(len(capacities)), key=lambda i: capacities[i])
    throughput_uph = capacities[bottleneck_index]
    shift_output = throughput_uph * hours_per_day

    return {
        "bottleneck_station": bottleneck_index + 1,
        "throughput_uph": round(throughput_uph, 2),
        "shift_output": round(shift_output, 2),
    }
