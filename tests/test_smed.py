"""Tests for the SMED internal/external setup classification generator (unit 3.2, Family B)."""
from generators.smed import CATEGORIES, STEPS, SmedSetupClassificationGenerator
from harness.validate import validate_task

GEN = SmedSetupClassificationGenerator()


# --- internal lookup-table sanity ---


def test_steps_table_covers_both_categories_both_pools():
    assert set(STEPS) == set(CATEGORIES)
    for category, pools in STEPS.items():
        assert pools["standard"], category
        assert pools["hard"], category


def test_no_step_text_is_duplicated_across_categories():
    seen: dict[str, str] = {}
    for category, pools in STEPS.items():
        for pool in ("standard", "hard"):
            for step in pools[pool]:
                assert step not in seen, f"{step!r} claimed by both {seen.get(step)} and {category}"
                seen[step] = category


def test_two_canonical_categories():
    assert set(CATEGORIES) == {"Internal", "External"}


# --- generator behavior ---


def test_determinism_same_seed_same_task():
    assert GEN.generate(seed=1) == GEN.generate(seed=1)


def test_distinct_seeds_can_produce_both_categories():
    categories = {GEN.generate(seed=s)["ground_truth"]["value"] for s in range(60)}
    assert categories == {"Internal", "External"}


def test_hard_difficulty_draws_from_the_hard_pool():
    task = GEN.generate(seed=1, difficulty="hard")
    category = task["ground_truth"]["value"]
    assert task["context"]["step"] in STEPS[category]["hard"]


def test_ground_truth_category_matches_the_step_shown_in_context():
    for seed in range(60):
        for difficulty in ("standard", "hard"):
            task = GEN.generate(seed=seed, difficulty=difficulty)
            category = task["ground_truth"]["value"]
            step = task["context"]["step"]
            assert step in STEPS[category][difficulty]


def test_prompt_lists_both_categories_and_the_step():
    task = GEN.generate(seed=2)
    for name in CATEGORIES:
        assert name in task["prompt"]
    assert task["context"]["step"] in task["prompt"]


def test_fixed_fields():
    task = GEN.generate(seed=1)
    assert task["id"] == "source.smed.000001"
    assert task["family"] == "source_grounded"
    assert task["domain"] == "methods_industrialization"
    assert task["reasoning_tier"] == "L2"
    assert task["answer_format"] == "classification"
    assert task["scorer"] == "classification"
    assert task["generator"] == "smed"
    assert task["public"] is True
    assert task["source"]
    assert task["source_url"] == "https://www.leanproduction.com/smed/"


def test_generated_tasks_validate_against_schema():
    for seed in range(60):
        for difficulty in ("standard", "hard"):
            validate_task(GEN.generate(seed=seed, difficulty=difficulty))
