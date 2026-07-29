"""Inventory policy generator.

Classic continuous-review (Q, R) policy under demand uncertainty: Economic Order Quantity,
safety stock, and reorder point from annual demand, ordering cost, holding cost, daily demand
variability, supplier lead time, and a target cycle-service level. The generator computes the
ground truth itself from the standard inventory-policy formulas -- correct by construction,
never a model's opinion.
"""
from __future__ import annotations

import math
import random
from datetime import datetime, timezone
from typing import Any

from generators.base import Generator

WORKING_DAYS_PER_YEAR = 250

# Standard-normal z-values for common cycle-service levels (textbook lookup table -- avoids a
# scipy/normal-inverse-CDF dependency for a small, fixed set of service levels).
SERVICE_LEVEL_Z = {
    0.90: 1.28,
    0.95: 1.65,
    0.975: 1.96,
    0.99: 2.33,
    0.999: 3.09,
}


class InventoryPolicyGenerator(Generator):
    name = "inventory_policy"

    def generate(self, seed: int, difficulty: str = "standard") -> dict[str, Any]:
        rng = random.Random(seed)

        annual_demand = rng.choice([1200, 2400, 3600, 4800, 6000, 9000, 12000, 18000])
        ordering_cost = rng.choice([25, 40, 50, 75, 100, 150, 200])
        unit_cost = rng.choice([5, 8, 10, 15, 20, 25, 40, 50])
        holding_rate = (
            rng.uniform(0.15, 0.30) if difficulty == "standard" else rng.uniform(0.10, 0.40)
        )
        holding_cost = round(unit_cost * holding_rate, 2)

        avg_daily_demand = annual_demand / WORKING_DAYS_PER_YEAR
        demand_cv = (
            rng.uniform(0.10, 0.25) if difficulty == "standard" else rng.uniform(0.05, 0.45)
        )
        daily_demand_stdev = round(avg_daily_demand * demand_cv, 2)

        lead_time_days = (
            rng.choice([3, 5, 7, 10, 14, 21])
            if difficulty == "standard"
            else rng.choice([2, 4, 6, 8, 12, 18, 25])
        )

        service_level = rng.choice(sorted(SERVICE_LEVEL_Z))
        z = SERVICE_LEVEL_Z[service_level]

        eoq = math.sqrt((2 * annual_demand * ordering_cost) / holding_cost)
        lead_time_demand_stdev = daily_demand_stdev * math.sqrt(lead_time_days)
        safety_stock = z * lead_time_demand_stdev
        reorder_point = avg_daily_demand * lead_time_days + safety_stock

        prompt = (
            f"A distribution center manages one SKU with the following annual demand and cost "
            f"parameters:\n\n"
            f"Annual demand: {annual_demand} units\n"
            f"Ordering cost: ${ordering_cost} per order\n"
            f"Holding cost: ${holding_cost:.2f} per unit per year\n"
            f"Average daily demand standard deviation: {daily_demand_stdev:.2f} units "
            f"(assume {WORKING_DAYS_PER_YEAR} working days per year)\n"
            f"Supplier lead time: {lead_time_days} days\n"
            f"Target cycle-service level: {service_level * 100:g}% (z = {z})\n\n"
            "Using standard continuous-review (Q, R) inventory-policy formulas:\n"
            "EOQ = sqrt(2 x Annual Demand x Ordering Cost / Holding Cost)\n"
            "Average Daily Demand = Annual Demand / Working Days Per Year\n"
            "Safety Stock = z x Daily Demand Standard Deviation x sqrt(Lead Time in days)\n"
            "Reorder Point = (Average Daily Demand x Lead Time in days) + Safety Stock\n\n"
            "Compute: (1) the Economic Order Quantity, (2) the Safety Stock, and (3) the "
            "Reorder Point, each rounded to 2 decimal places.\n\n"
            "Report 3 numbers in this order: EOQ, Safety Stock, Reorder Point."
        )

        parts = [
            {"value": round(eoq, 2), "tolerance": 0.01, "tolerance_type": "relative"},
            {"value": round(safety_stock, 2), "tolerance": 0.01, "tolerance_type": "relative"},
            {"value": round(reorder_point, 2), "tolerance": 0.01, "tolerance_type": "relative"},
        ]

        return {
            "id": f"compute.inventory_policy.{seed:06d}",
            "family": "computed",
            "domain": "supply_chain_sop",
            "reasoning_tier": "L2",
            "answer_format": "numeric",
            "prompt": prompt,
            "context": {
                "annual_demand": annual_demand,
                "ordering_cost": ordering_cost,
                "unit_cost": unit_cost,
                "holding_cost": holding_cost,
                "daily_demand_stdev": daily_demand_stdev,
                "lead_time_days": lead_time_days,
                "service_level": service_level,
                "z": z,
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
