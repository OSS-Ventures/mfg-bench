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
