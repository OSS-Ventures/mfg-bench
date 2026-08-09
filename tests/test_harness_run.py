"""End-to-end harness wiring test: generate -> run -> score -> log a valid result record.

Uses a fake Model (no network call) so this runs in CI without an API key; the real
Anthropic adapter is exercised by `python -m harness.run --generator oee --seed <n> --model
anthropic` when an ANTHROPIC_API_KEY is available.
"""
import copy
import json

import pytest

from generators.simulated_decision import (
    DemandSpikeRebalanceDecisionGenerator,
    DemandSpikeRebalanceOrchestrationGenerator,
    LineDownRecoveryDecisionGenerator,
    LineDownRecoveryOrchestrationGenerator,
)
from harness.adapters.base import Model, ModelResponse
from harness.run import run
from harness.validate import validate_result
from scorers.simulated import SimulatedScorer
from simulator import engine, policies
from simulator.scenarios import demand_spike_rebalance as dsr
from simulator.tools import SimulationSession


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


def _plan_json(initial_state: dict, policy_fn, horizon: int) -> str:
    """Drive `policy_fn` for `horizon` steps and JSON-encode the actions taken, to stand in for
    a model's one-shot plan (unit 2.4's L4 single-decision answer format)."""
    state = copy.deepcopy(initial_state)
    actions = []
    for _ in range(horizon):
        action = policy_fn(state)
        actions.append(action)
        state, _ = engine.step(state, action)
    return json.dumps(actions)


def test_run_scores_line_down_recovery_decision_task_end_to_end():
    task = LineDownRecoveryDecisionGenerator().generate(seed=1, difficulty="standard")
    gt = task["ground_truth"]
    plan = _plan_json(gt["initial_state"], policies.reference_policy, gt["horizon"])

    result = run(
        "line_down_recovery_decision",
        seed=1,
        model_name="anthropic",
        model=FakeModel(answer=plan),
    )
    validate_result(result)
    assert result["task_id"] == "simulated.line_down_recovery.000001"
    assert result["parse_failure"] is False
    assert result["parsed_answer"] == json.loads(plan)
    # The harness's parse -> score pipeline must agree with calling the scorer directly.
    assert result["score"] == SimulatedScorer().score(task, json.loads(plan))


def test_run_scores_demand_spike_rebalance_decision_task_end_to_end():
    task = DemandSpikeRebalanceDecisionGenerator().generate(seed=1, difficulty="standard")
    gt = task["ground_truth"]
    plan = _plan_json(gt["initial_state"], dsr._reference_policy_with_overtime, gt["horizon"])

    result = run(
        "demand_spike_rebalance_decision",
        seed=1,
        model_name="anthropic",
        model=FakeModel(answer=plan),
    )
    validate_result(result)
    assert result["task_id"] == "simulated.demand_spike_rebalance.000001"
    assert result["parse_failure"] is False
    assert result["score"] == SimulatedScorer().score(task, json.loads(plan))


def test_run_flags_parse_failure_for_simulated_task_when_answer_tag_missing():
    class NoTagModel(Model):
        name = "no-tag-model"

        def complete(self, prompt, tools=None, **kwargs):
            return ModelResponse(text="here is my plan", latency_ms=1)

    result = run(
        "line_down_recovery_decision", seed=1, model_name="anthropic", model=NoTagModel()
    )
    validate_result(result)
    assert result["parse_failure"] is True
    assert result["parsed_answer"] is None
    assert result["score"] == 0.0


def test_run_scores_0_for_simulated_task_with_illegal_plan():
    # Valid JSON, wrong shape (missing steps) -> the scorer rejects it, not the parser.
    result = run(
        "line_down_recovery_decision",
        seed=1,
        model_name="anthropic",
        model=FakeModel(answer="[]"),
    )
    validate_result(result)
    assert result["parse_failure"] is False
    assert result["score"] == 0.0


# --- L5 agentic orchestration (unit 2.5) --------------------------------------------------
# A FakeModel here must itself play the role of the agentic loop an adapter would normally run
# (harness.adapters.anthropic.AnthropicModel._run_agentic_loop is tested directly and separately
# in tests/test_anthropic_adapter.py) -- it calls `tool_executor` the same way a real tool-use
# loop would, so `harness.run.run_orchestration`'s wiring (constructing the SimulationSession,
# handing it a tool_executor, scoring the session's own final state) can be exercised without any
# network call.


class FakePolicyOrchestrationModel(Model):
    """Drives `policy_fn` through `tool_executor` for exactly `horizon` submit_action calls --
    stands in for a model that behaves like a known policy over the tool interface."""

    name = "fake-orchestration-model"

    def __init__(self, policy_fn, horizon):
        self._policy_fn = policy_fn
        self._horizon = horizon

    def complete(self, prompt, tools=None, tool_executor=None, max_turns=None, **kwargs):
        trajectory = []
        # The FakeModel doesn't see the session's real state directly (that would defeat the
        # point of going through tools) -- it queries get_state each step, exactly like a real
        # tool-calling model would, and feeds the observed state to the stand-in policy.
        for _ in range(self._horizon):
            observed = tool_executor("get_state", {})
            trajectory.append({"tool": "get_state", "result": observed})
            if observed.get("done"):
                break
            state_for_policy = {
                "time": observed["time"],
                "jobs": observed["jobs"],
                "machines": observed["machines"],
                "cumulative": observed["cumulative"],
            }
            action = self._policy_fn(state_for_policy)
            result = tool_executor("submit_action", action)
            trajectory.append({"tool": "submit_action", "action": action, "result": result})
        return ModelResponse(text="done", latency_ms=1, trajectory=trajectory)


class NeverCallsToolsModel(Model):
    name = "never-calls-tools-model"

    def complete(self, prompt, tools=None, tool_executor=None, max_turns=None, **kwargs):
        return ModelResponse(text="I decline to act.", latency_ms=1, trajectory=None)


def test_run_scores_line_down_recovery_orchestration_task_end_to_end():
    task = LineDownRecoveryOrchestrationGenerator().generate(seed=1, difficulty="standard")
    gt = task["ground_truth"]

    result = run(
        "line_down_recovery_orchestration",
        seed=1,
        model_name="anthropic",
        model=FakePolicyOrchestrationModel(policies.reference_policy, gt["horizon"]),
    )
    validate_result(result)
    assert result["task_id"] == "orchestration.line_down_recovery.000001"
    assert result["parse_failure"] is False
    assert result["score"] == 1.0
    # history is the sequence of actions actually applied through the session's tools.
    assert len(result["parsed_answer"]) == gt["horizon"]
    assert result["trajectory"] is not None and len(result["trajectory"]) > 0


def test_run_scores_demand_spike_rebalance_orchestration_task_end_to_end():
    task = DemandSpikeRebalanceOrchestrationGenerator().generate(seed=1, difficulty="standard")
    gt = task["ground_truth"]

    result = run(
        "demand_spike_rebalance_orchestration",
        seed=1,
        model_name="anthropic",
        model=FakePolicyOrchestrationModel(dsr._reference_policy_with_overtime, gt["horizon"]),
    )
    validate_result(result)
    assert result["task_id"] == "orchestration.demand_spike_rebalance.000001"
    assert result["score"] == 1.0


def test_run_scores_0_for_orchestration_task_when_model_never_calls_tools():
    # A model that ignores the tool interface entirely leaves the session at its initial
    # state -- a legitimate (if poor) result to score, not a parse failure or a crash.
    result = run(
        "line_down_recovery_orchestration",
        seed=1,
        model_name="anthropic",
        model=NeverCallsToolsModel(),
    )
    validate_result(result)
    assert result["parse_failure"] is False
    assert result["parsed_answer"] == []
    assert result["score"] == 0.0


def test_run_orchestration_score_matches_calling_score_state_directly():
    task = LineDownRecoveryOrchestrationGenerator().generate(seed=7, difficulty="standard")
    gt = task["ground_truth"]
    model = FakePolicyOrchestrationModel(policies.baseline_policy, gt["horizon"])

    result = run("line_down_recovery_orchestration", seed=7, model_name="anthropic", model=model)

    session = SimulationSession(gt["initial_state"], gt["horizon"], gt["max_turns"])
    for action in result["parsed_answer"]:
        session.submit_action(action)
    assert result["score"] == SimulatedScorer().score_state(task, session.state)


# --- Family B: 8D / APQP / PPAP closed-form tasks (unit 3.1) -----------------------------

# seed=1, standard eight_d task's ground truth discipline is "D2" (see tests/test_eight_d.py).


def test_run_scores_eight_d_task_end_to_end():
    result = run("eight_d", seed=1, model_name="anthropic", model=FakeModel(answer="D2"))
    validate_result(result)
    assert result["task_id"] == "source.eight_d.000001"
    assert result["parsed_answer"] == "D2"
    assert result["parse_failure"] is False
    assert result["score"] == 1.0


def test_run_scores_zero_on_wrong_eight_d_answer():
    result = run("eight_d", seed=1, model_name="anthropic", model=FakeModel(answer="D7"))
    validate_result(result)
    assert result["score"] == 0.0


def test_run_flags_parse_failure_for_eight_d_when_answer_tag_missing():
    class NoTagModel(Model):
        name = "no-tag-model"

        def complete(self, prompt, tools=None, **kwargs):
            return ModelResponse(text="D2", latency_ms=1)

    result = run("eight_d", seed=1, model_name="anthropic", model=NoTagModel())
    validate_result(result)
    assert result["parse_failure"] is True
    assert result["parsed_answer"] is None
    assert result["score"] == 0.0


def test_run_flags_parse_failure_for_eight_d_when_answer_tag_is_empty():
    result = run("eight_d", seed=1, model_name="anthropic", model=FakeModel(answer=""))
    validate_result(result)
    assert result["parse_failure"] is True
    assert result["parsed_answer"] is None
    assert result["score"] == 0.0


# seed=1, standard apqp_phase task's ground truth phase is "Phase 2" (see tests/test_apqp_ppap.py).


def test_run_scores_apqp_phase_task_end_to_end():
    result = run("apqp_phase", seed=1, model_name="anthropic", model=FakeModel(answer="Phase 2"))
    validate_result(result)
    assert result["task_id"] == "source.apqp_phase.000001"
    assert result["parsed_answer"] == "Phase 2"
    assert result["parse_failure"] is False
    assert result["score"] == 1.0


def test_run_scores_zero_on_wrong_apqp_phase_answer():
    result = run("apqp_phase", seed=1, model_name="anthropic", model=FakeModel(answer="Phase 5"))
    validate_result(result)
    assert result["score"] == 0.0


# seed=1, standard ppap_elements task's required items are ["Control Plan",
# "Customer-Specific Requirements Records", "Engineering Change Documents"]
# (see tests/test_apqp_ppap.py).


def test_run_scores_ppap_elements_task_end_to_end():
    result = run(
        "ppap_elements",
        seed=1,
        model_name="anthropic",
        model=FakeModel(
            answer="Control Plan, Customer-Specific Requirements Records, Engineering Change Documents"
        ),
    )
    validate_result(result)
    assert result["task_id"] == "source.ppap_elements.000001"
    assert result["parse_failure"] is False
    assert sorted(result["parsed_answer"]) == [
        "Control Plan",
        "Customer-Specific Requirements Records",
        "Engineering Change Documents",
    ]
    assert result["score"] == 1.0


def test_run_scores_partial_ppap_elements_answer_as_fraction_correct():
    # Only 1 of the 3 required elements named -> score 1/3.
    result = run(
        "ppap_elements", seed=1, model_name="anthropic", model=FakeModel(answer="Control Plan")
    )
    validate_result(result)
    assert result["score"] == pytest.approx(1 / 3)


def test_run_scores_zero_for_ppap_elements_when_answer_tag_is_explicitly_empty():
    result = run("ppap_elements", seed=1, model_name="anthropic", model=FakeModel(answer=""))
    validate_result(result)
    assert result["parse_failure"] is False
    assert result["parsed_answer"] == []
    assert result["score"] == 0.0
