"""Held-out set generator -- the official leaderboard's contamination-resistant twin of
`generate_public_set.py`.

Per SPEC.md Section 10: "the held-out set is generated from private seeds kept out of git.
Only the seeds' existence is tracked; instances are gitignored." This module never bakes a
usable seed value into the repository -- `--seed-base` (or the `seed_base` argument) must be
supplied explicitly at generation time, by whoever is running a release cycle, from a value
they keep to themselves. There is deliberately no default here: a hardcoded fallback would
just be a committed seed with extra steps.

Output goes to `data/heldout/`, which `.gitignore` already excludes (`data/heldout/*`, keeping
only `.gitkeep` so the directory itself is tracked). Regenerate with a fresh `--seed-base` each
release cycle (unit 7.1) to rotate the held-out instances.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Optional

from harness.generate_public_set import GENERATOR_TARGETS, load_taxonomy
from harness.run import GENERATORS
from harness.validate import validate_task

ROOT = Path(__file__).resolve().parent.parent
HELDOUT_DATA_DIR = ROOT / "data" / "heldout"

# The public set (unit 1.11) uses contiguous seeds starting at 0, one generator-count block at
# a time (see generate_public_set.PUBLIC_SEED_START). No public-set generator currently uses
# more than a few hundred seeds, so any --seed-base at or above this floor is guaranteed
# disjoint from every public-set instance, however GENERATOR_TARGETS grows.
MIN_SAFE_SEED_BASE = 10_000


def generate_generator_heldout_tasks(
    generator_name: str, count: int, hard_subset_fraction: float, seed_base: int
) -> list[dict]:
    """Generate `count` held-out tasks for one generator, seeded starting at `seed_base`.

    Mirrors `generate_public_set.generate_generator_tasks`'s standard/hard split exactly, just
    against a private, caller-supplied seed range instead of the public one.
    """
    num_hard = round(count * hard_subset_fraction)
    num_standard = count - num_hard

    generator = GENERATORS[generator_name]()
    tasks = []
    seed = seed_base
    for _ in range(num_standard):
        tasks.append(generator.generate(seed=seed, difficulty="standard"))
        seed += 1
    for _ in range(num_hard):
        tasks.append(generator.generate(seed=seed, difficulty="hard"))
        seed += 1
    return tasks


def generate_heldout_set(
    seed_base: int, generator_targets: Optional[dict[str, int]] = None
) -> dict[str, list[dict]]:
    """Generate the held-out set. Returns `{generator_name: [task, ...]}`.

    Raises `ValueError` if `seed_base` is below `MIN_SAFE_SEED_BASE` -- this is the one guard
    rail that keeps a careless call from accidentally regenerating (and thus leaking) public-set
    instances under the held-out label.
    """
    if seed_base < MIN_SAFE_SEED_BASE:
        raise ValueError(
            f"seed_base={seed_base} is below the minimum safe held-out seed base "
            f"({MIN_SAFE_SEED_BASE}); it risks colliding with the public set's seed range. "
            "Pick a private seed base at or above this floor."
        )

    taxonomy = load_taxonomy()
    hard_subset_fraction = taxonomy["hard_subset_fraction"]
    targets = generator_targets if generator_targets is not None else GENERATOR_TARGETS

    # Give every generator its own disjoint sub-range of the seed space, offset from
    # seed_base, so that no two generators can ever collide even though they share one
    # caller-supplied base -- mirrors generate_public_set()'s per-generator seed reset, just
    # translated by seed_base instead of always starting at 0.
    result = {}
    offset = 0
    for generator_name, count in targets.items():
        tasks = generate_generator_heldout_tasks(
            generator_name, count, hard_subset_fraction, seed_base + offset
        )
        for task in tasks:
            validate_task(task)
        result[generator_name] = tasks
        offset += count
    return result


def write_heldout_set(tasks_by_generator: dict[str, list[dict]]) -> None:
    HELDOUT_DATA_DIR.mkdir(parents=True, exist_ok=True)
    for generator_name, tasks in tasks_by_generator.items():
        out_path = HELDOUT_DATA_DIR / f"{generator_name}.jsonl"
        with out_path.open("w") as f:
            for task in tasks:
                f.write(json.dumps(task) + "\n")


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Generate the held-out set from a private seed base. --seed-base must be supplied "
            "explicitly and kept out of git; there is no committed default."
        )
    )
    parser.add_argument(
        "--seed-base",
        type=int,
        required=True,
        help=f"Private seed base, >= {MIN_SAFE_SEED_BASE}. Never commit this value.",
    )
    args = parser.parse_args()

    tasks_by_generator = generate_heldout_set(seed_base=args.seed_base)
    write_heldout_set(tasks_by_generator)
    total = sum(len(tasks) for tasks in tasks_by_generator.values())
    print(
        f"Wrote {total} held-out tasks across {len(tasks_by_generator)} generators to "
        f"{HELDOUT_DATA_DIR} (gitignored)."
    )


if __name__ == "__main__":
    main()
