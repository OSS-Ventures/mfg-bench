"""Anthropic adapter — thin wrapper around the Messages API.

One completion per `complete()` call, temperature 0 by default, UNLESS both `tools` and
`tool_executor` are given (the L5 orchestration path, unit 2.5): then `complete()` drives the
full multi-turn tool-calling loop itself, since Anthropic's tool-call wire format (`tool_use`
content blocks, `tool_result` blocks fed back as the next user turn) is this adapter's own
concern per `harness.adapters.base.Model.complete`'s docstring. The loop stops the first time a
response contains no `tool_use` block (the model is done) or after `max_turns` round trips
(a hard ceiling — `simulator.tools.SimulationSession`'s own turn budget, which `tool_executor`
enforces per call, is the primary limit; this is a belt-and-suspenders backstop against a model
that only ever queries and never lets the session finish itself).

Reads the API key from `ANTHROPIC_API_KEY` via the SDK's own default; no key handling lives here.
"""
from __future__ import annotations

import json
import time
from typing import Any, Callable, Optional

import anthropic

from harness.adapters.base import Model, ModelResponse

DEFAULT_MAX_TOKENS = 1024


def _block_to_dict(block: Any) -> dict[str, Any]:
    """JSON-serializable rendering of one response content block, for trajectory logging."""
    if block.type == "tool_use":
        return {"type": "tool_use", "id": block.id, "name": block.name, "input": block.input}
    return {"type": "text", "text": block.text}


class AnthropicModel(Model):
    def __init__(self, name: str, temperature: float = 0, max_tokens: int = DEFAULT_MAX_TOKENS):
        self.name = name
        self.temperature = temperature
        self.max_tokens = max_tokens
        self._client = anthropic.Anthropic()

    def complete(self, prompt: str, tools: Optional[list] = None, **kwargs: Any) -> ModelResponse:
        tool_executor = kwargs.pop("tool_executor", None)
        max_turns = kwargs.pop("max_turns", None)
        start = time.monotonic()

        if tools and tool_executor is not None:
            text, trajectory = self._run_agentic_loop(
                prompt, tools, tool_executor, max_turns or 1, kwargs
            )
            latency_ms = int((time.monotonic() - start) * 1000)
            return ModelResponse(text=text, latency_ms=latency_ms, trajectory=trajectory)

        response = self._client.messages.create(
            model=self.name,
            max_tokens=kwargs.pop("max_tokens", self.max_tokens),
            temperature=self.temperature,
            messages=[{"role": "user", "content": prompt}],
            **kwargs,
        )
        latency_ms = int((time.monotonic() - start) * 1000)
        text = "".join(block.text for block in response.content if block.type == "text")
        return ModelResponse(text=text, latency_ms=latency_ms, trajectory=None)

    def _run_agentic_loop(
        self,
        opening_prompt: str,
        tools: list,
        tool_executor: Callable[[str, dict], dict],
        max_turns: int,
        kwargs: dict,
    ) -> tuple[str, list[dict]]:
        max_tokens = kwargs.pop("max_tokens", self.max_tokens)
        messages: list[dict] = [{"role": "user", "content": opening_prompt}]
        trajectory: list[dict] = []
        final_text = ""

        for _ in range(max_turns):
            response = self._client.messages.create(
                model=self.name,
                max_tokens=max_tokens,
                temperature=self.temperature,
                tools=tools,
                messages=messages,
                **kwargs,
            )
            messages.append({"role": "assistant", "content": response.content})
            trajectory.append(
                {"role": "assistant", "content": [_block_to_dict(b) for b in response.content]}
            )

            tool_use_blocks = [b for b in response.content if b.type == "tool_use"]
            final_text = "".join(b.text for b in response.content if b.type == "text")
            if not tool_use_blocks:
                break

            tool_results = [
                {
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": json.dumps(tool_executor(block.name, block.input)),
                }
                for block in tool_use_blocks
            ]
            messages.append({"role": "user", "content": tool_results})
            trajectory.append({"role": "tool_result", "content": tool_results})

        return final_text, trajectory
