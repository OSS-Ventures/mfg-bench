"""Tests for the Lean 8-wastes (TIMWOODS) classification generator (unit 3.2, Family B)."""
from generators.lean_waste import SCENARIOS, WASTES, LeanWasteGenerator
from harness.validate import validate_task

GEN = LeanWasteGenerator()


# --- internal lookup-table sanity ---


def test_scenarios_table_covers_every_waste_both_pools():
    assert set(SCENARIOS) == set(WASTES)
    for waste, pools in SCENARIOS.items():
        assert pools["standard"], waste
        assert pools["hard"], waste


def test_no_scenario_text_is_duplicated_across_wastes():
    seen: dict[str, str] = {}
    for waste, pools in SCENARIOS.items():
        for pool in ("standard", "hard"):
            for scenario in pools[pool]:
                assert scenario not in seen, f"{scenario!r} claimed by both {seen.get(scenario)} and {waste}"
                seen[scenario] = waste


def test_eight_canonical_wastes():
    assert len(WASTES) == 8


# --- generator behavior ---


def test_determinism_same_seed_same_task():
    assert GEN.generate(seed=1) == GEN.generate(seed=1)


def test_distinct_seeds_can_produce_distinct_wastes():
    wastes = {GEN.generate(seed=s)["ground_truth"]["value"] for s in range(60)}
    assert len(wastes) > 1


def test_hard_difficulty_draws_from_the_hard_pool():
    task = GEN.generate(seed=1, difficulty="hard")
    waste = task["ground_truth"]["value"]
    assert task["context"]["scenario"] in SCENARIOS[waste]["hard"]


def test_ground_truth_waste_matches_the_scenario_shown_in_context():
    for seed in range(60):
        for difficulty in ("standard", "hard"):
            task = GEN.generate(seed=seed, difficulty=difficulty)
            waste = task["ground_truth"]["value"]
            scenario = task["context"]["scenario"]
            assert scenario in SCENARIOS[waste][difficulty]


def test_ground_truth_is_always_a_valid_waste_name():
    for seed in range(60):
        task = GEN.generate(seed=seed)
        assert task["ground_truth"]["value"] in WASTES


def test_prompt_lists_all_eight_wastes_and_the_scenario():
    task = GEN.generate(seed=7)
    for name in WASTES:
        assert name in task["prompt"]
    assert task["context"]["scenario"] in task["prompt"]


def test_fixed_fields():
    task = GEN.generate(seed=1)
    assert task["id"] == "source.lean_waste.000001"
    assert task["family"] == "source_grounded"
    assert task["domain"] == "continuous_improvement"
    assert task["reasoning_tier"] == "L2"
    assert task["answer_format"] == "classification"
    assert task["scorer"] == "classification"
    assert task["generator"] == "lean_waste"
    assert task["public"] is True
    assert task["source"]
    assert "6sigma.us" in task["source_url"]


def test_generated_tasks_validate_against_schema():
    for seed in range(60):
        for difficulty in ("standard", "hard"):
            validate_task(GEN.generate(seed=seed, difficulty=difficulty))
