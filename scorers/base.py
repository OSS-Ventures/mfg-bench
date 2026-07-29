"""Scorer interface.

A Scorer is a pure function (task, model_answer) -> float in [0, 1]. No side effects, no
network, no model calls. Truth comes from the task's ground_truth (computed/sourced/simulated),
never from a model's opinion.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class Scorer(ABC):
    #: Stable scorer name, e.g. "numeric". Matches a task's `scorer` field.
    name: str

    @abstractmethod
    def score(self, task: dict[str, Any], model_answer: Any) -> float:
        """Return a score in [0, 1]. Deterministic and pure."""
        raise NotImplementedError
