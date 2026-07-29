"""Bootstrap smoke tests — keep `main` green from day one.

These verify the blank-project scaffold is coherent. Real generator/scorer tests arrive with
their units (Phase 0 onward).
"""
import json
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent


def test_schemas_are_valid_json():
    for name in ("task", "result", "rubric"):
        data = json.loads((ROOT / "schemas" / f"{name}.schema.json").read_text())
        assert data["$schema"].startswith("http")


def test_config_loads():
    cfg = yaml.safe_load((ROOT / "config.yaml").read_text())
    assert cfg["harness_version"]
    assert "seed" in cfg


def test_core_docs_exist():
    for f in ("GOALS.md", "CLAUDE.md", "SPEC.md", "docs/roadmap.md", "docs/state.md",
              ".loop/build-loop.md", ".loop/budget.yaml"):
        assert (ROOT / f).exists(), f"missing {f}"


def test_base_interfaces_importable():
    from generators.base import Generator
    from scorers.base import Scorer
    from harness.adapters.base import Model, ModelResponse

    assert Generator and Scorer and Model and ModelResponse
