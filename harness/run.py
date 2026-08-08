"""Main runner: generate a task -> call a model -> score -> log a result record.

Unit 0.1 wires the OEE generator + numeric scorer + Anthropic adapter through this end to end:

    python -m harness.run --generator oee --seed 123 --model anthropic
"""
from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

import yaml

from generators.fmea import FMEAGenerator
from generators.inventory_policy import InventoryPolicyGenerator
from generators.mrp import MRPGenerator
from generators.oee import OEEGenerator
from generators.quality_economics import QualityEconomicsGenerator
from generators.scheduling import SchedulingGenerator
from generators.simulated_decision import (
    DemandSpikeRebalanceDecisionGenerator,
    DemandSpikeRebalanceOrchestrationGenerator,
    LineDownRecoveryDecisionGenerator,
    LineDownRecoveryOrchestrationGenerator,
)
from generators.spc import SPCGenerator
from generators.standard_cost_variance import StandardCostVarianceGenerator
from generators.toc import TOCGenerator
from harness.adapters.anthropic import AnthropicModel
from harness.adapters.base import Model
from harness.adapters.google import GoogleModel
from harness.adapters.openai import OpenAIModel
from harness.validate import validate_result, validate_task
from scorers.numeric import NumericScorer
from scorers.simulated import SimulatedScorer
from simulator.tools import TOOL_DEFINITIONS, SimulationSession, dispatch

ROOT = Path(__file__).resolve().parent.parent

GENERATORS = {
    "oee": OEEGenerator,
    "mrp": MRPGenerator,
    "inventory_policy": InventoryPolicyGenerator,
    "spc": SPCGenerator,
    "scheduling": SchedulingGenerator,
    "toc": TOCGenerator,
    "quality_economics": QualityEconomicsGenerator,
    "fmea": FMEAGenerator,
    "standard_cost_variance": StandardCostVarianceGenerator,
    "line_down_recovery_decision": LineDownRecoveryDecisionGenerator,
    "demand_spike_rebalance_decision": DemandSpikeRebalanceDecisionGenerator,
    "line_down_recovery_orchestration": LineDownRecoveryOrchestrationGenerator,
    "demand_spike_rebalance_orchestration": DemandSpikeRebalanceOrchestrationGenerator,
}
SCORERS = {"numeric": NumericScorer, "simulated": SimulatedScorer}
ADAPTERS = {"anthropic": AnthropicModel, "openai": OpenAIModel, "google": GoogleModel}


def load_config() -> dict:
    return yaml.safe_load((ROOT / "config.yaml").read_text())


def num_parts_of(task: dict[str, Any]) -> int:
    """Number of numeric answer parts a task expects (1 unless ground_truth has "parts")."""
    parts = task["ground_truth"].get("parts") if isinstance(task["ground_truth"], dict) else None
    return len(parts) if parts else 1


def build_prompt(task: dict[str, Any], answer_tag: str, num_parts: int = 1) -> str:
    if num_parts > 1:
        example = ", ".join(str(i) for i in range(1, num_parts + 1))
        instruction = (
            f"Respond with only your {num_parts} final numeric answers, comma-separated, "
            f"inside <{answer_tag}></{answer_tag}> tags, e.g. <{answer_tag}>{example}</{answer_tag}>."
        )
    else:
        instruction = (
            f"Respond with only your final numeric answer inside <{answer_tag}></{answer_tag}> "
            f"tags, e.g. <{answer_tag}>0.1234</{answer_tag}>."
        )
    return f"{task['prompt']}\n\n{instruction}"


def parse_numeric_answer(
    raw_response: str, answer_tag: str, num_parts: int = 1
) -> tuple[Optional[float] | list[float], bool]:
    """Parse the model's numeric answer(s) out of the `<answer_tag>` block.

    A single-part task (`num_parts == 1`) returns a bare float. A multi-part task expects
    exactly `num_parts` comma-separated numbers and returns a list of floats. Any mismatch
    (missing tag, wrong part count, non-numeric token) is a parse failure: `(None, True)`.
    """
    match = re.search(rf"<{answer_tag}>(.*?)</{answer_tag}>", raw_response, re.DOTALL)
    if not match:
        return None, True

    raw = match.group(1).strip()
    tokens = [t.strip() for t in raw.split(",")] if num_parts > 1 else [raw]
    tokens = [t for t in tokens if t]

    if len(tokens) != num_parts:
        return None, True

    try:
        values = [float(t) for t in tokens]
    except ValueError:
        return None, True

    return (values[0] if num_parts == 1 else values), False


def build_simulated_prompt(task: dict[str, Any], answer_tag: str) -> str:
    horizon = task["ground_truth"]["horizon"]
    instruction = (
        f"Respond with a single JSON list of exactly {horizon} objects, one per time step in "
        f"order (step 0 first, step {horizon - 1} last). Each object has the form "
        '{"assignments": {"<machine_id>": "<job_id>", ...}, "overtime": {"<machine_id>": true, '
        '...}}. Omit a machine from "assignments" (or map it to null) to leave it idle that '
        'step; omit "overtime" entirely, or a machine from it, to run that machine at normal '
        f"capacity. Respond with only that JSON list inside <{answer_tag}></{answer_tag}> tags, "
        "no other text."
    )
    return f"{task['prompt']}\n\n{instruction}"


def parse_simulated_answer(raw_response: str, answer_tag: str) -> tuple[Any, bool]:
    """Parse the model's action plan out of the `<answer_tag>` block: a JSON list (of anything
    -- per-step structural validity is `scorers.simulated.SimulatedScorer`'s concern, since an
    illegal-but-well-formed plan is a scoring outcome, not a parse failure). A missing tag or
    non-JSON-list content is a parse failure: `(None, True)`."""
    match = re.search(rf"<{answer_tag}>(.*?)</{answer_tag}>", raw_response, re.DOTALL)
    if not match:
        return None, True
    try:
        parsed = json.loads(match.group(1).strip())
    except json.JSONDecodeError:
        return None, True
    if not isinstance(parsed, list):
        return None, True
    return parsed, False


def run_orchestration(
    task: dict[str, Any], model: Model, scorer: SimulatedScorer
) -> tuple[Any, list[dict], float]:
    """L5 path (unit 2.5): drive the task's scenario through a live `SimulationSession` instead
    of parsing a one-shot `<answer>` block. The task's own prompt already explains the tool
    interaction, so it is sent as-is; `model.complete()` (for an adapter that implements the
    agentic loop, per `harness.adapters.base.Model.complete`'s docstring) calls `tool_executor`
    for every tool use until it stops or the turn budget is spent. The score comes from whatever
    final state the session actually reached -- never from the model's own account of what it
    did.
    """
    ground_truth = task["ground_truth"]
    session = SimulationSession(
        ground_truth["initial_state"], ground_truth["horizon"], ground_truth["max_turns"]
    )

    def tool_executor(tool_name: str, tool_input: Optional[dict]) -> dict:
        return dispatch(session, tool_name, tool_input)

    response = model.complete(
        task["prompt"],
        tools=TOOL_DEFINITIONS,
        tool_executor=tool_executor,
        max_turns=ground_truth["max_turns"],
    )
    score = scorer.score_state(task, session.state)
    return response, session.history, score


def build_model(model_name: str, config: dict) -> Model:
    model_config = next(m for m in config["models"] if m["adapter"] == model_name)
    adapter_cls = ADAPTERS[model_config["adapter"]]
    return adapter_cls(name=model_config["name"], temperature=model_config.get("temperature", 0))


def run(
    generator_name: str,
    seed: int,
    model_name: str,
    difficulty: str = "standard",
    model: Optional[Model] = None,
) -> dict[str, Any]:
    """Generate one task, run it through a model, score it, and return a result record."""
    config = load_config()

    task = GENERATORS[generator_name]().generate(seed=seed, difficulty=difficulty)
    validate_task(task)

    scorer = SCORERS[task["scorer"]]()
    model = model if model is not None else build_model(model_name, config)

    if task["answer_format"] == "simulated" and task["reasoning_tier"] == "L5":
        response, parsed_answer, score = run_orchestration(task, model, scorer)
        parse_failure = False
    elif task["answer_format"] == "simulated":
        prompt = build_simulated_prompt(task, config["answer_tag"])
        response = model.complete(prompt)
        parsed_answer, parse_failure = parse_simulated_answer(response.text, config["answer_tag"])
        score = 0.0 if parse_failure else scorer.score(task, parsed_answer)
    else:
        num_parts = num_parts_of(task)
        prompt = build_prompt(task, config["answer_tag"], num_parts)
        response = model.complete(prompt)
        parsed_answer, parse_failure = parse_numeric_answer(
            response.text, config["answer_tag"], num_parts
        )
        score = 0.0 if parse_failure else scorer.score(task, parsed_answer)

    result = {
        "task_id": task["id"],
        "model": model.name,
        "harness_version": config["harness_version"],
        "raw_response": response.text,
        "parsed_answer": parsed_answer,
        "score": score,
        "latency_ms": response.latency_ms,
        "trajectory": response.trajectory,
        "parse_failure": parse_failure,
        "created": datetime.now(timezone.utc).isoformat(),
    }
    validate_result(result)
    return result


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate a task, run it through a model, score it, and log the result."
    )
    parser.add_argument("--generator", required=True, choices=sorted(GENERATORS))
    parser.add_argument("--seed", type=int, required=True)
    parser.add_argument("--model", required=True, choices=sorted(ADAPTERS))
    parser.add_argument("--difficulty", default="standard", choices=["standard", "hard"])
    args = parser.parse_args()

    result = run(args.generator, args.seed, args.model, args.difficulty)

    results_dir = ROOT / "results"
    results_dir.mkdir(exist_ok=True)
    out_path = results_dir / f"{args.model}.jsonl"
    with out_path.open("a") as f:
        f.write(json.dumps(result) + "\n")

    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
