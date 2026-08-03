"""Deterministic public-set generator.

Generates the fixed, versioned snapshot committed to `data/public/` (SPEC.md Section 10: it
*will* be memorized by future models over time -- that's fine, its job is reproducibility and
onboarding, not the official held-out ranking). One JSONL file per generator, one task record
per line, each validated against `schemas/task.schema.json` before it's written.

    python -m harness.generate_public_set

Determinism: every task's `(generator, seed, difficulty)` is fixed by `GENERATOR_TARGETS` and
`taxonomy.yaml`'s `hard_subset_fraction` alone, so re-running this script always regenerates
byte-identical output (mod the `created` date stamp) -- there is no hidden randomness in *which*
seeds get used, only in what each generator does with a given seed (which is itself seeded).
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

import yaml

from harness.run import GENERATORS
from harness.validate import validate_task

ROOT = Path(__file__).resolve().parent.parent
TAXONOMY_PATH = ROOT / "taxonomy" / "taxonomy.yaml"
PUBLIC_DATA_DIR = ROOT / "data" / "public"

# Total task count per generator in the public set. Each generator maps to exactly one
# (domain, reasoning_tier, answer_format) cell (see each generator's `generate()`); these
# per-generator counts are how taxonomy.yaml's per-cell targets are actually produced -- see
# the comment above `targets:` in taxonomy.yaml for the generator -> cell breakdown.
GENERATOR_TARGETS = {
    "oee": 45,
    "mrp": 45,
    "inventory_policy": 45,
    "spc": 45,
    "scheduling": 45,
    "toc": 45,
    "quality_economics": 45,
    "fmea": 45,
    "standard_cost_variance": 45,
}

# Public-set seeds start at 0 and are contiguous per generator -- this range is reserved for
# the *public* set. The held-out set (unit 1.12) uses an entirely disjoint, non-committed seed
# range so held-out instances can never collide with (or be inferred from) the public set.
PUBLIC_SEED_START = 0


def load_taxonomy() -> dict:
    return yaml.safe_load(TAXONOMY_PATH.read_text())


def generate_generator_tasks(
    generator_name: str, count: int, hard_subset_fraction: float
) -> list[dict]:
    """Generate `count` tasks for one generator, deterministically split standard/hard.

    Seeds are contiguous starting at `PUBLIC_SEED_START`: the first `count - num_hard` seeds
    are `standard`, the remaining `num_hard` are `hard`. Every task is a fresh, distinct
    `(seed, difficulty)` combination -- no seed is ever reused within a generator's file.
    """
    num_hard = round(count * hard_subset_fraction)
    num_standard = count - num_hard

    generator = GENERATORS[generator_name]()
    tasks = []
    seed = PUBLIC_SEED_START
    for _ in range(num_standard):
        tasks.append(generator.generate(seed=seed, difficulty="standard"))
        seed += 1
    for _ in range(num_hard):
        tasks.append(generator.generate(seed=seed, difficulty="hard"))
        seed += 1
    return tasks


def generate_public_set(
    generator_targets: Optional[dict[str, int]] = None
) -> dict[str, list[dict]]:
    """Generate the full public set. Returns `{generator_name: [task, ...]}`.

    Every generated task is validated against `schemas/task.schema.json` before being
    returned; an invalid task raises rather than silently entering the public set.
    """
    taxonomy = load_taxonomy()
    hard_subset_fraction = taxonomy["hard_subset_fraction"]
    targets = generator_targets if generator_targets is not None else GENERATOR_TARGETS

    result = {}
    for generator_name, count in targets.items():
        tasks = generate_generator_tasks(generator_name, count, hard_subset_fraction)
        for task in tasks:
            validate_task(task)
        result[generator_name] = tasks
    return result


def write_public_set(tasks_by_generator: dict[str, list[dict]]) -> None:
    PUBLIC_DATA_DIR.mkdir(parents=True, exist_ok=True)
    for generator_name, tasks in tasks_by_generator.items():
        out_path = PUBLIC_DATA_DIR / f"{generator_name}.jsonl"
        with out_path.open("w") as f:
            for task in tasks:
                f.write(json.dumps(task) + "\n")


def main() -> None:
    tasks_by_generator = generate_public_set()
    write_public_set(tasks_by_generator)
    total = sum(len(tasks) for tasks in tasks_by_generator.values())
    print(
        f"Wrote {total} tasks across {len(tasks_by_generator)} generators to {PUBLIC_DATA_DIR}"
    )


if __name__ == "__main__":
    main()
