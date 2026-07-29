"""Numeric scorer: tolerance-based exact match.

score = 1.0 if |answer - truth| is within tolerance (absolute or relative), else 0.0. Any
answer that cannot be parsed as a float scores 0.0 rather than raising.
"""
from __future__ import annotations

from typing import Any

from scorers.base import Scorer


class NumericScorer(Scorer):
    name = "numeric"

    def score(self, task: dict[str, Any], model_answer: Any) -> float:
        if model_answer is None:
            return 0.0
        try:
            answer = float(model_answer)
        except (TypeError, ValueError):
            return 0.0

        ground_truth = task["ground_truth"]
        truth = ground_truth["value"]
        tolerance = ground_truth["tolerance"]
        tolerance_type = ground_truth.get("tolerance_type", "absolute")

        allowed = abs(truth) * tolerance if tolerance_type == "relative" else tolerance
        return 1.0 if abs(answer - truth) <= allowed else 0.0
