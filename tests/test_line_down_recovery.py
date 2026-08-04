"""Tests for simulator/scenarios/line_down_recovery.py (unit 2.2).

The core acceptance criterion for this unit ("both score bounds work") is
test_reference_never_worse_than_baseline_swept and
test_reference_strictly_better_than_baseline_for_most_seeds below: across a broad seed sweep,
the reference bound is never worse than the baseline bound (a mandatory property for KPI
normalization to be well-defined) and is strictly better on the large majority of instances (so
the bound is meaningfully non-degenerate, not just a tie every time).
"""
from __future__ import annotations

import pytest

from simulator.scenarios import line_down_recovery as ldr

SWEEP_SEEDS = range(500)
DIFFICULTIES = ("standard", "hard")


def test_generate_is_deterministic():
    a = ldr.generate(42, "standard")
    b = ldr.generate(42, "standard")
    assert a == b


def test_generate_distinct_seeds_differ():
    a = ldr.generate(1, "standard")
    b = ldr.generate(2, "standard")
    assert a != b


def test_generate_rejects_unknown_difficulty():
    with pytest.raises(ValueError):
        ldr.generate(1, "impossible")


@pytest.mark.parametrize("difficulty,expected_machines,expected_jobs", [
    ("standard", ldr.STANDARD_NUM_MACHINES, ldr.STANDARD_NUM_JOBS),
    ("hard", ldr.HARD_NUM_MACHINES, ldr.HARD_NUM_JOBS),
])
def test_generate_job_and_machine_counts_per_difficulty(difficulty, expected_machines, expected_jobs):
    for seed in range(20):
        scenario = ldr.generate(seed, difficulty)
        state = scenario["initial_state"]
        assert len(state["machines"]) == expected_machines
        assert len(state["jobs"]) == expected_jobs


def test_generate_exactly_one_machine_goes_down_mid_shift_within_horizon():
    for seed in range(50):
        for difficulty in DIFFICULTIES:
            scenario = ldr.generate(seed, difficulty)
            state = scenario["initial_state"]
            horizon = scenario["horizon"]
            down_machines = [m for m in state["machines"].values() if m["down_until"] > 0]
            assert len(down_machines) == 1
            down_until = down_machines[0]["down_until"]
            assert 0 < down_until < horizon


def test_generate_all_jobs_released_at_zero_and_not_yet_complete():
    scenario = ldr.generate(7, "standard")
    for job in scenario["initial_state"]["jobs"].values():
        assert job["release"] == 0
        assert job["completed_at"] is None
        assert job["remaining_work"] > 0


def test_total_weighted_tardiness_adds_penalty_for_unfinished_jobs():
    final_state = {
        "cumulative": {"weighted_tardiness": 5.0},
        "jobs": {
            "j0": {"weight": 2.0, "due": 3, "completed_at": 4},  # already costed in cumulative
            "j1": {"weight": 3.0, "due": 4, "completed_at": None},  # unfinished by horizon=10
        },
    }
    # unfinished penalty: weight 3.0 * max(0, 10 - 4) = 18.0, on top of the existing 5.0
    assert ldr.total_weighted_tardiness(final_state, horizon=10) == 5.0 + 18.0


def test_total_weighted_tardiness_no_penalty_when_all_jobs_complete():
    final_state = {
        "cumulative": {"weighted_tardiness": 5.0},
        "jobs": {"j0": {"weight": 2.0, "due": 3, "completed_at": 4}},
    }
    assert ldr.total_weighted_tardiness(final_state, horizon=100) == 5.0


def test_baseline_and_reference_episodes_run_without_illegal_actions():
    for seed in SWEEP_SEEDS:
        for difficulty in DIFFICULTIES:
            scenario = ldr.generate(seed, difficulty)
            init = scenario["initial_state"]
            horizon = scenario["horizon"]
            ldr.baseline_episode(init, horizon)
            ldr.reference_episode(init, horizon)


def test_reference_never_worse_than_baseline_swept():
    for seed in SWEEP_SEEDS:
        for difficulty in DIFFICULTIES:
            scenario = ldr.generate(seed, difficulty)
            init = scenario["initial_state"]
            horizon = scenario["horizon"]
            final_baseline, _ = ldr.baseline_episode(init, horizon)
            final_reference, _ = ldr.reference_episode(init, horizon)
            baseline_kpi = ldr.total_weighted_tardiness(final_baseline, horizon)
            reference_kpi = ldr.total_weighted_tardiness(final_reference, horizon)
            assert reference_kpi <= baseline_kpi + 1e-9, (seed, difficulty, baseline_kpi, reference_kpi)


def test_reference_strictly_better_than_baseline_for_most_seeds():
    strictly_better = 0
    total = 0
    for seed in SWEEP_SEEDS:
        for difficulty in DIFFICULTIES:
            scenario = ldr.generate(seed, difficulty)
            init = scenario["initial_state"]
            horizon = scenario["horizon"]
            final_baseline, _ = ldr.baseline_episode(init, horizon)
            final_reference, _ = ldr.reference_episode(init, horizon)
            baseline_kpi = ldr.total_weighted_tardiness(final_baseline, horizon)
            reference_kpi = ldr.total_weighted_tardiness(final_reference, horizon)
            total += 1
            if reference_kpi < baseline_kpi - 1e-9:
                strictly_better += 1
    # the reference bound should be a meaningful, non-degenerate improvement, not just a tie
    assert strictly_better / total > 0.9


def test_episodes_are_deterministic():
    scenario_a = ldr.generate(123, "hard")
    scenario_b = ldr.generate(123, "hard")
    assert scenario_a == scenario_b

    final_a, history_a = ldr.reference_episode(scenario_a["initial_state"], scenario_a["horizon"])
    final_b, history_b = ldr.reference_episode(scenario_b["initial_state"], scenario_b["horizon"])
    assert final_a == final_b
    assert history_a == history_b
