"""Leaderboard aggregation: results/*.jsonl -> markdown + csv, with per-domain and per-tier
breakdowns.

    python -m harness.aggregate

Reads every result record across `results/*.jsonl`, grouped by each record's own `model` field
(not by filename -- a results filename is keyed by *adapter*, e.g. `anthropic.jsonl`, and more
than one model config could in principle share an adapter). Each task's `domain` and
`reasoning_tier` are re-derived from its `task_id`'s generator segment rather than looked up in
a stored copy: every `generators/*.py` `generate()` hardcodes `domain`/`reasoning_tier`/
`family` as constants independent of `seed` and `difficulty` (see e.g. `generators/oee.py`), so
one throwaway instance per generator (seed 0) is all that's needed to recover them -- no
dependency on `data/public/` being present, and no risk of a stale cached copy drifting from
the generator's actual current definition.
"""
from __future__ import annotations

import csv
import json
import re
from collections import defaultdict
from pathlib import Path
from typing import Any

from harness.run import GENERATORS

ROOT = Path(__file__).resolve().parent.parent
RESULTS_DIR = ROOT / "results"
LEADERBOARD_MD_PATH = RESULTS_DIR / "leaderboard.md"
LEADERBOARD_CSV_PATH = RESULTS_DIR / "leaderboard.csv"

TASK_ID_PATTERN = re.compile(r"^[a-z_]+\.(?P<generator>[a-z_]+)\.\d+$")

_generator_metadata_cache: dict[str, dict[str, str]] = {}


def generator_metadata(generator_name: str) -> dict[str, str]:
    """`domain`/`reasoning_tier`/`family` for a generator -- fixed regardless of seed or
    difficulty, so one throwaway `seed=0` instance is enough to read them off. Cached per
    generator name since every call would otherwise re-generate an unused task."""
    if generator_name not in _generator_metadata_cache:
        task = GENERATORS[generator_name]().generate(seed=0, difficulty="standard")
        _generator_metadata_cache[generator_name] = {
            "domain": task["domain"],
            "reasoning_tier": task["reasoning_tier"],
            "family": task["family"],
        }
    return _generator_metadata_cache[generator_name]


def generator_of(task_id: str) -> str:
    match = TASK_ID_PATTERN.match(task_id)
    if not match:
        raise ValueError(f"cannot parse a generator name out of task_id: {task_id!r}")
    return match.group("generator")


def load_results(results_dir: Path = RESULTS_DIR) -> list[dict[str, Any]]:
    results = []
    for path in sorted(results_dir.glob("*.jsonl")):
        with path.open() as f:
            for line in f:
                line = line.strip()
                if line:
                    results.append(json.loads(line))
    return results


def _bucket_stats(results: list[dict[str, Any]]) -> dict[str, Any]:
    scores = [r["score"] for r in results]
    parse_failures = sum(1 for r in results if r.get("parse_failure"))
    return {
        "count": len(results),
        "mean_score": round(sum(scores) / len(scores), 4) if scores else 0.0,
        "parse_failure_rate": round(parse_failures / len(results), 4) if results else 0.0,
    }


def aggregate(results: list[dict[str, Any]]) -> dict[str, Any]:
    """Aggregate raw result records into overall / per-domain / per-tier stats, per model."""
    by_model: dict[str, list[dict]] = defaultdict(list)
    for r in results:
        by_model[r["model"]].append(r)

    overall: dict[str, Any] = {}
    by_domain: dict[str, dict[str, Any]] = {}
    by_tier: dict[str, dict[str, Any]] = {}

    for model, model_results in by_model.items():
        overall[model] = _bucket_stats(model_results)

        domain_groups: dict[str, list[dict]] = defaultdict(list)
        tier_groups: dict[str, list[dict]] = defaultdict(list)
        for r in model_results:
            meta = generator_metadata(generator_of(r["task_id"]))
            domain_groups[meta["domain"]].append(r)
            tier_groups[meta["reasoning_tier"]].append(r)

        by_domain[model] = {domain: _bucket_stats(rs) for domain, rs in domain_groups.items()}
        by_tier[model] = {tier: _bucket_stats(rs) for tier, rs in tier_groups.items()}

    return {"overall": overall, "by_domain": by_domain, "by_tier": by_tier}


def write_markdown(aggregated: dict[str, Any], path: Path = LEADERBOARD_MD_PATH) -> None:
    lines = ["# Leaderboard", ""]

    lines.append("## Overall")
    lines.append("")
    lines.append("| Model | Tasks | Mean score | Parse-failure rate |")
    lines.append("|---|---|---|---|")
    for model, stats in sorted(
        aggregated["overall"].items(), key=lambda kv: -kv[1]["mean_score"]
    ):
        lines.append(
            f"| {model} | {stats['count']} | {stats['mean_score']:.4f} | "
            f"{stats['parse_failure_rate']:.4f} |"
        )
    lines.append("")

    lines.append("## Per-domain")
    lines.append("")
    for model, domains in aggregated["by_domain"].items():
        lines.append(f"### {model}")
        lines.append("")
        lines.append("| Domain | Tasks | Mean score |")
        lines.append("|---|---|---|")
        for domain, stats in sorted(domains.items()):
            lines.append(f"| {domain} | {stats['count']} | {stats['mean_score']:.4f} |")
        lines.append("")

    lines.append("## Per-tier")
    lines.append("")
    for model, tiers in aggregated["by_tier"].items():
        lines.append(f"### {model}")
        lines.append("")
        lines.append("| Tier | Tasks | Mean score |")
        lines.append("|---|---|---|")
        for tier, stats in sorted(tiers.items()):
            lines.append(f"| {tier} | {stats['count']} | {stats['mean_score']:.4f} |")
        lines.append("")

    path.write_text("\n".join(lines) + "\n")


def write_csv(aggregated: dict[str, Any], path: Path = LEADERBOARD_CSV_PATH) -> None:
    rows = []
    for model, stats in aggregated["overall"].items():
        rows.append(("overall", model, "-", stats))
    for model, domains in aggregated["by_domain"].items():
        for domain, stats in domains.items():
            rows.append(("domain", model, domain, stats))
    for model, tiers in aggregated["by_tier"].items():
        for tier, stats in tiers.items():
            rows.append(("tier", model, tier, stats))

    with path.open("w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(
            ["breakdown", "model", "bucket", "count", "mean_score", "parse_failure_rate"]
        )
        for breakdown, model, bucket, stats in rows:
            writer.writerow(
                [
                    breakdown,
                    model,
                    bucket,
                    stats["count"],
                    stats["mean_score"],
                    stats["parse_failure_rate"],
                ]
            )


def main() -> None:
    results = load_results()
    if not results:
        print(f"No result records found under {RESULTS_DIR} -- nothing to aggregate.")
        return
    aggregated = aggregate(results)
    write_markdown(aggregated)
    write_csv(aggregated)
    print(f"Wrote leaderboard to {LEADERBOARD_MD_PATH} and {LEADERBOARD_CSV_PATH}.")


if __name__ == "__main__":
    main()
