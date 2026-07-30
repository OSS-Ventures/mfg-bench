"""Statistical process control (SPC) generator.

Given a series of subgroup measurements from an X-bar/R control chart, computes:
- X-bar chart control limits (UCL, LCL) from the grand mean and average subgroup range,
- process capability (Cp, Cpk) from the within-subgroup sigma estimate (Rbar / d2),
- process performance (Pp, Ppk) from the overall sample standard deviation of all
  individual measurements, and
- the count of subgroups whose mean falls outside the X-bar control limits (out-of-control,
  Western Electric Rule 1).

All of it is computed directly from the generated data series by the standard SPC formulas
-- correct by construction, never a model's opinion. The A2/d2 control-chart constants come
from a small hardcoded textbook lookup table (`SPC_CONSTANTS`), the same approach used for
the service-level z-table in `generators/inventory_policy.py`, so no scipy dependency is
needed.
"""
from __future__ import annotations

import random
import statistics
from datetime import datetime, timezone
from typing import Any

from generators.base import Generator

# Standard control-chart constants for X-bar/R charts, keyed by subgroup size n (textbook
# lookup table, e.g. Montgomery's "Introduction to Statistical Quality Control").
#   A2 -- multiplier of Rbar for X-bar chart 3-sigma limits.
#   d2 -- multiplier relating Rbar to the within-subgroup sigma estimate (sigma_hat = Rbar/d2).
SPC_CONSTANTS = {
    3: {"A2": 1.023, "d2": 1.693},
    4: {"A2": 0.729, "d2": 2.059},
    5: {"A2": 0.577, "d2": 2.326},
    6: {"A2": 0.483, "d2": 2.534},
    7: {"A2": 0.419, "d2": 2.704},
}


class SPCGenerator(Generator):
    name = "spc"

    def generate(self, seed: int, difficulty: str = "standard") -> dict[str, Any]:
        rng = random.Random(seed)

        num_subgroups = 15 if difficulty == "standard" else 20
        subgroup_size = rng.choice([4, 5]) if difficulty == "standard" else rng.choice([3, 6, 7])

        true_mean = rng.choice([20, 30, 40, 50, 60, 75, 90, 100, 120, 150])
        true_sigma = (
            rng.uniform(1.5, 3.0) if difficulty == "standard" else rng.uniform(1.0, 4.0)
        )
        tolerance_multiplier = (
            rng.uniform(3.5, 4.5) if difficulty == "standard" else rng.uniform(3.0, 5.0)
        )

        subgroups = [
            [round(rng.gauss(true_mean, true_sigma), 2) for _ in range(subgroup_size)]
            for _ in range(num_subgroups)
        ]

        if rng.random() < 0.4:
            shift = rng.choice([3, 4, 5]) * true_sigma
            subgroups[-1] = [round(x + shift, 2) for x in subgroups[-1]]

        usl = round(true_mean + tolerance_multiplier * true_sigma, 2)
        lsl = round(true_mean - tolerance_multiplier * true_sigma, 2)

        constants = SPC_CONSTANTS[subgroup_size]
        metrics = compute_spc_metrics(subgroups, usl, lsl, constants)

        subgroups_lines = "\n".join(
            f"Subgroup {i + 1}: {', '.join(f'{v:g}' for v in sg)}"
            for i, sg in enumerate(subgroups)
        )

        prompt = (
            f"A process characteristic is monitored with an X-bar/R control chart using "
            f"{num_subgroups} subgroups of size {subgroup_size}. The measurements are:\n\n"
            f"{subgroups_lines}\n\n"
            f"Specification limits: USL = {usl:g}, LSL = {lsl:g}\n"
            f"Control-chart constants for subgroup size {subgroup_size}: "
            f"A2 = {constants['A2']:g}, d2 = {constants['d2']:g}\n\n"
            "Using standard X-bar/R control-chart formulas:\n"
            "Grand mean (X-double-bar) = average of the subgroup means\n"
            "Average range (R-bar) = average of the subgroup ranges (max - min within each "
            "subgroup)\n"
            "UCL = X-double-bar + A2 x R-bar\n"
            "LCL = X-double-bar - A2 x R-bar\n"
            "Within-subgroup sigma estimate = R-bar / d2\n"
            "Cp = (USL - LSL) / (6 x within-subgroup sigma estimate)\n"
            "Cpk = min((USL - X-double-bar), (X-double-bar - LSL)) / (3 x within-subgroup "
            "sigma estimate)\n"
            "Overall sigma estimate = sample standard deviation of all individual "
            "measurements (all subgroups pooled)\n"
            "Pp = (USL - LSL) / (6 x overall sigma estimate)\n"
            "Ppk = min((USL - overall mean), (overall mean - LSL)) / (3 x overall sigma "
            "estimate)\n"
            "Out-of-control count = number of subgroups whose mean falls above UCL or below "
            "LCL\n\n"
            "Compute, each rounded to 2 decimal places: (1) UCL, (2) LCL, (3) Cp, (4) Cpk, "
            "(5) Pp, (6) Ppk, and (7) the out-of-control count (as a whole number).\n\n"
            "Report 7 numbers in this order: UCL, LCL, Cp, Cpk, Pp, Ppk, Out-of-control count."
        )

        parts = [
            {"value": metrics["ucl"], "tolerance": 0.01, "tolerance_type": "relative"},
            {"value": metrics["lcl"], "tolerance": 0.01, "tolerance_type": "relative"},
            {"value": metrics["cp"], "tolerance": 0.01, "tolerance_type": "relative"},
            {"value": metrics["cpk"], "tolerance": 0.01, "tolerance_type": "relative"},
            {"value": metrics["pp"], "tolerance": 0.01, "tolerance_type": "relative"},
            {"value": metrics["ppk"], "tolerance": 0.01, "tolerance_type": "relative"},
            {
                "value": float(metrics["out_of_control_count"]),
                "tolerance": 0.01,
                "tolerance_type": "absolute",
            },
        ]

        return {
            "id": f"compute.spc.{seed:06d}",
            "family": "computed",
            "domain": "quality_problem_solving",
            "reasoning_tier": "L2",
            "answer_format": "numeric",
            "prompt": prompt,
            "context": {
                "subgroups": subgroups,
                "subgroup_size": subgroup_size,
                "num_subgroups": num_subgroups,
                "usl": usl,
                "lsl": lsl,
                "a2": constants["A2"],
                "d2": constants["d2"],
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


def compute_spc_metrics(
    subgroups: list[list[float]], usl: float, lsl: float, constants: dict[str, float]
) -> dict[str, float]:
    """Compute X-bar/R control limits, Cp/Cpk, Pp/Ppk, and the out-of-control count.

    Pure function of the raw subgroup data + spec limits + control-chart constants -- no
    randomness, no model opinion. Shared by the generator and independently re-derived (not
    called) by the hand-verified tests.
    """
    subgroup_means = [statistics.mean(sg) for sg in subgroups]
    subgroup_ranges = [max(sg) - min(sg) for sg in subgroups]

    xbarbar = statistics.mean(subgroup_means)
    rbar = statistics.mean(subgroup_ranges)

    ucl = xbarbar + constants["A2"] * rbar
    lcl = xbarbar - constants["A2"] * rbar
    sigma_within = rbar / constants["d2"]

    cp = (usl - lsl) / (6 * sigma_within)
    cpk = min(usl - xbarbar, xbarbar - lsl) / (3 * sigma_within)

    all_values = [v for sg in subgroups for v in sg]
    overall_mean = statistics.mean(all_values)
    overall_sigma = statistics.stdev(all_values)

    pp = (usl - lsl) / (6 * overall_sigma)
    ppk = min(usl - overall_mean, overall_mean - lsl) / (3 * overall_sigma)

    out_of_control_count = sum(1 for m in subgroup_means if m > ucl or m < lcl)

    return {
        "ucl": round(ucl, 2),
        "lcl": round(lcl, 2),
        "cp": round(cp, 2),
        "cpk": round(cpk, 2),
        "pp": round(pp, 2),
        "ppk": round(ppk, 2),
        "out_of_control_count": out_of_control_count,
    }
