"""Schema validation helpers, shared by the runner and by tests."""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

import jsonschema

ROOT = Path(__file__).resolve().parent.parent
SCHEMAS_DIR = ROOT / "schemas"


@lru_cache(maxsize=None)
def _load_schema(name: str) -> dict:
    return json.loads((SCHEMAS_DIR / f"{name}.schema.json").read_text())


def validate_task(task: dict[str, Any]) -> None:
    jsonschema.validate(instance=task, schema=_load_schema("task"))


def validate_result(result: dict[str, Any]) -> None:
    jsonschema.validate(instance=result, schema=_load_schema("result"))
