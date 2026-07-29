"""MRP generator tests: hand-verified net-requirements cases, determinism, and schema validity."""
import pytest

from generators.mrp import MRPGenerator, NUM_PERIODS
from harness.validate import validate_task

# Each case: (seed, difficulty) -> the five ground-truth numbers (Net Requirement periods
# 1..4, then the Planned Order Release period for period 4's receipt), hand-computed from the
# generator's own context via the standard MRP time-phased netting formula:
#   Net[t] = max(0, Gross[t] - (OnHand[t-1] + ScheduledReceipts[t]))
#   OnHand[t] = max(0, OnHand[t-1] + ScheduledReceipts[t] - Gross[t])
#   Gross[t] = parent_demand[t] * qty_per
HAND_VERIFIED_CASES = [
    # seed=1: demand=[56,74,71,68] x qty_per=2 -> gross=[112,148,142,136];
    # on_hand=32, receipts=[0,65,0,0] -> net=[80,83,142,136]; lead_time=1 -> release=4-1=3.
    (1, "standard", [80.0, 83.0, 142.0, 136.0, 3.0]),
    # seed=42: demand=[21,67,37,35] x qty_per=1 -> gross=[21,67,37,35];
    # on_hand=4, receipts=[0,0,0,0] -> net=[17,67,37,35]; lead_time=1 -> release=3.
    (42, "standard", [17.0, 67.0, 37.0, 35.0, 3.0]),
    # seed=999: demand=[77,75,56,56] x qty_per=1 -> gross=[77,75,56,56];
    # on_hand=62, receipts=[0,11,0,0] -> net=[15,64,56,56]; lead_time=3 -> release=1.
    (999, "standard", [15.0, 64.0, 56.0, 56.0, 1.0]),
    # seed=123: demand=[84,61,148,102] x qty_per=1 -> gross=[84,61,148,102];
    # on_hand=13, receipts=[44,27,0,0] -> net=[27,34,148,102]; lead_time=2 -> release=2.
    (123, "hard", [27.0, 34.0, 148.0, 102.0, 2.0]),
    # seed=7: demand=[69,100,133,56] x qty_per=3 -> gross=[207,300,399,168];
    # on_hand=137, receipts=[84,24,0,0] -> net=[0,262,399,168]; lead_time=1 -> release=3.
    (7, "hard", [0.0, 262.0, 399.0, 168.0, 3.0]),
]


@pytest.mark.parametrize("seed,difficulty,expected_parts", HAND_VERIFIED_CASES)
def test_ground_truth_matches_hand_computed_net_requirements(seed, difficulty, expected_parts):
    task = MRPGenerator().generate(seed=seed, difficulty=difficulty)
    parts = [p["value"] for p in task["ground_truth"]["parts"]]
    assert parts == expected_parts


def _recompute_net_requirements(ctx):
    gross = [d * ctx["qty_per"] for d in ctx["parent_demand"]]
    on_hand = ctx["beginning_on_hand"]
    net = []
    for g, r in zip(gross, ctx["scheduled_receipts"]):
        available = on_hand + r
        if available >= g:
            net.append(0)
            on_hand = available - g
        else:
            net.append(g - available)
            on_hand = 0
    return net


@pytest.mark.parametrize("seed", range(30))
@pytest.mark.parametrize("difficulty", ["standard", "hard"])
def test_ground_truth_matches_independent_recomputation(seed, difficulty):
    task = MRPGenerator().generate(seed=seed, difficulty=difficulty)
    ctx = task["context"]
    recomputed_net = _recompute_net_requirements(ctx)
    recomputed_release = NUM_PERIODS - ctx["lead_time"]

    parts = [p["value"] for p in task["ground_truth"]["parts"]]
    assert parts == [float(n) for n in recomputed_net] + [float(recomputed_release)]


def test_generation_is_deterministic():
    a = MRPGenerator().generate(seed=555, difficulty="standard")
    b = MRPGenerator().generate(seed=555, difficulty="standard")
    assert a["context"] == b["context"]
    assert a["ground_truth"] == b["ground_truth"]
    assert a["id"] == b["id"]


def test_different_seeds_yield_different_instances():
    a = MRPGenerator().generate(seed=1, difficulty="standard")
    b = MRPGenerator().generate(seed=2, difficulty="standard")
    assert a["context"] != b["context"]


def test_generated_task_validates_against_schema():
    task = MRPGenerator().generate(seed=123, difficulty="standard")
    validate_task(task)  # raises on failure


def test_net_requirements_are_never_negative():
    for seed in range(20):
        for difficulty in ["standard", "hard"]:
            task = MRPGenerator().generate(seed=seed, difficulty=difficulty)
            net_requirements = [p["value"] for p in task["ground_truth"]["parts"][:-1]]
            assert all(n >= 0 for n in net_requirements)


def test_release_period_is_within_planning_horizon():
    for seed in range(20):
        for difficulty in ["standard", "hard"]:
            task = MRPGenerator().generate(seed=seed, difficulty=difficulty)
            release_period = task["ground_truth"]["parts"][-1]["value"]
            assert 1 <= release_period <= NUM_PERIODS - 1
