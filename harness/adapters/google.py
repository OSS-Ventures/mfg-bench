"""Google adapter -- thin wrapper around the Gemini API via the `google-genai` SDK (Google's
unified client for the Gemini Developer API and Vertex AI; supersedes the older, heavier
`google-generativeai` package).

One completion per `complete()` call, temperature 0 by default. Reads the API key from
`GEMINI_API_KEY` (or `GOOGLE_API_KEY`) via the SDK's own default; no key handling lives here.
"""
from __future__ import annotations

import time
from typing import Any, Optional

from google import genai
from google.genai import types

from harness.adapters.base import Model, ModelResponse

DEFAULT_MAX_TOKENS = 1024


class GoogleModel(Model):
    def __init__(self, name: str, temperature: float = 0, max_tokens: int = DEFAULT_MAX_TOKENS):
        self.name = name
        self.temperature = temperature
        self.max_tokens = max_tokens
        self._client = genai.Client()

    def complete(self, prompt: str, tools: Optional[list] = None, **kwargs: Any) -> ModelResponse:
        start = time.monotonic()
        config = types.GenerateContentConfig(
            temperature=self.temperature,
            max_output_tokens=kwargs.pop("max_output_tokens", self.max_tokens),
            **kwargs,
        )
        response = self._client.models.generate_content(
            model=self.name,
            contents=prompt,
            config=config,
        )
        latency_ms = int((time.monotonic() - start) * 1000)
        return ModelResponse(text=response.text or "", latency_ms=latency_ms, trajectory=None)
