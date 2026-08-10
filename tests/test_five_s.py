"""Tests for the 5S phase-classification generator (unit 3.2, Family B)."""
from generators.five_s import ACTIVITIES, PHASES, FiveSGenerator
from harness.validate import validate_task

GEN = FiveSGenerator()


# --- internal lookup-table sanity ---


def test_activities_table_covers_every_phase_both_pools():
    assert set(ACTIVITIES) == set(PHASES)
    for phase, pools in ACTIVITIES.items():
        assert pools["standard"], phase
        assert pools["hard"], phase


def test_no_activity_text_is_duplicated_across_phases():
    seen: dict[str, str] = {}
    for phase, pools in ACTIVITIES.items():
        for pool in ("standard", "hard"):
            for activity in pools[pool]:
                assert activity not in seen, f"{activity!r} claimed by both {seen.get(activity)} and {phase}"
                seen[activity] = phase


def test_five_canonical_phases_in_order():
    assert list(PHASES) == ["Sort", "Set In Order", "Shine", "Standardize", "Sustain"]


# --- generator behavior ---


def test_determinism_same_seed_same_task():
    assert GEN.generate(seed=1) == GEN.generate(seed=1)


def test_distinct_seeds_can_produce_distinct_phases():
    phases = {GEN.generate(seed=s)["ground_truth"]["value"] for s in range(60)}
    assert len(phases) > 1


def test_hard_difficulty_draws_from_the_hard_pool():
    task = GEN.generate(seed=1, difficulty="hard")
    phase = task["ground_truth"]["value"]
    assert task["context"]["activity"] in ACTIVITIES[phase]["hard"]


def test_ground_truth_phase_matches_the_activity_shown_in_context():
    for seed in range(60):
        for difficulty in ("standard", "hard"):
            task = GEN.generate(seed=seed, difficulty=difficulty)
            phase = task["ground_truth"]["value"]
            activity = task["context"]["activity"]
            assert activity in ACTIVITIES[phase][difficulty]


def test_prompt_lists_all_five_phases_and_the_activity():
    task = GEN.generate(seed=3)
    for phase in PHASES:
        assert phase in task["prompt"]
    assert task["context"]["activity"] in task["prompt"]


def test_fixed_fields():
    task = GEN.generate(seed=1)
    assert task["id"] == "source.five_s.000001"
    assert task["family"] == "source_grounded"
    assert task["domain"] == "continuous_improvement"
    assert task["reasoning_tier"] == "L2"
    assert task["answer_format"] == "classification"
    assert task["scorer"] == "classification"
    assert task["generator"] == "five_s"
    assert task["public"] is True
    assert task["source"]
    assert task["source_url"] == "https://asq.org/quality-resources/five-s-tutorial"


def test_generated_tasks_validate_against_schema():
    for seed in range(60):
        for difficulty in ("standard", "hard"):
            validate_task(GEN.generate(seed=seed, difficulty=difficulty))
