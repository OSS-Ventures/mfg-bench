"""Demand spike / rebalance scenario (Family C, SPEC.md Section 9, roadmap unit 2.3).

Demand jumps mid-shift: a batch of urgent, tightly-due orders arrives on top of a base load that
already keeps every machine close to its normal (non-overtime) capacity. A good policy has to
choose, order by order, between reallocating capacity toward the most urgent work and paying for
overtime (extra capacity at `engine.OVERTIME_COST_PER_UNIT` per extra unit, per
`simulator/engine.py`) to hit due dates it would otherwise miss. KPI: service level (fraction of
weighted demand fulfilled on time) and overtime cost.

Built on top of `simulator.engine`'s scenario-agnostic contract, same as unit 2.2's
`line_down_recovery.py`: this module supplies only scenario *content* (a seeded initial state + a
horizon), a KPI extraction, and score-bound policies. Unlike line-down recovery (where neither
`policies.baseline_policy` nor `policies.reference_policy` ever needs overtime, since the only
lever there is *which* machine works on a job), this scenario's whole point is the overtime
trade-off, so `reference_episode` here layers a scenario-specific overtime rule on top of the
scenario-agnostic `policies.reference_policy` assignment logic rather than reusing it unmodified.
"""
from __future__ import annotations

import random

from simulator import policies
from simulator.engine import OVERTIME_MULTIPLIER

STANDARD_NUM_MACHINES = 3
HARD_NUM_MACHINES = 3
STANDARD_NUM_BASE_JOBS = 4
HARD_NUM_BASE_JOBS = 5
STANDARD_NUM_SPIKE_JOBS = 4
HARD_NUM_SPIKE_JOBS = 6

CAPACITY_RANGE = (2, 5)
BASE_WORK_RANGE = (3, 9)
SPIKE_WORK_RANGE = (3, 9)
WEIGHT_RANGE = (1, 5)
BASE_DUE_SLACK_RANGE = (2, 5)
SPIKE_DUE_SLACK_RANGE = (1, 2)
SPIKE_START_RANGE = (2, 4)
HORIZON_BUFFER = 8

# This scenario's KPI treats "late by any amount" as a flat, weight-scaled miss (a service-level
# hit/miss framing), unlike line-down recovery's lateness-proportional weighted tardiness — a
# deliberate difference documented in `total_cost` below. The constant is a benchmark design
# choice (same spirit as `engine.OVERTIME_COST_PER_UNIT`), not a claimed real-world cost.
SERVICE_LEVEL_MISS_PENALTY = 50.0


def generate(seed: int, difficulty: str = "standard") -> dict:
    """Return `{"initial_state": ..., "horizon": int}` ready for `simulator.engine.step`.

    Deterministic: the same (seed, difficulty) always yields the same scenario. Base-load jobs
    are all released at t=0 with generous due-date slack (they are not the pressure point). A
    batch of spike jobs is released at a randomized mid-shift step with tight due-date slack,
    representing urgent rush orders layered on top of an already-busy line.
    """
    if difficulty not in ("standard", "hard"):
        raise ValueError(f"unknown difficulty {difficulty!r}")
    rng = random.Random(seed)

    num_machines = HARD_NUM_MACHINES if difficulty == "hard" else STANDARD_NUM_MACHINES
    num_base_jobs = HARD_NUM_BASE_JOBS if difficulty == "hard" else STANDARD_NUM_BASE_JOBS
    num_spike_jobs = HARD_NUM_SPIKE_JOBS if difficulty == "hard" else STANDARD_NUM_SPIKE_JOBS

    machines = {
        f"m{m}": {"capacity": float(rng.randint(*CAPACITY_RANGE)), "down_until": 0}
        for m in range(num_machines)
    }
    total_capacity = sum(m["capacity"] for m in machines.values())

    spike_start = rng.randint(*SPIKE_START_RANGE)

    jobs = {}
    for j in range(num_base_jobs):
        remaining_work = float(rng.randint(*BASE_WORK_RANGE))
        slack = rng.randint(*BASE_DUE_SLACK_RANGE)
        due = int(remaining_work / total_capacity) + slack
        jobs[f"b{j}"] = {
            "remaining_work": remaining_work,
            "release": 0,
            "due": due,
            "weight": float(rng.randint(*WEIGHT_RANGE)),
            "completed_at": None,
        }
    for j in range(num_spike_jobs):
        remaining_work = float(rng.randint(*SPIKE_WORK_RANGE))
        slack = rng.randint(*SPIKE_DUE_SLACK_RANGE)
        due = spike_start + int(remaining_work / total_capacity) + slack
        jobs[f"s{j}"] = {
            "remaining_work": remaining_work,
            "release": spike_start,
            "due": due,
            "weight": float(rng.randint(*WEIGHT_RANGE)),
            "completed_at": None,
        }

    total_work = sum(j["remaining_work"] for j in jobs.values())
    horizon = spike_start + int(total_work / total_capacity) + HORIZON_BUFFER

    initial_state = {
        "time": 0,
        "machines": machines,
        "jobs": jobs,
        "cumulative": {
            "weighted_tardiness": 0.0,
            "overtime_cost": 0.0,
            "jobs_completed": 0,
            "jobs_completed_on_time": 0,
        },
    }
    return {"initial_state": initial_state, "horizon": horizon}


def _completed_on_time(job: dict) -> bool:
    return job["completed_at"] is not None and job["completed_at"] <= job["due"]


def service_level(final_state: dict) -> float:
    """Weighted fraction of demand fulfilled on time: sum(weight of on-time jobs) / sum(all
    weights). Weighted so higher-priority orders count more toward the metric, consistent with
    `weight`'s meaning elsewhere in the engine."""
    jobs = final_state["jobs"].values()
    total_weight = sum(j["weight"] for j in jobs)
    if total_weight == 0:
        return 1.0
    on_time_weight = sum(j["weight"] for j in jobs if _completed_on_time(j))
    return on_time_weight / total_weight


def total_cost(final_state: dict) -> float:
    """This scenario's single scalar KPI: overtime cost actually incurred, plus a flat
    weight-scaled penalty for every job not completed on time (late, or never completed at all)
    — a hit/miss "missed the order" framing, deliberately different from line-down recovery's
    `total_weighted_tardiness`, which instead scales the penalty by *how late* a job is. Both are
    legitimate ways to turn an operational KPI into one comparable scalar; which one fits depends
    on whether the scenario's story is "minimize how late things run" (line-down) or "hit the
    delivery promise or don't" (demand spike / service level)."""
    cost = final_state["cumulative"]["overtime_cost"]
    for job in final_state["jobs"].values():
        if not _completed_on_time(job):
            cost += job["weight"] * SERVICE_LEVEL_MISS_PENALTY
    return cost


def _reference_policy_with_overtime(state: dict) -> dict:
    """The scenario-agnostic WSPT-style assignment from `policies.reference_policy`, layered with
    a scenario-specific overtime rule: a machine assigned to a job goes into overtime only when
    overtime would actually be *worth paying for* — normal capacity, sustained for the time
    remaining until the job's due date, is not enough to finish it (`capacity * time_left <
    remaining_work`), but overtime capacity, sustained the same way, would be
    (`remaining_work <= capacity * OVERTIME_MULTIPLIER * time_left`). A job already too far
    behind to make its due date even with overtime every remaining step is left at normal
    capacity, since paying overtime there buys no service-level benefit, only wasted cost."""
    assignments = policies.reference_policy(state)["assignments"]
    machines = state["machines"]
    jobs = state["jobs"]
    t = state["time"]

    overtime = {}
    for machine_id, job_id in assignments.items():
        job = jobs[job_id]
        capacity = machines[machine_id]["capacity"]
        time_left = job["due"] - t
        if time_left <= 0:
            continue
        needed_rate = job["remaining_work"] / time_left
        if capacity < needed_rate <= capacity * OVERTIME_MULTIPLIER:
            overtime[machine_id] = True
    return {"assignments": assignments, "overtime": overtime}


def baseline_episode(initial_state: dict, horizon: int) -> tuple[dict, list[dict]]:
    """Run `policies.baseline_policy` for the full episode — this scenario's baseline score
    bound. Never uses overtime (the policy is scenario-agnostic and has no overtime logic), so
    its overtime cost is always 0 and its total cost is driven entirely by missed due dates."""
    return policies.simulate_episode(initial_state, policies.baseline_policy, horizon)


def reference_episode(initial_state: dict, horizon: int) -> tuple[dict, list[dict]]:
    """Run `_reference_policy_with_overtime` for the full episode — this scenario's reference
    score bound. Documented as a heuristic, not a claimed exact optimum, per SPEC.md Section 9.

    Mirrors unit 2.2's safety net: a greedy heuristic can occasionally underperform the naive
    baseline on a specific instance (here, e.g., by paying overtime cost for a job that still
    ends up completed late anyway). Since a reference bound that can fall below its own baseline
    would break KPI normalization, this falls back to the baseline's own trajectory whenever that
    happens, making the reference bound provably never worse than the baseline bound.
    """
    final_heuristic, history_heuristic = policies.simulate_episode(
        initial_state, _reference_policy_with_overtime, horizon
    )
    final_baseline, history_baseline = baseline_episode(initial_state, horizon)

    if total_cost(final_heuristic) <= total_cost(final_baseline):
        return final_heuristic, history_heuristic
    return final_baseline, history_baseline
