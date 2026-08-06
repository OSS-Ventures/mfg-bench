"""Tests for generators/simulated_decision.py (unit 2.4): the L4 single-decision generators
wrapping the line-down-recovery and demand-spike-rebalance scenarios (units 2.2/2.3)."""
from __future__ import annotations

import pytest

from generators.simulated_decision import (
    DemandSpikeRebalanceDecisionGenerator,
    LineDownRecoveryDecisionGenerator,
)
from harness.validate import validate_task

GENERATORS = [LineDownRecoveryDecisionGenerator, DemandSpikeRebalanceDecisionGenerator]
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
    task = LineDownRecoveryDecisionGenerator().generate(seed=1, difficulty="standard")
    assert task["id"] == "simulated.line_down_recovery.000001"
    assert task["family"] == "simulated"
    assert task["domain"] == "production_scheduling"
    assert task["reasoning_tier"] == "L4"
    assert task["answer_format"] == "simulated"
    assert task["scorer"] == "simulated"
    assert task["generator"] == "line_down_recovery_decision"
    gt = task["ground_truth"]
    assert gt["scenario"] == "line_down_recovery"
    assert set(gt) == {"scenario", "initial_state", "horizon", "kpi_baseline", "kpi_reference"}


def test_demand_spike_rebalance_task_shape():
    task = DemandSpikeRebalanceDecisionGenerator().generate(seed=1, difficulty="standard")
    assert task["id"] == "simulated.demand_spike_rebalance.000001"
    assert task["family"] == "simulated"
    assert task["domain"] == "supply_chain_sop"
    assert task["reasoning_tier"] == "L4"
    assert task["answer_format"] == "simulated"
    assert task["scorer"] == "simulated"
    assert task["generator"] == "demand_spike_rebalance_decision"
    gt = task["ground_truth"]
    assert gt["scenario"] == "demand_spike_rebalance"


@pytest.mark.parametrize("generator_cls", GENERATORS)
@pytest.mark.parametrize("difficulty", DIFFICULTIES)
@pytest.mark.parametrize("seed", SWEEP_SEEDS)
def test_kpi_reference_never_worse_than_kpi_baseline(generator_cls, difficulty, seed):
    # Both scenarios' KPIs are "lower is better" (weighted tardiness / total cost) and both
    # scenario modules' reference_episode() falls back to the baseline trajectory whenever the
    # heuristic would otherwise be worse (units 2.2/2.3's own safety net) -- so kpi_reference
    # must never exceed kpi_baseline, which is exactly what makes the scorer's normalization
    # well-defined (denominator <= 0, never positive-in-the-wrong-direction).
    task = generator_cls().generate(seed=seed, difficulty=difficulty)
    gt = task["ground_truth"]
    assert gt["kpi_reference"] <= gt["kpi_baseline"]


@pytest.mark.parametrize("generator_cls", GENERATORS)
def test_context_matches_initial_state(generator_cls):
    task = generator_cls().generate(seed=5, difficulty="hard")
    gt = task["ground_truth"]
    ctx = task["context"]
    assert ctx["num_machines"] == len(gt["initial_state"]["machines"])
    assert ctx["num_jobs"] == len(gt["initial_state"]["jobs"])
    assert ctx["horizon"] == gt["horizon"]


@pytest.mark.parametrize("generator_cls", GENERATORS)
def test_prompt_mentions_every_machine_and_job(generator_cls):
    task = generator_cls().generate(seed=3, difficulty="standard")
    prompt = task["prompt"]
    for machine_id in task["ground_truth"]["initial_state"]["machines"]:
        assert machine_id in prompt
    for job_id in task["ground_truth"]["initial_state"]["jobs"]:
        assert job_id in prompt
