"""Checklist scorer tests against hand-verified cases: per-item fraction (score()) and the
all-or-nothing companion metric (all_or_nothing_score())."""
from scorers.checklist import ChecklistScorer
from harness.validate import validate_task

SCORER = ChecklistScorer()


def _task(required_items):
    return {"ground_truth": {"required_items": required_items}}


# --- fraction (score()) ---


def test_all_required_items_present_scores_one():
    assert SCORER.score(_task(["a", "b", "c"]), ["a", "b", "c"]) == 1.0


def test_two_of_three_present_scores_two_thirds():
    assert SCORER.score(_task(["a", "b", "c"]), ["a", "b"]) == 2 / 3


def test_one_of_four_present_scores_one_quarter():
    assert SCORER.score(_task(["a", "b", "c", "d"]), ["c"]) == 0.25


def test_none_present_scores_zero():
    assert SCORER.score(_task(["a", "b", "c"]), ["x", "y"]) == 0.0


def test_extra_non_required_items_are_not_penalized():
    # fraction is recall over required items -- extras don't reduce the score.
    assert SCORER.score(_task(["a", "b"]), ["a", "b", "extra"]) == 1.0


def test_case_and_whitespace_insensitive_matching():
    assert SCORER.score(_task(["Item A", "Item B"]), [" item a ", " ITEM B "]) == 1.0


def test_duplicate_answer_items_do_not_double_count():
    assert SCORER.score(_task(["a", "b"]), ["a", "a"]) == 0.5


def test_empty_required_items_scores_zero():
    assert SCORER.score(_task([]), ["a"]) == 0.0


def test_non_list_answer_scores_zero():
    assert SCORER.score(_task(["a", "b"]), "a") == 0.0


def test_answer_with_non_string_element_scores_zero():
    assert SCORER.score(_task(["a", "b"]), ["a", 2]) == 0.0


# --- all-or-nothing companion metric ---


def test_all_or_nothing_scores_one_when_complete():
    assert SCORER.all_or_nothing_score(_task(["a", "b", "c"]), ["a", "b", "c"]) == 1.0


def test_all_or_nothing_scores_one_with_extras_when_all_required_present():
    assert SCORER.all_or_nothing_score(_task(["a", "b"]), ["a", "b", "extra"]) == 1.0


def test_all_or_nothing_scores_zero_when_incomplete():
    assert SCORER.all_or_nothing_score(_task(["a", "b", "c"]), ["a", "b"]) == 0.0


def test_all_or_nothing_and_fraction_agree_on_boundary():
    # cross-check: all_or_nothing_score is 1.0 exactly when score() == 1.0, for the same inputs.
    for answer in [["a", "b"], ["a"], [], ["a", "b", "extra"]]:
        task = _task(["a", "b"])
        expected = 1.0 if SCORER.score(task, answer) == 1.0 else 0.0
        assert SCORER.all_or_nothing_score(task, answer) == expected


def test_generated_checklist_task_validates_against_schema():
    task = {
        "id": "source.control_plan.000001",
        "family": "source_grounded",
        "domain": "compliance_interpretation",
        "reasoning_tier": "L2",
        "answer_format": "checklist",
        "prompt": "Which required elements of a control plan are present in this excerpt?",
        "context": {},
        "ground_truth": {
            "required_items": [
                "process step",
                "characteristic",
                "specification/tolerance",
                "control method",
                "reaction plan",
            ]
        },
        "scorer": "checklist",
        "generator": "control_plan",
        "seed": 1,
        "difficulty": "standard",
        "source": "https://en.wikipedia.org/wiki/Control_plan",
        "source_url": "https://en.wikipedia.org/wiki/Control_plan",
        "created": "2026-08-02",
        "public": True,
    }
    validate_task(task)  # raises on failure
