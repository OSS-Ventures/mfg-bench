"""Simulated scorer: KPI-delta normalization for Family C decision tasks (SPEC.md Section 8/9).

    score = clip((kpi_model - kpi_baseline) / (kpi_reference - kpi_baseline), 0, 1)

`model_answer` is the model's full-horizon action plan for an L4 single-decision task: a list of
exactly `ground_truth["horizon"]` per-step action dicts (`{"assignments": {...}, "overtime":
{...}}`, matching `simulator.engine.step`'s own action shape), replayed step by step from
`ground_truth["initial_state"]` through the real deterministic engine to get the model's own KPI
-- the model's opinion never substitutes for what actually happens in the simulator.

A structurally invalid plan (wrong type/length, non-dict step, non-dict assignments/overtime) or
one containing an action the engine itself rejects (unknown/down machine, unreleased/completed/
double-booked job) scores 0.0 rather than raising. This differs from `simulator.engine.step`'s
own docstring, where an illegal action is treated as a caller bug (raised) because there the
caller is a trusted policy; here the caller is a fallible model, so an illegal decision is just a
scoring outcome -- the worst one.

`kpi_reference == kpi_baseline` (the reference bound ties the baseline -- both scenario modules'
`reference_episode` can fall back to the baseline trajectory) leaves no daylight to normalize
into; that degenerate case scores 1.0 only if the model's plan reproduces that exact KPI, else
0.0, rather than dividing by zero.
"""
from __future__ import annotations

import copy
from typing import Any

from scorers.base import Scorer
from simulator import engine
from simulator.scenarios.registry import SCENARIOS

_TIE_TOLERANCE = 1e-9


class SimulatedScorer(Scorer):
    name = "simulated"

    def score(self, task: dict[str, Any], model_answer: Any) -> float:
        ground_truth = task["ground_truth"]
        scenario = SCENARIOS[ground_truth["scenario"]]
        horizon = ground_truth["horizon"]

        kpi_model = self._replay(scenario, ground_truth["initial_state"], horizon, model_answer)
        if kpi_model is None:
            return 0.0

        kpi_baseline = ground_truth["kpi_baseline"]
        kpi_reference = ground_truth["kpi_reference"]
        denominator = kpi_reference - kpi_baseline
        if denominator == 0:
            return 1.0 if abs(kpi_model - kpi_baseline) < _TIE_TOLERANCE else 0.0
        return max(0.0, min(1.0, (kpi_model - kpi_baseline) / denominator))

    @staticmethod
    def _replay(scenario: dict, initial_state: dict, horizon: int, plan: Any) -> float | None:
        """Drive `plan` through the real engine from `initial_state`; return the scenario's KPI
        at the end, or None if the plan is structurally invalid or the engine rejects a step."""
        if not isinstance(plan, list) or len(plan) != horizon:
            return None

        state = copy.deepcopy(initial_state)
        for step_action in plan:
            if not isinstance(step_action, dict):
                return None
            assignments = step_action.get("assignments", {})
            overtime = step_action.get("overtime", {})
            if not isinstance(assignments, dict) or not isinstance(overtime, dict):
                return None
            try:
                state, _ = engine.step(state, {"assignments": assignments, "overtime": overtime})
            except (ValueError, KeyError, TypeError, AttributeError):
                return None

        return scenario["kpi"](state, horizon)
