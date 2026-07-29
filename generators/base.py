"""Generator interface.

A Generator produces task records that are *correct by construction*: it computes the ground
truth itself, so no model opinion is involved. Every task it emits must validate against
schemas/task.schema.json and carry its generator name, seed, and scorer.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class Generator(ABC):
    #: Stable generator name, e.g. "oee". Written into every task's `generator` field.
    name: str

    @abstractmethod
    def generate(self, seed: int, difficulty: str = "standard") -> dict[str, Any]:
        """Return one task record (a dict matching schemas/task.schema.json).

        Must be deterministic: the same (seed, difficulty) always yields the same task and the
        same ground truth. The ground truth is computed here, never supplied by a model.
        """
        raise NotImplementedError
