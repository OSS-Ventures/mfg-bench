"""Quality economics generator tests: hand-verified FPY/RTY/COPQ cases, an independent-
recomputation sweep, determinism, and schema validity."""
import pytest

from generators.quality_economics import QualityEconomicsGenerator
from harness.validate import validate_task

# Each case: (seed, difficulty) -> the 5 ground-truth numbers, in order:
#   average FPY (%), rolled throughput yield (%), total scrap cost ($), total rework cost ($),
#   COPQ ($).
# Hand-verified from the generator's own context (units_started, per-station scrap_pct/
# rework_pct/scrap_cost_per_unit/rework_cost_per_unit) via: for each station, scrapped =
# units_in * scrap_rate, reworked = units_in * rework_rate, fpy = 1 - scrap_rate - rework_rate,
# scrap_cost += scrapped * scrap_cost_per_unit, rework_cost += reworked * rework_cost_per_unit,
# units_in *= (1 - scrap_rate) for the next station; avg_fpy = mean(fpys), rty = product(fpys).
HAND_VERIFIED_CASES = [
    # seed=1, standard: 900 units; stations (scrap%,rework%,scrap$,rework$) =
    # (5,3,26,8), (4,9,40,25), (4,5,16,20) ->
    # fpys 0.92, 0.87, 0.91; units 900 -> 855 -> 820.8;
    # scrap_cost 1170 + 1368 + 525.312 = 3063.312; rework_cost 216 + 1923.75 + 820.8 = 2960.55.
    (1, "standard", [90.0, 72.84, 3063.31, 2960.55, 6023.86]),
    # seed=2, standard: 600 units; stations = (1,3,33,10), (6,6,26,24), (2,2,47,26) ->
    # fpys 0.96, 0.88, 0.96; units 600 -> 594 -> 558.36;
    # scrap_cost 198 + 926.64 + 524.8584 = 1649.4984; rework_cost 180 + 855.36 + 290.3472 =
    # 1325.7072.
    (2, "standard", [93.33, 81.1, 1649.5, 1325.71, 2975.21]),
    # seed=999, standard: 700 units; stations = (5,10,41,20), (2,7,51,30), (6,3,51,11) ->
    # fpys 0.85, 0.91, 0.91; units 700 -> 665 -> 651.7;
    # scrap_cost 1435 + 678.3 + 1994.202 = 4107.502; rework_cost 1400 + 1396.5 + 215.061 =
    # 3011.561.
    (999, "standard", [89.0, 70.39, 4107.5, 3011.56, 7119.06]),
    # seed=123, hard: 600 units; stations = (7,6,59,18), (7,6,12,17), (11,13,31,15),
    # (3,7,18,15) -> fpys 0.87, 0.87, 0.76, 0.90; units 600 -> 558 -> 518.94 -> 461.8566;
    # scrap_cost 2478 + 468.72 + 1769.5854 + 249.402564 = 4965.707964;
    # rework_cost 648 + 569.16 + 1011.933 + 484.94943 = 2714.04243.
    (123, "hard", [85.0, 51.77, 4965.71, 2714.04, 7679.75]),
    # seed=7, hard: 1500 units; stations = (5,11,51,6), (4,13,16,16), (12,5,42,11),
    # (3,6,37,18) -> fpys 0.84, 0.83, 0.83, 0.91; units 1500 -> 1425 -> 1368 -> 1203.84;
    # scrap_cost 3825 + 912 + 6894.72 + 1336.2624 = 12967.9824;
    # rework_cost 990 + 2964 + 752.4 + 1300.1472 = 6006.5472.
    (7, "hard", [85.25, 52.66, 12967.98, 6006.55, 18974.53]),
]


@pytest.mark.parametrize("seed,difficulty,expected_parts", HAND_VERIFIED_CASES)
def test_ground_truth_matches_hand_computed_metrics(seed, difficulty, expected_parts):
    task = QualityEconomicsGenerator().generate(seed=seed, difficulty=difficulty)
    parts = [p["value"] for p in task["ground_truth"]["parts"]]
    assert parts == expected_parts


def _recompute_metrics(units_started, stations):
    """Independent reimplementation: derives each station's FPY as good/units_in (a division)
    rather than 1 - scrap_rate - rework_rate (a subtraction), and accumulates costs via a plain
    running total rather than the generator's loop, so this genuinely cross-checks the
    generator's own `compute_quality_economics` rather than just calling it again."""
    units_in = units_started
    fpys = []
    scrap_cost_total = 0.0
    rework_cost_total = 0.0

    for station in stations:
        scrapped = units_in * station["scrap_pct"] / 100
        reworked = units_in * station["rework_pct"] / 100
        good = units_in - scrapped - reworked
        fpys.append(good / units_in)

        scrap_cost_total = scrap_cost_total + scrapped * station["scrap_cost_per_unit"]
        rework_cost_total = rework_cost_total + reworked * station["rework_cost_per_unit"]

        units_in = units_in - scrapped

    avg_fpy = sum(fpys) / len(fpys)
    rty = 1.0
    for fpy in fpys:
        rty = rty * fpy

    return [
        round(avg_fpy * 100, 2),
        round(rty * 100, 2),
        round(scrap_cost_total, 2),
        round(rework_cost_total, 2),
        round(scrap_cost_total + rework_cost_total, 2),
    ]


@pytest.mark.parametrize("seed", range(30))
@pytest.mark.parametrize("difficulty", ["standard", "hard"])
def test_ground_truth_matches_independent_recomputation(seed, difficulty):
    task = QualityEconomicsGenerator().generate(seed=seed, difficulty=difficulty)
    ctx = task["context"]
    recomputed = _recompute_metrics(ctx["units_started"], ctx["stations"])

    parts = [p["value"] for p in task["ground_truth"]["parts"]]
    assert parts == recomputed


def test_generation_is_deterministic():
    a = QualityEconomicsGenerator().generate(seed=555, difficulty="standard")
    b = QualityEconomicsGenerator().generate(seed=555, difficulty="standard")
    assert a["context"] == b["context"]
    assert a["ground_truth"] == b["ground_truth"]
    assert a["id"] == b["id"]


def test_different_seeds_yield_different_instances():
    a = QualityEconomicsGenerator().generate(seed=1, difficulty="standard")
    b = QualityEconomicsGenerator().generate(seed=2, difficulty="standard")
    assert a["context"] != b["context"]


def test_generated_task_validates_against_schema():
    task = QualityEconomicsGenerator().generate(seed=123, difficulty="standard")
    validate_task(task)  # raises on failure


def test_station_count_per_difficulty():
    for seed in range(20):
        standard = QualityEconomicsGenerator().generate(seed=seed, difficulty="standard")
        hard = QualityEconomicsGenerator().generate(seed=seed, difficulty="hard")
        assert len(standard["context"]["stations"]) == 3
        assert len(hard["context"]["stations"]) == 4


def test_fpy_and_rty_are_within_zero_to_hundred_percent():
    for seed in range(30):
        for difficulty in ["standard", "hard"]:
            task = QualityEconomicsGenerator().generate(seed=seed, difficulty=difficulty)
            avg_fpy, rty = (p["value"] for p in task["ground_truth"]["parts"][:2])
            assert 0.0 < avg_fpy <= 100.0
            assert 0.0 < rty <= 100.0


def test_rty_never_exceeds_average_fpy():
    # RTY is the product of several fractions each in (0, 1], which is never larger than the
    # smallest of them, which in turn is never larger than their arithmetic mean (average FPY).
    for seed in range(30):
        for difficulty in ["standard", "hard"]:
            task = QualityEconomicsGenerator().generate(seed=seed, difficulty=difficulty)
            avg_fpy, rty = (p["value"] for p in task["ground_truth"]["parts"][:2])
            assert rty <= avg_fpy + 0.01


def test_costs_are_never_negative():
    for seed in range(30):
        for difficulty in ["standard", "hard"]:
            task = QualityEconomicsGenerator().generate(seed=seed, difficulty=difficulty)
            scrap_cost, rework_cost, copq = (
                p["value"] for p in task["ground_truth"]["parts"][2:]
            )
            assert scrap_cost >= 0
            assert rework_cost >= 0
            assert copq >= 0
