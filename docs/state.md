# State — living progress log

The autonomous loop appends here every iteration. Newest entries on top.

## Current status
- **Phase:** 0 (scaffolding).
- **Next unit:** `0.1 — OEE generator + numeric scorer (end-to-end)`.
- **In flight:** none.
- **Blockers:** none.

## Log

### 2026-07-29 — Bootstrap (manual, Renan + Claude)
- Created the blank project: `GOALS.md`, `CLAUDE.md`, `docs/roadmap.md`, this file,
  `SPEC.md`, `config.yaml`, `requirements.txt`, `taxonomy/taxonomy.yaml`, the three JSON
  schemas, base interface stubs (`generators/base.py`, `scorers/base.py`,
  `harness/adapters/base.py`, `harness/run.py`, `simulator/engine.py`), CI workflow, README.
- Created the loop machinery: `.loop/build-loop.md` (per-firing prompt) and
  `.loop/budget.yaml` (self-governed spend ledger).
- No benchmark units built yet — Phase 0 (unit 0.1) is the loop's first task.
