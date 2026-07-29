# State — living progress log

The autonomous loop appends here every iteration. Newest entries on top.

## Current status
- **Phase:** 0 (scaffolding).
- **In flight:** `0.1 — OEE generator + numeric scorer (end-to-end)` — PR open, auto-merge enabled.
- **Next unit (after 0.1 merges):** `1.1 — Numeric scorer hardening + multi-part support`.
- **Blockers:** none.

## Log

### 2026-07-29 — Unit 0.1: OEE generator + numeric scorer (end-to-end)
- Added `generators/oee.py` (seeded, correct-by-construction: computes Availability x
  Performance x Quality from a synthetic shift log) and `scorers/numeric.py` (tolerance-based,
  absolute/relative, non-numeric answers score 0).
- Added `harness/adapters/anthropic.py` (thin Messages API wrapper, temperature 0) and
  `harness/validate.py` (schema validation helpers).
- Wired `harness/run.py`: `python -m harness.run --generator oee --seed <n> --model anthropic`
  now generates a task, prompts the model, parses the `<answer>` tag, scores it, validates the
  result against `schemas/result.schema.json`, and appends it to `results/anthropic.jsonl`.
- Fixed a latent dependency bug: `anthropic==0.39.0` is incompatible with `httpx>=0.28` (it
  passes a removed `proxies` kwarg); pinned `httpx==0.27.2` in `requirements.txt`.
- Tests: 24 new/updated cases across `tests/test_oee.py` (5 hand-verified OEE ground-truth
  cases, determinism, schema validity), `tests/test_numeric_scorer.py` (8 hand-verified scorer
  cases), and `tests/test_harness_run.py` (end-to-end wiring via a fake Model, no network
  needed in CI). All pass locally; schema validation passes.
- Verified the real CLI path reaches the Anthropic API call and fails only on the missing
  `ANTHROPIC_API_KEY` (not available in this sandbox or in CI) — confirms the wiring is
  correct end-to-end short of live credentials.

### 2026-07-29 — Bootstrap (manual, Renan + Claude)
- Created the blank project: `GOALS.md`, `CLAUDE.md`, `docs/roadmap.md`, this file,
  `SPEC.md`, `config.yaml`, `requirements.txt`, `taxonomy/taxonomy.yaml`, the three JSON
  schemas, base interface stubs (`generators/base.py`, `scorers/base.py`,
  `harness/adapters/base.py`, `harness/run.py`, `simulator/engine.py`), CI workflow, README.
- Created the loop machinery: `.loop/build-loop.md` (per-firing prompt) and
  `.loop/budget.yaml` (self-governed spend ledger).
- No benchmark units built yet — Phase 0 (unit 0.1) is the loop's first task.
