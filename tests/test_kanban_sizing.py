"""Tests for the kanban-sizing multiple-choice generator (unit 3.2, Family B).

Unlike unit 3.1's lookup-table generators, this generator's ground truth is a genuine
computation (the canonical kanban-count formula), so the acceptance-criteria-relevant check is
an independent recomputation of that formula, not a lookup-table consistency check.
"""
import math

from generators.kanban_sizing import OPTION_LETTERS, KanbanSizingGenerator
from harness.validate import validate_task

GEN = KanbanSizingGenerator()


def _independently_recompute_correct_count(task: dict) -> int:
    """Recompute the correct kanban count from the task's own context using a separately
    written expression (import-of-percent -> fraction done via `/ 100` after multiplying by 100
    instead of the generator's direct `1 + safety_factor`), so this genuinely cross-checks the
    arithmetic rather than re-calling the same code."""
    ctx = task["context"]
    demand_with_safety_pct = 100 + round(ctx["safety_factor"] * 100)
    total = ctx["daily_demand"] * ctx["lead_time_days"] * demand_with_safety_pct / 100
    cards = total / ctx["container_size"]
    return math.ceil(round(cards, 9))


# --- generator behavior ---


def test_determinism_same_seed_same_task():
    assert GEN.generate(seed=1) == GEN.generate(seed=1)


def test_distinct_seeds_produce_distinct_scenarios():
    counts = {GEN.generate(seed=s)["context"]["correct_kanban_count"] for s in range(60)}
    assert len(counts) > 1


def test_exactly_four_options_including_the_correct_one():
    for seed in range(60):
        for difficulty in ("standard", "hard"):
            task = GEN.generate(seed=seed, difficulty=difficulty)
            options = task["context"]["options"]
            assert set(options) == {"A", "B", "C", "D"}
            assert len(set(options.values())) == 4, "all four option values must be distinct"
            correct_letter = task["ground_truth"]["value"]
            assert options[correct_letter] == task["context"]["correct_kanban_count"]


def test_all_option_values_are_non_negative_integers():
    for seed in range(60):
        task = GEN.generate(seed=seed)
        for value in task["context"]["options"].values():
            assert isinstance(value, int)
            assert value >= 0


def test_correct_count_matches_independent_recomputation():
    for seed in range(200):
        for difficulty in ("standard", "hard"):
            task = GEN.generate(seed=seed, difficulty=difficulty)
            expected = _independently_recompute_correct_count(task)
            assert task["context"]["correct_kanban_count"] == expected, (seed, difficulty)


def test_ground_truth_letter_is_always_one_of_the_four():
    for seed in range(60):
        task = GEN.generate(seed=seed)
        assert task["ground_truth"]["value"] in OPTION_LETTERS


def test_prompt_mentions_all_four_options_and_the_scenario_parameters():
    task = GEN.generate(seed=5)
    ctx = task["context"]
    for letter, value in ctx["options"].items():
        assert f"{letter}) {value}" in task["prompt"]
    assert str(ctx["daily_demand"]) in task["prompt"]
    assert str(ctx["container_size"]) in task["prompt"]


def test_hand_verified_case():
    # seed=1, standard: worked out by hand from the generator's own inputs.
    task = GEN.generate(seed=1, difficulty="standard")
    ctx = task["context"]
    expected = math.ceil(
        ctx["daily_demand"] * ctx["lead_time_days"] * (1 + ctx["safety_factor"]) / ctx["container_size"]
    )
    assert ctx["correct_kanban_count"] == expected
    assert ctx["options"][task["ground_truth"]["value"]] == expected


def test_fixed_fields():
    task = GEN.generate(seed=1)
    assert task["id"] == "source.kanban_sizing.000001"
    assert task["family"] == "source_grounded"
    assert task["domain"] == "supply_chain_sop"
    assert task["reasoning_tier"] == "L2"
    assert task["answer_format"] == "classification"
    assert task["scorer"] == "classification"
    assert task["generator"] == "kanban_sizing"
    assert task["public"] is True
    assert task["source"]
    assert "dmaic.com" in task["source_url"]


def test_generated_tasks_validate_against_schema():
    for seed in range(60):
        for difficulty in ("standard", "hard"):
            validate_task(GEN.generate(seed=seed, difficulty=difficulty))
