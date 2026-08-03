"""Checklist / structured scorer: per-item fraction, with an all-or-nothing variant reported
alongside it.

`ground_truth["required_items"]` is the list of items a complete answer must include (e.g. the
disciplines of an 8D, the elements of a control plan). The model answer is a list/tuple of the
items it claims are present. Both sides are normalized (strip + case-fold) before comparison,
so item identity is by text, not by exact formatting.

`score()` (the primary, partial-credit score used for grading) is the *fraction* of required
items correctly present: `|required ∩ answer| / |required|`. Extra, non-required items in the
answer are not penalized -- this mirrors SPEC.md Section 8 ("fraction of required items
correctly present"), not a precision/recall blend.

`all_or_nothing_score()` is the stricter companion metric SPEC.md asks to report alongside the
fraction: 1.0 only if every required item is present (regardless of extras), else 0.0.
"""
from __future__ import annotations

from typing import Any

from scorers.base import Scorer


class ChecklistScorer(Scorer):
    name = "checklist"

    def score(self, task: dict[str, Any], model_answer: Any) -> float:
        required = task["ground_truth"]["required_items"]
        if not required:
            return 0.0
        if not isinstance(model_answer, (list, tuple)):
            return 0.0
        if not all(isinstance(item, str) for item in model_answer):
            return 0.0

        required_set = {self._normalize(item) for item in required}
        answer_set = {self._normalize(item) for item in model_answer}
        return len(required_set & answer_set) / len(required_set)

    def all_or_nothing_score(self, task: dict[str, Any], model_answer: Any) -> float:
        return 1.0 if self.score(task, model_answer) == 1.0 else 0.0

    @staticmethod
    def _normalize(item: Any) -> str:
        return str(item).strip().casefold()
