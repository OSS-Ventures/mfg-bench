# State — living progress log

The autonomous loop appends here every iteration. Newest entries on top.

## Current status
- **Phase:** 1 (Family A minimum lovable).
- **In flight:** `1.1 — Numeric scorer hardening + multi-part support` — PR open, auto-merge enabled.
- **Next unit (after 1.1 merges):** `1.2 — MRP explosion generator + scorer`.
- **Blockers:** none.

## Log

### 2026-07-29 — Unit 1.1: Numeric scorer hardening + multi-part support
- Reconciled stale state: `0.1` had already merged to `main` (PR #4) in a prior firing but the
  roadmap checkbox and this log were never flipped to `[x]` — fixed now.
- Generalized `scorers/numeric.py`: `ground_truth["parts"]` (a list of per-part
  `value`/`tolerance`/`tolerance_type` dicts) triggers multi-part scoring — `model_answer` must
  be a same-length list, and the score is the average of each part's tolerance-checked score.
  Single-part tasks (ground truth `value`/`tolerance` directly on the dict) are unchanged.
  Hardened `float()` coercion to reject `bool` (Python's `bool` is an `int` subclass, so
  `float(True) == 1.0` would otherwise silently "match" a truth of 1.0).
- Generalized `harness/run.py`'s answer parsing: added `num_parts_of(task)` (reads task
  ground truth to decide 1 vs. multi-part), extended `parse_numeric_answer` to parse
  comma-separated multi-part answers (all-or-nothing: wrong token count or any non-numeric
  token is a parse failure, scoring 0 — same as before for single-part), and extended
  `build_prompt` to instruct comma-separated multi-part answers when `num_parts > 1`.
- Tests: 20 new cases across `tests/test_numeric_scorer.py` (multi-part all/partial/none
  correct, wrong answer-count, non-list answer, non-numeric element, bool-answer rejection)
  and the new `tests/test_run_parsing.py` (single/multi-part parsing, parse failures,
  `num_parts_of`, `build_prompt` instruction text). Full suite: 43 passed.
- `parse_failure` (already in `schemas/result.schema.json`) continues to be the surfaced
  parse-failure signal per result record; multi-part parse failures set it the same way
  single-part ones always have.

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
