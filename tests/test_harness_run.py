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


def test_run_scores_multi_part_quality_economics_task_end_to_end():
    # seed=1, standard quality_economics task's ground truth is
    # [90.0, 72.84, 3063.31, 2960.55, 6023.86] (see tests/test_quality_economics.py).
    result = run(
        "quality_economics",
        seed=1,
        model_name="anthropic",
        model=FakeModel(answer="90.0, 72.84, 3063.31, 2960.55, 6023.86"),
    )
    validate_result(result)
    assert result["task_id"] == "compute.quality_economics.000001"
    assert result["parsed_answer"] == [90.0, 72.84, 3063.31, 2960.55, 6023.86]
    assert result["parse_failure"] is False
    assert result["score"] == 1.0


def test_run_scores_partial_quality_economics_answer_as_fraction_correct():
    # Only the first 2 of 5 parts (average FPY, RTY) are correct -> average score 2/5.
    result = run(
        "quality_economics",
        seed=1,
        model_name="anthropic",
        model=FakeModel(answer="90.0, 72.84, 0, 0, 0"),
    )
    validate_result(result)
    assert result["score"] == pytest.approx(2 / 5)


def test_run_scores_multi_part_fmea_task_end_to_end():
    # seed=1, standard FMEA task's ground truth is [60.0, 80.0, 448.0, 64.0, 3.0, 1.0]
    # (see tests/test_fmea.py).
    result = run(
        "fmea", seed=1, model_name="anthropic", model=FakeModel(answer="60, 80, 448, 64, 3, 1")
    )
    validate_result(result)
    assert result["task_id"] == "compute.fmea.000001"
    assert result["parsed_answer"] == [60.0, 80.0, 448.0, 64.0, 3.0, 1.0]
    assert result["parse_failure"] is False
    assert result["score"] == 1.0


def test_run_scores_partial_fmea_answer_as_fraction_correct():
    # Only the top-priority failure mode (3) and count-above-threshold (1) parts are correct
    # -> average score 2/6.
    result = run(
        "fmea", seed=1, model_name="anthropic", model=FakeModel(answer="0, 0, 0, 0, 3, 1")
    )
    validate_result(result)
    assert result["score"] == pytest.approx(2 / 6)


def test_run_scores_multi_part_standard_cost_variance_task_end_to_end():
    # seed=1, standard standard_cost_variance task's ground truth is
    # [12929.76, -18689.8, -26.25, 1027.8] (see tests/test_standard_cost_variance.py).
    result = run(
        "standard_cost_variance",
        seed=1,
        model_name="anthropic",
        model=FakeModel(answer="12929.76, -18689.8, -26.25, 1027.8"),
    )
    validate_result(result)
    assert result["task_id"] == "compute.standard_cost_variance.000001"
    assert result["parsed_answer"] == [12929.76, -18689.8, -26.25, 1027.8]
    assert result["parse_failure"] is False
    assert result["score"] == 1.0


def test_run_scores_partial_standard_cost_variance_answer_as_fraction_correct():
    # Only the first 2 of 4 parts (MPV, MQV) are correct -> average score 2/4.
    result = run(
        "standard_cost_variance",
        seed=1,
        model_name="anthropic",
        model=FakeModel(answer="12929.76, -18689.8, 0, 0"),
    )
    validate_result(result)
    assert result["score"] == pytest.approx(2 / 4)
