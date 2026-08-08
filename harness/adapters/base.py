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

        `tools`, when given, exposes the simulator tool interface for L5 orchestration tasks
        (`simulator.tools.TOOL_DEFINITIONS`). Two extra keyword arguments drive that mode:

        - `tool_executor: Callable[[str, dict], dict]` -- called with `(tool_name, tool_input)`
          for each tool call the model makes; returns the JSON-serializable result to hand back.
        - `max_turns: int` -- caps the number of model/tool round trips.

        When both are given, an adapter that supports native tool calling should run the full
        multi-turn loop itself (it alone knows its provider's tool-call wire format) and return
        the final text plus a logged `trajectory`. An adapter that does not implement this yet
        must still not raise -- per `GOALS.md`, a model that can't use tools is a legitimate
        (if poor) L5 result to score, not a harness bug -- so it should simply pop `tool_executor`
        and `max_turns` off `kwargs` and fall back to one ordinary completion (see
        `openai.py` / `google.py`).
        """
        raise NotImplementedError
