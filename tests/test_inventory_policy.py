"""Inventory policy generator tests: hand-verified EOQ/safety-stock/ROP cases, determinism,
and schema validity."""
import math

import pytest

from generators.inventory_policy import (
    SERVICE_LEVEL_Z,
    WORKING_DAYS_PER_YEAR,
    InventoryPolicyGenerator,
)
from harness.validate import validate_task

# Each case: (seed, difficulty) -> the three ground-truth numbers (EOQ, Safety Stock, Reorder
# Point), independently hand-computed from the generator's own context via the standard
# continuous-review (Q, R) formulas:
#   EOQ = sqrt(2 * annual_demand * ordering_cost / holding_cost)
#   avg_daily_demand = annual_demand / 250
#   safety_stock = z * daily_demand_stdev * sqrt(lead_time_days)
#   reorder_point = avg_daily_demand * lead_time_days + safety_stock
HAND_VERIFIED_CASES = [
    # seed=1: D=3600, S=100, H=1.51 -> EOQ=sqrt(2*3600*100/1.51)=690.52
    # avg_daily=14.4, stdev=2.51, L=10, z=2.33 -> ss=2.33*2.51*sqrt(10)=18.49
    # rop=14.4*10+18.49=162.49
    (1, "standard", [690.52, 18.49, 162.49]),
    # seed=42: D=2400, S=25, H=3.73 -> EOQ=sqrt(2*2400*25/3.73)=179.36
    # avg_daily=9.6, stdev=1.16, L=3, z=3.09 -> ss=3.09*1.16*sqrt(3)=6.21
    # rop=9.6*3+6.21=35.01
    (42, "standard", [179.36, 6.21, 35.01]),
    # seed=999: D=2400, S=200, H=11.13 -> EOQ=sqrt(2*2400*200/11.13)=293.69
    # avg_daily=9.6, stdev=2.22, L=21, z=1.96 -> ss=1.96*2.22*sqrt(21)=19.94
    # rop=9.6*21+19.94=221.54
    (999, "standard", [293.69, 19.94, 221.54]),
    # seed=123 hard: D=1200, S=50, H=2.65 -> EOQ=sqrt(2*1200*50/2.65)=212.8
    # avg_daily=4.8, stdev=0.75, L=25, z=1.28 -> ss=1.28*0.75*sqrt(25)=4.8
    # rop=4.8*25+4.8=124.8
    (123, "hard", [212.8, 4.8, 124.8]),
    # seed=7 hard: D=9000, S=40, H=11.81 -> EOQ=sqrt(2*9000*40/11.81)=246.91
    # avg_daily=36.0, stdev=2.84, L=12, z=1.28 -> ss=1.28*2.84*sqrt(12)=12.59
    # rop=36.0*12+12.59=444.59
    (7, "hard", [246.91, 12.59, 444.59]),
]


@pytest.mark.parametrize("seed,difficulty,expected_parts", HAND_VERIFIED_CASES)
def test_ground_truth_matches_hand_computed_policy(seed, difficulty, expected_parts):
    task = InventoryPolicyGenerator().generate(seed=seed, difficulty=difficulty)
    parts = [p["value"] for p in task["ground_truth"]["parts"]]
    assert parts == expected_parts


def _recompute_policy(ctx):
    eoq = math.sqrt((2 * ctx["annual_demand"] * ctx["ordering_cost"]) / ctx["holding_cost"])
    avg_daily_demand = ctx["annual_demand"] / WORKING_DAYS_PER_YEAR
    safety_stock = ctx["z"] * ctx["daily_demand_stdev"] * math.sqrt(ctx["lead_time_days"])
    reorder_point = avg_daily_demand * ctx["lead_time_days"] + safety_stock
    return [round(eoq, 2), round(safety_stock, 2), round(reorder_point, 2)]


@pytest.mark.parametrize("seed", range(30))
@pytest.mark.parametrize("difficulty", ["standard", "hard"])
def test_ground_truth_matches_independent_recomputation(seed, difficulty):
    task = InventoryPolicyGenerator().generate(seed=seed, difficulty=difficulty)
    ctx = task["context"]
    recomputed = _recompute_policy(ctx)

    parts = [p["value"] for p in task["ground_truth"]["parts"]]
    assert parts == recomputed


def test_generation_is_deterministic():
    a = InventoryPolicyGenerator().generate(seed=555, difficulty="standard")
    b = InventoryPolicyGenerator().generate(seed=555, difficulty="standard")
    assert a["context"] == b["context"]
    assert a["ground_truth"] == b["ground_truth"]
    assert a["id"] == b["id"]


def test_different_seeds_yield_different_instances():
    a = InventoryPolicyGenerator().generate(seed=1, difficulty="standard")
    b = InventoryPolicyGenerator().generate(seed=2, difficulty="standard")
    assert a["context"] != b["context"]


def test_generated_task_validates_against_schema():
    task = InventoryPolicyGenerator().generate(seed=123, difficulty="standard")
    validate_task(task)  # raises on failure


def test_service_level_z_values_are_used_consistently():
    for seed in range(20):
        for difficulty in ["standard", "hard"]:
            task = InventoryPolicyGenerator().generate(seed=seed, difficulty=difficulty)
            ctx = task["context"]
            assert SERVICE_LEVEL_Z[ctx["service_level"]] == ctx["z"]


def test_policy_values_are_never_negative():
    for seed in range(20):
        for difficulty in ["standard", "hard"]:
            task = InventoryPolicyGenerator().generate(seed=seed, difficulty=difficulty)
            values = [p["value"] for p in task["ground_truth"]["parts"]]
            assert all(v >= 0 for v in values)
