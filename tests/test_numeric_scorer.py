"""Numeric scorer tests against hand-verified cases."""
from scorers.numeric import NumericScorer

SCORER = NumericScorer()


def _task(value, tolerance=0.001, tolerance_type="absolute"):
    return {
        "ground_truth": {
            "value": value,
            "tolerance": tolerance,
            "tolerance_type": tolerance_type,
        }
    }


def test_exact_match_scores_one():
    assert SCORER.score(_task(0.7594), 0.7594) == 1.0


def test_within_absolute_tolerance_scores_one():
    assert SCORER.score(_task(0.7594, tolerance=0.001), 0.7598) == 1.0


def test_outside_absolute_tolerance_scores_zero():
    assert SCORER.score(_task(0.7594, tolerance=0.001), 0.7610) == 0.0


def test_within_relative_tolerance_scores_one():
    # truth=1000, 1% relative tolerance -> allowed = 10, answer off by 5 passes.
    assert SCORER.score(_task(1000, tolerance=0.01, tolerance_type="relative"), 1005) == 1.0


def test_outside_relative_tolerance_scores_zero():
    # truth=1000, 1% relative tolerance -> allowed = 10, answer off by 50 fails.
    assert SCORER.score(_task(1000, tolerance=0.01, tolerance_type="relative"), 1050) == 0.0


def test_non_numeric_answer_scores_zero():
    assert SCORER.score(_task(0.7594), "not a number") == 0.0


def test_none_answer_scores_zero():
    assert SCORER.score(_task(0.7594), None) == 0.0


def test_string_numeric_answer_is_coerced():
    assert SCORER.score(_task(0.7594), "0.7594") == 1.0


def test_bool_answer_scores_zero():
    # bool is a subclass of int in Python; float(True) == 1.0 would otherwise silently "match".
    assert SCORER.score(_task(1.0, tolerance=0.5), True) == 0.0


def _multi_task(parts):
    return {"ground_truth": {"parts": parts}}


def test_multi_part_all_correct_scores_one():
    parts = [
        {"value": 10.0, "tolerance": 0.01, "tolerance_type": "absolute"},
        {"value": 200.0, "tolerance": 0.02, "tolerance_type": "relative"},
    ]
    assert SCORER.score(_multi_task(parts), [10.005, 204.0]) == 1.0


def test_multi_part_partial_correct_averages():
    # part 1 correct (within 0.01), part 2 wrong (off by 50 with tolerance 4) -> avg 0.5.
    parts = [
        {"value": 10.0, "tolerance": 0.01, "tolerance_type": "absolute"},
        {"value": 200.0, "tolerance": 0.02, "tolerance_type": "relative"},
    ]
    assert SCORER.score(_multi_task(parts), [10.005, 250.0]) == 0.5


def test_multi_part_none_correct_scores_zero():
    parts = [
        {"value": 10.0, "tolerance": 0.01, "tolerance_type": "absolute"},
        {"value": 200.0, "tolerance": 0.02, "tolerance_type": "relative"},
    ]
    assert SCORER.score(_multi_task(parts), [99.0, 1.0]) == 0.0


def test_multi_part_wrong_answer_count_scores_zero():
    parts = [
        {"value": 10.0, "tolerance": 0.01, "tolerance_type": "absolute"},
        {"value": 200.0, "tolerance": 0.02, "tolerance_type": "relative"},
    ]
    assert SCORER.score(_multi_task(parts), [10.0]) == 0.0


def test_multi_part_non_list_answer_scores_zero():
    parts = [{"value": 10.0, "tolerance": 0.01, "tolerance_type": "absolute"}]
    assert SCORER.score(_multi_task(parts), 10.0) == 0.0


def test_multi_part_non_numeric_element_scores_partial():
    parts = [
        {"value": 10.0, "tolerance": 0.01, "tolerance_type": "absolute"},
        {"value": 200.0, "tolerance": 0.02, "tolerance_type": "relative"},
    ]
    assert SCORER.score(_multi_task(parts), [10.0, "not a number"]) == 0.5
