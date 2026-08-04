"""Line-down recovery scenario (Family C, SPEC.md Section 9, roadmap unit 2.2).

A machine goes down mid-shift; a good policy reallocates its work onto the other machines
instead of leaving it to sit idle in a fixed queue. KPI: total weighted tardiness over the
scenario's horizon.

Built on top of `simulator.engine`'s scenario-agnostic contract (SPEC.md Section 9,
`simulator/engine.py`'s own docstring) — this module supplies only the scenario *content* (a
seeded initial state + a horizon) and the KPI extraction that accounts for jobs still
unfinished when the horizon ends. The engine itself has no notion of a horizon and only costs
tardiness at the moment a job actually completes, so a policy that simply never finishes a job
would otherwise show zero tardiness for it — `total_weighted_tardiness` closes that gap by
costing an unfinished job as if it completed exactly at the horizon, using the same
`weight * max(0, lateness)` formula the engine itself uses.
"""
from __future__ import annotations

import random

from simulator import policies

STANDARD_NUM_MACHINES = 3
HARD_NUM_MACHINES = 3
STANDARD_NUM_JOBS = 5
HARD_NUM_JOBS = 7

CAPACITY_RANGE = (2, 5)
WORK_RANGE = (3, 9)
WEIGHT_RANGE = (1, 5)
DUE_SLACK_RANGE = (0, 3)
DOWN_START_RANGE = (2, 4)
DOWN_DURATION_RANGE = (2, 4)
HORIZON_BUFFER = 6


def generate(seed: int, difficulty: str = "standard") -> dict:
    """Return `{"initial_state": ..., "horizon": int}` ready for `simulator.engine.step`.

    Deterministic: the same (seed, difficulty) always yields the same scenario. All jobs are
    released at t=0 (production is already mid-shift when the machine goes down); exactly one
    machine goes down for `[down_start, down_start + down_duration)`.
    """
    if difficulty not in ("standard", "hard"):
        raise ValueError(f"unknown difficulty {difficulty!r}")
    rng = random.Random(seed)

    num_machines = HARD_NUM_MACHINES if difficulty == "hard" else STANDARD_NUM_MACHINES
    num_jobs = HARD_NUM_JOBS if difficulty == "hard" else STANDARD_NUM_JOBS

    machines = {
        f"m{m}": {"capacity": float(rng.randint(*CAPACITY_RANGE)), "down_until": 0}
        for m in range(num_machines)
    }

    down_machine = rng.choice(sorted(machines.keys()))
    down_start = rng.randint(*DOWN_START_RANGE)
    down_duration = rng.randint(*DOWN_DURATION_RANGE)
    machines[down_machine]["down_until"] = down_start + down_duration

    avg_capacity = sum(m["capacity"] for m in machines.values()) / num_machines

    jobs = {}
    for j in range(num_jobs):
        remaining_work = float(rng.randint(*WORK_RANGE))
        slack = rng.randint(*DUE_SLACK_RANGE)
        due = int(remaining_work / avg_capacity) + slack
        jobs[f"j{j}"] = {
            "remaining_work": remaining_work,
            "release": 0,
            "due": due,
            "weight": float(rng.randint(*WEIGHT_RANGE)),
            "completed_at": None,
        }

    total_work = sum(j["remaining_work"] for j in jobs.values())
    total_capacity = sum(m["capacity"] for m in machines.values())
    horizon = int(total_work / total_capacity) + down_duration + HORIZON_BUFFER

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


def total_weighted_tardiness(final_state: dict, horizon: int) -> float:
    """This scenario's KPI: cumulative weighted tardiness, plus the same
    `weight * max(0, lateness)` penalty (lateness measured against the horizon) for any job
    still unfinished when the horizon ends."""
    total = final_state["cumulative"]["weighted_tardiness"]
    for job in final_state["jobs"].values():
        if job["completed_at"] is None:
            total += job["weight"] * max(0, horizon - job["due"])
    return total


def baseline_episode(initial_state: dict, horizon: int) -> tuple[dict, list[dict]]:
    """Run `policies.baseline_policy` for the full episode. This is the scenario's baseline
    score bound."""
    return policies.simulate_episode(initial_state, policies.baseline_policy, horizon)


def reference_episode(initial_state: dict, horizon: int) -> tuple[dict, list[dict]]:
    """Run `policies.reference_policy` (the scenario-agnostic WSPT-style heuristic) for the
    full episode — this scenario's reference score bound.

    `reference_policy` is a *greedy, per-step* heuristic and, like any such heuristic, can
    occasionally underperform the naive `baseline_policy` on a specific instance (SPEC.md
    Section 9 explicitly does not require reference policies to be a claimed exact optimum).
    Since a bound that can fall below the thing it's supposed to sit above would break KPI
    normalization, this falls back to the baseline's own trajectory whenever that happens —
    which makes the reference bound *provably* never worse than the baseline bound, at the
    cost of occasionally tying it rather than improving on it.
    """
    final_heuristic, history_heuristic = policies.simulate_episode(
        initial_state, policies.reference_policy, horizon
    )
    final_baseline, history_baseline = baseline_episode(initial_state, horizon)

    if total_weighted_tardiness(final_heuristic, horizon) <= total_weighted_tardiness(
        final_baseline, horizon
    ):
        return final_heuristic, history_heuristic
    return final_baseline, history_baseline
