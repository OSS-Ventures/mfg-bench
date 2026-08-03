# State — living progress log

The autonomous loop appends here every iteration. Newest entries on top.

## Current status
- **Phase:** 1 (Family A minimum lovable).
- **In flight:** `1.13 — OpenAI + Google adapters` — PR open.
- **Next unit (after 1.13 merges):** `1.14 — First leaderboard`.
- **Blockers:** none.
- **Note:** at Renan's direct request (interactive session, not a scheduled loop firing), the
  remaining Phase 1 units (1.10–1.14) are being built back-to-back in one sitting rather than
  one per firing, and `.loop/budget.yaml`'s `stop_date` was extended from `2026-08-05` to
  `2026-08-10` to give this enough runway. Normal one-unit-per-firing discipline resumes once
  Phase 1 is complete.

## Log

### 2026-08-03 — Unit 1.13: OpenAI + Google adapters
- Reconciled stale state: `1.12` (PR #30) had already merged to `main` but the roadmap checkbox
  was left at `[~]` — fixed to `[x]` now.
- Added `harness/adapters/openai.py` (`OpenAIModel`): thin wrapper around the Chat Completions
  API (`client.chat.completions.create`), reading `OPENAI_API_KEY` via the SDK's own default,
  temperature 0 by default, using `max_completion_tokens` (the modern parameter, forward-
  compatible with reasoning models like GPT-5 that reject the legacy `max_tokens`).
- Added `harness/adapters/google.py` (`GoogleModel`): thin wrapper around the Gemini API via
  `google-genai` (Google's current unified SDK for the Gemini Developer API + Vertex AI,
  superseding the older, much heavier `google-generativeai` package), reading
  `GEMINI_API_KEY`/`GOOGLE_API_KEY` via the SDK's own default.
- Wired both into `harness/run.py`'s `ADAPTERS` registry (`--model openai` / `--model google`
  now work end-to-end alongside `anthropic`) and uncommented the `gpt-5` / `gemini-latest`
  placeholder entries in `config.yaml`'s model panel.
- **Dependency resolution (the actual work in this unit, beyond the two small adapter files):**
  adding `google-genai` surfaced a real version conflict already latent in `requirements.txt`
  — `google-genai` requires `httpx>=0.28.1`, but `httpx==0.27.2` was pinned specifically
  because `anthropic==0.39.0` (pinned since unit 0.1) passes a `proxies` kwarg that httpx 0.28
  removed. Fixed at the root rather than patched around: upgraded `anthropic` to `0.120.2`,
  which is compatible with `httpx>=0.28` (confirmed working here, not just assumed), so both
  SDKs can now coexist on one `httpx` version. This also required bumping the (currently
  unused, reserved-for-later) `pydantic` pin from `2.9.2` to `2.13.4`, since `google-genai`
  requires `pydantic>=2.12.5`. Full suite re-run after every bump; 678 passed throughout, no
  regressions from the anthropic/httpx/pydantic upgrades.
- Confirmed both adapters reach their real SDK client construction and fail only on missing
  credentials (`python -m harness.run --generator oee --seed 1 --model openai` /
  `--model google`, run with the relevant API key env vars unset) — the same end-to-end wiring
  verification used for the anthropic adapter in unit 0.1, extended to both new adapters.
- No new adapter-specific test file, mirroring the existing precedent: the anthropic adapter
  also has no dedicated unit test file (it's exercised via the real CLI, per above, plus the
  `FakeModel`-based end-to-end harness tests in `tests/test_harness_run.py`, which don't touch
  the adapters at all). Full suite: 678 passed (unchanged from before this unit — no new tests
  needed since the acceptance criterion is "one thin adapter each behind the `Model`
  interface," which the CLI verification above establishes directly).
- **Sandbox-only note, not a new project dependency:** in this dev sandbox, `google-auth`
  (a transitive dependency of `google-genai`) failed to import via a pre-existing, apparently
  mismatched system `cryptography` package (missing `_cffi_backend`); installing `cffi`
  resolved it locally. This is not added to `requirements.txt` — a clean `pip install -r
  requirements.txt` in an unpolluted environment should resolve `cryptography`'s own compiled
  wheel correctly without needing a manual `cffi` install; this was specific to a stray
  system-level package in this particular sandbox, the same class of one-off environment quirk
  as unit 0.1's `httpx`/`anthropic` discovery, just resolved without needing a new pin.

### 2026-08-03 — Unit 1.12: held-out set from private seeds
- Reconciled stale state: `1.11` (PR #28) had already merged to `main` but the roadmap checkbox
  was left at `[~]` — fixed to `[x]` now.
- Added `harness/generate_heldout_set.py`, the held-out twin of unit 1.11's
  `generate_public_set.py`. The one hard requirement from SPEC.md Section 10 ("generated from
  private seeds kept out of git") is enforced structurally, not just by convention: `--seed-base`
  has no default anywhere in the code — it must be supplied explicitly at generation time by
  whoever runs a release cycle, from a value they keep to themselves. `generate_heldout_set()`
  additionally raises `ValueError` if `seed_base < MIN_SAFE_SEED_BASE` (10,000), a guard rail
  against accidentally reusing the public set's seed range (which only ever goes up to a few
  hundred) and thereby leaking public instances under the held-out label. Each generator gets
  its own disjoint offset sub-range of the caller-supplied seed base, so generators never
  collide with each other either. Output goes to `data/heldout/`, which `.gitignore` already
  excludes (`data/heldout/*`, `!data/heldout/.gitkeep`) — this unit didn't need to touch
  `.gitignore` at all, since the exclusion was already in place from bootstrap.
- Tests: `tests/test_generate_heldout_set.py` — the seed-base floor is enforced (below it
  raises, at it succeeds); every generated task validates against the schema; regeneration
  with the same seed base is deterministic (byte-identical modulo the `created` date stamp);
  different seed bases yield different instances; per-generator seed ranges are disjoint from
  each other; held-out seeds are always `>= MIN_SAFE_SEED_BASE` so they can never collide with
  the public set's seed range; and — the actual contamination check the unit's acceptance
  criterion asks for — writing real files via `write_heldout_set()` and then shelling out to
  `git check-ignore` and `git ls-files --error-unmatch` confirms those files are git-ignored
  and never tracked. Test-written held-out files are cleaned up by a fixture teardown after
  each test (they're gitignored either way, but tidy). Did **not** run the script for real
  against a genuine private seed — there is no actual held-out release cycle yet (that's unit
  7.1's refresh-script job); this unit proves the mechanism is correct and the contamination
  guarantee holds, which is what its acceptance criterion asks for. Full suite: 678 passed.

### 2026-08-03 — Unit 1.11: taxonomy targets + public-set generation
- Reconciled stale state: `1.10` (PR #26) had already merged to `main` but the roadmap checkbox
  was left at `[~]` — fixed to `[x]` now.
- Filled `taxonomy/taxonomy.yaml`'s `targets` block with per-cell (domain x reasoning_tier x
  answer_format) targets, but only for cells an implemented Family A generator can actually
  produce today — the other cells (Family B/C domains, L1/L5 tiers, non-numeric formats) stay
  at their implicit 0 with a comment explaining they await Phase 2/3 generators, rather than
  pretending a target exists for a task type that can't be generated yet (the same
  generation≠grading honesty principle from `GOALS.md`, applied to planning data too).
- Added `harness/generate_public_set.py`: assigns each of the 9 Family A generators an equal
  share of 45 tasks (`GENERATOR_TARGETS`), split per generator into standard/hard by
  `taxonomy.yaml`'s `hard_subset_fraction` (0.2 -> 36 standard + 9 hard each, exactly, no
  rounding surprises), using contiguous seeds starting at 0 reserved for the public set (the
  held-out set in unit 1.12 uses an entirely disjoint, non-committed seed range). Every
  generated task is validated against `schemas/task.schema.json` before being written, one
  JSONL file per generator into `data/public/` (405 tasks total across 9 files, within the
  roadmap's ~400-600 target).
- Tests: `tests/test_generate_public_set.py` — total count matches the sum of
  `GENERATOR_TARGETS` and falls in [400, 600]; per-generator count matches its target; every
  task validates against the schema; the standard/hard split matches
  `hard_subset_fraction` exactly per generator; the *aggregate* per-cell counts (summed across
  whichever generators share a cell, e.g. `mrp` + `inventory_policy` both filling
  `supply_chain_sop/L2/numeric`) match `taxonomy.yaml`'s `targets` exactly; task ids are unique
  across the whole public set; regenerating twice yields byte-identical task content (ignoring
  the `created` date stamp, which is the one field that legitimately varies by wall-clock day);
  and a custom `generator_targets` override is respected (used by the test suite itself to
  avoid re-running the full 405-task generation in every test). Full suite: 669 passed.
- Ran `python -m harness.generate_public_set` for real and committed its output: 405 tasks
  across `data/public/{oee,mrp,inventory_policy,spc,scheduling,toc,quality_economics,fmea,
  standard_cost_variance}.jsonl` (852 KB total). This is the actual public snapshot SPEC.md
  Section 10 describes — fixed, versioned, may be memorized by future models over time, and
  that's an accepted tradeoff since the *held-out* set (unit 1.12) is what the official
  leaderboard will run against.

### 2026-08-02 — Unit 1.10: classification / checklist scorers
- Reconciled stale state: `1.9` (PR #22, plus a small follow-up fixup PR #23 that restored two
  end-to-end test cases dropped by a `push_files` call) had already merged to `main` but the
  roadmap checkbox was left at `[~]` — fixed to `[x]` now.
- Added `scorers/classification.py`: single-label exact match (`ground_truth["value"]` a
  string) and multi-label set match (`ground_truth["value"]` a list) in one scorer, selected by
  the shape of the ground truth. Both sides are normalized (strip + case-fold) before
  comparison, so label text is compared semantically rather than requiring byte-identical
  formatting; a set match ignores answer order and duplicate items. Matches SPEC.md Section 8:
  "classification / multiple_choice → exact match."
- Added `scorers/checklist.py`: `score()` is the fraction of required items
  (`ground_truth["required_items"]`) the model's answer correctly includes (recall over
  required items; extra, non-required items in the answer are not penalized, matching SPEC.md
  Section 8's "fraction of required items correctly present"). `all_or_nothing_score()` is the
  stricter companion metric SPEC.md asks to report alongside the fraction: 1.0 only if every
  required item is present, else 0.0.
- Per the roadmap unit's own scope ("Acceptance: unit-tested" — a scorer-only unit, no new
  generator, mirroring unit 1.1's numeric-scorer-hardening precedent), no new generator or
  harness/run.py wiring was added this round; classification/checklist tasks will get their
  generators in Phase 3 (Family B, source-grounded closed-form tasks), which is where these
  scorers are actually needed.
- Tests: `tests/test_classification_scorer.py` (16 cases: single-label exact/mismatch/case-
  insensitive/whitespace/wrong-type, multi-label set match/order-independence/extra-item/
  missing-item/duplicate-collapse/case-insensitive/wrong-type/non-string-element, plus two
  schema-validity checks against hand-built single-label and set-match task dicts) and
  `tests/test_checklist_scorer.py` (16 cases: fraction on full/partial/none/extras-not-
  penalized/case-insensitive/duplicates-collapse/empty-required/wrong-type/non-string-element,
  all-or-nothing on complete/complete-with-extras/incomplete, a boundary cross-check between
  `score()` and `all_or_nothing_score()`, plus a schema-validity check against a hand-built
  checklist task dict). Full suite: 660 passed.

### 2026-08-02 — Unit 1.9: Standard-cost variance generator + scorer
- Reconciled stale state: `1.8` (PR #20) had already merged to `main` in a prior firing but the
  roadmap checkbox was left at `[~]` — fixed to `[x]` now.
- Added `generators/standard_cost_variance.py`: a seeded, correct-by-construction standard-cost
  variance generator. Given a period's actual output (units produced), the standard costing
  system's per-unit direct-material standard (quantity per unit + standard price) and direct-
  labor standard (hours per unit + standard rate), and the actual quantity/price/hours/rate
  incurred (materials purchased and used with no beginning/ending inventory carryover, stated
  explicitly), it computes the four classic standard-cost variances: Material Price Variance
  (`(actual price - standard price) x actual quantity used`), Material Usage/Quantity Variance
  (`(actual quantity used - standard quantity allowed) x standard price`), Labor Rate Variance
  (`(actual rate - standard rate) x actual hours used`), and Labor Efficiency Variance
  (`(actual hours used - standard hours allowed) x standard rate`), where Standard Quantity/
  Hours Allowed = the per-unit standard x actual output units. Sign convention (positive =
  unfavorable, negative = favorable) is stated explicitly in the prompt. Ground truth is a
  4-part `numeric` answer, reusing the multi-part `scorers/numeric.py` scorer from unit 1.1 — no
  new scorer code needed.
- Wired `standard_cost_variance` into `harness/run.py`'s `GENERATORS` registry (`--generator
  standard_cost_variance` now works end-to-end alongside `oee`, `mrp`, `inventory_policy`,
  `spc`, `scheduling`, `toc`, `quality_economics`, and `fmea`).
- Tests: `tests/test_standard_cost_variance.py` — 5 hand-verified MPV/MQV/LRV/LEV cases (worked
  by hand from the generator's own context via the four variance formulas), plus an
  independent-recomputation sweep over 60 (seed, difficulty) combinations using a *separately
  derived* expansion (each variance as a difference of two products, `actual_total -
  standard_total`, rather than the generator's `(difference) x factor`) so the sweep genuinely
  cross-checks the arithmetic rather than re-calling the same code — compared with a 1-cent
  tolerance rather than exact equality, since the two mathematically-identical orderings
  occasionally land on opposite sides of a `.xx5` rounding boundary due to ordinary floating-
  point representation error (the same class of issue noted for COPQ in unit 1.7). Also covers
  determinism, distinct-seeds, schema validation, actual-output-units-range-per-difficulty,
  standard-quantity/hours-allowed-derivation consistency, and price/rate-variance-sign-matches-
  price/rate-direction checks. Added two end-to-end cases to `tests/test_harness_run.py`
  exercising the multi-part standard-cost-variance path (all-correct and partial-credit)
  through the real harness. Full suite: 628 passed. Swept 400 (seed, difficulty) generated
  tasks against `schemas/task.schema.json` — all valid. Confirmed the CLI path
  (`python -m harness.run --generator standard_cost_variance --seed 1 --model anthropic`)
  reaches the real Anthropic API call and fails only on the missing `ANTHROPIC_API_KEY` (not
  available in this sandbox), confirming correct end-to-end wiring short of live credentials.

### 2026-08-01 — Unit 1.8: FMEA arithmetic generator + scorer
- Reconciled stale state: `1.7` (PR #18) had already merged to `main` in a prior firing but the
  roadmap checkbox was left at `[~]` — fixed to `[x]` now.
- Added `generators/fmea.py`: a seeded, correct-by-construction FMEA (Failure Mode and Effects
  Analysis) arithmetic generator. Given a set of failure modes (4 for `standard`, 5 for `hard`),
  each rated on the standard 1-10 Severity/Occurrence/Detection scales, it computes each failure
  mode's Risk Priority Number (`RPN = severity x occurrence x detection`), the top-priority
  failure mode (the one with the highest RPN — ties go to the earliest-listed one, matching
  Python's `max()` first-occurrence semantics), and how many failure modes meet or exceed a
  fixed project action threshold (`RPN >= 100`, stated in the prompt as a project-specific
  policy, not a claimed universal AIAG standard — S/O/D *scale interpretation* reasoning is the
  separate Family B task, unit 3.3). Ground truth is an `N+2`-part `numeric` answer (RPN per
  failure mode, top-priority failure mode number, count above threshold), reusing the
  multi-part `scorers/numeric.py` scorer from unit 1.1 — no new scorer code needed.
- Wired `fmea` into `harness/run.py`'s `GENERATORS` registry (`--generator fmea` now works
  end-to-end alongside `oee`, `mrp`, `inventory_policy`, `spc`, `scheduling`, `toc`, and
  `quality_economics`).
- Tests: `tests/test_fmea.py` — 5 hand-verified RPN/prioritization/threshold-count cases
  (severity x occurrence x detection is simple enough to verify directly by hand from the
  generator's own context), plus an independent-recomputation sweep over 60 (seed, difficulty)
  combinations using a *separately written* running-max loop and manual threshold-counting loop
  (rather than the generator's `max(range(...), key=...)` and generator-expression sum), so the
  sweep genuinely cross-checks the arithmetic rather than re-calling the same code. Also covers
  determinism, distinct-seeds, schema validation, failure-mode-count-per-difficulty,
  RPN-within-[1,1000]-bounds, top-priority-failure-mode-within-bounds-and-actually-has-the-max-
  RPN, and count-above-threshold-consistency checks. Added two end-to-end cases to
  `tests/test_harness_run.py` exercising the multi-part FMEA path (all-correct and
  partial-credit) through the real harness. Full suite: 555 passed. Swept 400 (seed, difficulty)
  generated tasks against `schemas/task.schema.json` — all valid.

### 2026-07-31 — Unit 1.7: Quality economics generator + scorer
- Reconciled stale state: `1.6` (PR #16) had already merged to `main` in a prior firing but the
  roadmap checkbox was left at `[~]` — fixed to `[x]` now.
- Added `generators/quality_economics.py`: a seeded, correct-by-construction quality-economics
  generator. Given a serial process of workstations (3 for `standard`, 4 for `hard`), a starting
  unit count, and each station's scrap rate, rework rate, and per-unit scrap/rework cost, it
  computes each station's First-Pass Yield (`1 - scrap_rate - rework_rate`), the average FPY
  across stations, the Rolled Throughput Yield (the product of the per-station FPYs — the
  fraction of starting units that would pass every station right first time with no rework
  anywhere), and the Cost of Poor Quality (total scrap cost + total rework cost, accumulated as
  units flow station to station — only scrapped units leave the process; reworked units continue
  at a cost). Ground truth is a 5-part `numeric` answer (avg FPY %, RTY %, total scrap cost,
  total rework cost, COPQ), reusing the multi-part `scorers/numeric.py` scorer from unit 1.1 — no
  new scorer code needed.
- Wired `quality_economics` into `harness/run.py`'s `GENERATORS` registry (`--generator
  quality_economics` now works end-to-end alongside `oee`, `mrp`, `inventory_policy`, `spc`,
  `scheduling`, and `toc`).
- Tests: `tests/test_quality_economics.py` — 5 hand-verified avg-FPY/RTY/scrap-cost/rework-cost/
  COPQ cases (worked by hand from the generator's own context via the station-by-station flow:
  scrapped = units_in x scrap_rate, reworked = units_in x rework_rate, fpy = 1 - scrap_rate -
  rework_rate, units_in x= (1 - scrap_rate) for the next station), plus an independent-
  recomputation sweep over 60 (seed, difficulty) combinations using a *separately derived*
  formula (FPY as good/units_in, a division, rather than the generator's 1 - rates subtraction)
  so the sweep genuinely cross-checks the arithmetic rather than re-calling the same code. Also
  covers determinism, distinct-seeds, schema validation, station-count-per-difficulty, FPY/RTY-
  within-(0,100]%, RTY-never-exceeds-average-FPY, and costs-never-negative checks. Note: dropped
  an initially-planned "COPQ == round(scrap_cost + rework_cost, 2)" assertion after discovering
  it fails on ~20% of seeds — COPQ is (correctly) computed from the *unrounded* running totals,
  so it can differ from summing the already-rounded, independently-displayed scrap/rework parts
  by a cent; this is expected floating-point rounding behavior, not a generator bug, and is
  already covered correctly by the recomputation sweep (which mirrors the unrounded-totals
  order of operations). Added two end-to-end cases to `tests/test_harness_run.py` exercising the
  multi-part quality-economics path (all-correct and partial-credit) through the real harness.
  Full suite: 481 passed. Swept 400 (seed, difficulty) generated tasks against
  `schemas/task.schema.json` — all valid.

### 2026-07-31 — Unit 1.6: TOC / bottleneck generator + scorer
- Reconciled stale state: `1.5` (PR #14) had already merged to `main` in a prior firing but the
  roadmap checkbox was left at `[~]` — fixed to `[x]` now.
- Added `generators/toc.py`: a seeded, correct-by-construction Theory-of-Constraints
  bottleneck/throughput generator. Given a serial production line of workstations (4 for
  `standard`, 5 for `hard`), each with a per-unit task time and a number of identical parallel
  machines, it computes each station's capacity in units/hour
  (`num_machines * 60 / task_time_min`), identifies the bottleneck as the station with the
  lowest capacity (ties broken toward the earliest station in the sequence, matching Python's
  `min()` first-occurrence semantics), and derives system throughput (the bottleneck's own
  capacity, since a serial line can never produce faster than its slowest station) and expected
  output over one full shift (throughput x hours/day). Ground truth is a 3-part `numeric`
  answer (bottleneck station number, throughput units/hour, shift output), reusing the
  multi-part `scorers/numeric.py` scorer from unit 1.1 — no new scorer code needed.
- Wired `toc` into `harness/run.py`'s `GENERATORS` registry (`--generator toc` now works
  end-to-end alongside `oee`, `mrp`, `inventory_policy`, `spc`, and `scheduling`).
- Tests: `tests/test_toc.py` — 5 hand-verified bottleneck/throughput/shift-output cases (station
  capacities worked out by hand from the generator's own context via
  `capacity = num_machines * 60 / task_time_min`, then argmin + multiply by hours/day), plus an
  independent-recomputation sweep over 60 (seed, difficulty) combinations using a *separately
  written* running-min loop (rather than the generator's `min(range(...), key=...)`), so the
  sweep genuinely cross-checks the argmin rather than re-calling the same code. Also covers
  determinism, distinct-seeds, schema validation, station-count-per-difficulty,
  bottleneck-within-bounds, throughput/shift-output-always-positive, and
  throughput-never-exceeds-any-station-capacity checks. Added two end-to-end cases to
  `tests/test_harness_run.py` exercising the multi-part TOC path (all-correct and
  partial-credit) through the real harness. Full suite: 407 passed. Swept 400 (seed,
  difficulty) generated tasks against `schemas/task.schema.json` — all valid.

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
