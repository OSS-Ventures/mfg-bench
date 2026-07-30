"""Scheduling generator tests: hand-verified permutation-search cases, an independent
recomputation sweep, determinism, and schema validity.

The ground truth is defined as "the minimum total (weighted) tardiness across every possible
processing sequence" -- there is no closed-form shortcut, so a human can only hand-verify it by
enumerating all n! sequences directly. That is fully tractable for n=3 (6 orderings), so the
hand-verified cases below use small, hand-constructed 3-job instances (independent of the
seeded generator) and enumerate every ordering explicitly in comments; each order's completion
times, tardiness, and (where applicable) weighted tardiness are worked by hand and cross-checked
against `SchedulingGenerator._total_tardiness`, the exact function `generate()` uses internally.

The generator's actual seeded output (5/6 jobs) is then checked with an independent
recomputation sweep: a *separately written* brute-force implementation (recursive DFS rather
than the generator's `itertools.permutations` + list-comprehension) that recomputes the optimum
straight from `task["context"]` for many (seed, difficulty) combinations.
"""
import pytest

from generators.scheduling import SchedulingGenerator
from harness.validate import validate_task


def test_total_tardiness_matches_hand_enumeration_unweighted_tie():
    # Jobs (p, d): A=(3,2), B=(2,3), C=(4,4), all weight 1.
    # All 6 orderings, hand-computed completion times / tardiness:
    #   A,B,C: compA=3(t1) compB=5(t2) compC=9(t5) -> total 8
    #   A,C,B: compA=3(t1) compC=7(t3) compB=9(t6) -> total 10
    #   B,A,C: compB=2(t0) compA=5(t3) compC=9(t5) -> total 8
    #   B,C,A: compB=2(t0) compC=6(t2) compA=9(t7) -> total 9
    #   C,A,B: compC=4(t0) compA=7(t5) compB=9(t6) -> total 11
    #   C,B,A: compC=4(t0) compB=6(t3) compA=9(t7) -> total 10
    # Minimum across all 6 orderings = 8 (achieved by A,B,C and B,A,C).
    jobs = [(3, 2, 1), (2, 3, 1), (4, 4, 1)]
    assert SchedulingGenerator._total_tardiness(jobs, (0, 1, 2)) == 8
    assert SchedulingGenerator._total_tardiness(jobs, (0, 2, 1)) == 10
    assert SchedulingGenerator._total_tardiness(jobs, (1, 0, 2)) == 8
    assert SchedulingGenerator._total_tardiness(jobs, (1, 2, 0)) == 9
    assert SchedulingGenerator._total_tardiness(jobs, (2, 0, 1)) == 11
    assert SchedulingGenerator._total_tardiness(jobs, (2, 1, 0)) == 10
    from itertools import permutations

    assert min(SchedulingGenerator._total_tardiness(jobs, o) for o in permutations(range(3))) == 8


def test_total_tardiness_zero_when_loose_due_dates():
    # Jobs (p, d): a=(5,5), b=(3,10), c=(2,10). SPT-in-EDD order a,b,c never runs tardy:
    # compA=5(t0) compB=8(t0, due 10) compC=10(t0, due 10) -> total 0.
    jobs = [(5, 5, 1), (3, 10, 1), (2, 10, 1)]
    assert SchedulingGenerator._total_tardiness(jobs, (0, 1, 2)) == 0
    from itertools import permutations

    assert min(SchedulingGenerator._total_tardiness(jobs, o) for o in permutations(range(3))) == 0


def test_total_weighted_tardiness_matches_hand_enumeration():
    # Jobs (p, d, w): A=(4,4,1), B=(3,4,2), C=(5,4,3), all due date 4 (tight).
    # All 6 orderings, hand-computed weighted tardiness:
    #   A,B,C: compA=4(t0*1=0) compB=7(t3*2=6) compC=12(t8*3=24) -> total 30
    #   A,C,B: compA=4(0) compC=9(t5*3=15) compB=12(t8*2=16) -> total 31
    #   B,A,C: compB=3(t0*2=0) compA=7(t3*1=3) compC=12(t8*3=24) -> total 27
    #   B,C,A: compB=3(0) compC=8(t4*3=12) compA=12(t8*1=8) -> total 20
    #   C,A,B: compC=5(t1*3=3) compA=9(t5*1=5) compB=12(t8*2=16) -> total 24
    #   C,B,A: compC=5(3) compB=8(t4*2=8) compA=12(t8*1=8) -> total 19
    # Minimum = 19 (order C,B,A).
    jobs = [(4, 4, 1), (3, 4, 2), (5, 4, 3)]
    assert SchedulingGenerator._total_tardiness(jobs, (0, 1, 2)) == 30
    assert SchedulingGenerator._total_tardiness(jobs, (0, 2, 1)) == 31
    assert SchedulingGenerator._total_tardiness(jobs, (1, 0, 2)) == 27
    assert SchedulingGenerator._total_tardiness(jobs, (1, 2, 0)) == 20
    assert SchedulingGenerator._total_tardiness(jobs, (2, 0, 1)) == 24
    assert SchedulingGenerator._total_tardiness(jobs, (2, 1, 0)) == 19
    from itertools import permutations

    assert min(SchedulingGenerator._total_tardiness(jobs, o) for o in permutations(range(3))) == 19


def test_total_tardiness_matches_hand_enumeration_unweighted_second_tie():
    # Jobs (p, d): A=(6,5), B=(2,5), C=(3,5), all weight 1.
    #   A,B,C: compA=6(t1) compB=8(t3) compC=11(t6) -> total 10
    #   A,C,B: compA=6(1) compC=9(4) compB=11(6) -> total 11
    #   B,A,C: compB=2(0) compA=8(3) compC=11(6) -> total 9
    #   B,C,A: compB=2(0) compC=5(0) compA=11(6) -> total 6
    #   C,A,B: compC=3(0) compA=9(4) compB=11(6) -> total 10
    #   C,B,A: compC=3(0) compB=5(0) compA=11(6) -> total 6
    # Minimum = 6 (achieved by B,C,A and C,B,A).
    jobs = [(6, 5, 1), (2, 5, 1), (3, 5, 1)]
    assert SchedulingGenerator._total_tardiness(jobs, (0, 1, 2)) == 10
    assert SchedulingGenerator._total_tardiness(jobs, (0, 2, 1)) == 11
    assert SchedulingGenerator._total_tardiness(jobs, (1, 0, 2)) == 9
    assert SchedulingGenerator._total_tardiness(jobs, (1, 2, 0)) == 6
    assert SchedulingGenerator._total_tardiness(jobs, (2, 0, 1)) == 10
    assert SchedulingGenerator._total_tardiness(jobs, (2, 1, 0)) == 6
    from itertools import permutations

    assert min(SchedulingGenerator._total_tardiness(jobs, o) for o in permutations(range(3))) == 6


def test_total_weighted_tardiness_matches_hand_enumeration_second_case():
    # Jobs (p, d, w): A=(3,3,3), B=(5,3,1), C=(2,10,2).
    #   A,B,C: compA=3(t0*3=0) compB=8(t5*1=5) compC=10(t0*2=0) -> total 5
    #   A,C,B: compA=3(0) compC=5(t0*2=0) compB=10(t7*1=7) -> total 7
    #   B,A,C: compB=5(t2*1=2) compA=8(t5*3=15) compC=10(t0*2=0) -> total 17
    #   B,C,A: compB=5(2) compC=7(t0*2=0) compA=10(t7*3=21) -> total 23
    #   C,A,B: compC=2(t0*2=0) compA=5(t2*3=6) compB=10(t7*1=7) -> total 13
    #   C,B,A: compC=2(0) compB=7(t4*1=4) compA=10(t7*3=21) -> total 25
    # Minimum = 5 (order A,B,C).
    jobs = [(3, 3, 3), (5, 3, 1), (2, 10, 2)]
    assert SchedulingGenerator._total_tardiness(jobs, (0, 1, 2)) == 5
    assert SchedulingGenerator._total_tardiness(jobs, (0, 2, 1)) == 7
    assert SchedulingGenerator._total_tardiness(jobs, (1, 0, 2)) == 17
    assert SchedulingGenerator._total_tardiness(jobs, (1, 2, 0)) == 23
    assert SchedulingGenerator._total_tardiness(jobs, (2, 0, 1)) == 13
    assert SchedulingGenerator._total_tardiness(jobs, (2, 1, 0)) == 25
    from itertools import permutations

    assert min(SchedulingGenerator._total_tardiness(jobs, o) for o in permutations(range(3))) == 5


def _recompute_optimal_tardiness(processing_times, due_dates, weights):
    """Independently-written exhaustive search: recursive DFS building sequences one job at a
    time, tracking running completion time -- a different code path from the generator's
    itertools.permutations + flat list-comprehension, so this genuinely cross-checks it."""
    n = len(processing_times)
    best = [None]

    def dfs(remaining, completion, acc_tardiness):
        if best[0] is not None and acc_tardiness >= best[0]:
            return
        if not remaining:
            if best[0] is None or acc_tardiness < best[0]:
                best[0] = acc_tardiness
            return
        for idx in remaining:
            new_completion = completion + processing_times[idx]
            tardy = max(0, new_completion - due_dates[idx]) * weights[idx]
            dfs(remaining - {idx}, new_completion, acc_tardiness + tardy)

    dfs(set(range(n)), 0, 0)
    return best[0]


@pytest.mark.parametrize("seed", range(30))
@pytest.mark.parametrize("difficulty", ["standard", "hard"])
def test_ground_truth_matches_independent_recomputation(seed, difficulty):
    task = SchedulingGenerator().generate(seed=seed, difficulty=difficulty)
    ctx = task["context"]
    recomputed = _recompute_optimal_tardiness(
        ctx["processing_times"], ctx["due_dates"], ctx["weights"]
    )
    assert task["ground_truth"]["value"] == float(recomputed)


def test_generation_is_deterministic():
    a = SchedulingGenerator().generate(seed=555, difficulty="standard")
    b = SchedulingGenerator().generate(seed=555, difficulty="standard")
    assert a["context"] == b["context"]
    assert a["ground_truth"] == b["ground_truth"]
    assert a["id"] == b["id"]


def test_different_seeds_yield_different_instances():
    a = SchedulingGenerator().generate(seed=1, difficulty="standard")
    b = SchedulingGenerator().generate(seed=2, difficulty="standard")
    assert a["context"] != b["context"]


def test_generated_task_validates_against_schema():
    task = SchedulingGenerator().generate(seed=123, difficulty="standard")
    validate_task(task)  # raises on failure


def test_standard_difficulty_is_five_unweighted_jobs():
    for seed in range(20):
        task = SchedulingGenerator().generate(seed=seed, difficulty="standard")
        ctx = task["context"]
        assert len(ctx["processing_times"]) == 5
        assert len(ctx["due_dates"]) == 5
        assert ctx["weights"] == [1, 1, 1, 1, 1]


def test_hard_difficulty_is_six_weighted_jobs():
    for seed in range(20):
        task = SchedulingGenerator().generate(seed=seed, difficulty="hard")
        ctx = task["context"]
        assert len(ctx["processing_times"]) == 6
        assert len(ctx["due_dates"]) == 6
        assert all(1 <= w <= 5 for w in ctx["weights"])


def test_optimal_tardiness_is_never_negative():
    for seed in range(20):
        for difficulty in ["standard", "hard"]:
            task = SchedulingGenerator().generate(seed=seed, difficulty=difficulty)
            assert task["ground_truth"]["value"] >= 0
