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

from generators.oee import OEEGenerator
from harness.adapters.anthropic import AnthropicModel
from harness.adapters.base import Model
from harness.validate import validate_result, validate_task
from scorers.numeric import NumericScorer

ROOT = Path(__file__).resolve().parent.parent

GENERATORS = {"oee": OEEGenerator}
SCORERS = {"numeric": NumericScorer}
ADAPTERS = {"anthropic": AnthropicModel}


def load_config() -> dict:
    return yaml.safe_load((ROOT / "config.yaml").read_text())


def build_prompt(task: dict[str, Any], answer_tag: str) -> str:
    return (
        f"{task['prompt']}\n\n"
        f"Respond with only your final numeric answer inside <{answer_tag}></{answer_tag}> tags, "
        f"e.g. <{answer_tag}>0.1234</{answer_tag}>."
    )


def parse_numeric_answer(raw_response: str, answer_tag: str) -> tuple[Optional[float], bool]:
    match = re.search(rf"<{answer_tag}>(.*?)</{answer_tag}>", raw_response, re.DOTALL)
    if not match:
        return None, True
    try:
        return float(match.group(1).strip()), False
    except ValueError:
        return None, True


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

    prompt = build_prompt(task, config["answer_tag"])
    response = model.complete(prompt)
    parsed_answer, parse_failure = parse_numeric_answer(response.text, config["answer_tag"])
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
