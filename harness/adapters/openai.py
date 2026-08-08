"""OpenAI adapter -- thin wrapper around the Chat Completions API.

One completion per `complete()` call, temperature 0 by default. Reads the API key from
`OPENAI_API_KEY` via the SDK's own default; no key handling lives here.
"""
from __future__ import annotations

import time
from typing import Any, Optional

import openai

from harness.adapters.base import Model, ModelResponse

DEFAULT_MAX_TOKENS = 1024


class OpenAIModel(Model):
    def __init__(self, name: str, temperature: float = 0, max_tokens: int = DEFAULT_MAX_TOKENS):
        self.name = name
        self.temperature = temperature
        self.max_tokens = max_tokens
        self._client = openai.OpenAI()

    def complete(self, prompt: str, tools: Optional[list] = None, **kwargs: Any) -> ModelResponse:
        # Native tool-calling (L5 orchestration) is not yet implemented for this adapter; drop
        # the L5-only kwargs and fall back to one ordinary completion rather than raising (see
        # harness.adapters.base.Model.complete's docstring).
        kwargs.pop("tool_executor", None)
        kwargs.pop("max_turns", None)
        start = time.monotonic()
        response = self._client.chat.completions.create(
            model=self.name,
            max_completion_tokens=kwargs.pop("max_completion_tokens", self.max_tokens),
            temperature=self.temperature,
            messages=[{"role": "user", "content": prompt}],
            **kwargs,
        )
        latency_ms = int((time.monotonic() - start) * 1000)
        text = response.choices[0].message.content or ""
        return ModelResponse(text=text, latency_ms=latency_ms, trajectory=None)
