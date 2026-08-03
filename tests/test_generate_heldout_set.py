"""Held-out set generator tests: seed-base safety guard, schema validity, determinism, and the
contamination check unit 1.12 is actually for -- generated instances must be git-ignored."""
import subprocess

import pytest

from harness.generate_heldout_set import (
    HELDOUT_DATA_DIR,
    MIN_SAFE_SEED_BASE,
    generate_heldout_set,
    write_heldout_set,
)
from harness.validate import validate_task

SAFE_SEED_BASE = 500_000


def test_seed_base_below_floor_raises():
    with pytest.raises(ValueError):
        generate_heldout_set(seed_base=MIN_SAFE_SEED_BASE - 1, generator_targets={"oee": 3})


def test_seed_base_at_floor_is_accepted():
    tasks = generate_heldout_set(seed_base=MIN_SAFE_SEED_BASE, generator_targets={"oee": 3})
    assert len(tasks["oee"]) == 3


def test_every_task_validates_against_schema():
    tasks_by_generator = generate_heldout_set(
        seed_base=SAFE_SEED_BASE, generator_targets={"oee": 5, "mrp": 5}
    )
    for tasks in tasks_by_generator.values():
        for task in tasks:
            validate_task(task)  # raises on failure


def test_regeneration_is_deterministic():
    targets = {"oee": 5, "toc": 5}
    first = generate_heldout_set(seed_base=SAFE_SEED_BASE, generator_targets=targets)
    second = generate_heldout_set(seed_base=SAFE_SEED_BASE, generator_targets=targets)

    def strip_created(task):
        return {k: v for k, v in task.items() if k != "created"}

    for generator_name in targets:
        a = [strip_created(t) for t in first[generator_name]]
        b = [strip_created(t) for t in second[generator_name]]
        assert a == b


def test_different_seed_bases_yield_different_instances():
    a = generate_heldout_set(seed_base=SAFE_SEED_BASE, generator_targets={"oee": 5})
    b = generate_heldout_set(seed_base=SAFE_SEED_BASE + 1000, generator_targets={"oee": 5})
    assert a["oee"] != b["oee"]


def test_seed_ranges_are_disjoint_across_generators():
    # Each generator gets its own offset sub-range of the seed space (see generate_heldout_set's
    # `offset` bookkeeping) -- no two generators should ever draw from overlapping seeds.
    tasks_by_generator = generate_heldout_set(
        seed_base=SAFE_SEED_BASE, generator_targets={"oee": 5, "mrp": 5, "toc": 5}
    )
    seeds_by_generator = {
        name: {task["seed"] for task in tasks} for name, tasks in tasks_by_generator.items()
    }
    all_seed_sets = list(seeds_by_generator.values())
    for i, seeds_a in enumerate(all_seed_sets):
        for seeds_b in all_seed_sets[i + 1 :]:
            assert seeds_a.isdisjoint(seeds_b)


def test_heldout_seeds_never_collide_with_public_seed_range():
    # The public set (unit 1.11) uses contiguous seeds starting at 0, well below
    # MIN_SAFE_SEED_BASE for every generator it currently targets.
    tasks_by_generator = generate_heldout_set(
        seed_base=SAFE_SEED_BASE, generator_targets={"oee": 5, "mrp": 5}
    )
    for tasks in tasks_by_generator.values():
        for task in tasks:
            assert task["seed"] >= MIN_SAFE_SEED_BASE


@pytest.fixture
def cleanup_heldout_files():
    written = []
    yield written
    for path in written:
        path.unlink(missing_ok=True)


def test_written_heldout_files_are_git_ignored(cleanup_heldout_files):
    tasks_by_generator = generate_heldout_set(
        seed_base=SAFE_SEED_BASE, generator_targets={"oee": 3}
    )
    write_heldout_set(tasks_by_generator)

    out_path = HELDOUT_DATA_DIR / "oee.jsonl"
    cleanup_heldout_files.append(out_path)
    assert out_path.exists()

    # git check-ignore exits 0 if the path IS ignored, 1 if it is tracked/not ignored.
    result = subprocess.run(
        ["git", "check-ignore", "-q", str(out_path)],
        cwd=HELDOUT_DATA_DIR.parent.parent,
    )
    assert result.returncode == 0, "held-out instance file must be git-ignored"


def test_written_heldout_files_are_not_tracked_by_git(cleanup_heldout_files):
    tasks_by_generator = generate_heldout_set(
        seed_base=SAFE_SEED_BASE, generator_targets={"mrp": 3}
    )
    write_heldout_set(tasks_by_generator)

    out_path = HELDOUT_DATA_DIR / "mrp.jsonl"
    cleanup_heldout_files.append(out_path)

    result = subprocess.run(
        ["git", "ls-files", "--error-unmatch", str(out_path)],
        cwd=HELDOUT_DATA_DIR.parent.parent,
        capture_output=True,
    )
    assert result.returncode != 0, "held-out instance file must never be tracked by git"
