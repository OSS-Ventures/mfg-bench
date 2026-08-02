"""Standard-cost variance generator tests: hand-verified variance cases, an independent-
recomputation sweep, determinism, and schema validity."""
import pytest

from generators.standard_cost_variance import StandardCostVarianceGenerator
from harness.validate import validate_task

# Each case: (seed, difficulty) -> the 4 ground-truth numbers, in order:
#   Material Price Variance, Material Usage Variance, Labor Rate Variance,
#   Labor Efficiency Variance (all in dollars; positive = unfavorable).
# Hand-verified from the generator's own context (standard/actual price, quantity, rate, hours)
# via: MPV = (actual_price - standard_price) * actual_qty_used; MQV = (actual_qty_used -
# standard_qty_allowed) * standard_price; LRV = (actual_rate - standard_rate) * actual_hours_used;
# LEV = (actual_hours_used - standard_hours_allowed) * standard_rate.
HAND_VERIFIED_CASES = [
    # seed=1, standard: standard price/qty allowed = $23, 6200.0 lb; actual price/qty =
    # $25.40, 5387.4 lb; standard/actual rate = $18, $17.98/hr; standard hours allowed/actual
    # hours = 1255.5, 1312.6 ->
    # MPV = (25.40-23)*5387.4 = 2.40*5387.4 = 12929.76;
    # MQV = (5387.4-6200.0)*23 = -812.6*23 = -18689.80;
    # LRV = (17.98-18)*1312.6 = -0.02*1312.6 = -26.252 -> -26.25;
    # LEV = (1312.6-1255.5)*18 = 57.1*18 = 1027.80.
    (1, "standard", [12929.76, -18689.8, -26.25, 1027.8]),
    # seed=2, standard: standard price/qty allowed = $7, 4920.0 lb; actual price/qty =
    # $6.13, 4431.6 lb; standard/actual rate = $40, $42.04/hr; standard hours allowed/actual
    # hours = 781.05, 805.9 ->
    # MPV = (6.13-7)*4431.6 = -0.87*4431.6 = -3855.492 -> -3855.49;
    # MQV = (4431.6-4920.0)*7 = -488.4*7 = -3418.80;
    # LRV = (42.04-40)*805.9 = 2.04*805.9 = 1644.036 -> 1644.04;
    # LEV = (805.9-781.05)*40 = 24.85*40 = 994.00.
    (2, "standard", [-3855.49, -3418.8, 1644.04, 994.0]),
    # seed=999, standard: standard price/qty allowed = $7, 11340.0 lb; actual price/qty =
    # $7.83, 11590.9 lb; standard/actual rate = $30, $29.85/hr; standard hours allowed/actual
    # hours = 5103.0, 5328.6 ->
    # MPV = (7.83-7)*11590.9 = 0.83*11590.9 = 9620.447 -> 9620.45;
    # MQV = (11590.9-11340.0)*7 = 250.9*7 = 1756.30;
    # LRV = (29.85-30)*5328.6 = -0.15*5328.6 = -799.29;
    # LEV = (5328.6-5103.0)*30 = 225.6*30 = 6768.00.
    (999, "standard", [9620.45, 1756.3, -799.29, 6768.0]),
    # seed=123, hard: standard price/qty allowed = $13, 6070.0 lb; actual price/qty =
    # $10.32, 5361.5 lb; standard/actual rate = $16, $15.03/hr; standard hours allowed/actual
    # hours = 2318.74, 2134.2 ->
    # MPV = (10.32-13)*5361.5 = -2.68*5361.5 = -14368.82;
    # MQV = (5361.5-6070.0)*13 = -708.5*13 = -9210.50;
    # LRV = (15.03-16)*2134.2 = -0.97*2134.2 = -2070.174 -> -2070.17;
    # LEV = (2134.2-2318.74)*16 = -184.54*16 = -2952.64.
    (123, "hard", [-14368.82, -9210.5, -2070.17, -2952.64]),
    # seed=7, hard: standard price/qty allowed = $9, 4652.0 lb; actual price/qty =
    # $8.53, 3657.5 lb; standard/actual rate = $32, $25.51/hr; standard hours allowed/actual
    # hours = 4558.96, 5492.9 ->
    # MPV = (8.53-9)*3657.5 = -0.47*3657.5 = -1719.025 -> -1719.03 (float rounding);
    # MQV = (3657.5-4652.0)*9 = -994.5*9 = -8950.50;
    # LRV = (25.51-32)*5492.9 = -6.49*5492.9 = -35648.921 -> -35648.92;
    # LEV = (5492.9-4558.96)*32 = 933.94*32 = 29886.08.
    (7, "hard", [-1719.03, -8950.5, -35648.92, 29886.08]),
]


@pytest.mark.parametrize("seed,difficulty,expected_parts", HAND_VERIFIED_CASES)
def test_ground_truth_matches_hand_computed_metrics(seed, difficulty, expected_parts):
    task = StandardCostVarianceGenerator().generate(seed=seed, difficulty=difficulty)
    parts = [p["value"] for p in task["ground_truth"]["parts"]]
    assert parts == expected_parts


def _recompute_metrics(ctx):
    """Independent reimplementation: expands each variance as a difference of two products
    (actual_total - standard_total) rather than the generator's (difference) x factor, so this
    genuinely cross-checks the generator's own `compute_standard_cost_variances` rather than
    just calling it again."""
    mpv = (
        ctx["actual_price_per_unit"] * ctx["actual_qty_used"]
        - ctx["standard_price_per_unit"] * ctx["actual_qty_used"]
    )
    mqv = (
        ctx["standard_price_per_unit"] * ctx["actual_qty_used"]
        - ctx["standard_price_per_unit"] * ctx["standard_qty_allowed"]
    )
    lrv = (
        ctx["actual_rate_per_hour"] * ctx["actual_hours_used"]
        - ctx["standard_rate_per_hour"] * ctx["actual_hours_used"]
    )
    lev = (
        ctx["standard_rate_per_hour"] * ctx["actual_hours_used"]
        - ctx["standard_rate_per_hour"] * ctx["standard_hours_allowed"]
    )
    return [round(mpv, 2), round(mqv, 2), round(lrv, 2), round(lev, 2)]


@pytest.mark.parametrize("seed", range(30))
@pytest.mark.parametrize("difficulty", ["standard", "hard"])
def test_ground_truth_matches_independent_recomputation(seed, difficulty):
    task = StandardCostVarianceGenerator().generate(seed=seed, difficulty=difficulty)
    recomputed = _recompute_metrics(task["context"])

    parts = [p["value"] for p in task["ground_truth"]["parts"]]
    # Allow a 1-cent tolerance: the generator's (difference) x factor and this test's
    # (product) - (product) are mathematically identical but occasionally land on opposite
    # sides of a .xx5 rounding boundary due to ordinary floating-point representation error
    # (e.g. true value 9303.075 stored as 9303.075000000003 vs 9303.074999999997) -- expected
    # floating-point behavior, not a generator bug (same class of issue noted for COPQ in unit
    # 1.7's quality_economics generator).
    for actual, expected in zip(parts, recomputed):
        assert abs(actual - expected) <= 0.011


def test_generation_is_deterministic():
    a = StandardCostVarianceGenerator().generate(seed=555, difficulty="standard")
    b = StandardCostVarianceGenerator().generate(seed=555, difficulty="standard")
    assert a["context"] == b["context"]
    assert a["ground_truth"] == b["ground_truth"]
    assert a["id"] == b["id"]


def test_different_seeds_yield_different_instances():
    a = StandardCostVarianceGenerator().generate(seed=1, difficulty="standard")
    b = StandardCostVarianceGenerator().generate(seed=2, difficulty="standard")
    assert a["context"] != b["context"]


def test_generated_task_validates_against_schema():
    task = StandardCostVarianceGenerator().generate(seed=123, difficulty="standard")
    validate_task(task)  # raises on failure


def test_actual_output_units_within_range_per_difficulty():
    for seed in range(20):
        standard = StandardCostVarianceGenerator().generate(seed=seed, difficulty="standard")
        hard = StandardCostVarianceGenerator().generate(seed=seed, difficulty="hard")
        assert 500 <= standard["context"]["actual_output_units"] <= 2000
        assert 1000 <= hard["context"]["actual_output_units"] <= 5000


def test_standard_quantity_and_hours_allowed_are_derived_from_actual_output():
    for seed in range(30):
        for difficulty in ["standard", "hard"]:
            task = StandardCostVarianceGenerator().generate(seed=seed, difficulty=difficulty)
            ctx = task["context"]
            assert ctx["standard_qty_allowed"] == (
                ctx["standard_qty_per_unit"] * ctx["actual_output_units"]
            )
            assert ctx["standard_hours_allowed"] == round(
                ctx["standard_hours_per_unit"] * ctx["actual_output_units"], 2
            )


def test_price_variance_sign_matches_price_direction():
    # If the actual price/rate exceeds standard, the corresponding variance must be
    # unfavorable (positive), since quantities/hours used are always positive; and vice versa.
    for seed in range(30):
        for difficulty in ["standard", "hard"]:
            task = StandardCostVarianceGenerator().generate(seed=seed, difficulty=difficulty)
            ctx = task["context"]
            mpv, _, lrv, _ = (p["value"] for p in task["ground_truth"]["parts"])

            price_delta = ctx["actual_price_per_unit"] - ctx["standard_price_per_unit"]
            rate_delta = ctx["actual_rate_per_hour"] - ctx["standard_rate_per_hour"]
            assert (mpv > 0) == (price_delta > 0)
            assert (lrv > 0) == (rate_delta > 0)
