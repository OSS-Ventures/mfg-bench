"""Tests for simulator/policies.py (unit 2.2).

Hand-verified cases work through baseline_policy/reference_policy's own documented mechanics by
hand (static round-robin queue order for baseline; capacity-descending x priority-descending
pairing for reference) rather than re-deriving from the implementation.
"""
from __future__ import annotations

import copy

from simulator import engine, policies


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


def test_baseline_policy_assigns_static_round_robin_queues_hand_verified():
    # 4 jobs (j0..j3), 2 machines (m0, m1) -> sorted job order j0,j1,j2,j3 queues onto
    # m0,m1,m0,m1 respectively (index i % 2).
    state = make_state(
        machines={
            "m0": {"capacity": 5.0, "down_until": 0},
            "m1": {"capacity": 3.0, "down_until": 0},
        },
        jobs={
            "j0": {"remaining_work": 10.0, "release": 0, "due": 5, "weight": 1.0, "completed_at": None},
            "j1": {"remaining_work": 10.0, "release": 0, "due": 5, "weight": 1.0, "completed_at": None},
            "j2": {"remaining_work": 10.0, "release": 0, "due": 5, "weight": 1.0, "completed_at": None},
            "j3": {"remaining_work": 10.0, "release": 0, "due": 5, "weight": 1.0, "completed_at": None},
        },
    )
    action = policies.baseline_policy(state)
    assert action == {"assignments": {"m0": "j0", "m1": "j1"}}


def test_baseline_policy_skips_down_machine_and_does_not_reallocate_its_queue():
    state = make_state(
        machines={
            "m0": {"capacity": 5.0, "down_until": 3},
            "m1": {"capacity": 3.0, "down_until": 0},
        },
        jobs={
            "j0": {"remaining_work": 10.0, "release": 0, "due": 5, "weight": 1.0, "completed_at": None},
            "j1": {"remaining_work": 10.0, "release": 0, "due": 5, "weight": 1.0, "completed_at": None},
        },
        time=1,
    )
    action = policies.baseline_policy(state)
    # m0 is down at t=1 (< down_until=3); its queued job j0 is left idle, not reassigned to m1.
    assert action == {"assignments": {"m1": "j1"}}


def test_baseline_policy_advances_queue_once_earlier_job_completes():
    state = make_state(
        machines={"m0": {"capacity": 5.0, "down_until": 0}},
        jobs={
            "j0": {"remaining_work": 0.0, "release": 0, "due": 5, "weight": 1.0, "completed_at": 0},
            "j1": {"remaining_work": 10.0, "release": 0, "due": 5, "weight": 1.0, "completed_at": None},
        },
        time=1,
    )
    action = policies.baseline_policy(state)
    assert action == {"assignments": {"m0": "j1"}}


def test_reference_policy_pairs_fastest_machine_with_highest_priority_job_hand_verified():
    # priority = weight / remaining_work: j0 -> 1/2 = 0.5, j1 -> 4/1 = 4.0. j1 is more urgent,
    # so it should get the faster machine (m0, capacity 5) and j0 the slower one (m1, capacity 2).
    state = make_state(
        machines={
            "m0": {"capacity": 5.0, "down_until": 0},
            "m1": {"capacity": 2.0, "down_until": 0},
        },
        jobs={
            "j0": {"remaining_work": 2.0, "release": 0, "due": 10, "weight": 1.0, "completed_at": None},
            "j1": {"remaining_work": 1.0, "release": 0, "due": 10, "weight": 4.0, "completed_at": None},
        },
    )
    action = policies.reference_policy(state)
    assert action == {"assignments": {"m0": "j1", "m1": "j0"}}


def test_reference_policy_skips_down_and_unreleased_and_completed():
    state = make_state(
        machines={
            "m0": {"capacity": 5.0, "down_until": 3},
            "m1": {"capacity": 2.0, "down_until": 0},
        },
        jobs={
            "j0": {"remaining_work": 2.0, "release": 0, "due": 10, "weight": 1.0, "completed_at": None},
            "j1": {"remaining_work": 5.0, "release": 5, "due": 10, "weight": 4.0, "completed_at": None},
            "j2": {"remaining_work": 0.0, "release": 0, "due": 10, "weight": 4.0, "completed_at": 0},
        },
        time=1,
    )
    action = policies.reference_policy(state)
    # m0 down at t=1; j1 not yet released; j2 already completed -> only j0 on m1 is legal.
    assert action == {"assignments": {"m1": "j0"}}


def test_reference_policy_never_double_books_when_jobs_outnumber_machines():
    state = make_state(
        machines={"m0": {"capacity": 5.0, "down_until": 0}},
        jobs={
            "j0": {"remaining_work": 2.0, "release": 0, "due": 10, "weight": 1.0, "completed_at": None},
            "j1": {"remaining_work": 1.0, "release": 0, "due": 10, "weight": 4.0, "completed_at": None},
        },
    )
    action = policies.reference_policy(state)
    assert len(action["assignments"]) == 1


def test_simulate_episode_matches_direct_engine_step_and_does_not_mutate_input():
    initial_state = make_state(
        machines={"m0": {"capacity": 5.0, "down_until": 0}},
        jobs={"j0": {"remaining_work": 10.0, "release": 0, "due": 2, "weight": 1.0, "completed_at": None}},
    )
    snapshot = copy.deepcopy(initial_state)

    final_state, history = policies.simulate_episode(initial_state, policies.baseline_policy, horizon=2)

    expected_state, expected_kpis0 = engine.step(copy.deepcopy(snapshot), {"assignments": {"m0": "j0"}})
    expected_state, expected_kpis1 = engine.step(expected_state, {"assignments": {"m0": "j0"}})

    assert final_state == expected_state
    assert history == [expected_kpis0, expected_kpis1]
    assert initial_state == snapshot


def test_simulate_episode_is_deterministic():
    initial_state = make_state(
        machines={
            "m0": {"capacity": 4.0, "down_until": 0},
            "m1": {"capacity": 2.0, "down_until": 1},
        },
        jobs={
            "j0": {"remaining_work": 9.0, "release": 0, "due": 3, "weight": 1.0, "completed_at": None},
            "j1": {"remaining_work": 5.0, "release": 0, "due": 2, "weight": 3.0, "completed_at": None},
        },
    )

    final_a, history_a = policies.simulate_episode(copy.deepcopy(initial_state), policies.reference_policy, horizon=5)
    final_b, history_b = policies.simulate_episode(copy.deepcopy(initial_state), policies.reference_policy, horizon=5)

    assert final_a == final_b
    assert history_a == history_b
