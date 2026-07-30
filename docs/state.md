# State — living progress log

The autonomous loop appends here every iteration. Newest entries on top.

## Current status
- **Phase:** 1 (Family A minimum lovable).
- **In flight:** `1.5 — Scheduling generator + scorer` — PR open, auto-merge enabled.
- **Next unit (after 1.5 merges):** `1.6 — TOC / bottleneck generator + scorer`.
- **Blockers:** none.

## Log

### 2026-07-30 — Unit 1.5: Scheduling generator + scorer
- Reconciled stale state: `1.4` (PR #12) had already merged to `main` in a prior firing but the
  roadmap checkbox was left at `[~]` — fixed to `[x]` now.
- Added `generators/scheduling.py`: a seeded, correct-by-construction single-machine job
  sequencing generator. Given `n` jobs (5 for `standard`, unweighted; 6 for `hard`, with a
  per-job priority weight), each with a processing time and a due date, all released at time 0
  with no preemption and no idle time, the generator computes the ground truth by exhaustively
  searching every one of the `n!` possible processing sequences (`itertools.permutations`) and
  taking the minimum total (weighted) tardiness achieved — `n` is kept small enough (120 or 720
  orderings) that the exhaustive search is exact and fast, so the reported "optimal" is provably
  correct rather than a heuristic or a model's opinion. Ground truth is a single-part `numeric`
  answer, reusing `scorers/numeric.py` — no new scorer code needed.
- Wired `scheduling` into `harness/run.py`'s `GENERATORS` registry (`--generator scheduling` now
  works end-to-end alongside `oee`, `mrp`, `inventory_policy`, and `spc`).
- Tests: `tests/test_scheduling.py` — since minimum-total-tardiness has no closed-form formula,
  "hand-verified" here means 5 small (n=3, 6-orderings-enumerable-by-hand) job instances with
  every one of the 6 orderings' completion times / tardiness / weighted tardiness worked out by
  hand in comments and checked directly against `SchedulingGenerator._total_tardiness` (the
  exact function `generate()` uses internally) — 2 unweighted, 2 weighted, 1 all-zero-tardiness
  case. The generator's actual seeded output (5/6 jobs) is then checked with an independent
  recomputation sweep over 60 (seed, difficulty) combinations using a *separately written*
  brute-force implementation (recursive DFS tracking running completion time, rather than the
  generator's `itertools.permutations` + flat list-comprehension) so the sweep genuinely
  cross-checks the search rather than re-calling the same code. Also covers determinism,
  distinct-seeds, schema validation, job-count/weight-range-per-difficulty, and
  optimal-tardiness-is-never-negative checks. Added two end-to-end cases to
  `tests/test_harness_run.py` exercising the single-part scheduling path (correct and wrong
  answer) through the real harness. Full suite: 333 passed.

### 2026-07-30 — Unit 1.4: SPC generator + scorer
- Reconciled stale state: `1.3` (PR #10) had already merged to `main` in a prior firing but the
  roadmap checkbox was left at `[~]` — fixed to `[x]` now.
- Added `generators/spc.py`: a seeded, correct-by-construction X-bar/R statistical-process-
  control generator. Given a series of subgroup measurements (subgroup size drawn from a small
  set per difficulty, 15 subgroups for `standard` / 20 for `hard`, generated from a randomized
  true mean/sigma with an occasional injected special-cause shift on the last subgroup), spec
  limits (USL/LSL), and control-chart constants (A2, d2, from a small hardcoded textbook lookup
  table `SPC_CONSTANTS` keyed by subgroup size — same approach as unit 1.3's service-level
  z-table, so no scipy dependency is needed), it computes: X-bar chart control limits (UCL,
  LCL) from the grand mean and average subgroup range; process capability (Cp, Cpk) from the
  within-subgroup sigma estimate (Rbar / d2); process performance (Pp, Ppk) from the overall
  sample standard deviation of all pooled individual measurements; and the out-of-control count
  (subgroups whose mean falls outside the X-bar limits, Western Electric Rule 1). All 7 values
  are computed directly from the generated data series by the generator itself — the model
  never supplies or influences ground truth.
- Ground truth is a 7-part `numeric` answer (UCL, LCL, Cp, Cpk, Pp, Ppk, out-of-control count),
  reusing the multi-part `scorers/numeric.py` scorer hardened in unit 1.1 — no new scorer code
  needed.
- Wired `spc` into `harness/run.py`'s `GENERATORS` registry (`--generator spc` now works
  end-to-end alongside `oee`, `mrp`, and `inventory_policy`).
- Tests: `tests/test_spc.py` — 5 hand-verified cases (control limits/Cp/Cpk/Pp/Ppk/out-of-
  control-count computed from the generator's own context via the standard X-bar/R formulas),
  plus an independent-recomputation sweep over 60 (seed, difficulty) combinations using a
  separately-written formula implementation (plain `sum()`/`len()` arithmetic rather than the
  `statistics` module the generator uses, so the sweep genuinely cross-checks the formulas
  rather than re-calling the same code), determinism, distinct-seeds, schema validation,
  control-chart-constant consistency, Cp-always-positive, and out-of-control-count-bounds
  checks. Added two end-to-end cases to `tests/test_harness_run.py` exercising the multi-part
  SPC path (all-correct and partial-credit) through the real harness. Full suite: 260 passed.

### 2026-07-29 — Unit 1.3: Inventory policy generator + scorer
- Reconciled stale state: `1.1` (PR #6) and `1.2` (PR #8) had already merged to `main` in prior
  firings but the roadmap checkboxes were left at `[~]` — fixed to `[x]` now.
- Added `generators/inventory_policy.py`: a seeded, correct-by-construction continuous-review
  (Q, R) inventory-policy generator. Given annual demand, ordering cost, unit cost (used to
  derive a holding cost via a randomized holding rate), daily demand standard deviation,
  supplier lead time, and a target cycle-service level, it computes the Economic Order
  Quantity (`sqrt(2 x D x S / H)`), Safety Stock (`z x daily_demand_stdev x sqrt(lead_time)`),
  and Reorder Point (`avg_daily_demand x lead_time + safety_stock`). The service-level z-value
  comes from a small hardcoded textbook lookup table (`SERVICE_LEVEL_Z`) rather than a
  scipy/normal-inverse-CDF call, keeping the dependency list unchanged. Ground truth is a
  3-part `numeric` answer (EOQ, Safety Stock, Reorder Point) with relative tolerance, reusing
  the multi-part `scorers/numeric.py` scorer from unit 1.1 — no new scorer code needed.
- Wired `inventory_policy` into `harness/run.py`'s `GENERATORS` registry (`--generator
  inventory_policy` now works end-to-end alongside `oee` and `mrp`).
- Tests: `tests/test_inventory_policy.py` — 5 hand-verified EOQ/Safety-Stock/Reorder-Point
  cases (worked by hand from the generator's own context via the standard (Q, R) formulas),
  plus an independent-recomputation sweep over 60 (seed, difficulty) combinations, determinism,
  distinct-seeds, schema validation, service-level/z consistency, and non-negative-value
  checks. Added two end-to-end cases to `tests/test_harness_run.py` exercising the multi-part
  inventory-policy path (all-correct and partial-credit) through the real harness. Full suite:
  187 passed.

### 2026-07-29 — Unit 1.2: MRP explosion generator + scorer
- Added `generators/mrp.py`: a single-component, 4-period MRP time-phased net-requirements
  generator (lot-for-lot, no safety stock). Given a finished-product demand schedule, a BOM
  quantity-per, beginning on-hand inventory, scheduled receipts, and a supplier lead time, it
  computes Gross Requirements (demand x qty-per), nets them period-by-period against on-hand +
  scheduled receipts (carrying any surplus forward, flooring shortfall-covered on-hand at 0),
  and derives the Planned Order Release period for period 4's receipt from the lead time
  (`NUM_PERIODS - lead_time`). Ground truth is a 5-part `numeric` answer (4 net requirements +
  1 release period), reusing the multi-part `scorers/numeric.py` scorer hardened in unit 1.1 —
  no new scorer code needed.
- Wired `mrp` into `harness/run.py`'s `GENERATORS` registry (`--generator mrp` now works
  end-to-end alongside `oee`).
- Tests: `tests/test_mrp.py` — 5 hand-verified net-requirement/release-period cases (worked by
  hand from the generator's own context: demand x qty-per gross requirements, netted against
  on-hand + scheduled receipts), plus an independent-recomputation sweep over 60 (seed,
  difficulty) combinations, determinism, distinct-seeds, schema validation, non-negative net
  requirements, and release-period-within-horizon checks. Added two end-to-end cases to
  `tests/test_harness_run.py` exercising the multi-part MRP path (all-correct and
  partial-credit) through the real harness. Full suite: 115 passed.

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
  token is a parse failure), and extended `build_prompt` to instruct comma-separated
  multi-part answers when `num_parts > 1`.
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
