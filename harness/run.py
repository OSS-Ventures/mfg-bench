"""Main runner skeleton: load/generate tasks -> call model -> score -> log a result record.

Phase 0 (unit 0.1) wires the OEE generator + numeric scorer + Anthropic adapter through this.
Registries are intentionally empty here; each build unit registers its generator/scorer/adapter.
"""
from __future__ import annotations

# Populated as units land (0.1 adds "oee" / "numeric" / "anthropic").
GENERATORS: dict = {}
SCORERS: dict = {}
ADAPTERS: dict = {}


def main() -> None:
    raise NotImplementedError(
        "Runner is a Phase 0 skeleton. Unit 0.1 implements generate -> run -> score -> log."
    )


if __name__ == "__main__":
    main()
