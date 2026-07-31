"""TOC/bottleneck generator tests: hand-verified bottleneck/throughput/shift-output cases, an
independent-recomputation sweep, determinism, and schema validity."""
import pytest

from generators.toc import TOCGenerator
from harness.validate import validate_task

# Each case: (seed, difficulty) -> the 3 ground-truth numbers, in order:
#   bottleneck station number, system throughput (units/hour), shift output (units).
# Hand-verified from the generator's own context (task_time_min/num_machines per station,
# hours_per_day) via: capacity_i = num_machines_i * 60 / task_time_i; bottleneck = argmin
# capacity (first on ties); throughput = min capacity; shift_output = throughput * hours.
HAND_VERIFIED_CASES = [
    # seed=1, standard: stations 8min/3m, 6min/2m, 7min/2m, 18min/2m ->
    # capacities 22.5, 20, 17.142857, 6.666667 -> station 4 is the constraint.
    (1, "standard", [4.0, 6.67, 60.0]),
    # seed=2, standard: stations 5min/1m, 6min/2m, 9min/3m, 13min/2m ->
    # capacities 12, 20, 20, 9.230769 -> station 4 is the constraint.
    (2, "standard", [4.0, 9.23, 92.31]),
    # seed=999, standard: stations 6min/3m, 19min/2m, 8min/3m, 14min/3m ->
    # capacities 30, 6.315789, 22.5, 12.857143 -> station 2 is the constraint.
    (999, "standard", [2.0, 6.32, 37.89]),
    # seed=123, hard: stations 4min/3m, 5min/4m, 11min/1m, 4min/4m, 20min/3m ->
    # capacities 45, 48, 5.454545, 60, 9 -> station 3 is the constraint.
    (123, "hard", [3.0, 5.45, 43.64]),
    # seed=7, hard: stations 13min/2m, 15min/1m, 5min/1m, 14min/1m, 19min/2m ->
    # capacities 9.230769, 4, 12, 4.285714, 6.315789 -> station 2 is the constraint.
    (7, "hard", [2.0, 4.0, 24.0]),
]


@pytest.mark.parametrize("seed,difficulty,expected_parts", HAND_VERIFIED_CASES)
def test_ground_truth_matches_hand_computed_metrics(seed, difficulty, expected_parts):
    task = TOCGenerator().generate(seed=seed, difficulty=difficulty)
    parts = [p["value"] for p in task["ground_truth"]["parts"]]
    assert parts == expected_parts


def _recompute_metrics(stations, hours_per_day):
    """Independent reimplementation (a running-min loop instead of `min(range(...), key=...)`),
    so this genuinely cross-checks the generator's own `compute_toc_metrics` rather than just
    calling it again."""
    best_index = None
    best_capacity = None
    for i, s in enumerate(stations):
        capacity = s["num_machines"] * 60 / s["task_time_min"]
        if best_capacity is None or capacity < best_capacity:
            best_capacity = capacity
            best_index = i

    shift_output = best_capacity * hours_per_day

    return [
        float(best_index + 1),
        round(best_capacity, 2),
        round(shift_output, 2),
    ]


@pytest.mark.parametrize("seed", range(30))
@pytest.mark.parametrize("difficulty", ["standard", "hard"])
def test_ground_truth_matches_independent_recomputation(seed, difficulty):
    task = TOCGenerator().generate(seed=seed, difficulty=difficulty)
    ctx = task["context"]
    recomputed = _recompute_metrics(ctx["stations"], ctx["hours_per_day"])

    parts = [p["value"] for p in task["ground_truth"]["parts"]]
    assert parts == recomputed


def test_generation_is_deterministic():
    a = TOCGenerator().generate(seed=555, difficulty="standard")
    b = TOCGenerator().generate(seed=555, difficulty="standard")
    assert a["context"] == b["context"]
    assert a["ground_truth"] == b["ground_truth"]
    assert a["id"] == b["id"]


def test_different_seeds_yield_different_instances():
    a = TOCGenerator().generate(seed=1, difficulty="standard")
    b = TOCGenerator().generate(seed=2, difficulty="standard")
    assert a["context"] != b["context"]


def test_generated_task_validates_against_schema():
    task = TOCGenerator().generate(seed=123, difficulty="standard")
    validate_task(task)  # raises on failure


def test_station_count_per_difficulty():
    for seed in range(20):
        standard = TOCGenerator().generate(seed=seed, difficulty="standard")
        hard = TOCGenerator().generate(seed=seed, difficulty="hard")
        assert len(standard["context"]["stations"]) == 4
        assert len(hard["context"]["stations"]) == 5


def test_bottleneck_station_within_bounds():
    for seed in range(30):
        for difficulty in ["standard", "hard"]:
            task = TOCGenerator().generate(seed=seed, difficulty=difficulty)
            num_stations = len(task["context"]["stations"])
            bottleneck = task["ground_truth"]["parts"][0]["value"]
            assert 1 <= bottleneck <= num_stations


def test_throughput_and_shift_output_are_always_positive():
    for seed in range(30):
        for difficulty in ["standard", "hard"]:
            task = TOCGenerator().generate(seed=seed, difficulty=difficulty)
            throughput = task["ground_truth"]["parts"][1]["value"]
            shift_output = task["ground_truth"]["parts"][2]["value"]
            assert throughput > 0
            assert shift_output > 0


def test_throughput_never_exceeds_any_station_capacity():
    # The bottleneck's capacity must be <= every station's own capacity, by definition.
    for seed in range(30):
        for difficulty in ["standard", "hard"]:
            task = TOCGenerator().generate(seed=seed, difficulty=difficulty)
            ctx = task["context"]
            throughput = task["ground_truth"]["parts"][1]["value"]
            capacities = [
                s["num_machines"] * 60 / s["task_time_min"] for s in ctx["stations"]
            ]
            assert all(throughput <= round(c, 2) + 0.01 for c in capacities)
