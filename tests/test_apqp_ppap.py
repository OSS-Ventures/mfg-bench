"""Tests for the APQP phase-classification and PPAP element-identification generators
(unit 3.1, Family B)."""
from generators.apqp_ppap import (
    APQP_ACTIVITIES,
    APQP_PHASES,
    PPAP_ELEMENTS,
    ApqpPhaseGenerator,
    PpapElementsGenerator,
)
from harness.validate import validate_task

APQP_GEN = ApqpPhaseGenerator()
PPAP_GEN = PpapElementsGenerator()


# --- APQP phase generator: lookup-table sanity ---


def test_apqp_activities_table_covers_every_phase_both_pools():
    assert set(APQP_ACTIVITIES) == set(APQP_PHASES)
    for phase, pools in APQP_ACTIVITIES.items():
        assert pools["standard"], phase
        assert pools["hard"], phase


def test_no_apqp_activity_text_is_duplicated_across_phases():
    seen: dict[str, str] = {}
    for phase, pools in APQP_ACTIVITIES.items():
        for pool in ("standard", "hard"):
            for activity in pools[pool]:
                assert activity not in seen, f"{activity!r} claimed by both {seen.get(activity)} and {phase}"
                seen[activity] = phase


# --- APQP phase generator: behavior ---


def test_apqp_determinism_same_seed_same_task():
    assert APQP_GEN.generate(seed=1) == APQP_GEN.generate(seed=1)


def test_apqp_distinct_seeds_can_produce_distinct_phases():
    phases = {APQP_GEN.generate(seed=s)["ground_truth"]["value"] for s in range(60)}
    assert len(phases) > 1


def test_apqp_ground_truth_phase_matches_the_activity_shown_in_context():
    for seed in range(60):
        for difficulty in ("standard", "hard"):
            task = APQP_GEN.generate(seed=seed, difficulty=difficulty)
            phase = task["ground_truth"]["value"]
            activity = task["context"]["activity"]
            assert activity in APQP_ACTIVITIES[phase][difficulty]


def test_apqp_prompt_lists_all_five_phases_and_the_activity():
    task = APQP_GEN.generate(seed=3)
    for phase in APQP_PHASES:
        assert phase in task["prompt"]
    assert task["context"]["activity"] in task["prompt"]


def test_apqp_fixed_fields():
    task = APQP_GEN.generate(seed=1)
    assert task["id"] == "source.apqp_phase.000001"
    assert task["family"] == "source_grounded"
    assert task["domain"] == "compliance_interpretation"
    assert task["reasoning_tier"] == "L2"
    assert task["answer_format"] == "classification"
    assert task["scorer"] == "classification"
    assert task["generator"] == "apqp_phase"
    assert task["public"] is True
    assert task["source"]
    assert "6sigma.us" in task["source_url"]


def test_apqp_generated_tasks_validate_against_schema():
    for seed in range(60):
        for difficulty in ("standard", "hard"):
            validate_task(APQP_GEN.generate(seed=seed, difficulty=difficulty))


# --- PPAP element generator: lookup-table sanity ---


def test_ppap_elements_table_has_eighteen_entries():
    assert len(PPAP_ELEMENTS) == 18


# --- PPAP element generator: behavior ---


def test_ppap_determinism_same_seed_same_task():
    assert PPAP_GEN.generate(seed=1) == PPAP_GEN.generate(seed=1)


def test_ppap_distinct_seeds_can_produce_distinct_included_sets():
    included_sets = {
        tuple(PPAP_GEN.generate(seed=s)["ground_truth"]["required_items"]) for s in range(60)
    }
    assert len(included_sets) > 1


def test_ppap_standard_difficulty_includes_three_elements():
    task = PPAP_GEN.generate(seed=1, difficulty="standard")
    assert len(task["ground_truth"]["required_items"]) == 3


def test_ppap_hard_difficulty_includes_five_elements():
    task = PPAP_GEN.generate(seed=1, difficulty="hard")
    assert len(task["ground_truth"]["required_items"]) == 5


def test_ppap_included_elements_are_a_subset_of_the_canonical_eighteen_with_no_duplicates():
    for seed in range(60):
        for difficulty in ("standard", "hard"):
            task = PPAP_GEN.generate(seed=seed, difficulty=difficulty)
            included = task["ground_truth"]["required_items"]
            assert len(included) == len(set(included))
            assert set(included) <= set(PPAP_ELEMENTS)


def test_ppap_context_all_elements_is_always_the_full_canonical_list():
    task = PPAP_GEN.generate(seed=1)
    assert set(task["context"]["all_elements"]) == set(PPAP_ELEMENTS)


def test_ppap_prompt_mentions_every_included_element_and_lists_all_eighteen_options():
    task = PPAP_GEN.generate(seed=5, difficulty="hard")
    for name in PPAP_ELEMENTS:
        assert name in task["prompt"]
    for name in task["ground_truth"]["required_items"]:
        assert PPAP_ELEMENTS[name] in task["prompt"]


def test_ppap_fixed_fields():
    task = PPAP_GEN.generate(seed=1)
    assert task["id"] == "source.ppap_elements.000001"
    assert task["family"] == "source_grounded"
    assert task["domain"] == "compliance_interpretation"
    assert task["reasoning_tier"] == "L2"
    assert task["answer_format"] == "checklist"
    assert task["scorer"] == "checklist"
    assert task["generator"] == "ppap_elements"
    assert task["public"] is True
    assert task["source"]
    assert task["source_url"] == "https://quality-one.com/ppap/"


def test_ppap_generated_tasks_validate_against_schema():
    for seed in range(60):
        for difficulty in ("standard", "hard"):
            validate_task(PPAP_GEN.generate(seed=seed, difficulty=difficulty))
