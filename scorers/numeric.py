"""Numeric scorer: tolerance-based exact match.

score = 1.0 if |answer - truth| is within tolerance (absolute or relative), else 0.0. Any
answer that cannot be parsed as a float scores 0.0 rather than raising.

Multi-part tasks carry `ground_truth["parts"]`, a list of single-part ground-truth dicts (each
with its own `value` / `tolerance` / `tolerance_type`). `model_answer` must then be a
list/tuple of the same length; the score is the average of the per-part scores. A single-part
task keeps `value` / `tolerance` / `tolerance_type` directly on `ground_truth`, as before.
"""
from __future__ import annotations

from typing import Any

from scorers.base import Scorer


class NumericScorer(Scorer):
    name = "numeric"

    def score(self, task: dict[str, Any], model_answer: Any) -> float:
        ground_truth = task["ground_truth"]
        parts = ground_truth.get("parts")

        if parts is None:
            return self._score_part(ground_truth, model_answer)

        if not isinstance(model_answer, (list, tuple)) or len(model_answer) != len(parts):
            return 0.0
        if not parts:
            return 0.0

        part_scores = [
            self._score_part(part, answer) for part, answer in zip(parts, model_answer)
        ]
        return sum(part_scores) / len(part_scores)

    @staticmethod
    def _score_part(ground_truth_part: dict[str, Any], model_answer: Any) -> float:
        if model_answer is None or isinstance(model_answer, bool):
            return 0.0
        try:
            answer = float(model_answer)
        except (TypeError, ValueError):
            return 0.0

        truth = ground_truth_part["value"]
        tolerance = ground_truth_part["tolerance"]
        tolerance_type = ground_truth_part.get("tolerance_type", "absolute")

        allowed = abs(truth) * tolerance if tolerance_type == "relative" else tolerance
        return 1.0 if abs(answer - truth) <= allowed else 0.0
