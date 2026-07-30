"""SPC generator tests: hand-verified control-limit/Cp/Cpk/Pp/Ppk/out-of-control cases,
an independent-recomputation sweep, determinism, and schema validity."""
import pytest

from generators.spc import SPC_CONSTANTS, SPCGenerator
from harness.validate import validate_task

# Each case: (seed, difficulty) -> the 7 ground-truth numbers, in order:
#   UCL, LCL, Cp, Cpk, Pp, Ppk, out-of-control count.
# Independently hand-verified from the generator's own context (subgroups, USL/LSL, A2/d2)
# via the standard X-bar/R formulas:
#   xbarbar = mean(subgroup means); rbar = mean(subgroup ranges)
#   UCL/LCL = xbarbar +/- A2 * rbar; sigma_within = rbar / d2
#   Cp = (USL-LSL) / (6*sigma_within); Cpk = min(USL-xbarbar, xbarbar-LSL) / (3*sigma_within)
#   overall_sigma = sample stdev of all individual measurements (pooled)
#   Pp = (USL-LSL) / (6*overall_sigma); Ppk = min(USL-mean, mean-LSL) / (3*overall_sigma)
#   out-of-control count = # subgroup means outside [LCL, UCL]
HAND_VERIFIED_CASES = [
    # seed=1, standard: n=4, k=15, USL=161.82, LSL=138.18 -> xbarbar=154.71, rbar A2=0.729,
    # d2=2.059 give UCL=154.71+0.729*rbar, no subgroup mean strays outside -> 0 out-of-control.
    (1, "standard", [154.71, 145.02, 1.22, 1.21, 1.35, 1.34, 0.0]),
    # seed=2, standard: n=4, k=15, USL=37.06, LSL=22.94 -- the injected special-cause shift on
    # the last subgroup pushes exactly 1 subgroup mean outside the X-bar limits.
    (2, "standard", [33.5, 28.04, 1.29, 1.15, 0.91, 0.81, 1.0]),
    # seed=999, standard: n=4, k=15, USL=159.42, LSL=140.58 -> stable process, 0 out-of-control.
    (999, "standard", [154.16, 146.75, 1.27, 1.21, 1.27, 1.21, 0.0]),
    # seed=123, hard: n=3, k=20, USL=64.81, LSL=55.19 -- shifted last subgroup -> 1
    # out-of-control.
    (123, "hard", [62.43, 58.53, 1.42, 1.28, 0.92, 0.83, 1.0]),
    # seed=7, hard: n=6, k=20, USL=46.76, LSL=33.24 -> stable process, 0 out-of-control.
    (7, "hard", [42.28, 37.13, 1.07, 1.03, 1.09, 1.04, 0.0]),
]


@pytest.mark.parametrize("seed,difficulty,expected_parts", HAND_VERIFIED_CASES)
def test_ground_truth_matches_hand_computed_metrics(seed, difficulty, expected_parts):
    task = SPCGenerator().generate(seed=seed, difficulty=difficulty)
    parts = [p["value"] for p in task["ground_truth"]["parts"]]
    assert parts == expected_parts


def _recompute_metrics(subgroups, usl, lsl, a2, d2):
    """Independent reimplementation of the X-bar/R formulas (plain sum/len arithmetic, not
    `statistics.mean`/`statistics.stdev`), so this genuinely cross-checks the generator's own
    `compute_spc_metrics` rather than just calling it again."""
    subgroup_means = [sum(sg) / len(sg) for sg in subgroups]
    subgroup_ranges = [max(sg) - min(sg) for sg in subgroups]

    xbarbar = sum(subgroup_means) / len(subgroup_means)
    rbar = sum(subgroup_ranges) / len(subgroup_ranges)

    ucl = xbarbar + a2 * rbar
    lcl = xbarbar - a2 * rbar
    sigma_within = rbar / d2

    cp = (usl - lsl) / (6 * sigma_within)
    cpk = min(usl - xbarbar, xbarbar - lsl) / (3 * sigma_within)

    all_values = [v for sg in subgroups for v in sg]
    n = len(all_values)
    overall_mean = sum(all_values) / n
    variance = sum((v - overall_mean) ** 2 for v in all_values) / (n - 1)
    overall_sigma = variance ** 0.5

    pp = (usl - lsl) / (6 * overall_sigma)
    ppk = min(usl - overall_mean, overall_mean - lsl) / (3 * overall_sigma)

    out_of_control_count = sum(1 for m in subgroup_means if m > ucl or m < lcl)

    return [
        round(ucl, 2),
        round(lcl, 2),
        round(cp, 2),
        round(cpk, 2),
        round(pp, 2),
        round(ppk, 2),
        float(out_of_control_count),
    ]


@pytest.mark.parametrize("seed", range(30))
@pytest.mark.parametrize("difficulty", ["standard", "hard"])
def test_ground_truth_matches_independent_recomputation(seed, difficulty):
    task = SPCGenerator().generate(seed=seed, difficulty=difficulty)
    ctx = task["context"]
    recomputed = _recompute_metrics(ctx["subgroups"], ctx["usl"], ctx["lsl"], ctx["a2"], ctx["d2"])

    parts = [p["value"] for p in task["ground_truth"]["parts"]]
    assert parts == recomputed


def test_generation_is_deterministic():
    a = SPCGenerator().generate(seed=555, difficulty="standard")
    b = SPCGenerator().generate(seed=555, difficulty="standard")
    assert a["context"] == b["context"]
    assert a["ground_truth"] == b["ground_truth"]
    assert a["id"] == b["id"]


def test_different_seeds_yield_different_instances():
    a = SPCGenerator().generate(seed=1, difficulty="standard")
    b = SPCGenerator().generate(seed=2, difficulty="standard")
    assert a["context"] != b["context"]


def test_generated_task_validates_against_schema():
    task = SPCGenerator().generate(seed=123, difficulty="standard")
    validate_task(task)  # raises on failure


def test_control_chart_constants_are_used_consistently():
    for seed in range(20):
        for difficulty in ["standard", "hard"]:
            task = SPCGenerator().generate(seed=seed, difficulty=difficulty)
            ctx = task["context"]
            constants = SPC_CONSTANTS[ctx["subgroup_size"]]
            assert constants["A2"] == ctx["a2"]
            assert constants["d2"] == ctx["d2"]


def test_cp_is_always_positive():
    # Cp depends only on spread (USL - LSL > 0, sigma_within > 0), never on centering.
    for seed in range(30):
        for difficulty in ["standard", "hard"]:
            task = SPCGenerator().generate(seed=seed, difficulty=difficulty)
            cp = task["ground_truth"]["parts"][2]["value"]
            assert cp > 0


def test_out_of_control_count_within_bounds():
    for seed in range(30):
        for difficulty in ["standard", "hard"]:
            task = SPCGenerator().generate(seed=seed, difficulty=difficulty)
            ctx = task["context"]
            count = task["ground_truth"]["parts"][6]["value"]
            assert 0 <= count <= ctx["num_subgroups"]
