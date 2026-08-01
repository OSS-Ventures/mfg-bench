"""FMEA (Failure Mode and Effects Analysis) arithmetic generator.

Given a set of failure modes, each rated on the standard 1-10 Severity / Occurrence /
Detection scales, computes:
- each failure mode's Risk Priority Number (RPN = Severity x Occurrence x Detection),
- the top-priority failure mode (the one with the highest RPN -- the one the team should
  address first; ties go to the earliest-listed failure mode), and
- how many failure modes meet or exceed the project's action threshold.

All values are derived directly from each failure mode's S/O/D ratings and the given
threshold -- correct by construction, never a model's opinion. (Note: this is arithmetic
prioritization over generated ratings, not a claim about what the S/O/D scales "should" mean --
that scale-interpretation reasoning belongs to the Family B FMEA task, unit 3.3.)
"""
from __future__ import annotations

import random
from datetime import datetime, timezone
from typing import Any

from generators.base import Generator

ACTION_THRESHOLD = 100


class FMEAGenerator(Generator):
    name = "fmea"

    def generate(self, seed: int, difficulty: str = "standard") -> dict[str, Any]:
        rng = random.Random(seed)

        num_failure_modes = 4 if difficulty == "standard" else 5

        failure_modes = [
            {
                "description": f"Failure mode {i + 1}",
                "severity": rng.randint(1, 10),
                "occurrence": rng.randint(1, 10),
                "detection": rng.randint(1, 10),
            }
            for i in range(num_failure_modes)
        ]

        metrics = compute_fmea_metrics(failure_modes, ACTION_THRESHOLD)

        fm_lines = "\n".join(
            f"Failure mode {i + 1}: Severity = {fm['severity']}, "
            f"Occurrence = {fm['occurrence']}, Detection = {fm['detection']}"
            for i, fm in enumerate(failure_modes)
        )

        prompt = (
            f"An FMEA has identified {num_failure_modes} failure modes for a process, each "
            "rated on the standard 1-10 Severity, Occurrence, and Detection scales:\n\n"
            f"{fm_lines}\n\n"
            "Formulas:\n"
            "- Risk Priority Number (RPN) = Severity x Occurrence x Detection, for each "
            "failure mode.\n"
            "- The top-priority failure mode is the one with the highest RPN (the one the "
            "team should address first). If two or more failure modes tie for the highest "
            "RPN, the top priority is the earliest-listed one.\n"
            f"- For this project, any failure mode with RPN >= {ACTION_THRESHOLD} requires "
            "priority corrective action.\n\n"
            f"Compute, in this order: (1)-({num_failure_modes}) the RPN of each failure mode, "
            f"in listed order, ({num_failure_modes + 1}) the number (1-{num_failure_modes}) of "
            f"the top-priority failure mode, ({num_failure_modes + 2}) how many failure modes "
            f"require priority corrective action (RPN >= {ACTION_THRESHOLD})."
        )

        parts = [
            {"value": float(rpn), "tolerance": 0.01, "tolerance_type": "absolute"}
            for rpn in metrics["rpns"]
        ]
        parts.append(
            {
                "value": float(metrics["top_priority_failure_mode"]),
                "tolerance": 0.01,
                "tolerance_type": "absolute",
            }
        )
        parts.append(
            {
                "value": float(metrics["count_above_threshold"]),
                "tolerance": 0.01,
                "tolerance_type": "absolute",
            }
        )

        return {
            "id": f"compute.fmea.{seed:06d}",
            "family": "computed",
            "domain": "quality_problem_solving",
            "reasoning_tier": "L3",
            "answer_format": "numeric",
            "prompt": prompt,
            "context": {
                "failure_modes": failure_modes,
                "action_threshold": ACTION_THRESHOLD,
            },
            "ground_truth": {"parts": parts},
            "scorer": "numeric",
            "generator": self.name,
            "seed": seed,
            "difficulty": difficulty,
            "source": None,
            "source_url": None,
            "created": datetime.now(timezone.utc).date().isoformat(),
            "public": True,
        }


def compute_fmea_metrics(
    failure_modes: list[dict[str, Any]], action_threshold: int
) -> dict[str, Any]:
    """Compute each failure mode's RPN, the top-priority failure mode, and the count meeting
    or exceeding the action threshold.

    Pure function of each failure mode's severity/occurrence/detection ratings and the
    threshold -- no randomness, no model opinion. Shared by the generator and independently
    re-derived (not called) by the hand-verified tests.
    """
    rpns = [fm["severity"] * fm["occurrence"] * fm["detection"] for fm in failure_modes]
    top_priority_index = max(range(len(rpns)), key=lambda i: rpns[i])
    count_above_threshold = sum(1 for rpn in rpns if rpn >= action_threshold)

    return {
        "rpns": rpns,
        "top_priority_failure_mode": top_priority_index + 1,
        "count_above_threshold": count_above_threshold,
    }
