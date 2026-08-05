"""Tests for simulator/scenarios/demand_spike_rebalance.py (unit 2.3).

The core acceptance criterion for this unit ("both score bounds work") is
test_reference_never_worse_than_baseline_swept and
test_reference_strictly_better_than_baseline_for_most_seeds below: across a broad seed sweep, the
reference bound is never worse than the baseline bound (a mandatory property for KPI
normalization to be well-defined) and is strictly better on the large majority of instances (so
the bound is meaningfully non-degenerate, not just a tie every time). test_baseline_service_level
* / test_reference_service_level_improves_on_baseline_on_average confirm the scenario is actually
capacity-constrained (baseline misses due dates on real fraction of demand, not near-100%
service level by construction).
"""
from __future__ import annotations

import copy

import pytest

from simulator import policies
from simulator.scenarios import demand_spike_rebalance as dsr

SWEEP_SEEDS = range(500)
DIFFICULTIES = ("standard", "hard")


def test_generate_is_deterministic():
    a = dsr.generate(42, "standard")
    b = dsr.generate(42, "standard")
    assert a == b


def test_generate_distinct_seeds_differ():
    a = dsr.generate(1, "standard")
    b = dsr.generate(2, "standard")
    assert a != b


def test_generate_rejects_unknown_difficulty():
    with pytest.raises(ValueError):
        dsr.generate(1, "impossible")


@pytest.mark.parametrize("difficulty,expected_machines,expected_base,expected_spike", [
    ("standard", dsr.STANDARD_NUM_MACHINES, dsr.STANDARD_NUM_BASE_JOBS, dsr.STANDARD_NUM_SPIKE_JOBS),
    ("hard", dsr.HARD_NUM_MACHINES, dsr.HARD_NUM_BASE_JOBS, dsr.HARD_NUM_SPIKE_JOBS),
])
def test_generate_job_and_machine_counts_per_difficulty(difficulty, expected_machines, expected_base, expected_spike):
    for seed in range(20):
        scenario = dsr.generate(seed, difficulty)
        state = scenario["initial_state"]
        assert len(state["machines"]) == expected_machines
        base_jobs = [j for jid, j in state["jobs"].items() if jid.startswith("b")]
        spike_jobs = [j for jid, j in state["jobs"].items() if jid.startswith("s")]
        assert len(base_jobs) == expected_base
        assert len(spike_jobs) == expected_spike


def test_generate_base_jobs_released_at_zero_spike_jobs_released_mid_shift():
    for seed in range(50):
        for difficulty in DIFFICULTIES:
            scenario = dsr.generate(seed, difficulty)
            state = scenario["initial_state"]
            horizon = scenario["horizon"]
            base_releases = {j["release"] for jid, j in state["jobs"].items() if jid.startswith("b")}
            spike_releases = {j["release"] for jid, j in state["jobs"].items() if jid.startswith("s")}
            assert base_releases == {0}
            assert len(spike_releases) == 1
            spike_start = next(iter(spike_releases))
            assert 0 < spike_start < horizon
            for job in state["jobs"].values():
                assert job["completed_at"] is None
                assert job["remaining_work"] > 0
                assert job["due"] < horizon


def test_no_machine_ever_starts_down():
    # unlike line-down recovery, this scenario's pressure comes from demand volume, not
    # machine availability -- every machine should be up from t=0.
    for seed in range(20):
        for difficulty in DIFFICULTIES:
            scenario = dsr.generate(seed, difficulty)
            for machine in scenario["initial_state"]["machines"].values():
                assert machine["down_until"] == 0


def test_service_level_all_jobs_on_time():
    final_state = {
        "cumulative": {"overtime_cost": 0.0},
        "jobs": {
            "j0": {"weight": 2.0, "due": 3, "completed_at": 3},
            "j1": {"weight": 3.0, "due": 4, "completed_at": 4},
        },
    }
    assert dsr.service_level(final_state) == 1.0


def test_service_level_partial_hand_verified():
    # j0 (weight 2) on time, j1 (weight 3) late, j2 (weight 5) never completed.
    # on-time weight = 2, total weight = 10 -> service level = 0.2
    final_state = {
        "cumulative": {"overtime_cost": 0.0},
        "jobs": {
            "j0": {"weight": 2.0, "due": 3, "completed_at": 3},
            "j1": {"weight": 3.0, "due": 4, "completed_at": 6},
            "j2": {"weight": 5.0, "due": 5, "completed_at": None},
        },
    }
    assert dsr.service_level(final_state) == pytest.approx(0.2)


def test_total_cost_hand_verified():
    # overtime cost 40.0, plus a flat penalty for each not-on-time job:
    # j1 late (weight 3) -> 3 * 50 = 150; j2 never completed (weight 5) -> 5 * 50 = 250
    # j0 on time -> no penalty. total = 40 + 150 + 250 = 440
    final_state = {
        "cumulative": {"overtime_cost": 40.0},
        "jobs": {
            "j0": {"weight": 2.0, "due": 3, "completed_at": 3},
            "j1": {"weight": 3.0, "due": 4, "completed_at": 6},
            "j2": {"weight": 5.0, "due": 5, "completed_at": None},
        },
    }
    assert dsr.total_cost(final_state) == pytest.approx(40.0 + 3.0 * 50.0 + 5.0 * 50.0)


def test_total_cost_zero_when_everything_on_time_and_no_overtime():
    final_state = {
        "cumulative": {"overtime_cost": 0.0},
        "jobs": {"j0": {"weight": 2.0, "due": 3, "completed_at": 3}},
    }
    assert dsr.total_cost(final_state) == 0.0


def make_state(machines: dict, jobs: dict, time: int = 0) -> dict:
    return {
        "time": time,
        "machines": copy.deepcopy(machines),
        "jobs": copy.deepcopy(jobs),
        "cumulative": {
            "weighted_tardiness": 0.0,
            "overtime_cost": 0.0,
            "jobs_completed": 0,
            "jobs_completed_on_time": 0,
        },
    }


def test_reference_policy_with_overtime_triggers_when_worthwhile_hand_verified():
    # m0 capacity 2, assigned j0: remaining_work 10, due at t=5 -> time_left=5.
    # normal: 2*5=10 == remaining_work -> NOT strictly short (10 > 10 is False) -> no overtime.
    # Use remaining_work=11 so normal capacity (10) < needed, but overtime capacity
    # (2*1.5*5=15) >= 11 -> should trigger overtime.
    state = make_state(
        machines={"m0": {"capacity": 2.0, "down_until": 0}},
        jobs={"j0": {"remaining_work": 11.0, "release": 0, "due": 5, "weight": 1.0, "completed_at": None}},
    )
    action = dsr._reference_policy_with_overtime(state)
    assert action["assignments"] == {"m0": "j0"}
    assert action["overtime"] == {"m0": True}


def test_reference_policy_with_overtime_skips_when_normal_capacity_suffices():
    # m0 capacity 5, j0 remaining_work 10, due at t=5 -> time_left=5, needed_rate=2 <= capacity=5.
    state = make_state(
        machines={"m0": {"capacity": 5.0, "down_until": 0}},
        jobs={"j0": {"remaining_work": 10.0, "release": 0, "due": 5, "weight": 1.0, "completed_at": None}},
    )
    action = dsr._reference_policy_with_overtime(state)
    assert action["overtime"] == {}


def test_reference_policy_with_overtime_skips_when_hopeless_even_with_overtime():
    # m0 capacity 2, j0 remaining_work 100, due at t=2 -> time_left=2.
    # needed_rate = 50, way above capacity*OVERTIME_MULTIPLIER (2*1.5=3) -> overtime would be
    # wasted cost with no service-level benefit, so it should be skipped.
    state = make_state(
        machines={"m0": {"capacity": 2.0, "down_until": 0}},
        jobs={"j0": {"remaining_work": 100.0, "release": 0, "due": 2, "weight": 1.0, "completed_at": None}},
    )
    action = dsr._reference_policy_with_overtime(state)
    assert action["overtime"] == {}


def test_reference_policy_with_overtime_skips_when_already_overdue():
    # time_left <= 0 (job already past due) -> no overtime, matching the "no benefit" rule.
    state = make_state(
        machines={"m0": {"capacity": 2.0, "down_until": 0}},
        jobs={"j0": {"remaining_work": 5.0, "release": 0, "due": 0, "weight": 1.0, "completed_at": None}},
        time=1,
    )
    action = dsr._reference_policy_with_overtime(state)
    assert action["overtime"] == {}


def test_baseline_and_reference_episodes_run_without_illegal_actions():
    for seed in SWEEP_SEEDS:
        for difficulty in DIFFICULTIES:
            scenario = dsr.generate(seed, difficulty)
            init = scenario["initial_state"]
            horizon = scenario["horizon"]
            dsr.baseline_episode(init, horizon)
            dsr.reference_episode(init, horizon)


def test_reference_never_worse_than_baseline_swept():
    for seed in SWEEP_SEEDS:
        for difficulty in DIFFICULTIES:
            scenario = dsr.generate(seed, difficulty)
            init = scenario["initial_state"]
            horizon = scenario["horizon"]
            final_baseline, _ = dsr.baseline_episode(init, horizon)
            final_reference, _ = dsr.reference_episode(init, horizon)
            baseline_kpi = dsr.total_cost(final_baseline)
            reference_kpi = dsr.total_cost(final_reference)
            assert reference_kpi <= baseline_kpi + 1e-9, (seed, difficulty, baseline_kpi, reference_kpi)


def test_reference_strictly_better_than_baseline_for_most_seeds():
    strictly_better = 0
    total = 0
    for seed in SWEEP_SEEDS:
        for difficulty in DIFFICULTIES:
            scenario = dsr.generate(seed, difficulty)
            init = scenario["initial_state"]
            horizon = scenario["horizon"]
            final_baseline, _ = dsr.baseline_episode(init, horizon)
            final_reference, _ = dsr.reference_episode(init, horizon)
            baseline_kpi = dsr.total_cost(final_baseline)
            reference_kpi = dsr.total_cost(final_reference)
            total += 1
            if reference_kpi < baseline_kpi - 1e-9:
                strictly_better += 1
    # the reference bound should be a meaningful, non-degenerate improvement, not just a tie
    assert strictly_better / total > 0.8


def test_baseline_service_level_shows_genuine_capacity_pressure():
    # the scenario must actually be capacity-constrained for the baseline: it should not achieve
    # near-perfect service level "for free" (that would mean the spike creates no real pressure).
    levels = []
    for seed in SWEEP_SEEDS:
        for difficulty in DIFFICULTIES:
            scenario = dsr.generate(seed, difficulty)
            init = scenario["initial_state"]
            horizon = scenario["horizon"]
            final_baseline, _ = dsr.baseline_episode(init, horizon)
            levels.append(dsr.service_level(final_baseline))
    assert sum(levels) / len(levels) < 0.9


def test_reference_service_level_improves_on_baseline_on_average():
    baseline_levels = []
    reference_levels = []
    for seed in SWEEP_SEEDS:
        for difficulty in DIFFICULTIES:
            scenario = dsr.generate(seed, difficulty)
            init = scenario["initial_state"]
            horizon = scenario["horizon"]
            final_baseline, _ = dsr.baseline_episode(init, horizon)
            final_reference, _ = dsr.reference_episode(init, horizon)
            baseline_levels.append(dsr.service_level(final_baseline))
            reference_levels.append(dsr.service_level(final_reference))
    assert sum(reference_levels) / len(reference_levels) > sum(baseline_levels) / len(baseline_levels)


def test_episodes_are_deterministic():
    scenario_a = dsr.generate(123, "hard")
    scenario_b = dsr.generate(123, "hard")
    assert scenario_a == scenario_b

    final_a, history_a = dsr.reference_episode(scenario_a["initial_state"], scenario_a["horizon"])
    final_b, history_b = dsr.reference_episode(scenario_b["initial_state"], scenario_b["horizon"])
    assert final_a == final_b
    assert history_a == history_b


def test_reference_policy_with_overtime_never_double_books_or_illegally_assigns():
    # sanity check that the overtime wrapper doesn't corrupt the underlying assignment logic
    # inherited from policies.reference_policy.
    for seed in range(50):
        for difficulty in DIFFICULTIES:
            scenario = dsr.generate(seed, difficulty)
            policies.simulate_episode(
                scenario["initial_state"], dsr._reference_policy_with_overtime, scenario["horizon"]
            )
