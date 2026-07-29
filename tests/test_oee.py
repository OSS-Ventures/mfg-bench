"""OEE generator tests: determinism, schema validity, and hand-verified ground truth."""
import pytest

from generators.oee import OEEGenerator
from harness.validate import validate_task

# Each case: (seed, difficulty) -> context tuple (planned, downtime, produced, ideal, rejects)
# and the independently hand-computed OEE (avail x perf x qual, rounded to 4 dp).
HAND_VERIFIED_CASES = [
    (1, "standard", 0.7562),
    (42, "standard", 0.801),
    (123, "standard", 0.7689),
    (999, "standard", 0.799),
    (123, "hard", 0.4715),
]


@pytest.mark.parametrize("seed,difficulty,expected_oee", HAND_VERIFIED_CASES)
def test_ground_truth_matches_hand_computed_oee(seed, difficulty, expected_oee):
    task = OEEGenerator().generate(seed=seed, difficulty=difficulty)
    ctx = task["context"]

    operating_time = ctx["planned_time_min"] - ctx["downtime_min"]
    availability = operating_time / ctx["planned_time_min"]
    performance = (ctx["units_produced"] / operating_time) / ctx["ideal_rate_upm"]
    quality = (ctx["units_produced"] - ctx["rejects"]) / ctx["units_produced"]
    recomputed = round(availability * performance * quality, 4)

    assert recomputed == expected_oee
    assert task["ground_truth"]["value"] == expected_oee


def test_generation_is_deterministic():
    a = OEEGenerator().generate(seed=555, difficulty="standard")
    b = OEEGenerator().generate(seed=555, difficulty="standard")
    assert a["context"] == b["context"]
    assert a["ground_truth"] == b["ground_truth"]
    assert a["id"] == b["id"]


def test_different_seeds_yield_different_instances():
    a = OEEGenerator().generate(seed=1, difficulty="standard")
    b = OEEGenerator().generate(seed=2, difficulty="standard")
    assert a["context"] != b["context"]


def test_generated_task_validates_against_schema():
    task = OEEGenerator().generate(seed=123, difficulty="standard")
    validate_task(task)  # raises on failure


def test_quality_and_performance_stay_in_sane_bounds():
    for seed in range(20):
        task = OEEGenerator().generate(seed=seed, difficulty="standard")
        ctx = task["context"]
        assert ctx["rejects"] < ctx["units_produced"]
        assert 0 < task["ground_truth"]["value"] < 1
