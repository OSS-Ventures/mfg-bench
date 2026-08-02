"""Standard-cost variance generator.

Given a period's actual output, the standard (material quantity + price, labor hours + rate)
set by the costing system, and the actual quantities/prices/hours/rates incurred, computes the
four classic standard-cost variances:
- Material Price Variance: the cost impact of paying a different price per unit of material
  than standard, at the actual quantity used.
- Material Usage (Quantity) Variance: the cost impact of using a different quantity of
  material than the standard allowed for the actual output, at the standard price.
- Labor Rate Variance: the cost impact of paying a different rate per hour than standard, at
  the actual hours worked.
- Labor Efficiency Variance: the cost impact of using a different number of labor hours than
  the standard allowed for the actual output, at the standard rate.

Sign convention: a positive variance is unfavorable (actual cost exceeded standard); a
negative variance is favorable. All values are derived directly from the given standards and
actuals -- correct by construction, never a model's opinion.
"""
from __future__ import annotations

import random
from datetime import datetime, timezone
from typing import Any

from generators.base import Generator


class StandardCostVarianceGenerator(Generator):
    name = "standard_cost_variance"

    def generate(self, seed: int, difficulty: str = "standard") -> dict[str, Any]:
        rng = random.Random(seed)

        deviation_range = (0.85, 1.15) if difficulty == "standard" else (0.75, 1.25)
        output_low, output_high = (500, 2000) if difficulty == "standard" else (1000, 5000)

        actual_output_units = rng.randint(output_low, output_high)

        standard_price_per_unit = rng.randint(5, 25)
        actual_price_per_unit = round(standard_price_per_unit * rng.uniform(*deviation_range), 2)

        standard_qty_per_unit = rng.randint(2, 8)
        standard_qty_allowed = float(standard_qty_per_unit * actual_output_units)
        actual_qty_used = round(standard_qty_allowed * rng.uniform(*deviation_range), 1)

        standard_rate_per_hour = rng.randint(15, 40)
        actual_rate_per_hour = round(standard_rate_per_hour * rng.uniform(*deviation_range), 2)

        standard_hours_per_unit = round(rng.uniform(0.5, 3.0), 2)
        standard_hours_allowed = round(standard_hours_per_unit * actual_output_units, 2)
        actual_hours_used = round(standard_hours_allowed * rng.uniform(*deviation_range), 1)

        context = {
            "actual_output_units": actual_output_units,
            "standard_price_per_unit": standard_price_per_unit,
            "actual_price_per_unit": actual_price_per_unit,
            "standard_qty_per_unit": standard_qty_per_unit,
            "standard_qty_allowed": standard_qty_allowed,
            "actual_qty_used": actual_qty_used,
            "standard_rate_per_hour": standard_rate_per_hour,
            "actual_rate_per_hour": actual_rate_per_hour,
            "standard_hours_per_unit": standard_hours_per_unit,
            "standard_hours_allowed": standard_hours_allowed,
            "actual_hours_used": actual_hours_used,
        }

        metrics = compute_standard_cost_variances(context)

        prompt = (
            f"A manufacturing plant produced {actual_output_units} units of a product during "
            "the period. Its standard costing system set the following per-unit standards for "
            "direct material and direct labor:\n\n"
            f"Direct material standard: {standard_qty_per_unit} lb per unit at a standard "
            f"price of ${standard_price_per_unit}/lb.\n"
            f"Direct labor standard: {standard_hours_per_unit:.2f} hours per unit at a "
            f"standard rate of ${standard_rate_per_hour}/hour.\n\n"
            f"Actual results for the period: {actual_qty_used:g} lb of material were "
            "purchased and used (assume no beginning or ending material inventory) at an "
            f"actual price of ${actual_price_per_unit:.2f}/lb, and {actual_hours_used:g} "
            f"direct labor hours were worked at an actual rate of ${actual_rate_per_hour:.2f}/"
            "hour.\n\n"
            "Formulas (sign convention: a positive variance is unfavorable -- actual cost "
            "exceeded standard; a negative variance is favorable):\n"
            "- Standard Quantity Allowed = standard quantity per unit x actual units "
            "produced.\n"
            "- Standard Hours Allowed = standard hours per unit x actual units produced.\n"
            "- Material Price Variance = (Actual Price - Standard Price) x Actual Quantity "
            "Used.\n"
            "- Material Usage (Quantity) Variance = (Actual Quantity Used - Standard "
            "Quantity Allowed) x Standard Price.\n"
            "- Labor Rate Variance = (Actual Rate - Standard Rate) x Actual Hours Used.\n"
            "- Labor Efficiency Variance = (Actual Hours Used - Standard Hours Allowed) x "
            "Standard Rate.\n\n"
            "Compute, in this order: (1) Material Price Variance, (2) Material Usage "
            "Variance, (3) Labor Rate Variance, (4) Labor Efficiency Variance -- each in "
            "dollars, rounded to 2 decimal places (positive = unfavorable, negative = "
            "favorable)."
        )

        parts = [
            {
                "value": metrics["material_price_variance"],
                "tolerance": 0.01,
                "tolerance_type": "relative",
            },
            {
                "value": metrics["material_usage_variance"],
                "tolerance": 0.01,
                "tolerance_type": "relative",
            },
            {
                "value": metrics["labor_rate_variance"],
                "tolerance": 0.01,
                "tolerance_type": "relative",
            },
            {
                "value": metrics["labor_efficiency_variance"],
                "tolerance": 0.01,
                "tolerance_type": "relative",
            },
        ]

        return {
            "id": f"compute.standard_cost_variance.{seed:06d}",
            "family": "computed",
            "domain": "cost_performance",
            "reasoning_tier": "L2",
            "answer_format": "numeric",
            "prompt": prompt,
            "context": context,
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


def compute_standard_cost_variances(context: dict[str, Any]) -> dict[str, float]:
    """Compute the material price/usage and labor rate/efficiency variances.

    Pure function of the given standards and actuals -- no randomness, no model opinion.
    Shared by the generator and independently re-derived (not called) by the hand-verified
    tests.
    """
    material_price_variance = (
        context["actual_price_per_unit"] - context["standard_price_per_unit"]
    ) * context["actual_qty_used"]
    material_usage_variance = (
        context["actual_qty_used"] - context["standard_qty_allowed"]
    ) * context["standard_price_per_unit"]
    labor_rate_variance = (
        context["actual_rate_per_hour"] - context["standard_rate_per_hour"]
    ) * context["actual_hours_used"]
    labor_efficiency_variance = (
        context["actual_hours_used"] - context["standard_hours_allowed"]
    ) * context["standard_rate_per_hour"]

    return {
        "material_price_variance": round(material_price_variance, 2),
        "material_usage_variance": round(material_usage_variance, 2),
        "labor_rate_variance": round(labor_rate_variance, 2),
        "labor_efficiency_variance": round(labor_efficiency_variance, 2),
    }
