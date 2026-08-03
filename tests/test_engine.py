"""Tests for simulator/engine.py (unit 2.1).

Hand-verified cases work through step()'s own documented mechanics by hand (capacity applied to
remaining_work, tardiness = weight * max(0, completed_at - due), overtime cost = extra capacity
x OVERTIME_COST_PER_UNIT) rather than re-deriving from the implementation, so they genuinely
check the arithmetic.
"""
from __future__ import annotations

import copy

import pytest

from simulator import engine


def make_state(machines: dict, jobs: dict) -> dict:
    return {
        "time": 0,
        "machines": copy.deepcopy(machines),
        "jobs": copy.deepcopy(jobs),
        "cumulative": {
            "weighted_tardiness": 0.0,
            "overtime_cost": 0.0,
            "jobs_completed": 0,
            "jobs_completed_on_time": 0,
        },
    }


def test_on_time_completion_two_steps_hand_verified():
    state = make_state(
        machines={
            "m1": {"capacity": 5.0, "down_until": 0},
            "m2": {"capacity": 3.0, "down_until": 0},
        },
        jobs={
            "j1": {"remaining_work": 10.0, "release": 0, "due": 2, "weight": 1.0, "completed_at": None},
            "j2": {"remaining_work": 3.0, "release": 0, "due": 1, "weight": 2.0, "completed_at": None},
        },
    )

    state, kpis0 = engine.step(state, {"assignments": {"m1": "j1", "m2": "j2"}})
    assert kpis0["tardiness_incurred"] == 0.0
    assert kpis0["overtime_cost_incurred"] == 0.0
    assert kpis0["jobs_completed_this_step"] == ["j2"]
    assert kpis0["cumulative"] == {
        "weighted_tardiness": 0.0,
        "overtime_cost": 0.0,
        "jobs_completed": 1,
        "jobs_completed_on_time": 1,
    }
    assert state["time"] == 1
    assert state["jobs"]["j1"]["remaining_work"] == 5.0
    assert state["jobs"]["j2"]["completed_at"] == 1

    state, kpis1 = engine.step(state, {"assignments": {"m1": "j1"}})
    assert kpis1["tardiness_incurred"] == 0.0
    assert kpis1["jobs_completed_this_step"] == ["j1"]
    assert kpis1["cumulative"]["jobs_completed"] == 2
    assert kpis1["cumulative"]["jobs_completed_on_time"] == 2
    assert state["jobs"]["j1"]["remaining_work"] == 0.0
    assert state["jobs"]["j1"]["completed_at"] == 2


def test_late_completion_costs_weighted_tardiness_hand_verified():
    state = make_state(
        machines={"m1": {"capacity": 5.0, "down_until": 0}},
        jobs={"j3": {"remaining_work": 4.0, "release": 0, "due": 0, "weight": 2.0, "completed_at": None}},
    )

    state, kpis = engine.step(state, {"assignments": {"m1": "j3"}})

    # completes at t+1 = 1; due = 0 -> lateness = 1; weight 2.0 -> tardiness 2.0
    assert state["jobs"]["j3"]["completed_at"] == 1
    assert kpis["tardiness_incurred"] == 2.0
    assert kpis["cumulative"]["weighted_tardiness"] == 2.0
    assert kpis["cumulative"]["jobs_completed_on_time"] == 0


def test_overtime_boosts_capacity_and_costs_extra_hand_verified():
    state = make_state(
        machines={"m1": {"capacity": 4.0, "down_until": 0}},
        jobs={"j1": {"remaining_work": 20.0, "release": 0, "due": 10, "weight": 1.0, "completed_at": None}},
    )

    state, kpis = engine.step(state, {"assignments": {"m1": "j1"}, "overtime": {"m1": True}})

    # effective capacity = 4.0 * 1.5 = 6.0; extra = 2.0; cost = 2.0 * 10.0 = 20.0
    assert state["jobs"]["j1"]["remaining_work"] == 14.0
    assert kpis["overtime_cost_incurred"] == 20.0
    assert kpis["cumulative"]["overtime_cost"] == 20.0
    assert kpis["tardiness_incurred"] == 0.0


def test_idle_machine_via_omission_and_explicit_none_are_equivalent():
    machines = {"m1": {"capacity": 5.0, "down_until": 0}}
    jobs = {"j1": {"remaining_work": 10.0, "release": 0, "due": 2, "weight": 1.0, "completed_at": None}}

    state_omitted = make_state(machines, jobs)
    state_omitted, _ = engine.step(state_omitted, {"assignments": {}})

    state_none = make_state(machines, jobs)
    state_none, _ = engine.step(state_none, {"assignments": {"m1": None}})

    assert state_omitted == state_none
    assert state_omitted["jobs"]["j1"]["remaining_work"] == 10.0
    assert state_omitted["time"] == 1


def test_step_does_not_mutate_input_state():
    state = make_state(
        machines={"m1": {"capacity": 5.0, "down_until": 0}},
        jobs={"j1": {"remaining_work": 10.0, "release": 0, "due": 2, "weight": 1.0, "completed_at": None}},
    )
    snapshot = copy.deepcopy(state)

    engine.step(state, {"assignments": {"m1": "j1"}})

    assert state == snapshot


def test_determinism_same_actions_produce_same_states_and_kpis():
    def initial_state():
        return make_state(
            machines={
                "m1": {"capacity": 4.0, "down_until": 0},
                "m2": {"capacity": 2.0, "down_until": 1},
            },
            jobs={
                "j1": {"remaining_work": 9.0, "release": 0, "due": 3, "weight": 1.0, "completed_at": None},
                "j2": {"remaining_work": 5.0, "release": 1, "due": 2, "weight": 3.0, "completed_at": None},
            },
        )

    actions = [
        {"assignments": {"m1": "j1"}},
        {"assignments": {"m1": "j1", "m2": "j2"}, "overtime": {"m2": True}},
        {"assignments": {"m2": "j2"}},
    ]

    def run(initial):
        state = initial
        history = []
        for action in actions:
            state, kpis = engine.step(state, action)
            history.append((copy.deepcopy(state), copy.deepcopy(kpis)))
        return history

    history_a = run(initial_state())
    history_b = run(initial_state())

    assert history_a == history_b


def test_assigning_unknown_machine_raises():
    state = make_state(
        machines={"m1": {"capacity": 5.0, "down_until": 0}},
        jobs={"j1": {"remaining_work": 10.0, "release": 0, "due": 2, "weight": 1.0, "completed_at": None}},
    )
    with pytest.raises(ValueError):
        engine.step(state, {"assignments": {"m404": "j1"}})


def test_assigning_unknown_job_raises():
    state = make_state(
        machines={"m1": {"capacity": 5.0, "down_until": 0}},
        jobs={"j1": {"remaining_work": 10.0, "release": 0, "due": 2, "weight": 1.0, "completed_at": None}},
    )
    with pytest.raises(ValueError):
        engine.step(state, {"assignments": {"m1": "j404"}})


def test_assigning_down_machine_raises():
    state = make_state(
        machines={"m1": {"capacity": 5.0, "down_until": 2}},
        jobs={"j1": {"remaining_work": 10.0, "release": 0, "due": 2, "weight": 1.0, "completed_at": None}},
    )
    with pytest.raises(ValueError):
        engine.step(state, {"assignments": {"m1": "j1"}})


def test_machine_becomes_available_after_down_until():
    state = make_state(
        machines={"m1": {"capacity": 5.0, "down_until": 1}},
        jobs={"j1": {"remaining_work": 10.0, "release": 0, "due": 2, "weight": 1.0, "completed_at": None}},
    )
    with pytest.raises(ValueError):
        engine.step(state, {"assignments": {"m1": "j1"}})

    state, _ = engine.step(state, {"assignments": {}})
    assert state["time"] == 1
    # now t == down_until == 1, so the machine is available
    state, kpis = engine.step(state, {"assignments": {"m1": "j1"}})
    assert state["jobs"]["j1"]["remaining_work"] == 5.0


def test_assigning_unreleased_job_raises():
    state = make_state(
        machines={"m1": {"capacity": 5.0, "down_until": 0}},
        jobs={"j1": {"remaining_work": 10.0, "release": 5, "due": 10, "weight": 1.0, "completed_at": None}},
    )
    with pytest.raises(ValueError):
        engine.step(state, {"assignments": {"m1": "j1"}})


def test_assigning_already_completed_job_raises():
    state = make_state(
        machines={"m1": {"capacity": 5.0, "down_until": 0}},
        jobs={"j1": {"remaining_work": 0.0, "release": 0, "due": 2, "weight": 1.0, "completed_at": 0}},
    )
    with pytest.raises(ValueError):
        engine.step(state, {"assignments": {"m1": "j1"}})


def test_double_booking_a_job_raises():
    state = make_state(
        machines={
            "m1": {"capacity": 5.0, "down_until": 0},
            "m2": {"capacity": 3.0, "down_until": 0},
        },
        jobs={"j1": {"remaining_work": 10.0, "release": 0, "due": 2, "weight": 1.0, "completed_at": None}},
    )
    with pytest.raises(ValueError):
        engine.step(state, {"assignments": {"m1": "j1", "m2": "j1"}})
