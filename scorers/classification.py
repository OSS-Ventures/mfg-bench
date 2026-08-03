"""Classification / multiple-choice scorer: exact match (single-label) or set match
(multi-label).

score = 1.0 if the (normalized) model answer exactly matches the (normalized) ground-truth
label(s), else 0.0. Normalization is a strip + case-fold, so "Root Cause A" and "root cause a"
are treated as the same label -- labels are compared as text, not as opaque tokens.

Single-label tasks carry `ground_truth["value"]` as a string; the model answer must be a
string. Multi-label ("set match") tasks carry `ground_truth["value"]` as a list of strings;
the model answer must be a list/tuple of strings and is compared as an unordered set (so
answer order never matters, and duplicates collapse).
"""
from __future__ import annotations

from typing import Any

from scorers.base import Scorer


class ClassificationScorer(Scorer):
    name = "classification"

    def score(self, task: dict[str, Any], model_answer: Any) -> float:
        truth = task["ground_truth"]["value"]

        if isinstance(truth, (list, tuple)):
            return self._score_set(truth, model_answer)
        return self._score_single(truth, model_answer)

    @staticmethod
    def _normalize(label: Any) -> str:
        return str(label).strip().casefold()

    @classmethod
    def _score_single(cls, truth: str, model_answer: Any) -> float:
        if not isinstance(model_answer, str):
            return 0.0
        return 1.0 if cls._normalize(model_answer) == cls._normalize(truth) else 0.0

    @classmethod
    def _score_set(cls, truth: list[str], model_answer: Any) -> float:
        if not isinstance(model_answer, (list, tuple)):
            return 0.0
        if not all(isinstance(item, str) for item in model_answer):
            return 0.0

        truth_set = {cls._normalize(item) for item in truth}
        answer_set = {cls._normalize(item) for item in model_answer}
        return 1.0 if answer_set == truth_set else 0.0
