"""Classification scorer tests against hand-verified cases: single-label exact match and
multi-label set match."""
from scorers.classification import ClassificationScorer
from harness.validate import validate_task

SCORER = ClassificationScorer()


def _task(value):
    return {"ground_truth": {"value": value}}


# --- single-label exact match ---


def test_exact_match_scores_one():
    assert SCORER.score(_task("root_cause_a"), "root_cause_a") == 1.0


def test_mismatched_label_scores_zero():
    assert SCORER.score(_task("root_cause_a"), "root_cause_b") == 0.0


def test_case_insensitive_match_scores_one():
    assert SCORER.score(_task("Root Cause A"), "root cause a") == 1.0


def test_surrounding_whitespace_is_stripped():
    assert SCORER.score(_task("root_cause_a"), "  root_cause_a  ") == 1.0


def test_non_string_answer_scores_zero():
    assert SCORER.score(_task("root_cause_a"), 1) == 0.0


def test_none_answer_scores_zero():
    assert SCORER.score(_task("root_cause_a"), None) == 0.0


def test_list_answer_against_single_label_truth_scores_zero():
    # truth is single-label; a list answer is the wrong shape, not a set-match attempt.
    assert SCORER.score(_task("root_cause_a"), ["root_cause_a"]) == 0.0


# --- multi-label set match ---


def test_matching_set_in_same_order_scores_one():
    assert SCORER.score(_task(["waste_a", "waste_b"]), ["waste_a", "waste_b"]) == 1.0


def test_matching_set_in_different_order_scores_one():
    # set match: order never matters.
    assert SCORER.score(_task(["waste_a", "waste_b", "waste_c"]), ["waste_c", "waste_a", "waste_b"]) == 1.0


def test_set_with_extra_item_scores_zero():
    assert SCORER.score(_task(["waste_a", "waste_b"]), ["waste_a", "waste_b", "waste_c"]) == 0.0


def test_set_missing_item_scores_zero():
    assert SCORER.score(_task(["waste_a", "waste_b"]), ["waste_a"]) == 0.0


def test_set_duplicates_in_answer_collapse_and_still_match():
    assert SCORER.score(_task(["waste_a", "waste_b"]), ["waste_a", "waste_a", "waste_b"]) == 1.0


def test_set_case_and_whitespace_insensitive():
    assert SCORER.score(_task(["Waste A", "Waste B"]), [" waste b ", " WASTE A "]) == 1.0


def test_non_list_answer_against_set_truth_scores_zero():
    assert SCORER.score(_task(["waste_a", "waste_b"]), "waste_a") == 0.0


def test_set_answer_with_non_string_element_scores_zero():
    assert SCORER.score(_task(["waste_a", "waste_b"]), ["waste_a", 2]) == 0.0


def test_generated_single_label_task_validates_against_schema():
    task = {
        "id": "source.eightd.000001",
        "family": "source_grounded",
        "domain": "quality_problem_solving",
        "reasoning_tier": "L1",
        "answer_format": "classification",
        "prompt": "Which 8D discipline addresses containment?",
        "context": {},
        "ground_truth": {"value": "D3"},
        "scorer": "classification",
        "generator": "eightd",
        "seed": 1,
        "difficulty": "standard",
        "source": "https://asq.org/quality-resources/eight-disciplines-8d",
        "source_url": "https://asq.org/quality-resources/eight-disciplines-8d",
        "created": "2026-08-02",
        "public": True,
    }
    validate_task(task)  # raises on failure


def test_generated_set_match_task_validates_against_schema():
    task = {
        "id": "source.wastes.000001",
        "family": "source_grounded",
        "domain": "continuous_improvement",
        "reasoning_tier": "L1",
        "answer_format": "classification",
        "prompt": "Which of the 7 wastes are present in this scenario?",
        "context": {},
        "ground_truth": {"value": ["overproduction", "waiting"]},
        "scorer": "classification",
        "generator": "wastes",
        "seed": 1,
        "difficulty": "standard",
        "source": "https://en.wikipedia.org/wiki/Muda_(Japanese_term)",
        "source_url": "https://en.wikipedia.org/wiki/Muda_(Japanese_term)",
        "created": "2026-08-02",
        "public": True,
    }
    validate_task(task)  # raises on failure
