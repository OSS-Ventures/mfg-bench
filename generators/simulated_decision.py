"""L4 single-decision generators for Family C scenarios (SPEC.md Section 9, roadmap unit 2.4).

"L4 (single decision) -- the agent sees the full situation and outputs a plan/decision once; the
sim scores the outcome" (SPEC.md Section 9). Each generator here wraps an existing scenario
module (units 2.2/2.3, reached via `simulator.scenarios.registry`) into a task: the prompt
describes the full initial situation (machines, jobs, mechanics) and asks the model for one
complete action plan covering the whole horizon; the ground truth carries what
`scorers.simulated.SimulatedScorer` needs to replay that plan through the real engine and
normalize its KPI against the scenario's own `baseline_episode`/`reference_episode` bounds --
never a model's opinion, per `GOALS.md`'s non-negotiable rule.
"""
from __future__ import annotations

from abc import abstractmethod
from datetime import datetime, timezone
from typing import Any

from generators.base import Generator
from simulator.engine import OVERTIME_COST_PER_UNIT, OVERTIME_MULTIPLIER
from simulator.scenarios.registry import SCENARIOS


def _render_machines(machines: dict) -> str:
    lines = []
    for machine_id in sorted(machines):
        info = machines[machine_id]
        down = (
            f", down (unavailable) for steps 0-{info['down_until'] - 1}"
            if info["down_until"] > 0
            else ""
        )
        lines.append(f"  {machine_id}: capacity {info['capacity']} work units/step{down}")
    return "\n".join(lines)


def _render_jobs(jobs: dict) -> str:
    lines = []
    for job_id in sorted(jobs):
        info = jobs[job_id]
        lines.append(
            f"  {job_id}: {info['remaining_work']} work units remaining, released at step "
            f"{info['release']}, due by step {info['due']}, weight {info['weight']}"
        )
    return "\n".join(lines)


class _SimulatedDecisionGenerator(Generator):
    #: Key into simulator.scenarios.registry.SCENARIOS.
    scenario_name: str
    domain: str
    #: Human-readable description of the KPI, for the prompt's scoring-rule paragraph.
    kpi_description: str
    #: Scenario-specific rules appended after the generic mechanics paragraph.
    extra_rules: str = ""

    def generate(self, seed: int, difficulty: str = "standard") -> dict[str, Any]:
        scenario = SCENARIOS[self.scenario_name]
        built = scenario["generate"](seed=seed, difficulty=difficulty)
        initial_state, horizon = built["initial_state"], built["horizon"]

        final_baseline, _ = scenario["baseline_episode"](initial_state, horizon)
        final_reference, _ = scenario["reference_episode"](initial_state, horizon)
        kpi_baseline = scenario["kpi"](final_baseline, horizon)
        kpi_reference = scenario["kpi"](final_reference, horizon)

        machines = initial_state["machines"]
        jobs = initial_state["jobs"]

        prompt = (
            f"{self._scenario_intro()}\n\n"
            f"Machines:\n{_render_machines(machines)}\n\n"
            f"Jobs:\n{_render_jobs(jobs)}\n\n"
            "Mechanics: each step, a machine assigned to a job reduces that job's remaining "
            "work by its capacity (or capacity x "
            f"{OVERTIME_MULTIPLIER} if run in overtime that step, at a cost of "
            f"{OVERTIME_COST_PER_UNIT} per extra work unit produced). A job completes the step "
            "its remaining work reaches 0. A job cannot be assigned before its release step, "
            "after it has completed, to a down machine, or to two machines in the same step.\n\n"
            f"{self.extra_rules}"
            f"The schedule runs for {horizon} steps (steps 0 through {horizon - 1}). You will "
            f"be scored on {self.kpi_description}, normalized between a naive baseline policy "
            "(score 0) and a strong reference policy (score 1)."
        )

        return {
            "id": f"simulated.{self.scenario_name}.{seed:06d}",
            "family": "simulated",
            "domain": self.domain,
            "reasoning_tier": "L4",
            "answer_format": "simulated",
            "prompt": prompt,
            "context": {
                "scenario": self.scenario_name,
                "num_machines": len(machines),
                "num_jobs": len(jobs),
                "horizon": horizon,
            },
            "ground_truth": {
                "scenario": self.scenario_name,
                "initial_state": initial_state,
                "horizon": horizon,
                "kpi_baseline": kpi_baseline,
                "kpi_reference": kpi_reference,
            },
            "scorer": "simulated",
            "generator": self.name,
            "seed": seed,
            "difficulty": difficulty,
            "source": None,
            "source_url": None,
            "created": datetime.now(timezone.utc).date().isoformat(),
            "public": True,
        }

    @abstractmethod
    def _scenario_intro(self) -> str:
        raise NotImplementedError


class LineDownRecoveryDecisionGenerator(_SimulatedDecisionGenerator):
    name = "line_down_recovery_decision"
    scenario_name = "line_down_recovery"
    domain = "production_scheduling"
    kpi_description = "total weighted tardiness across all jobs (lower is better)"
    extra_rules = (
        "A job still unfinished when the schedule ends is penalized as if it had completed "
        "exactly at the final step. "
    )

    def _scenario_intro(self) -> str:
        return (
            "One machine in a production line goes down for part of the shift. Decide, for "
            "every step of the shift, which machine (if any) works on which job -- including "
            "reallocating work away from the down machine while it is unavailable -- to "
            "minimize total weighted tardiness across all jobs."
        )


class DemandSpikeRebalanceDecisionGenerator(_SimulatedDecisionGenerator):
    name = "demand_spike_rebalance_decision"
    scenario_name = "demand_spike_rebalance"
    domain = "supply_chain_sop"
    kpi_description = (
        "total cost: overtime cost actually incurred, plus a flat weight-scaled penalty for "
        "every job not completed on time (lower is better)"
    )
    extra_rules = (
        "A batch of urgent jobs is released partway through the shift on top of a base load "
        "that already keeps every machine close to its normal capacity; running a machine in "
        "overtime lets it work faster that step at extra cost. A job counts as missed (and is "
        "penalized) if it is not completed by its own due step, no matter how late. "
    )

    def _scenario_intro(self) -> str:
        return (
            "A demand spike hits partway through the shift: a batch of tightly-due orders "
            "arrives on top of an already-busy base load. Decide, for every step of the shift, "
            "which machine (if any) works on which job and whether to run it in overtime, to "
            "minimize total cost (overtime cost plus missed-order penalties)."
        )
