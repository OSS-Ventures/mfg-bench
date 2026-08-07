"""Tests for scorers/simulated.py (unit 2.4).

Hand-verified cases build small, manually-worked-out `initial_state`s (one machine, one job) so
the replay-through-the-real-engine arithmetic can be checked by hand. A separate sweep
(`test_*_baseline_and_reference_plans_score_their_bounds`) reconstructs each real scenario's own
baseline/reference action sequence via the real generators and confirms feeding it back through
the scorer reproduces exactly the score bounds (0.0 / 1.0) those trajectories are supposed to
define -- the actual acceptance bar for KPI-delta normalization.
"""
from __future__ import annotations

import copy

import pytest

from generators.simulated_decision import (
    DemandSpikeRebalanceDecisionGenerator,
    LineDownRecoveryDecisionGenerator,
)
from scorers.simulated import SimulatedScorer
from simulator import engine, policies
from simulator.scenarios import demand_spike_rebalance as dsr
from simulator.scenarios import line_down_recovery as ldr

SCORER = SimulatedScorer()


def _ldr_task(kpi_baseline: float, kpi_reference: float, horizon: int, due: int = 2) -> dict:
    """A minimal `line_down_recovery`-scenario task: one machine (capacity 5), one job
    (10 work units, weight 2), never down."""
    initial_state = {
        "time": 0,
        "machines": {"m0": {"capacity": 5.0, "down_until": 0}},
        "jobs": {
            "j0": {
                "remaining_work": 10.0,
                "release": 0,
                "due": due,
                "weight": 2.0,
                "completed_at": None,
            }
        },
        "cumulative": {
            "weighted_tardiness": 0.0,
            "overtime_cost": 0.0,
            "jobs_completed": 0,
            "jobs_completed_on_time": 0,
        },
    }
    return {
        "ground_truth": {
            "scenario": "line_down_recovery",
            "initial_state": initial_state,
            "horizon": horizon,
            "kpi_baseline": kpi_baseline,
            "kpi_reference": kpi_reference,
        }
    }


# Fixture used by the "full" (assign every step until done, then idle) / "idle" (never assign) /
# "partial" (idle first, then assign) plans below: capacity 5, remaining_work 10, due 2, weight
# 2, horizon 4.
#   - idle for all 4 steps: job never completes; unfinished penalty = weight * max(0, horizon -
#     due) = 2 * max(0, 4 - 2) = 4.  -> kpi_baseline = 4.0
#   - assign steps 0-1 (then idle, since the job is done): completes at t=2, on time (due=2) ->
#     weighted tardiness 0.  -> kpi_reference = 0.0
FULL_PLAN = [{"assignments": {"m0": "j0"}}, {"assignments": {"m0": "j0"}}, {}, {}]
IDLE_PLAN = [{}, {}, {}, {}]
# idle step 0, then assign steps 1-2 (then idle): completes at t=3, lateness = 3 - 2 = 1,
# weighted tardiness = 2 * 1 = 2.
PARTIAL_PLAN = [{}, {"assignments": {"m0": "j0"}}, {"assignments": {"m0": "j0"}}, {}]


def test_plan_matching_the_reference_kpi_scores_1():
    task = _ldr_task(kpi_baseline=4.0, kpi_reference=0.0, horizon=4)
    assert SCORER.score(task, FULL_PLAN) == 1.0


def test_plan_matching_the_baseline_kpi_scores_0():
    task = _ldr_task(kpi_baseline=4.0, kpi_reference=0.0, horizon=4)
    assert SCORER.score(task, IDLE_PLAN) == 0.0


def test_plan_midway_between_bounds_scores_midway():
    # kpi_model = 2.0; score = clip((2 - 4) / (0 - 4), 0, 1) = clip(0.5, 0, 1) = 0.5.
    task = _ldr_task(kpi_baseline=4.0, kpi_reference=0.0, horizon=4)
    assert SCORER.score(task, PARTIAL_PLAN) == 0.5


def test_worse_than_baseline_plan_clips_to_0():
    # One machine, capacity 100 (deliberately way more than needed); one job, 1 work unit, due
    # at step 5, weight 1, horizon 1, demand_spike_rebalance's `total_cost` KPI. Assigning
    # without overtime finishes the (trivial) job instantly and on time -> cost 0 ->
    # kpi_reference = 0.0. Idle -> the job never completes -> cost = weight * 50
    # (SERVICE_LEVEL_MISS_PENALTY) = 50.0 -> kpi_baseline = 50.0. A plan that pays for overtime
    # it doesn't need still finishes on time (no missed-order penalty) but burns overtime cost =
    # extra_capacity (100 * 0.5 = 50) * OVERTIME_COST_PER_UNIT (10) = 500 -- far worse than
    # baseline. score = clip((500 - 50) / (0 - 50), 0, 1) = clip(-9.0, 0, 1) = 0.0.
    initial_state = {
        "time": 0,
        "machines": {"m0": {"capacity": 100.0, "down_until": 0}},
        "jobs": {
            "j0": {
                "remaining_work": 1.0,
                "release": 0,
                "due": 5,
                "weight": 1.0,
                "completed_at": None,
            }
        },
        "cumulative": {
            "weighted_tardiness": 0.0,
            "overtime_cost": 0.0,
            "jobs_completed": 0,
            "jobs_completed_on_time": 0,
        },
    }
    task = {
        "ground_truth": {
            "scenario": "demand_spike_rebalance",
            "initial_state": initial_state,
            "horizon": 1,
            "kpi_baseline": 50.0,
            "kpi_reference": 0.0,
        }
    }
    wasteful_plan = [{"assignments": {"m0": "j0"}, "overtime": {"m0": True}}]
    assert SCORER.score(task, wasteful_plan) == 0.0


def test_kpi_reference_equal_kpi_baseline_scores_1_only_on_exact_match():
    # due=2, weight=2 (this fixture's fixed job weight), horizon=7 -> idling the whole horizon
    # leaves the job unfinished with penalty = 2 * max(0, 7 - 2) = 10, hand-picked to equal both
    # (tied) bounds below.
    task = _ldr_task(kpi_baseline=10.0, kpi_reference=10.0, horizon=7, due=2)
    idle_plan = [{}] * 7
    assert SCORER.score(task, idle_plan) == 1.0

    # Finishing the job on time instead (assign steps 0-1, then idle) gives kpi_model = 0.0,
    # which does not match the tied bound -> must score 0, not 1.
    finish_plan = [
        {"assignments": {"m0": "j0"}},
        {"assignments": {"m0": "j0"}},
        {},
        {},
        {},
        {},
        {},
    ]
    assert SCORER.score(task, finish_plan) == 0.0


@pytest.mark.parametrize(
    "malformed_plan",
    [
        "not a list",
        None,
        {},
        [{}],  # wrong length (horizon is 4)
        [{}, {}, {}, "not a dict"],
        [{}, {}, {}, {"assignments": "not a dict"}],
        [{}, {}, {}, {"overtime": "not a dict"}],
    ],
)
def test_structurally_invalid_plan_scores_0(malformed_plan):
    task = _ldr_task(kpi_baseline=4.0, kpi_reference=0.0, horizon=4)
    assert SCORER.score(task, malformed_plan) == 0.0


@pytest.mark.parametrize(
    "illegal_plan",
    [
        # unknown job
        [{"assignments": {"m0": "no-such-job"}}, {}, {}, {}],
        # unknown machine
        [{"assignments": {"no-such-machine": "j0"}}, {}, {}, {}],
        # re-assigning a job that already completed (after steps 0-1 finish it)
        [
            {"assignments": {"m0": "j0"}},
            {"assignments": {"m0": "j0"}},
            {"assignments": {"m0": "j0"}},
            {},
        ],
    ],
)
def test_engine_rejected_plan_scores_0(illegal_plan):
    task = _ldr_task(kpi_baseline=4.0, kpi_reference=0.0, horizon=4)
    assert SCORER.score(task, illegal_plan) == 0.0


def _actions_from_policy(initial_state: dict, policy_fn, horizon: int) -> list[dict]:
    """Test-only helper: capture the exact per-step action sequence a policy takes, so it can be
    fed back into `SimulatedScorer` as a "model" plan and checked against the score bound that
    trajectory is supposed to define. Mirrors `simulator.policies.simulate_episode`'s own driving
    loop but returns the actions instead of discarding them."""
    state = copy.deepcopy(initial_state)
    actions = []
    for _ in range(horizon):
        action = policy_fn(state)
        actions.append(action)
        state, _ = engine.step(state, action)
    return actions


SWEEP = [(seed, difficulty) for seed in range(60) for difficulty in ("standard", "hard")]


@pytest.mark.parametrize("seed,difficulty", SWEEP)
def test_line_down_recovery_baseline_and_reference_plans_score_their_bounds(seed, difficulty):
    task = LineDownRecoveryDecisionGenerator().generate(seed=seed, difficulty=difficulty)
    gt = task["ground_truth"]
    initial_state, horizon = gt["initial_state"], gt["horizon"]

    if gt["kpi_reference"] == gt["kpi_baseline"]:
        pytest.skip("degenerate seed where reference ties baseline; covered by the hand-verified tie case")

    baseline_plan = _actions_from_policy(initial_state, policies.baseline_policy, horizon)
    baseline_final, _ = policies.simulate_episode(initial_state, policies.baseline_policy, horizon)
    if ldr.total_weighted_tardiness(baseline_final, horizon) == gt["kpi_baseline"]:
        assert SCORER.score(task, baseline_plan) == 0.0

    reference_plan = _actions_from_policy(initial_state, policies.reference_policy, horizon)
    reference_final, _ = policies.simulate_episode(initial_state, policies.reference_policy, horizon)
    if ldr.total_weighted_tardiness(reference_final, horizon) == gt["kpi_reference"]:
        assert SCORER.score(task, reference_plan) == 1.0


@pytest.mark.parametrize("seed,difficulty", SWEEP)
def test_demand_spike_rebalance_baseline_and_reference_plans_score_their_bounds(seed, difficulty):
    task = DemandSpikeRebalanceDecisionGenerator().generate(seed=seed, difficulty=difficulty)
    gt = task["ground_truth"]
    initial_state, horizon = gt["initial_state"], gt["horizon"]

    if gt["kpi_reference"] == gt["kpi_baseline"]:
        pytest.skip("degenerate seed where reference ties baseline; covered by the hand-verified tie case")

    baseline_plan = _actions_from_policy(initial_state, policies.baseline_policy, horizon)
    baseline_final, _ = policies.simulate_episode(initial_state, policies.baseline_policy, horizon)
    if dsr.total_cost(baseline_final) == gt["kpi_baseline"]:
        assert SCORER.score(task, baseline_plan) == 0.0

    reference_plan = _actions_from_policy(initial_state, dsr._reference_policy_with_overtime, horizon)
    reference_final, _ = policies.simulate_episode(
        initial_state, dsr._reference_policy_with_overtime, horizon
    )
    if dsr.total_cost(reference_final) == gt["kpi_reference"]:
        assert SCORER.score(task, reference_plan) == 1.0
