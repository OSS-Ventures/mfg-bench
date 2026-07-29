"""Model adapter interface.

One thin adapter per provider. Adding a model = adding one small file that implements this.
This is the ONE abstraction worth having; keep everything else concrete. No per-model prompt
tuning — the harness owns the prompt so comparison stays apples-to-apples.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Optional


@dataclass
class ModelResponse:
    text: str
    latency_ms: Optional[int] = None
    trajectory: Optional[list] = None  # multi-turn tool trajectory for L5 tasks


class Model(ABC):
    #: Model id as it appears in config.yaml / result records.
    name: str

    @abstractmethod
    def complete(self, prompt: str, tools: Optional[list] = None, **kwargs: Any) -> ModelResponse:
        """Run one completion at temperature 0 where the provider allows.

        `tools`, when given, exposes the simulator tool interface for L5 orchestration tasks.
        """
        raise NotImplementedError
