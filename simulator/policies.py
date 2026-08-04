"""Baseline + reference policies for Family C score bounds (SPEC.md Section 9).

Every scenario must ship with a `baseline` policy (naive) and a `reference` policy (a
well-known strong heuristic, documented as such — not a claimed exact optimum) so a model's
KPI can be normalized between them. Both policies here are scenario-agnostic: they read only
the current `state` (the same shape `simulator.engine.step` consumes/produces) and derive their
decision from it, so they apply to any scenario built on the engine, not just line-down
recovery.

`simulate_episode` is the generic runner scenarios use to score a policy: it drives
`engine.step` for a fixed number of steps, feeding each resulting state back into the policy.
"""
from __future__ import annotations

import copy

from simulator import engine


def simulate_episode(initial_state: dict, policy_fn, horizon: int) -> tuple[dict, list[dict]]:
    """Run `policy_fn` for `horizon` steps from `initial_state`. Returns (final_state, kpi_history).

    Does not mutate `initial_state` (mirrors `engine.step`'s own no-mutation contract).
    """
    state = copy.deepcopy(initial_state)
    history = []
    for _ in range(horizon):
        action = policy_fn(state)
        state, kpis = engine.step(state, action)
        history.append(kpis)
    return state, history


def baseline_policy(state: dict) -> dict:
    """Naive: a fixed, static job-to-machine queue assignment (job `i` in sorted job-id order
    queues on machine `i % num_machines`, also in sorted order) that never reallocates work
    away from a machine once assigned — including while that machine is down. A down machine's
    queued jobs simply wait; other machines' queues are unaffected, even if they have spare
    capacity."""
    machines = state["machines"]
    jobs = state["jobs"]
    t = state["time"]

    machine_ids = sorted(machines.keys())
    job_ids = sorted(jobs.keys())
    num_machines = len(machine_ids)

    queues: dict[str, list[str]] = {m: [] for m in machine_ids}
    for i, job_id in enumerate(job_ids):
        queues[machine_ids[i % num_machines]].append(job_id)

    assignments = {}
    for m in machine_ids:
        if machines[m]["down_until"] > t:
            continue
        for job_id in queues[m]:
            job = jobs[job_id]
            if job["completed_at"] is None and job["release"] <= t:
                assignments[m] = job_id
                break
    return {"assignments": assignments}


def reference_policy(state: dict) -> dict:
    """Well-known heuristic (weighted-shortest-remaining-work-first, a WSPT variant): each
    step, pairs the highest-capacity currently-available machine with the highest-priority
    currently-workable job (priority = weight / remaining_work, ties broken by earlier due
    date then job id), and so on down both sorted lists. Adapts immediately to a machine going
    down or coming back up, and freely reallocates jobs between machines every step — legal
    because the engine has no setup-time or machine-affinity cost. Documented as a strong
    heuristic, not a claimed exact optimum, per SPEC.md Section 9."""
    machines = state["machines"]
    jobs = state["jobs"]
    t = state["time"]

    available_machines = sorted(
        (m for m, info in machines.items() if info["down_until"] <= t),
        key=lambda m: (-machines[m]["capacity"], m),
    )
    available_jobs = sorted(
        (j for j, info in jobs.items() if info["completed_at"] is None and info["release"] <= t),
        key=lambda j: (-(jobs[j]["weight"] / max(jobs[j]["remaining_work"], 1e-9)), jobs[j]["due"], j),
    )

    assignments = {m: j for m, j in zip(available_machines, available_jobs)}
    return {"assignments": assignments}
