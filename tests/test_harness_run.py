"""End-to-end harness wiring test: generate -> run -> score -> log a valid result record.

Uses a fake Model (no network call) so this runs in CI without an API key; the real
Anthropic adapter is exercised by `python -m harness.run --generator oee --seed <n> --model
anthropic` when an ANTHROPIC_API_KEY is available.
"""
import pytest

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


def test_run_scores_multi_part_mrp_task_end_to_end():
    # seed=1, standard MRP task's ground truth is [80, 83, 142, 136, 3] (see tests/test_mrp.py).
    result = run("mrp", seed=1, model_name="anthropic", model=FakeModel(answer="80, 83, 142, 136, 3"))
    validate_result(result)
    assert result["task_id"] == "compute.mrp.000001"
    assert result["parsed_answer"] == [80.0, 83.0, 142.0, 136.0, 3.0]
    assert result["parse_failure"] is False
    assert result["score"] == 1.0


def test_run_scores_partial_mrp_answer_as_fraction_correct():
    # Only the last of 5 parts (release period = 3) is correct -> average score 0.2.
    result = run("mrp", seed=1, model_name="anthropic", model=FakeModel(answer="0, 0, 0, 0, 3"))
    validate_result(result)
    assert result["score"] == 0.2


def test_run_scores_multi_part_inventory_policy_task_end_to_end():
    # seed=1, standard inventory_policy task's ground truth is [690.52, 18.49, 162.49] (see
    # tests/test_inventory_policy.py).
    result = run(
        "inventory_policy",
        seed=1,
        model_name="anthropic",
        model=FakeModel(answer="690.52, 18.49, 162.49"),
    )
    validate_result(result)
    assert result["task_id"] == "compute.inventory_policy.000001"
    assert result["parsed_answer"] == [690.52, 18.49, 162.49]
    assert result["parse_failure"] is False
    assert result["score"] == 1.0


def test_run_scores_partial_inventory_policy_answer_as_fraction_correct():
    # Only the first of 3 parts (EOQ = 690.52) is correct -> average score ~0.333.
    result = run(
        "inventory_policy",
        seed=1,
        model_name="anthropic",
        model=FakeModel(answer="690.52, 0, 0"),
    )
    validate_result(result)
    assert result["score"] == pytest.approx(1 / 3)


def test_run_scores_multi_part_spc_task_end_to_end():
    # seed=1, standard SPC task's ground truth is [154.71, 145.02, 1.22, 1.21, 1.35, 1.34, 0.0]
    # (see tests/test_spc.py).
    result = run(
        "spc",
        seed=1,
        model_name="anthropic",
        model=FakeModel(answer="154.71, 145.02, 1.22, 1.21, 1.35, 1.34, 0.0"),
    )
    validate_result(result)
    assert result["task_id"] == "compute.spc.000001"
    assert result["parsed_answer"] == [154.71, 145.02, 1.22, 1.21, 1.35, 1.34, 0.0]
    assert result["parse_failure"] is False
    assert result["score"] == 1.0


def test_run_scores_partial_spc_answer_as_fraction_correct():
    # Only 2 of 7 parts (UCL, LCL) correct -> average score 2/7.
    result = run(
        "spc",
        seed=1,
        model_name="anthropic",
        model=FakeModel(answer="154.71, 145.02, 0, 0, 0, 0, 5"),
    )
    validate_result(result)
    assert result["score"] == pytest.approx(2 / 7)


def test_run_scores_scheduling_task_end_to_end():
    # seed=8, standard scheduling task's optimal total tardiness is 5.0 (see test_scheduling.py).
    result = run("scheduling", seed=8, model_name="anthropic", model=FakeModel(answer="5"))
    validate_result(result)
    assert result["task_id"] == "compute.scheduling.000008"
    assert result["parsed_answer"] == 5.0
    assert result["parse_failure"] is False
    assert result["score"] == 1.0


def test_run_scores_zero_on_wrong_scheduling_answer():
    # seed=12, hard scheduling task's optimal total weighted tardiness is 43.0.
    result = run("scheduling", seed=12, model_name="anthropic", model=FakeModel(answer="0"))
    validate_result(result)
    assert result["score"] == 0.0


def test_run_scores_multi_part_toc_task_end_to_end():
    # seed=1, standard TOC task's ground truth is [4.0, 6.67, 60.0] (see tests/test_toc.py).
    result = run("toc", seed=1, model_name="anthropic", model=FakeModel(answer="4, 6.67, 60.0"))
    validate_result(result)
    assert result["task_id"] == "compute.toc.000001"
    assert result["parsed_answer"] == [4.0, 6.67, 60.0]
    assert result["parse_failure"] is False
    assert result["score"] == 1.0


def test_run_scores_partial_toc_answer_as_fraction_correct():
    # Only the first of 3 parts (bottleneck station = 4) is correct -> average score 1/3.
    result = run("toc", seed=1, model_name="anthropic", model=FakeModel(answer="4, 0, 0"))
    validate_result(result)
    assert result["score"] == pytest.approx(1 / 3)
