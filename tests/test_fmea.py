"""FMEA generator tests: hand-verified RPN/prioritization cases, an independent-recomputation
sweep, determinism, and schema validity."""
import pytest

from generators.fmea import ACTION_THRESHOLD, FMEAGenerator
from harness.validate import validate_task

# Each case: (seed, difficulty) -> the ground-truth numbers, in order:
#   RPN of each failure mode (in listed order), top-priority failure mode number,
#   count of failure modes with RPN >= ACTION_THRESHOLD (100).
# Hand-verified from the generator's own context (severity/occurrence/detection per failure
# mode) via: RPN = severity * occurrence * detection; top priority = argmax RPN (first on
# ties); count = how many RPNs are >= 100.
HAND_VERIFIED_CASES = [
    # seed=1, standard: (S,O,D) = (3,10,2), (5,2,8), (8,8,7), (4,2,8) ->
    # RPNs 60, 80, 448, 64 -> max is failure mode 3 (448); only 448 >= 100.
    (1, "standard", [60.0, 80.0, 448.0, 64.0, 3.0, 1.0]),
    # seed=2, standard: (S,O,D) = (1,2,2), (6,3,5), (5,10,4), (10,1,10) ->
    # RPNs 4, 90, 200, 100 -> max is failure mode 3 (200); 200 and 100 are >= 100.
    (2, "standard", [4.0, 90.0, 200.0, 100.0, 3.0, 2.0]),
    # seed=999, standard: (S,O,D) = (2,10,10), (9,8,8), (3,6,2), (4,3,5) ->
    # RPNs 200, 576, 36, 60 -> max is failure mode 2 (576); 200 and 576 are >= 100.
    (999, "standard", [200.0, 576.0, 36.0, 60.0, 2.0, 2.0]),
    # seed=123, hard: (S,O,D) = (1,5,2), (7,5,2), (1,7,9), (9,6,6), (1,3,3) ->
    # RPNs 10, 70, 63, 324, 9 -> max is failure mode 4 (324); only 324 >= 100.
    (123, "hard", [10.0, 70.0, 63.0, 324.0, 9.0, 4.0, 1.0]),
    # seed=7, hard: (S,O,D) = (6,3,7), (1,2,9), (2,6,10), (1,9,4), (1,2,7) ->
    # RPNs 126, 18, 120, 36, 14 -> max is failure mode 1 (126); 126 and 120 are >= 100.
    (7, "hard", [126.0, 18.0, 120.0, 36.0, 14.0, 1.0, 2.0]),
]


@pytest.mark.parametrize("seed,difficulty,expected_parts", HAND_VERIFIED_CASES)
def test_ground_truth_matches_hand_computed_metrics(seed, difficulty, expected_parts):
    task = FMEAGenerator().generate(seed=seed, difficulty=difficulty)
    parts = [p["value"] for p in task["ground_truth"]["parts"]]
    assert parts == expected_parts


def _recompute_metrics(failure_modes, threshold):
    """Independent reimplementation: accumulates RPNs via a running-max loop (rather than the
    generator's `max(range(...), key=...)`) and counts the threshold with a manual loop, so
    this genuinely cross-checks the generator's own `compute_fmea_metrics` rather than just
    calling it again."""
    rpns = []
    for fm in failure_modes:
        rpn = 1
        for rating in (fm["severity"], fm["occurrence"], fm["detection"]):
            rpn = rpn * rating
        rpns.append(rpn)

    best_index = 0
    best_rpn = rpns[0]
    for i, rpn in enumerate(rpns):
        if rpn > best_rpn:
            best_rpn = rpn
            best_index = i

    count = 0
    for rpn in rpns:
        if rpn >= threshold:
            count += 1

    return [float(r) for r in rpns] + [float(best_index + 1), float(count)]


@pytest.mark.parametrize("seed", range(30))
@pytest.mark.parametrize("difficulty", ["standard", "hard"])
def test_ground_truth_matches_independent_recomputation(seed, difficulty):
    task = FMEAGenerator().generate(seed=seed, difficulty=difficulty)
    ctx = task["context"]
    recomputed = _recompute_metrics(ctx["failure_modes"], ctx["action_threshold"])

    parts = [p["value"] for p in task["ground_truth"]["parts"]]
    assert parts == recomputed


def test_generation_is_deterministic():
    a = FMEAGenerator().generate(seed=555, difficulty="standard")
    b = FMEAGenerator().generate(seed=555, difficulty="standard")
    assert a["context"] == b["context"]
    assert a["ground_truth"] == b["ground_truth"]
    assert a["id"] == b["id"]


def test_different_seeds_yield_different_instances():
    a = FMEAGenerator().generate(seed=1, difficulty="standard")
    b = FMEAGenerator().generate(seed=2, difficulty="standard")
    assert a["context"] != b["context"]


def test_generated_task_validates_against_schema():
    task = FMEAGenerator().generate(seed=123, difficulty="standard")
    validate_task(task)  # raises on failure


def test_failure_mode_count_per_difficulty():
    for seed in range(20):
        standard = FMEAGenerator().generate(seed=seed, difficulty="standard")
        hard = FMEAGenerator().generate(seed=seed, difficulty="hard")
        assert len(standard["context"]["failure_modes"]) == 4
        assert len(hard["context"]["failure_modes"]) == 5


def test_rpns_are_within_one_to_a_thousand():
    for seed in range(30):
        for difficulty in ["standard", "hard"]:
            task = FMEAGenerator().generate(seed=seed, difficulty=difficulty)
            num_fm = len(task["context"]["failure_modes"])
            rpns = [p["value"] for p in task["ground_truth"]["parts"][:num_fm]]
            assert all(1 <= rpn <= 1000 for rpn in rpns)


def test_top_priority_failure_mode_is_within_bounds_and_has_the_max_rpn():
    for seed in range(30):
        for difficulty in ["standard", "hard"]:
            task = FMEAGenerator().generate(seed=seed, difficulty=difficulty)
            num_fm = len(task["context"]["failure_modes"])
            parts = [p["value"] for p in task["ground_truth"]["parts"]]
            rpns, top_priority = parts[:num_fm], parts[num_fm]
            assert 1 <= top_priority <= num_fm
            assert rpns[int(top_priority) - 1] == max(rpns)


def test_count_above_threshold_is_consistent_with_rpns():
    for seed in range(30):
        for difficulty in ["standard", "hard"]:
            task = FMEAGenerator().generate(seed=seed, difficulty=difficulty)
            num_fm = len(task["context"]["failure_modes"])
            parts = [p["value"] for p in task["ground_truth"]["parts"]]
            rpns, count_above = parts[:num_fm], parts[num_fm + 1]
            assert count_above == sum(1 for rpn in rpns if rpn >= ACTION_THRESHOLD)
