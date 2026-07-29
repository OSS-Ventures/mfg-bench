"""End-to-end harness wiring test: generate -> run -> score -> log a valid result record.

Uses a fake Model (no network call) so this runs in CI without an API key; the real
Anthropic adapter is exercised by `python -m harness.run --generator oee --seed <n> --model
anthropic` when an ANTHROPIC_API_KEY is available.
"""
from harness.adapters.base import Model, ModelResponse
from harness.run import run
from harness.validate import validate_result


class FakeModel(Model):
    def __init__(self, name="fake-model", answer="0.7689"):
        self.name = name
        self._answer = answer

    def complete(self, prompt, tools=None, **kwargs):
        return ModelResponse(text=f"<answer>{self._answer}</answer>", latency_ms=1)


def test_run_produces_a_valid_result_record():
    result = run("oee", seed=123, model_name="anthropic", model=FakeModel())
    validate_result(result)  # raises on schema failure
    assert result["task_id"] == "compute.oee.000123"
    assert result["parsed_answer"] == 0.7689
    assert result["parse_failure"] is False
    assert result["score"] == 1.0


def test_run_scores_zero_on_wrong_answer():
    result = run("oee", seed=123, model_name="anthropic", model=FakeModel(answer="0.1"))
    validate_result(result)
    assert result["score"] == 0.0


def test_run_flags_parse_failure_when_answer_tag_missing():
    class NoTagModel(Model):
        name = "no-tag-model"

        def complete(self, prompt, tools=None, **kwargs):
            return ModelResponse(text="the answer is 0.75", latency_ms=1)

    result = run("oee", seed=123, model_name="anthropic", model=NoTagModel())
    validate_result(result)
    assert result["parse_failure"] is True
    assert result["parsed_answer"] is None
    assert result["score"] == 0.0
