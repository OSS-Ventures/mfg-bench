"""OEE (Overall Equipment Effectiveness) generator.

OEE = Availability x Performance x Quality, computed from a synthetic production-line shift
log. The generator picks the shift parameters and computes the ground truth itself from the
standard formula — correct by construction, never a model's opinion.
"""
from __future__ import annotations

import random
from datetime import datetime, timezone
from typing import Any

from generators.base import Generator


class OEEGenerator(Generator):
    name = "oee"

    def generate(self, seed: int, difficulty: str = "standard") -> dict[str, Any]:
        rng = random.Random(seed)

        planned_time_min = rng.choice([360, 420, 480, 540, 600, 720, 960])
        downtime_frac = (
            rng.uniform(0.03, 0.12) if difficulty == "standard" else rng.uniform(0.10, 0.25)
        )
        downtime_min = round(planned_time_min * downtime_frac)
        operating_time_min = planned_time_min - downtime_min

        ideal_rate_upm = rng.choice([4, 5, 6, 8, 10, 12, 15, 20, 25])
        max_possible_units = operating_time_min * ideal_rate_upm

        performance_frac = (
            rng.uniform(0.80, 0.98) if difficulty == "standard" else rng.uniform(0.55, 0.85)
        )
        units_produced = max(1, round(max_possible_units * performance_frac))

        reject_frac = (
            rng.uniform(0.005, 0.05) if difficulty == "standard" else rng.uniform(0.03, 0.15)
        )
        rejects = round(units_produced * reject_frac)
        rejects = min(rejects, units_produced - 1) if units_produced > 1 else 0

        availability = operating_time_min / planned_time_min
        performance = (units_produced / operating_time_min) / ideal_rate_upm
        quality = (units_produced - rejects) / units_produced
        oee = availability * performance * quality

        prompt = (
            f"A production line ran for a planned {planned_time_min} minutes. Downtime during "
            f"the shift totaled {downtime_min} minutes. The line's ideal (design) rate is "
            f"{ideal_rate_upm} units per minute. It produced {units_produced} total units, of "
            f"which {rejects} were rejected for quality.\n\n"
            "Compute the line's OEE (Overall Equipment Effectiveness) as a decimal, to 4 "
            "decimal places, using:\n"
            "OEE = Availability x Performance x Quality\n"
            "Availability = Operating Time / Planned Time, where Operating Time = Planned "
            "Time - Downtime\n"
            "Performance = (Total Units Produced / Operating Time) / Ideal Rate\n"
            "Quality = (Total Units Produced - Rejects) / Total Units Produced"
        )

        return {
            "id": f"compute.oee.{seed:06d}",
            "family": "computed",
            "domain": "continuous_improvement",
            "reasoning_tier": "L2",
            "answer_format": "numeric",
            "prompt": prompt,
            "context": {
                "planned_time_min": planned_time_min,
                "downtime_min": downtime_min,
                "units_produced": units_produced,
                "ideal_rate_upm": ideal_rate_upm,
                "rejects": rejects,
            },
            "ground_truth": {
                "value": round(oee, 4),
                "tolerance": 0.001,
                "tolerance_type": "absolute",
            },
            "scorer": "numeric",
            "generator": self.name,
            "seed": seed,
            "difficulty": difficulty,
            "source": None,
            "source_url": None,
            "created": datetime.now(timezone.utc).date().isoformat(),
            "public": True,
        }
