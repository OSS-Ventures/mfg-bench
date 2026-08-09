"""Tests for the 8D discipline-classification generator (unit 3.1, Family B)."""
from generators.eight_d import ACTIVITIES, DISCIPLINES, EightDGenerator
from harness.validate import validate_task

GEN = EightDGenerator()

# --- internal lookup-table sanity (the "hand-verified ground truth" for a canonical-structure
# generator: since there is no formula to independently re-derive, the check is that the fixed
# lookup table itself is unambiguous and complete) ---


def test_activities_table_covers_every_discipline_both_pools():
    assert set(ACTIVITIES) == set(DISCIPLINES)
    for discipline, pools in ACTIVITIES.items():
        assert pools["standard"], discipline
        assert pools["hard"], discipline


def test_no_activity_text_is_duplicated_across_disciplines():
    seen: dict[str, str] = {}
    for discipline, pools in ACTIVITIES.items():
        for pool in ("standard", "hard"):
            for activity in pools[pool]:
                assert activity not in seen, f"{activity!r} claimed by both {seen.get(activity)} and {discipline}"
                seen[activity] = discipline


# --- generator behavior ---


def test_determinism_same_seed_same_task():
    assert GEN.generate(seed=1) == GEN.generate(seed=1)


def test_distinct_seeds_can_produce_distinct_disciplines():
    disciplines = {GEN.generate(seed=s)["ground_truth"]["value"] for s in range(60)}
    assert len(disciplines) > 1


def test_hard_difficulty_draws_from_the_hard_pool():
    task = GEN.generate(seed=1, difficulty="hard")
    discipline = task["ground_truth"]["value"]
    assert task["context"]["activity"] in ACTIVITIES[discipline]["hard"]


def test_ground_truth_discipline_matches_the_activity_shown_in_context():
    for seed in range(60):
        for difficulty in ("standard", "hard"):
            task = GEN.generate(seed=seed, difficulty=difficulty)
            discipline = task["ground_truth"]["value"]
            activity = task["context"]["activity"]
            assert activity in ACTIVITIES[discipline][difficulty]


def test_ground_truth_is_always_a_valid_discipline_code():
    for seed in range(60):
        task = GEN.generate(seed=seed)
        assert task["ground_truth"]["value"] in DISCIPLINES


def test_prompt_lists_all_nine_disciplines_and_the_activity():
    task = GEN.generate(seed=7)
    for code in DISCIPLINES:
        assert code in task["prompt"]
    assert task["context"]["activity"] in task["prompt"]


def test_fixed_fields():
    task = GEN.generate(seed=1)
    assert task["id"] == "source.eight_d.000001"
    assert task["family"] == "source_grounded"
    assert task["domain"] == "quality_problem_solving"
    assert task["reasoning_tier"] == "L2"
    assert task["answer_format"] == "classification"
    assert task["scorer"] == "classification"
    assert task["generator"] == "eight_d"
    assert task["public"] is True
    assert task["source"]
    assert task["source_url"] == "https://asq.org/quality-resources/eight-disciplines-8d"


def test_generated_tasks_validate_against_schema():
    for seed in range(60):
        for difficulty in ("standard", "hard"):
            validate_task(GEN.generate(seed=seed, difficulty=difficulty))
