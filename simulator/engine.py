"""Operations simulator engine (Family C, SPEC.md Section 9).

Core contract:
    state, kpis = step(state, action)

Pure and deterministic: no randomness, no I/O, no mutation of the input `state` (step() returns
a new state; the caller's original state dict is left untouched). Given the same initial state
and the same sequence of actions, repeated runs always produce the same sequence of states and
KPIs.

Scenario-agnostic on purpose: this module knows about jobs, machines, and time — not about
"line-down recovery" or "demand spike" specifically. Those are scenario definitions (initial
state + a scoring function over the KPI history) built on top of this engine in units 2.2/2.3.
A machine going down mid-shift, for instance, is just a machine whose `down_until` in the
initial state is greater than 0 — the engine applies that schedule generically.

State shape:
    {
        "time": int,                       # current step, starts at 0
        "jobs": {
            job_id: {
                "remaining_work": float,    # work units left; job completes when this hits 0
                "release": int,             # step at which the job becomes assignable
                "due": int,                 # step by which the job should complete
                "weight": float,            # priority weight used to cost tardiness
                "completed_at": int | None, # step the job finished, or None while in progress
            },
            ...
        },
        "machines": {
            machine_id: {
                "capacity": float,  # work units performed per step when assigned a job
                "down_until": int,  # machine is unavailable for steps < down_until (0 = never down)
            },
            ...
        },
        "cumulative": {
            "weighted_tardiness": float,      # running total of weight * max(0, completed_at - due)
            "overtime_cost": float,           # running total overtime cost incurred
            "jobs_completed": int,
            "jobs_completed_on_time": int,    # of those, how many had completed_at <= due
        },
    }

Action shape:
    {
        "assignments": {machine_id: job_id, ...},  # at most one job per machine this step; a
                                                     # machine absent from this dict is idle
        "overtime": {machine_id: True, ...},        # optional; a flagged machine processes at
                                                     # OVERTIME_MULTIPLIER x its normal capacity
                                                     # this step, at OVERTIME_COST_PER_UNIT per
                                                     # extra work unit produced
    }

step() validates the action against the current state and raises ValueError for an illegal
action (assigning a down/nonexistent machine, a nonexistent/unreleased/already-completed job, or
double-booking a job across two machines in the same step) rather than silently ignoring it — an
illegal action is a bug in the caller (agent or harness), not a simulation outcome to be scored.

Jobs still incomplete when a scenario's horizon ends are that scenario's scorer's concern (built
in units 2.2/2.3), not this engine's — the engine has no notion of a horizon and only costs
tardiness at the moment a job actually completes.
"""
from __future__ import annotations

import copy

OVERTIME_MULTIPLIER = 1.5
OVERTIME_COST_PER_UNIT = 10.0


def step(state: dict, action: dict) -> tuple[dict, dict]:
    new_state = copy.deepcopy(state)
    jobs = new_state["jobs"]
    machines = new_state["machines"]
    cumulative = new_state["cumulative"]
    t = new_state["time"]

    assignments = action.get("assignments", {})
    overtime = action.get("overtime", {})

    assigned_job_ids: set[str] = set()
    step_tardiness = 0.0
    step_overtime_cost = 0.0
    jobs_completed_this_step = []
    jobs_completed_on_time_this_step = 0

    for machine_id, job_id in assignments.items():
        if job_id is None:
            continue
        if machine_id not in machines:
            raise ValueError(f"unknown machine {machine_id!r}")
        machine = machines[machine_id]
        if t < machine["down_until"]:
            raise ValueError(f"machine {machine_id!r} is down at step {t}")
        if job_id not in jobs:
            raise ValueError(f"unknown job {job_id!r}")
        job = jobs[job_id]
        if job["release"] > t:
            raise ValueError(f"job {job_id!r} not yet released at step {t}")
        if job["completed_at"] is not None:
            raise ValueError(f"job {job_id!r} already completed")
        if job_id in assigned_job_ids:
            raise ValueError(f"job {job_id!r} assigned to more than one machine at step {t}")
        assigned_job_ids.add(job_id)

        capacity = machine["capacity"]
        if overtime.get(machine_id):
            extra_capacity = capacity * (OVERTIME_MULTIPLIER - 1.0)
            step_overtime_cost += extra_capacity * OVERTIME_COST_PER_UNIT
            capacity *= OVERTIME_MULTIPLIER

        job["remaining_work"] = max(0.0, job["remaining_work"] - capacity)
        if job["remaining_work"] == 0.0:
            completed_at = t + 1
            job["completed_at"] = completed_at
            lateness = max(0, completed_at - job["due"])
            step_tardiness += job["weight"] * lateness
            jobs_completed_this_step.append(job_id)
            if lateness == 0:
                jobs_completed_on_time_this_step += 1

    cumulative["weighted_tardiness"] += step_tardiness
    cumulative["overtime_cost"] += step_overtime_cost
    cumulative["jobs_completed"] += len(jobs_completed_this_step)
    cumulative["jobs_completed_on_time"] += jobs_completed_on_time_this_step

    new_state["time"] = t + 1

    kpis = {
        "time": t,
        "tardiness_incurred": step_tardiness,
        "overtime_cost_incurred": step_overtime_cost,
        "jobs_completed_this_step": jobs_completed_this_step,
        "cumulative": copy.deepcopy(cumulative),
    }
    return new_state, kpis
