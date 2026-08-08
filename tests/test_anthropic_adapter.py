"""Tests for harness/adapters/anthropic.py's agentic tool-calling loop (unit 2.5).

The real `anthropic.Anthropic()` client needs network + an API key -- exercised for real only
by `python -m harness.run --generator ... --model anthropic` (confirmed elsewhere to reach the
real API call and fail only on the missing key). Here, `AnthropicModel._client` is replaced with
a small stub exposing just `.messages.create(...)`, returning plain `SimpleNamespace` stand-ins
for the SDK's `Message`/content-block objects (matching the field names the real SDK uses:
`content`, block `.type`/`.text`/`.id`/`.name`/`.input`) -- this tests the loop's own control
flow (turn capping, tool dispatch, message/trajectory construction), not the SDK.
"""
from __future__ import annotations

import json
from types import SimpleNamespace

from harness.adapters.anthropic import AnthropicModel


def _text_block(text: str) -> SimpleNamespace:
    return SimpleNamespace(type="text", text=text)


def _tool_use_block(id_: str, name: str, input_: dict) -> SimpleNamespace:
    return SimpleNamespace(type="tool_use", id=id_, name=name, input=input_)


def _message(*blocks: SimpleNamespace) -> SimpleNamespace:
    return SimpleNamespace(content=list(blocks))


class StubClient:
    """Stands in for `anthropic.Anthropic()`: `.messages.create(...)` returns the next queued
    response and records every call's kwargs for inspection."""

    def __init__(self, responses: list[SimpleNamespace]):
        self._responses = list(responses)
        self.calls: list[dict] = []

    class _Messages:
        def __init__(self, outer: "StubClient"):
            self._outer = outer

        def create(self, **kwargs):
            # `messages` is the loop's live, mutated-in-place list; snapshot it now (a shallow
            # copy of the list, not its contents) so a later inspection of an earlier call sees
            # what was actually sent at that point in time, not whatever the list grew into.
            snapshot = {**kwargs, "messages": list(kwargs["messages"])}
            self._outer.calls.append(snapshot)
            return self._outer._responses.pop(0)

    @property
    def messages(self):
        return self._Messages(self)


def _model_with_stub(responses: list[SimpleNamespace]) -> tuple[AnthropicModel, StubClient]:
    model = AnthropicModel(name="claude-test")
    stub = StubClient(responses)
    model._client = stub
    return model, stub


def test_complete_without_tools_makes_one_call_and_returns_text():
    model, stub = _model_with_stub([_message(_text_block("0.7594"))])
    response = model.complete("what is OEE?")
    assert len(stub.calls) == 1
    assert stub.calls[0]["messages"] == [{"role": "user", "content": "what is OEE?"}]
    assert response.text == "0.7594"
    assert response.trajectory is None


def test_agentic_loop_stops_immediately_on_a_tool_free_response():
    model, stub = _model_with_stub([_message(_text_block("no tools needed"))])
    calls_to_executor = []

    response = model.complete(
        "prompt", tools=[{"name": "get_state"}], tool_executor=calls_to_executor.append, max_turns=5
    )

    assert len(stub.calls) == 1
    assert calls_to_executor == []
    assert response.text == "no tools needed"
    assert response.trajectory == [{"role": "assistant", "content": [{"type": "text", "text": "no tools needed"}]}]


def test_agentic_loop_executes_a_tool_call_and_feeds_the_result_back():
    responses = [
        _message(_tool_use_block("t1", "get_state", {})),
        _message(_text_block("done")),
    ]
    model, stub = _model_with_stub(responses)

    executor_calls = []

    def tool_executor(name, tool_input):
        executor_calls.append((name, tool_input))
        return {"time": 0, "done": False}

    response = model.complete(
        "prompt", tools=[{"name": "get_state"}], tool_executor=tool_executor, max_turns=5
    )

    assert executor_calls == [("get_state", {})]
    assert len(stub.calls) == 2
    # Second call's message history includes the tool_result fed back for the first tool call.
    second_call_messages = stub.calls[1]["messages"]
    assert second_call_messages[-1] == {
        "role": "user",
        "content": [
            {"type": "tool_result", "tool_use_id": "t1", "content": json.dumps({"time": 0, "done": False})}
        ],
    }
    assert response.text == "done"
    assert len(response.trajectory) == 3  # assistant(tool_use), tool_result, assistant(text)
    assert response.trajectory[0]["content"][0]["name"] == "get_state"
    assert response.trajectory[1]["role"] == "tool_result"


def test_agentic_loop_executes_multiple_tool_calls_in_one_turn():
    responses = [
        _message(
            _tool_use_block("t1", "get_state", {}),
            _tool_use_block("t2", "submit_action", {"assignments": {}}),
        ),
        _message(_text_block("done")),
    ]
    model, stub = _model_with_stub(responses)
    executor_calls = []

    model.complete(
        "prompt",
        tools=[{"name": "get_state"}, {"name": "submit_action"}],
        tool_executor=lambda name, inp: executor_calls.append((name, inp)) or {"ok": True},
        max_turns=5,
    )

    assert executor_calls == [("get_state", {}), ("submit_action", {"assignments": {}})]
    tool_result_content = stub.calls[1]["messages"][-1]["content"]
    assert [c["tool_use_id"] for c in tool_result_content] == ["t1", "t2"]


def test_agentic_loop_respects_max_turns_cap_even_if_model_never_stops():
    # Every response keeps requesting another tool call -- without a cap this would loop forever.
    def always_tool_use(**kwargs):
        return _message(_tool_use_block("t", "get_state", {}))

    model = AnthropicModel(name="claude-test")
    stub = StubClient([])
    stub.messages.create = always_tool_use  # type: ignore[method-assign]
    model._client = SimpleNamespace(messages=SimpleNamespace(create=always_tool_use))

    call_count = {"n": 0}

    def tool_executor(name, tool_input):
        call_count["n"] += 1
        return {"turns_remaining": 0}

    response = model.complete(
        "prompt", tools=[{"name": "get_state"}], tool_executor=tool_executor, max_turns=4
    )
    assert call_count["n"] == 4
    assert len(response.trajectory) == 8  # 4x (assistant tool_use + tool_result)


def test_complete_ignores_tools_when_no_tool_executor_given():
    # tools alone (no executor) is not enough to trigger the agentic loop -- falls back to one
    # ordinary completion, matching every other adapter's behavior when tools go unused.
    model, stub = _model_with_stub([_message(_text_block("plain answer"))])
    response = model.complete("prompt", tools=[{"name": "get_state"}])
    assert len(stub.calls) == 1
    assert "tools" not in stub.calls[0]
    assert response.text == "plain answer"
    assert response.trajectory is None
