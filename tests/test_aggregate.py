"""Leaderboard aggregation tests: generator metadata lookup, hand-verified aggregation math,
markdown/csv rendering, and jsonl loading -- all against synthetic fixtures (never the real
`results/` directory, so tests never leave demo data behind)."""
import csv
import json

import pytest

from harness.aggregate import (
    aggregate,
    generator_metadata,
    generator_of,
    load_results,
    write_csv,
    write_markdown,
)


def _result(task_id, model, score, parse_failure=False):
    return {
        "task_id": task_id,
        "model": model,
        "harness_version": "0.1",
        "raw_response": "...",
        "score": score,
        "parse_failure": parse_failure,
        "created": "2026-08-03T00:00:00Z",
    }


def test_generator_of_parses_task_id():
    assert generator_of("compute.oee.000123") == "oee"
    assert generator_of("compute.standard_cost_variance.000001") == "standard_cost_variance"


def test_generator_of_rejects_unparseable_id():
    with pytest.raises(ValueError):
        generator_of("not-a-valid-task-id")


def test_generator_metadata_matches_known_generator_cells():
    # Hand-verified against each generator's own hardcoded domain/reasoning_tier (see
    # generators/*.py) -- these are fixed constants, independent of seed/difficulty.
    assert generator_metadata("oee") == {
        "domain": "continuous_improvement",
        "reasoning_tier": "L2",
        "family": "computed",
    }
    assert generator_metadata("mrp") == {
        "domain": "supply_chain_sop",
        "reasoning_tier": "L2",
        "family": "computed",
    }
    assert generator_metadata("fmea") == {
        "domain": "quality_problem_solving",
        "reasoning_tier": "L3",
        "family": "computed",
    }
    assert generator_metadata("scheduling") == {
        "domain": "production_scheduling",
        "reasoning_tier": "L4",
        "family": "computed",
    }


def test_generator_metadata_is_cached_across_calls():
    a = generator_metadata("toc")
    b = generator_metadata("toc")
    assert a is b  # same cached dict instance, not regenerated


def test_aggregate_overall_mean_score_hand_verified():
    # 3 oee results at scores 1.0, 0.5, 0.0 -> mean 0.5.
    results = [
        _result("compute.oee.000001", "model-a", 1.0),
        _result("compute.oee.000002", "model-a", 0.5),
        _result("compute.oee.000003", "model-a", 0.0),
    ]
    aggregated = aggregate(results)
    assert aggregated["overall"]["model-a"] == {
        "count": 3,
        "mean_score": 0.5,
        "parse_failure_rate": 0.0,
    }


def test_aggregate_separates_models():
    results = [
        _result("compute.oee.000001", "model-a", 1.0),
        _result("compute.oee.000002", "model-b", 0.0),
    ]
    aggregated = aggregate(results)
    assert aggregated["overall"]["model-a"]["mean_score"] == 1.0
    assert aggregated["overall"]["model-b"]["mean_score"] == 0.0


def test_aggregate_parse_failure_rate_hand_verified():
    # 4 results, 1 parse failure -> rate 0.25.
    results = [
        _result("compute.oee.000001", "model-a", 1.0, parse_failure=False),
        _result("compute.oee.000002", "model-a", 1.0, parse_failure=False),
        _result("compute.oee.000003", "model-a", 1.0, parse_failure=False),
        _result("compute.oee.000004", "model-a", 0.0, parse_failure=True),
    ]
    aggregated = aggregate(results)
    assert aggregated["overall"]["model-a"]["parse_failure_rate"] == 0.25


def test_aggregate_by_domain_groups_generators_sharing_a_cell():
    # mrp and inventory_policy both fill supply_chain_sop/L2 -- their scores should pool into
    # one domain bucket for the same model.
    results = [
        _result("compute.mrp.000001", "model-a", 1.0),
        _result("compute.inventory_policy.000001", "model-a", 0.0),
        _result("compute.oee.000001", "model-a", 1.0),
    ]
    aggregated = aggregate(results)
    by_domain = aggregated["by_domain"]["model-a"]
    assert by_domain["supply_chain_sop"] == {
        "count": 2,
        "mean_score": 0.5,
        "parse_failure_rate": 0.0,
    }
    assert by_domain["continuous_improvement"] == {
        "count": 1,
        "mean_score": 1.0,
        "parse_failure_rate": 0.0,
    }


def test_aggregate_by_tier_hand_verified():
    results = [
        _result("compute.toc.000001", "model-a", 1.0),  # production_scheduling / L3
        _result("compute.fmea.000001", "model-a", 0.0),  # quality_problem_solving / L3
        _result("compute.scheduling.000001", "model-a", 0.5),  # production_scheduling / L4
    ]
    aggregated = aggregate(results)
    by_tier = aggregated["by_tier"]["model-a"]
    assert by_tier["L3"] == {"count": 2, "mean_score": 0.5, "parse_failure_rate": 0.0}
    assert by_tier["L4"] == {"count": 1, "mean_score": 0.5, "parse_failure_rate": 0.0}


def test_aggregate_empty_results_yields_empty_aggregation():
    assert aggregate([]) == {"overall": {}, "by_domain": {}, "by_tier": {}}


def test_load_results_reads_all_jsonl_files_in_directory(tmp_path):
    (tmp_path / "anthropic.jsonl").write_text(
        json.dumps(_result("compute.oee.000001", "claude-opus-4-8", 1.0)) + "\n"
    )
    (tmp_path / "openai.jsonl").write_text(
        json.dumps(_result("compute.mrp.000001", "gpt-5", 0.0)) + "\n\n"  # trailing blank line
    )

    results = load_results(tmp_path)
    assert len(results) == 2
    assert {r["model"] for r in results} == {"claude-opus-4-8", "gpt-5"}


def test_load_results_on_empty_directory_returns_empty_list(tmp_path):
    assert load_results(tmp_path) == []


def test_write_markdown_renders_overall_and_breakdown_sections(tmp_path):
    results = [
        _result("compute.oee.000001", "model-a", 1.0),
        _result("compute.mrp.000001", "model-a", 0.0),
    ]
    aggregated = aggregate(results)
    out_path = tmp_path / "leaderboard.md"
    write_markdown(aggregated, out_path)

    text = out_path.read_text()
    assert "# Leaderboard" in text
    assert "## Overall" in text
    assert "## Per-domain" in text
    assert "## Per-tier" in text
    assert "model-a" in text
    assert "continuous_improvement" in text
    assert "supply_chain_sop" in text
    assert "L2" in text


def test_write_csv_renders_all_breakdown_rows(tmp_path):
    results = [
        _result("compute.oee.000001", "model-a", 1.0),
        _result("compute.mrp.000001", "model-a", 0.0),
    ]
    aggregated = aggregate(results)
    out_path = tmp_path / "leaderboard.csv"
    write_csv(aggregated, out_path)

    with out_path.open() as f:
        rows = list(csv.DictReader(f))

    assert rows[0].keys() == {
        "breakdown",
        "model",
        "bucket",
        "count",
        "mean_score",
        "parse_failure_rate",
    }
    breakdowns = {row["breakdown"] for row in rows}
    assert breakdowns == {"overall", "domain", "tier"}

    overall_row = next(r for r in rows if r["breakdown"] == "overall")
    assert overall_row["model"] == "model-a"
    assert overall_row["count"] == "2"
    assert overall_row["mean_score"] == "0.5"
