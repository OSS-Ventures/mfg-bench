"""Public-set generation tests: counts match taxonomy targets, every task is schema-valid,
and regeneration is deterministic (unit 1.11's three acceptance criteria)."""
from collections import Counter

import pytest

from harness.generate_public_set import (
    GENERATOR_TARGETS,
    generate_public_set,
    load_taxonomy,
)
from harness.validate import validate_task

# Each Family A generator maps to exactly one fixed (domain, reasoning_tier, answer_format)
# cell -- see each generator's `generate()`. Used to check that the *aggregate* per-cell count
# produced by generate_public_set() matches taxonomy.yaml's `targets`.
GENERATOR_CELL = {
    "oee": ("continuous_improvement", "L2", "numeric"),
    "mrp": ("supply_chain_sop", "L2", "numeric"),
    "inventory_policy": ("supply_chain_sop", "L2", "numeric"),
    "spc": ("quality_problem_solving", "L2", "numeric"),
    "fmea": ("quality_problem_solving", "L3", "numeric"),
    "toc": ("production_scheduling", "L3", "numeric"),
    "scheduling": ("production_scheduling", "L4", "numeric"),
    "quality_economics": ("cost_performance", "L2", "numeric"),
    "standard_cost_variance": ("cost_performance", "L2", "numeric"),
}


@pytest.fixture(scope="module")
def public_set():
    return generate_public_set()


def test_covers_every_targeted_generator():
    assert set(GENERATOR_TARGETS) == set(GENERATOR_CELL)


def test_total_count_is_within_roadmap_range(public_set):
    total = sum(len(tasks) for tasks in public_set.values())
    assert total == sum(GENERATOR_TARGETS.values())
    assert 400 <= total <= 600


def test_per_generator_count_matches_target(public_set):
    for generator_name, target in GENERATOR_TARGETS.items():
        assert len(public_set[generator_name]) == target


def test_every_task_validates_against_schema(public_set):
    for tasks in public_set.values():
        for task in tasks:
            validate_task(task)  # raises on failure


def test_hard_subset_fraction_split_per_generator(public_set):
    hard_subset_fraction = load_taxonomy()["hard_subset_fraction"]
    for generator_name, tasks in public_set.items():
        difficulties = Counter(task["difficulty"] for task in tasks)
        expected_hard = round(len(tasks) * hard_subset_fraction)
        assert difficulties["hard"] == expected_hard
        assert difficulties["standard"] == len(tasks) - expected_hard


def test_aggregate_per_cell_counts_match_taxonomy_targets(public_set):
    taxonomy_targets = load_taxonomy()["targets"]

    cell_counts = Counter()
    for generator_name, tasks in public_set.items():
        cell_counts[GENERATOR_CELL[generator_name]] += len(tasks)

    for (domain, tier, fmt), count in cell_counts.items():
        assert taxonomy_targets[domain][tier][fmt] == count


def test_task_ids_are_unique_within_and_across_generators(public_set):
    all_ids = [task["id"] for tasks in public_set.values() for task in tasks]
    assert len(all_ids) == len(set(all_ids))


def test_regeneration_is_deterministic(public_set):
    regenerated = generate_public_set()

    def strip_created(task):
        return {k: v for k, v in task.items() if k != "created"}

    for generator_name, tasks in public_set.items():
        other_tasks = regenerated[generator_name]
        assert [strip_created(t) for t in tasks] == [strip_created(t) for t in other_tasks]


def test_custom_generator_targets_are_respected():
    subset = generate_public_set(generator_targets={"oee": 10})
    assert set(subset) == {"oee"}
    assert len(subset["oee"]) == 10
