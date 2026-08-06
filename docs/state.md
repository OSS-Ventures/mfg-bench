# State — living progress log

The autonomous loop appends here every iteration. Newest entries on top.

## Current status
- **Phase:** 2 (Family C — simulated decision & orchestration) — in progress.
- **Reconciled:** `2.3` (PR #40) had already merged to `main` (CI green on the merge commit)
  but the roadmap checkbox was left at `[~]` — fixed to `[x]` now.
- **In flight:** `2.4 — L4 single-decision mode + simulated scorer` — PR #42 open, all 1271
  tests green locally and via schema validation, but the `github-actions` check-suite never got
  created on the PR's head commit (confirmed via the GitHub API: only the unrelated `claude` app
  check-suite exists, no `github-actions` one at all — a trigger anomaly, not a red run). Pushed
  this doc update as a fresh commit to see if a new push event gets CI to fire.
- **Next unit (after 2.4 merges):** `2.5 — L5 agentic tool interface` (Phase 2, Family C).
- **Blockers:** PR #42's CI has not started (see above) — do not merge until a real
  `github-actions` run completes green on its head commit.

## Log

### 2026-08-06 — Unit 2.4: L4 single-decision mode + simulated scorer
- Reconciled stale state: `2.3` (PR #40) had already merged to `main` (verified the merge
  commit's CI run is green) but the roadmap checkbox was left at `[~]` — fixed to `[x]` now.
- Added `simulator/scenarios/registry.py`: a small `SCENARIOS` dict mapping each scenario name
  (`line_down_recovery`, `demand_spike_rebalance`) to its `generate`/`baseline_episode`/
  `reference_episode` functions plus a `kpi(final_state, horizon) -> float` lambda that
  normalizes the two scenario modules' differently-shaped KPI functions
  (`line_down_recovery.total_weighted_tardiness(final_state, horizon)` vs.
  `demand_spike_rebalance.total_cost(final_state)`) into one uniform signature — lets consuming
  code (this unit's generators/scorer, and unit 2.5's L5 mode later) work with any scenario by
  name without scenario-specific branching, and without touching units 2.2/2.3's already-merged
  scenario modules.
- Added `scorers/simulated.py` (`SimulatedScorer`): implements SPEC.md Section 8's KPI-delta
  normalization, `score = clip((kpi_model - kpi_baseline) / (kpi_reference - kpi_baseline), 0,
  1)`. `model_answer` is the model's one-shot L4 plan — a list of exactly `horizon` per-step
  `{"assignments": ..., "overtime": ...}` action dicts — replayed from `ground_truth
  ["initial_state"]` through the *real* `simulator.engine.step` to get the model's own KPI
  (never a model's opinion, per `GOALS.md`). A structurally invalid plan, or one containing an
  action the engine itself rejects (unknown/down machine, unreleased/completed/double-booked
  job), scores 0.0 rather than raising — an illegal decision from a fallible model is a scoring
  outcome, not a caller bug (contrast with `engine.step`'s own docstring, which treats an illegal
  action from a trusted *policy* as a bug to raise on). The degenerate case where a scenario's
  `reference_episode` ties its own baseline (`kpi_reference == kpi_baseline`, possible via
  units 2.2/2.3's own fallback-to-baseline safety net) is handled explicitly rather than dividing
  by zero: score 1.0 only if the model's plan reproduces that exact tied KPI, else 0.0.
- Added `generators/simulated_decision.py`: `LineDownRecoveryDecisionGenerator` (domain
  `production_scheduling`) and `DemandSpikeRebalanceDecisionGenerator` (domain
  `supply_chain_sop`, matching SPEC.md's "demand/supply balancing" framing of that domain),
  both `family: "simulated"` / `reasoning_tier: "L4"` / `answer_format: "simulated"`. Each wraps
  its scenario (via the new registry) into a task whose prompt describes the full initial
  situation in plain text (every machine's capacity and any down window, every job's remaining
  work/release/due/weight, the step mechanics including overtime) and asks for one complete
  action plan up front — SPEC.md Section 9's "the agent sees the full situation and outputs a
  plan/decision once" — and whose `ground_truth` carries the scenario name, initial state,
  horizon, and the `kpi_baseline`/`kpi_reference` bounds computed directly from that scenario's
  own (already-tested) `baseline_episode`/`reference_episode` — the generator never invents or
  guesses these numbers, it only calls the existing, already-verified scenario functions.
- Wired both generators into `harness/run.py`'s `GENERATORS` registry and `SimulatedScorer` into
  `SCORERS`; `run()` now branches on `task["answer_format"]`: `"simulated"` tasks get a new
  `build_simulated_prompt` (asks for a JSON list of exactly `horizon` action objects inside the
  `<answer>` tag) and `parse_simulated_answer` (a missing tag or non-JSON-list content is a
  parse failure — `0.0` and logged, per SPEC.md Section 8 — while a well-formed-but-illegal plan
  is left to the scorer, since that's a scoring outcome, not a parse failure); every other
  `answer_format` keeps the existing numeric path unchanged. `python -m harness.run --generator
  line_down_recovery_decision --seed 1 --model anthropic` (and the `demand_spike_rebalance_decision`
  counterpart) now work end-to-end alongside the 9 Family A generators.
- Tests: `tests/test_simulated_scorer.py` (hand-verified single-machine/single-job cases worked
  out by hand — a plan matching the reference bound scores 1.0, matching the baseline bound
  scores 0.0, a partial plan midway between the bounds scores exactly 0.5, a plan that wastes
  overtime cost it doesn't need scores 0.0 via the `max(0.0, ...)` clip rather than going
  negative, the tied-bounds degenerate case scores 1.0 only on an exact match, and a parametrized
  sweep of structurally-invalid plans (wrong type/length, non-dict steps/assignments/overtime)
  and engine-rejected plans (unknown job, unknown machine, re-assigning a completed job) all
  score 0.0 without raising; a 60-seed x 2-difficulty x 2-scenario integration sweep reconstructs
  each real scenario's actual baseline/reference action sequence and confirms it reproduces
  exactly the 0.0/1.0 bound, skipping seeds where a scenario's own fallback makes the bound
  degenerate), `tests/test_simulated_decision_generators.py` (determinism, distinct-seeds, schema
  validation across a 60-seed x 2-difficulty x 2-generator sweep, correct id/family/domain/tier/
  answer_format/scorer fields, `kpi_reference <= kpi_baseline` always holds, context mirrors the
  initial state, and the prompt mentions every machine and job id), plus additions to
  `tests/test_run_parsing.py` (simulated prompt/parse unit tests) and `tests/test_harness_run.py`
  (end-to-end: a reference-policy plan and a demand-spike reference-with-overtime plan each run
  through the real harness and agree with calling the scorer directly, a missing-tag response is
  a parse failure, and a valid-JSON-but-wrong-length plan scores 0 without raising). Full suite:
  1271 passed (was 748 before this unit).
- Confirmed the CLI path (`python -m harness.run --generator line_down_recovery_decision --seed 1
  --model anthropic`, and the demand-spike counterpart) reaches the real Anthropic API call and
  fails only on the missing `ANTHROPIC_API_KEY` (not available in this sandbox), confirming
  correct end-to-end wiring short of live credentials. Also swept 60 seeds x 2 difficulties x 2
  generators of real generated tasks against `schemas/task.schema.json` — all valid.
- Out of scope for this unit (per its own roadmap text and the issue's scope boundaries): the L5
  agentic tool interface (`simulator/tools.py`, trajectory logging) is unit 2.5; new scenarios
  (supplier delay, quality hold cascade, changeover optimization) are not built; these two new
  L4 generators are not yet added to `taxonomy/taxonomy.yaml`'s targets or `data/public/` —
  Family C's public-set inclusion is left for a later unit, mirroring how unit 1.11 deferred
  Family B/C taxonomy cells until their generators existed.

### 2026-08-05 — Unit 2.3: Scenario: demand spike / rebalance + baseline & reference policies
- Reconciled stale state: `2.3` (PR #40) had already merged to `main` (verified the merge
  commit's CI run is green) but the roadmap checkbox was left at `[~]` — fixed to `[x]` now.
- Added `simulator/scenarios/demand_spike_rebalance.py`: a seeded scenario generator built on
  `engine.step`'s contract, same as unit 2.2. `generate(seed, difficulty)` produces an initial
  state with a base demand load released at t=0 (generous due-date slack) plus a batch of urgent
  spike jobs released at a randomized mid-shift step (tight due-date slack) — no machine ever
  starts down (unlike line-down recovery, the pressure here is demand volume, not machine
  availability). `total_cost(final_state)` is this scenario's KPI: actual overtime cost incurred
  plus a flat, weight-scaled penalty for every job not completed on time — a hit/miss
  "missed-the-order" framing (service level), deliberately different from unit 2.2's
  lateness-proportional `total_weighted_tardiness`. `service_level(final_state)` reports the
  weighted fraction of demand fulfilled on time as a separate, human-readable readout alongside
  the combined cost scalar.
- Added `_reference_policy_with_overtime` in the scenario module (kept scenario-specific rather
  than added to `simulator/policies.py`, since the overtime decision is this scenario's whole
  point, unlike line-down recovery where neither policy ever needed overtime): layers a targeted
  overtime rule on top of `policies.reference_policy`'s scenario-agnostic WSPT-style assignment —
  a machine goes into overtime only when normal capacity can't make the assigned job's due date
  but overtime capacity, sustained for the remaining time, would; a job already too far behind to
  make its due date even with overtime is left at normal capacity (paying overtime there buys no
  service-level benefit, only wasted cost). `reference_episode` keeps the same
  never-worse-than-baseline safety net unit 2.2 established: it falls back to
  `baseline_episode`'s own trajectory whenever the heuristic's `total_cost` would otherwise come
  out worse. Empirically this fallback is exercised more often here than in line-down recovery
  (raw heuristic underperforms baseline on ~6% of a 2000-instance seed x difficulty sweep, vs.
  line-down's ~0.05%) — overtime is a genuine two-sided bet (it can be spent on a job that ends
  up late anyway), so a heuristic that sometimes loses that bet is expected; the fallback is what
  makes the bound provably sound regardless.
- Verified empirically (not just asserted) that the scenario is actually capacity-constrained:
  across the same 2000-instance sweep, `baseline_policy` (which never uses overtime) averages
  ~47% weighted service level, `reference_episode` averages ~70% — a real, non-trivial
  improvement, not a scenario where either bound trivially hits 100%.
- Tests: `tests/test_demand_spike_rebalance.py` — generator determinism/distinct-seeds/invalid-
  difficulty, job/machine counts per difficulty, base-jobs-at-zero vs. spike-jobs-mid-shift
  release timing, no-machine-starts-down, hand-verified `service_level` and `total_cost` cases,
  hand-verified `_reference_policy_with_overtime` decision cases (triggers when worthwhile, skips
  when normal capacity already suffices, skips when hopeless even with overtime, skips when
  already overdue), a 500-seed x 2-difficulty sweep (1000 instances, 2000 (seed, difficulty)
  combinations) asserting zero illegal actions, zero cases where reference is worse than
  baseline, a >80% strictly-better assertion, the capacity-pressure and service-level-improvement
  checks above, and an episode-level determinism check. Full suite: 748 passed (was 726 before
  this unit).
- No task-schema/generator/harness wiring in this unit — per the roadmap unit's own scope
  (scenario + baseline/reference policies only; the `simulated` scorer, KPI-delta normalization,
  and L4/L5 harness modes are units 2.4/2.5), there is nothing yet for `harness/run.py` or
  `schemas/task.schema.json` to touch — same scoping note as unit 2.2.

### 2026-08-05 — Unit 2.3: Scenario: demand spike / rebalance + baseline & reference policies

### 2026-08-05 — Unit 2.3: Scenario: demand spike / rebalance + baseline & reference policies

### 2026-08-05 — Unit 2.3: Scenario: demand spike / rebalance + baseline & reference policies

### 2026-08-05 — Unit 2.3: Scenario: demand spike / rebalance + baseline & reference policies