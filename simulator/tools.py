"""Tool interface for L5 agentic orchestration tasks (SPEC.md Section 9, roadmap unit 2.5).

Where the L4 single-decision mode (unit 2.4) asks a model to submit one full-horizon plan up
front, L5 asks it to drive `simulator.engine.step` interactively, one tool call at a time --
"the agent interacts turn-by-turn through `simulator/tools.py` (query state, place actions),
capped at N turns" (SPEC.md Section 9). `SimulationSession` is the pure, deterministic state
machine behind that interaction: it holds the current simulator state and exposes exactly two
operations an agent can call -- `get_state` (a read-only look at the current situation) and
`submit_action` (attempt one step of `engine.step`) -- and counts every call, of either kind,
against a fixed `max_turns` budget, so a model that only ever queries and never acts still
eventually runs out of turns rather than looping forever.

This module owns turn/session bookkeeping only, not simulation mechanics -- state transitions
are always `simulator.engine.step` itself, reused as-is. Per `GOALS.md`'s non-negotiable rule, a
model's illegal or malformed tool call is a failed turn to report back to the model, not a bug
to raise (contrast `engine.step`'s own docstring, where an illegal action from a trusted policy
*is* a caller bug): the model is fallible, the harness/session code calling it is not.
"""
from __future__ import annotations

import copy
from typing import Any, Optional

from simulator import engine

#: Anthropic-style tool schemas for the two operations a session exposes. Reused verbatim as the
#: `tools` argument to `Model.complete()` for L5 tasks.
TOOL_DEFINITIONS = [
    {
        "name": "get_state",
        "description": (
            "Look at the current state of the simulation: every job's remaining work, release "
            "step, due step, and weight; every machine's capacity and whether it is down; the "
            "current time step; cumulative KPIs so far; and how many turns remain. Costs one "
            "turn. Does not advance the simulation."
        ),
        "input_schema": {"type": "object", "properties": {}, "additionalProperties": False},
    },
    {
        "name": "submit_action",
        "description": (
            "Attempt to advance the simulation by exactly one time step: assign each machine "
            "(if any) to a job for this step, optionally flagging a machine to run in "
            "overtime. Costs one turn. An illegal assignment (unknown/down machine, "
            "unreleased/completed/double-booked job) is rejected -- the simulation does not "
            "advance, but the turn is still spent."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "assignments": {
                    "type": "object",
                    "description": (
                        "machine_id -> job_id for this step; omit a machine (or map it to "
                        "null) to leave it idle this step."
                    ),
                    "additionalProperties": {"type": ["string", "null"]},
                },
                "overtime": {
                    "type": "object",
                    "description": (
                        "machine_id -> true to run that machine in overtime this step; omit a "
                        "machine to run it at normal capacity."
                    ),
                    "additionalProperties": {"type": "boolean"},
                },
            },
            "additionalProperties": False,
        },
    },
]


class SimulationSession:
    """Turn-capped, tool-driven wrapper around one episode of `engine.step`.

    `turns_used` never exceeds `max_turns`: once the budget is spent, `get_state` and
    `submit_action` both refuse (an error dict, no further bookkeeping) rather than let a
    model keep querying or acting for free. `history` records only the actions actually
    *applied* (i.e. accepted by `engine.step`), in order -- a rejected call leaves it untouched.
    """

    def __init__(self, initial_state: dict, horizon: int, max_turns: int):
        self.state = copy.deepcopy(initial_state)
        self.horizon = horizon
        self.max_turns = max_turns
        self.turns_used = 0
        self.history: list[dict] = []

    @property
    def done(self) -> bool:
        return self.turns_used >= self.max_turns or self.state["time"] >= self.horizon

    def get_state(self, _tool_input: Optional[dict] = None) -> dict[str, Any]:
        if self.turns_used >= self.max_turns:
            return {"error": "turn budget exhausted", "done": True}
        self.turns_used += 1
        return {
            "time": self.state["time"],
            "horizon": self.horizon,
            "turns_remaining": self.max_turns - self.turns_used,
            "jobs": copy.deepcopy(self.state["jobs"]),
            "machines": copy.deepcopy(self.state["machines"]),
            "cumulative": copy.deepcopy(self.state["cumulative"]),
            "done": self.done,
        }

    def submit_action(self, tool_input: dict) -> dict[str, Any]:
        if self.turns_used >= self.max_turns:
            return {"error": "turn budget exhausted", "done": True}
        self.turns_used += 1

        if self.state["time"] >= self.horizon:
            return {"error": "simulation already complete", "time": self.state["time"], "done": True}

        assignments = (tool_input or {}).get("assignments") or {}
        overtime = (tool_input or {}).get("overtime") or {}
        if not isinstance(assignments, dict) or not isinstance(overtime, dict):
            return {
                "error": "'assignments' and 'overtime' must both be objects",
                "time": self.state["time"],
                "done": self.done,
            }

        try:
            new_state, kpis = engine.step(
                self.state, {"assignments": assignments, "overtime": overtime}
            )
        except (ValueError, KeyError, TypeError, AttributeError) as exc:
            return {"error": str(exc), "time": self.state["time"], "done": self.done}

        self.state = new_state
        self.history.append({"assignments": assignments, "overtime": overtime})
        return {
            "time": self.state["time"],
            "kpis_this_step": {
                "tardiness_incurred": kpis["tardiness_incurred"],
                "overtime_cost_incurred": kpis["overtime_cost_incurred"],
                "jobs_completed_this_step": kpis["jobs_completed_this_step"],
            },
            "cumulative": copy.deepcopy(self.state["cumulative"]),
            "done": self.done,
        }


def dispatch(session: SimulationSession, tool_name: str, tool_input: Optional[dict]) -> dict[str, Any]:
    """Route one model tool call to the matching `SimulationSession` method.

    `tool_name` is only ever one of the two names in `TOOL_DEFINITIONS` -- that's the complete
    set of tools an adapter hands the model -- so a mismatch here is an adapter/harness bug, not
    a model or scoring outcome, and is raised rather than swallowed.
    """
    if tool_name == "get_state":
        return session.get_state(tool_input)
    if tool_name == "submit_action":
        return session.submit_action(tool_input or {})
    raise ValueError(f"unknown tool {tool_name!r}")
