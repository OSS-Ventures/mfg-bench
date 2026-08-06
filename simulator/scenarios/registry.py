"""Registry mapping a scenario name to its generate/baseline/reference/KPI functions.

Lets scenario-consuming code (unit 2.4's L4 single-decision generators/scorer today, unit 2.5's
L5 agentic mode later) work with any scenario by name instead of importing and branching on each
scenario module directly. New scenarios (SPEC.md Section 9 mentions supplier delay, quality hold
cascade, changeover optimization as later additions) plug in here without the consuming code
needing to change.

Each scenario's `kpi` entry is normalized to a single `(final_state, horizon) -> float` shape
even though the two scenario modules' own KPI functions differ in signature
(`line_down_recovery.total_weighted_tardiness(final_state, horizon)` needs the horizon to cost
still-unfinished jobs; `demand_spike_rebalance.total_cost(final_state)` does not) -- callers that
just want "this scenario's KPI" shouldn't need to know which shape a given scenario happens to
use.
"""
from __future__ import annotations

from simulator.scenarios import demand_spike_rebalance, line_down_recovery

SCENARIOS = {
    "line_down_recovery": {
        "generate": line_down_recovery.generate,
        "baseline_episode": line_down_recovery.baseline_episode,
        "reference_episode": line_down_recovery.reference_episode,
        "kpi": lambda final_state, horizon: line_down_recovery.total_weighted_tardiness(
            final_state, horizon
        ),
    },
    "demand_spike_rebalance": {
        "generate": demand_spike_rebalance.generate,
        "baseline_episode": demand_spike_rebalance.baseline_episode,
        "reference_episode": demand_spike_rebalance.reference_episode,
        "kpi": lambda final_state, horizon: demand_spike_rebalance.total_cost(final_state),
    },
}
