"""MRP explosion generator.

Time-phased net-requirements calculation (lot-for-lot, no safety stock) for a single
component of a bill of materials: net requirements = gross requirements (parent demand x
BOM quantity-per) netted against on-hand inventory and scheduled receipts, carried period to
period, plus the planned-order-release period implied by the component's supplier lead time.
The generator computes the ground truth itself from the standard MRP netting logic —
correct by construction, never a model's opinion.
"""
from __future__ import annotations

import random
from datetime import datetime, timezone
from typing import Any

from generators.base import Generator

NUM_PERIODS = 4


class MRPGenerator(Generator):
    name = "mrp"

    def generate(self, seed: int, difficulty: str = "standard") -> dict[str, Any]:
        rng = random.Random(seed)

        qty_per = rng.choice([1, 2, 3, 4])
        demand_low, demand_high = (20, 80) if difficulty == "standard" else (50, 150)
        parent_demand = [rng.randint(demand_low, demand_high) for _ in range(NUM_PERIODS)]
        gross_requirements = [d * qty_per for d in parent_demand]

        lead_time = rng.randint(1, NUM_PERIODS - 1)
        beginning_on_hand = rng.randint(0, gross_requirements[0])

        scheduled_receipts = [0] * NUM_PERIODS
        if difficulty == "standard":
            if rng.random() < 0.5:
                idx = rng.randint(0, 1)
                scheduled_receipts[idx] = rng.randint(5, gross_requirements[idx] // 2 + 5)
        else:
            for idx in rng.sample(range(NUM_PERIODS), k=2):
                scheduled_receipts[idx] = rng.randint(10, gross_requirements[idx] // 2 + 10)

        net_requirements = self._net_requirements(
            gross_requirements, beginning_on_hand, scheduled_receipts
        )
        release_period_for_last = NUM_PERIODS - lead_time

        receipts_line = ", ".join(
            f"period {i + 1}: {qty}" for i, qty in enumerate(scheduled_receipts)
        )
        demand_line = ", ".join(
            f"period {i + 1}: {qty}" for i, qty in enumerate(parent_demand)
        )

        prompt = (
            "A finished product has the following independent demand schedule over the next "
            f"{NUM_PERIODS} periods: {demand_line}.\n\n"
            f"Building one unit of the finished product requires {qty_per} "
            f"{'unit' if qty_per == 1 else 'units'} of Component X per the bill of materials."
            "\n\n"
            f"Component X beginning on-hand inventory (before period 1): {beginning_on_hand}\n"
            f"Component X scheduled receipts by period: {receipts_line}\n"
            f"Component X supplier lead time: {lead_time} periods\n\n"
            "Using standard MRP time-phased netting logic (lot-for-lot ordering, no safety "
            "stock), for each period t:\n"
            "Gross Requirements[t] = Finished-product demand[t] x Quantity-per\n"
            "Net Requirements[t] = max(0, Gross Requirements[t] - (On-hand carried into period t "
            "+ Scheduled Receipts[t]))\n"
            "A planned order receipt exactly covers any shortfall (lot-for-lot), so On-hand "
            "carried into period t+1 = max(0, On-hand carried into period t + Scheduled "
            f"Receipts[t] - Gross Requirements[t]).\n\n"
            f"Compute Component X's Net Requirements for periods 1 through {NUM_PERIODS}.\n\n"
            f"Then, given the {lead_time}-period supplier lead time, in which period must the "
            f"planned order be released so its receipt is available in period {NUM_PERIODS} "
            f"(i.e., period {NUM_PERIODS} minus the lead time)?\n\n"
            f"Report {NUM_PERIODS + 1} numbers in this order: Net Requirement period 1, "
            f"Net Requirement period 2, ..., Net Requirement period {NUM_PERIODS}, then the "
            f"Planned Order Release period for period {NUM_PERIODS}'s receipt."
        )

        parts = [
            {"value": float(nr), "tolerance": 0.01, "tolerance_type": "absolute"}
            for nr in net_requirements
        ] + [
            {
                "value": float(release_period_for_last),
                "tolerance": 0.01,
                "tolerance_type": "absolute",
            }
        ]

        return {
            "id": f"compute.mrp.{seed:06d}",
            "family": "computed",
            "domain": "supply_chain_sop",
            "reasoning_tier": "L2",
            "answer_format": "numeric",
            "prompt": prompt,
            "context": {
                "parent_demand": parent_demand,
                "qty_per": qty_per,
                "beginning_on_hand": beginning_on_hand,
                "scheduled_receipts": scheduled_receipts,
                "lead_time": lead_time,
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

    @staticmethod
    def _net_requirements(
        gross_requirements: list[int],
        beginning_on_hand: int,
        scheduled_receipts: list[int],
    ) -> list[int]:
        net_requirements = []
        on_hand = beginning_on_hand
        for gross, receipt in zip(gross_requirements, scheduled_receipts):
            available = on_hand + receipt
            if available >= gross:
                net_requirements.append(0)
                on_hand = available - gross
            else:
                net_requirements.append(gross - available)
                on_hand = 0
        return net_requirements
