"""Tests for the L5 agentic-orchestration generators in generators/simulated_decision.py
(unit 2.5): wraps the same line-down-recovery / demand-spike-rebalance scenarios (units 2.2/2.3)
as the L4 counterparts (unit 2.4), but for turn-by-turn tool interaction instead of a one-shot
plan."""
from __future__ import annotations

import pytest

from generators.simulated_decision import (
    DemandSpikeRebalanceOrchestrationGenerator,
    LineDownRecoveryOrchestrationGenerator,
)
from harness.validate import validate_task

GENERATORS = [LineDownRecoveryOrchestrationGenerator, DemandSpikeRebalanceOrchestrationGenerator]
SWEEP_SEEDS = range(60)
DIFFICULTIES = ("standard", "hard")


@pytest.mark.parametrize("generator_cls", GENERATORS)
def test_generate_is_deterministic(generator_cls):
    gen = generator_cls()
    a = gen.generate(seed=42, difficulty="standard")
    b = gen.generate(seed=42, difficulty="standard")
    assert a == b


@pytest.mark.parametrize("generator_cls", GENERATORS)
def test_generate_distinct_seeds_differ(generator_cls):
    gen = generator_cls()
    a = gen.generate(seed=1, difficulty="standard")
    b = gen.generate(seed=2, difficulty="standard")
    assert a != b


@pytest.mark.parametrize("generator_cls", GENERATORS)
@pytest.mark.parametrize("difficulty", DIFFICULTIES)
@pytest.mark.parametrize("seed", [0, 1, 7, 42, 999])
def test_generated_task_validates_against_schema(generator_cls, difficulty, seed):
    task = generator_cls().generate(seed=seed, difficulty=difficulty)
    validate_task(task)  # raises on schema failure


def test_line_down_recovery_task_shape():
    task = LineDownRecoveryOrchestrationGenerator().generate(seed=1, difficulty="standard")
    assert task["id"] == "orchestration.line_down_recovery.000001"
    assert task["family"] == "simulated"
    assert task["domain"] == "production_scheduling"
    assert task["reasoning_tier"] == "L5"
    assert task["answer_format"] == "simulated"
    assert task["scorer"] == "simulated"
    assert task["generator"] == "line_down_recovery_orchestration"
    gt = task["ground_truth"]
    assert gt["scenario"] == "line_down_recovery"
    assert set(gt) == {
        "scenario", "initial_state", "horizon", "max_turns", "kpi_baseline", "kpi_reference",
    }


def test_demand_spike_rebalance_task_shape():
    task = DemandSpikeRebalanceOrchestrationGenerator().generate(seed=1, difficulty="standard")
    assert task["id"] == "orchestration.demand_spike_rebalance.000001"
    assert task["family"] == "simulated"
    assert task["domain"] == "supply_chain_sop"
    assert task["reasoning_tier"] == "L5"
    assert task["answer_format"] == "simulated"
    assert task["scorer"] == "simulated"
    assert task["generator"] == "demand_spike_rebalance_orchestration"
    gt = task["ground_truth"]
    assert gt["scenario"] == "demand_spike_rebalance"


@pytest.mark.parametrize("generator_cls", GENERATORS)
def test_orchestration_task_id_never_collides_with_its_l4_counterpart(generator_cls):
    # Both modes wrap the same scenario at the same seed; the "orchestration." vs "simulated."
    # id prefix is what keeps them from colliding, since family/scenario/seed are identical.
    task = generator_cls().generate(seed=1, difficulty="standard")
    assert task["id"].startswith("orchestration.")


@pytest.mark.parametrize("generator_cls", GENERATORS)
@pytest.mark.parametrize("difficulty", DIFFICULTIES)
@pytest.mark.parametrize("seed", SWEEP_SEEDS)
def test_kpi_reference_never_worse_than_kpi_baseline(generator_cls, difficulty, seed):
    task = generator_cls().generate(seed=seed, difficulty=difficulty)
    gt = task["ground_truth"]
    assert gt["kpi_reference"] <= gt["kpi_baseline"]


@pytest.mark.parametrize("generator_cls", GENERATORS)
@pytest.mark.parametrize("difficulty", DIFFICULTIES)
@pytest.mark.parametrize("seed", SWEEP_SEEDS)
def test_max_turns_covers_at_least_one_submit_action_per_horizon_step(generator_cls, difficulty, seed):
    # A perfect agent needs at minimum `horizon` submit_action calls; max_turns must always leave
    # room for that many, or the turn cap alone would make a perfect score unreachable.
    task = generator_cls().generate(seed=seed, difficulty=difficulty)
    gt = task["ground_truth"]
    assert gt["max_turns"] >= gt["horizon"]


@pytest.mark.parametrize("generator_cls", GENERATORS)
def test_context_matches_initial_state_and_max_turns(generator_cls):
    task = generator_cls().generate(seed=5, difficulty="hard")
    gt = task["ground_truth"]
    ctx = task["context"]
    assert ctx["num_machines"] == len(gt["initial_state"]["machines"])
    assert ctx["num_jobs"] == len(gt["initial_state"]["jobs"])
    assert ctx["horizon"] == gt["horizon"]
    assert ctx["max_turns"] == gt["max_turns"]


@pytest.mark.parametrize("generator_cls", GENERATORS)
def test_prompt_mentions_every_machine_and_job_and_the_tool_interaction(generator_cls):
    task = generator_cls().generate(seed=3, difficulty="standard")
    prompt = task["prompt"]
    for machine_id in task["ground_truth"]["initial_state"]["machines"]:
        assert machine_id in prompt
    for job_id in task["ground_truth"]["initial_state"]["jobs"]:
        assert job_id in prompt
    assert "get_state" in prompt
    assert "submit_action" in prompt
    assert str(task["ground_truth"]["max_turns"]) in prompt
