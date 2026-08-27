# State — living progress log

The autonomous loop appends here every iteration. Newest entries on top.

## Current status
- **Phase:** 3 (Family B — source-grounded closed-form tasks) — in progress.
- **Reconciled:** `3.2` (PR #48) had already merged to `main` (merge commit `b2e5d4a`) but the
  roadmap checkbox was left at `[~]` — fixed to `[x]` now.
- **Next unit:** `3.3 — FMEA S/O/D scale reasoning closed-form tasks` (Family B, source-grounded,
  completes Phase 3) — **not started**: the 2026-08-27 firing's budget guard tripped before unit
  selection (see log below).
- **Blockers:** `.loop/budget.yaml`'s `stop_date: "2026-08-10"` is 17 days in the past as of this
  firing (2026-08-27) — the loop will keep exiting without building until `stop_date` is
  extended by Renan.

## Log

### 2026-08-27 — Skipped: stop_date passed (budget guard)
- Step 1 guard checks, in order: (1) budget guard — `.loop/budget.yaml` has `stop_date:
  "2026-08-10"`, which is before today (2026-08-27), so this guard trips immediately per
  `build-loop.md` Step 1.1. No unit was selected, no issue/PR opened, no new branch work done.
- While here, reconciled stale bookkeeping left over from the last successful firing: PR #48
  (unit 3.2) is merged to `main` (`git log main` head `b2e5d4a` is the PR #48 merge commit;
  `origin/claude/zen-carson-5jtbyh` points at the same commit) but `docs/roadmap.md` still
  showed `3.2` as `[~]` — flipped to `[x]`. Confirmed no open `claude/` PR exists (`state=open`
  list is empty), so the concurrency guard has nothing to act on either.
- This note + the roadmap checkbox fix were pushed to `claude/loop-log-2026-08-27` (not `main`,
  not a unit branch) via the GitHub MCP tools, per the budget guard's own instructions.
- **Action needed from Renan:** bump `stop_date` in `.loop/budget.yaml` (and review
  `runs_by_day`) to resume the loop; unit `3.3` is queued and ready to be picked up by the next
  firing once the guard passes.

### 2026-08-10 — Unit 3.2: 7/8 wastes, SMED / 5S / kanban sizing closed-form tasks
- Reconciled stale state: `3.1` (PR #46) had already merged to `main` (verified the merge
  commit's CI run is green) but the roadmap checkbox was left at `[~]` — fixed to `[x]` now.
- Added four new Family B (source-grounded) generators, mirroring unit 3.1's classification/
  checklist pattern and reusing its already-merged scorers unchanged — no new harness plumbing
  needed:
  - **`generators/lean_waste.py`** (`LeanWasteGenerator`, domain `continuous_improvement`):
    classification over the canonical 8-waste TIMWOODS taxonomy (Transportation, Inventory,
    Motion, Waiting, Overproduction, Overprocessing, Defects, Skills). Cited to SixSigma.us's
    free TIMWOODS guide. 8 wastes x (2 standard + 2 hard) = 32 original-paraphrase scenarios.
  - **`generators/five_s.py`** (`FiveSGenerator`, domain `continuous_improvement`): classification
    over the canonical 5 phases of 5S (Sort, Set In Order, Shine, Standardize, Sustain). Cited to
    ASQ's free 5S tutorial. 5 phases x (2 standard + 2 hard) = 20 original-paraphrase activities.
  - **`generators/smed.py`** (`SmedSetupClassificationGenerator`, domain
    `methods_industrialization`): classification of a changeover step as SMED's canonical
    "Internal" (machine must be stopped) vs "External" (can be done while running). Cited to
    Lean Production's free SMED guide. 2 categories x (2 standard + 2 hard) = 8 original-
    paraphrase steps.
  - **`generators/kanban_sizing.py`** (`KanbanSizingGenerator`, domain `supply_chain_sop`): the
    one generator in this unit whose ground truth is a genuine computation rather than a fixed
    lookup — the canonical kanban-card-count formula (`ceil(daily demand x lead time x
    (1 + safety factor) / container size)`), cited to DMAIC.com's free kanban-calculation guide.
    Kept closed-form per SPEC.md's Family B rule ("multiple-choice / classification / checklist")
    by presenting the correctly-computed count alongside 3 distractors built from common
    calculation mistakes (omitting the safety factor, flooring instead of ceiling, off-by-one),
    deduplicated against each other and the correct value, and asking the model to pick the
    correct letter — reusing `scorers/classification.py` as the multiple-choice grading
    mechanism, exactly as unit 3.1 did for 8D/APQP-phase classification.
- Wired all 4 generators into `harness/run.py`'s `GENERATORS` registry (`--generator lean_waste`
  / `five_s` / `smed` / `kanban_sizing` now work end-to-end); no new scorer or prompt/parse code
  needed since all 4 use the already-merged `classification` answer-format path from unit 3.1.
- Tests: `tests/test_lean_waste.py`, `tests/test_five_s.py`, `tests/test_smed.py` (lookup-table
  internal consistency — every category has both pools populated, no scenario/activity/step text
  claimed by two categories — plus generator determinism, distinct-seeds, schema validation
  across a 60-seed x 2-difficulty sweep, ground-truth-matches-context cross-checks, and
  fixed-field checks including `source`/`source_url`); `tests/test_kanban_sizing.py` (since this
  generator computes rather than looks up its ground truth, the acceptance-relevant check is an
  *independent recomputation* of the kanban formula using a separately-written expression —
  percent-based rather than the generator's direct `1 + safety_factor` — cross-checked over 200
  seeds x 2 difficulties, plus checks that all 4 options are distinct non-negative integers, the
  ground-truth letter's option always equals the independently-verified correct count, and a
  hand-verified seed=1 case); extensions to `tests/test_harness_run.py` (end-to-end correct/wrong
  cases for all 4 new generators through the real harness, plus parse-failure cases for
  `lean_waste` (missing tag) and `kanban_sizing` (empty tag)). Full suite: **2149 passed** (was
  2098 before this unit); swept 500 seeds x 2 difficulties x all 4 new generators (4000 generated
  tasks) against `schemas/task.schema.json` — all valid. Confirmed the CLI path
  (`python -m harness.run --generator lean_waste --seed 1 --model anthropic`, and the `five_s` /
  `smed` / `kanban_sizing` counterparts) reaches the real Anthropic API call and fails only on
  the missing `ANTHROPIC_API_KEY` (not available in this sandbox), confirming correct end-to-end
  wiring short of live credentials.
- Out of scope for this unit (mirrors how unit 3.1 deferred its own generators from the taxonomy/
  public-set, and unit 3.1's own remaining roadmap item): unit 3.3 (FMEA S/O/D scale reasoning)
  is not built; these 4 new generators are not yet added to `taxonomy/taxonomy.yaml`'s targets or
  `data/public/`.

### 2026-08-09 — Unit 3.1: 8D / APQP-PPAP closed-form tasks
- Reconciled stale state: `2.5` (PR #44) had already merged to `main` (the merge commit
  `3442934` confirms CI green on the head commit) but the roadmap checkbox was left at `[~]` —
  fixed to `[x]` now. **This completes Phase 2** (all 5 units, 2.1–2.5).
- Added `generators/eight_d.py` (`EightDGenerator`): a Family B (source-grounded) classification
  generator over the canonical 8D corrective-action structure (D0-D8, cited to ASQ's free "What
  is 8D?" page). `DISCIPLINES` is the fixed, cited D0-D8 structure; `ACTIVITIES` is a hand-written
  bank of original paraphrases (2 "standard" + 2 "hard" per discipline, 36 total) of a concrete
  activity a team performs during that discipline — never a quotation from any paywalled AIAG
  text, per SPEC.md Section 4's licensing rule. `generate()` picks a discipline and one of its
  activities by seed, and asks the model to classify which of the 9 disciplines (listed in full
  in the prompt) the described activity belongs to. Ground truth is the fixed discipline label
  the activity bank was written under — a lookup, not a judgment call. `answer_format`/`scorer`:
  `classification`, reusing unit 1.10's already-merged `scorers/classification.py` unchanged.
- Added `generators/apqp_ppap.py` with two generators sharing the module (both cited to free
  sources, no paywalled AIAG manual text reproduced): `ApqpPhaseGenerator` mirrors `EightDGenerator`'s
  design over the canonical 5 APQP phases (cited to 6Sigma.us's free APQP guide) — 2 standard + 1
  hard original-paraphrase activity per phase (15 total), classification-scored.
  `PpapElementsGenerator` covers the canonical 18-element PPAP structure (cited to Quality-One
  International's free PPAP page): each of the 18 elements has an original one-line paraphrase of
  what a package including it would contain; `generate()` samples 3 (`standard`) or 5 (`hard`) of
  the 18 by seed, narrates a supplier's PPAP package containing exactly those items' contents (the
  full 18-name list is also given in the prompt as the closed set to classify against), and asks
  which canonical elements the package's contents satisfy. Ground truth is the sampled element
  names; `answer_format`/`scorer`: `checklist`, reusing unit 1.10's already-merged
  `scorers/checklist.py` unchanged. (Per that scorer's own documented recall-only semantics —
  extra, non-required items in the model's answer are not penalized — a model that names every
  one of the 18 elements regardless of the narrative would still score 1.0; this is pre-existing,
  already-merged scorer behavior from unit 1.10, not something this unit changes.)
- **Harness wiring (the acceptance criterion "every task carries `source`/`source_url`" and
  "graded by exact/checklist match" both required this, since no `classification`/`checklist`
  answer-format path existed in the harness before this unit — only `numeric` and `simulated`
  did):** added `build_classification_prompt`/`parse_classification_answer` and
  `build_checklist_prompt`/`parse_checklist_answer` to `harness/run.py`, and two new branches in
  `run()`. Classification mirrors the numeric path's single-vs-multi-part distinction via a new
  `is_multi_label_classification(task)` helper (true when `ground_truth["value"]` is a list) —
  none of this unit's own tasks are multi-label, but `scorers/classification.py` already supports
  it (for a future Family B task, e.g. unit 3.2's "which of the 7 wastes apply"), so the harness
  path supports it now too rather than needing a second retrofit later. A missing tag, an empty
  tag, or (multi-label) a tag with no items, is a parse failure for classification — there is no
  legitimate "no answer". Checklist parsing treats an explicitly empty tag differently: a
  legitimate "none of these apply" answer (parsed as `[]`, `parse_failure=False`), since a
  checklist ground truth can legitimately have nothing present — only a *missing* tag is a parse
  failure. Registered both new scorers (`classification`, `checklist`) and all three new
  generators (`eight_d`, `apqp_phase`, `ppap_elements`) in `harness/run.py`'s `SCORERS`/`GENERATORS`.
- Tests: `tests/test_eight_d.py` (the activity-bank's own internal consistency — every discipline
  has both pools populated, no activity text is claimed by two disciplines — plus generator
  determinism, distinct-seeds, schema validation across a 60-seed x 2-difficulty sweep, the
  returned ground-truth discipline always matches the activity actually shown in `context` cross-
  checked against the bank directly, the prompt lists all 9 discipline codes, and fixed-field
  checks including `source`/`source_url`), `tests/test_apqp_ppap.py` (the same bank-consistency
  and generator-behavior checks for both `ApqpPhaseGenerator` and `PpapElementsGenerator`, plus
  PPAP-specific checks: the element table has exactly 18 entries, standard/hard difficulty samples
  exactly 3/5 elements with no duplicates and always a subset of the canonical 18, and the prompt
  mentions every included element's narrative plus all 18 option names), extensions to
  `tests/test_run_parsing.py` (unit tests for all 4 new prompt/parse functions: single- and multi-
  label classification, missing/empty-tag failures, checklist's empty-tag-is-legitimate-empty-list
  distinction), and extensions to `tests/test_harness_run.py` (end-to-end: correct/wrong/missing-
  tag/empty-tag cases for `eight_d` and `apqp_phase` through the real harness, and full-credit/
  partial-credit/explicitly-empty-answer cases for `ppap_elements`). Full suite: **2098 passed**
  (was 2047 before this unit); swept 500 seeds x 2 difficulties x all 3 new generators (3000
  generated tasks) against `schemas/task.schema.json` — all valid. Confirmed the CLI path
  (`python -m harness.run --generator eight_d --seed 1 --model anthropic`, and the `apqp_phase` /
  `ppap_elements` counterparts) reaches the real Anthropic API call and fails only on the missing
  `ANTHROPIC_API_KEY` (not available in this sandbox), confirming correct end-to-end wiring short
  of live credentials.
- Out of scope for this unit (mirrors how unit 1.11 deferred Family B/C taxonomy cells until
  their generators existed, and how units 2.4/2.5 deferred their own new generators from the same
  taxonomy/public-set inclusion): these three new generators are not yet added to
  `taxonomy/taxonomy.yaml`'s targets or `data/public/`; units 3.2 (7/8 wastes, SMED/5S/kanban
  sizing) and 3.3 (FMEA S/O/D scale reasoning) are not built.

### 2026-08-08 — Unit 2.5: L5 agentic tool interface
- Reconciled stale state: `2.4` (PR #42) had already merged to `main` (the merge commit's own
  message confirms CI green on the head commit, run #48) but the roadmap checkbox was left at
  `[~]` — fixed to `[x]` now.
- Added `simulator/tools.py`: `SimulationSession`, the turn-capped state machine behind L5
  ("the agent interacts turn-by-turn through `simulator/tools.py` (query state, place actions),
  capped at N turns" — SPEC.md Section 9). Exposes exactly two operations, `get_state` (read-only
  snapshot) and `submit_action` (attempt one step of the real `simulator.engine.step`), each
  spending one turn from a fixed `max_turns` budget regardless of whether it's a query or an
  action — a model that only ever queries still eventually runs out of turns. An illegal or
  malformed `submit_action` call is rejected (an error dict, turn still spent, state unchanged)
  rather than raised — same generation≠grading stance unit 2.4 took for L4's plan replay, applied
  here to a live session instead. `TOOL_DEFINITIONS` (Anthropic tool-schema format) and `dispatch()`
  (routes a tool call by name to the session) round out the module.
- Extended `scorers/simulated.py` with `SimulatedScorer.score_state(task, final_state)`: the L5
  counterpart to unit 2.4's `score()` (which replays a submitted plan). L5 has no plan to replay
  — the session already drove every accepted action through the real engine — so this scores
  whatever final state the session actually reached (by horizon or by running out of turns)
  directly against the same `kpi_baseline`/`kpi_reference` bounds. Refactored the shared
  clip/tie-handling normalization math into `_normalize()`, used by both `score()` and
  `score_state()` so the two paths can never drift apart on how a KPI delta becomes a `[0,1]`
  score.
- Added two new generators to `generators/simulated_decision.py`: `LineDownRecoveryOrchestrationGenerator`
  and `DemandSpikeRebalanceOrchestrationGenerator` (`reasoning_tier: "L5"`, same scenarios/domains
  as unit 2.4's L4 generators, via the same `simulator.scenarios.registry`). Each task's prompt
  describes the initial situation plus the tool-based interaction (call `get_state`/`submit_action`
  up to `max_turns` times, `max_turns = 3 x horizon + 5` — enough for one `submit_action` per
  step plus slack for queries and mistakes) instead of asking for a one-shot plan. Task ids use an
  `orchestration.` prefix (vs. L4's `simulated.` prefix) so an L4 and L5 task built from the same
  scenario and seed never collide.
- Extended the `Model` interface (`harness/adapters/base.py`, docstring only, no signature
  change since `**kwargs` already covers it) to document two new optional `complete()` kwargs:
  `tool_executor` (callback for tool calls) and `max_turns` (round-trip cap). An adapter that
  doesn't implement the agentic loop must pop both and fall back to one ordinary completion
  rather than raise — a model that can't use tools is a legitimate (if poor) L5 result, not a
  harness bug. Implemented the real loop in `harness/adapters/anthropic.py`
  (`AnthropicModel._run_agentic_loop`): sends the opening prompt with `tools`, and on every
  `tool_use` block in the response, calls `tool_executor(name, input)` and feeds the JSON-encoded
  result back as a `tool_result` block in the next user turn, until a response contains no
  `tool_use` block or `max_turns` round trips are spent (a defensive ceiling on top of the
  session's own turn budget). Logs the full exchange as `trajectory`. `harness/adapters/openai.py`
  and `harness/adapters/google.py` each gained a one-line fix (`kwargs.pop("tool_executor", None)`
  / `kwargs.pop("max_turns", None)`) so passing these kwargs uniformly from the harness never
  crashes an adapter that doesn't support them yet — confirmed by hand that both now fail only on
  the missing API key, same as before this unit, rather than a `TypeError` on the new kwargs.
- Wired both orchestration generators into `harness/run.py`'s `GENERATORS` registry and added
  `run_orchestration()`: for a `reasoning_tier == "L5"` task, builds a `SimulationSession` from
  the task's ground truth, hands the model a `tool_executor` closure bound to that session, calls
  `model.complete(task["prompt"], tools=TOOL_DEFINITIONS, tool_executor=..., max_turns=...)`, and
  scores via `scorer.score_state(task, session.state)` once the model stops (or the loop/turn cap
  ends it). `parsed_answer` is `session.history` — the ordered list of actions the session
  actually applied — and `parse_failure` is always `False` for L5 (there is no `<answer>` tag to
  fail to parse; an unproductive session is a scoring outcome, exactly like unit 2.4's illegal
  plans). `python -m harness.run --generator line_down_recovery_orchestration --seed 1 --model
  anthropic` (and the `demand_spike_rebalance_orchestration` counterpart) reach the real Anthropic
  API call and fail only on the missing `ANTHROPIC_API_KEY` (not available in this sandbox).
- Tests: `tests/test_simulator_tools.py` (tool-definition shape, `get_state`/`submit_action` turn
  accounting and budget exhaustion, legal actions cross-checked directly against `engine.step`,
  illegal/malformed actions rejected without raising and without advancing state, horizon-reached
  vs. turn-cap-reached `done` semantics, a determinism check, and `dispatch()` routing including
  an unknown-tool-name rejection), extensions to `tests/test_simulated_scorer.py` (`score_state`
  hand-verified cases mirroring `score()`'s existing fixtures, plus a 60-seed x 2-difficulty x
  2-scenario sweep that drives each scenario's real baseline/reference policy through a live
  `SimulationSession` — unit 2.5's actual harness path — and confirms `score_state` reproduces the
  same 0.0/1.0 bounds unit 2.4's plan-replay sweep already established), `tests/test_simulated_orchestration_generators.py`
  (determinism, distinct-seeds, schema validation across a 60-seed x 2-difficulty x 2-generator
  sweep, correct id/family/domain/tier/answer_format/scorer fields and non-colliding ids,
  `kpi_reference <= kpi_baseline`, `max_turns >= horizon` always, context mirrors ground truth,
  and the prompt names both tools and the turn cap), `tests/test_anthropic_adapter.py` (the new
  agentic-loop control flow against a stubbed client: stops on a tool-free response, executes a
  tool call and feeds the JSON-encoded result back correctly, handles multiple tool calls in one
  turn, respects `max_turns` even against a model that never stops, and confirms `tools` alone
  without a `tool_executor` still falls back to one ordinary completion), and extensions to
  `tests/test_harness_run.py` (end-to-end: a `FakePolicyOrchestrationModel` that drives a known
  policy through `tool_executor` exactly like a real tool-calling model would scores 1.0 via the
  real harness path for both scenarios, a model that never calls any tool scores 0.0 without a
  parse failure, and the harness's score agrees with calling `score_state` directly on a
  reconstructed session). Full suite: **2047 passed** (was 1271 before this unit); swept 240
  freshly-generated orchestration tasks (60 seeds x 2 difficulties x 2 generators) against
  `schemas/task.schema.json` — all valid.
- Out of scope for this unit (mirrors unit 2.4's own scope boundaries): the two new L5 generators
  are not yet added to `taxonomy/taxonomy.yaml`'s targets or `data/public/`; OpenAI/Google
  adapters gained defensive kwarg-popping only, not a native tool-calling implementation of their
  own (documented in `harness/adapters/base.py`'s docstring as a legitimate, non-crashing
  degradation, not a bug); this completes Phase 2's roadmap text ("the L5 agentic tool
  interface") but does not add further simulator scenarios (supplier delay, quality hold cascade,
  changeover optimization), which SPEC.md Section 9 lists as later additions, not part of 2.5.

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
- Reconciled stale state: `2.2` (PR #38) had already merged to `main` (verified the merge
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

### 2026-08-04 — Unit 2.2: Scenario: line-down recovery + baseline & reference policies
- Reconciled stale state: `2.1` (PR #36) had already merged to `main` (verified the merge
  commit's CI run is green) but the roadmap checkbox was left at `[~]` — fixed to `[x]` now.
- Added `simulator/scenarios/line_down_recovery.py`: a seeded scenario generator built on top
  of unit 2.1's `engine.step` contract. `generate(seed, difficulty)` produces an initial state
  (3 machines, 5 jobs standard / 7 jobs hard, all released at t=0) with exactly one machine
  going down for a randomized window mid-shift, plus a horizon sized with a comfortable margin
  over total-work / total-capacity. `total_weighted_tardiness(final_state, horizon)` is this
  scenario's KPI: the engine's own `cumulative.weighted_tardiness` plus a same-formula
  (`weight * max(0, lateness)`) penalty for any job still unfinished when the horizon ends —
  needed because the engine itself (per its own unit-2.1 docstring) only costs tardiness at
  actual completion, so a policy that simply never finishes a job would otherwise show zero
  tardiness for it.
- Added `simulator/policies.py`, scenario-agnostic (reads only the engine's own state shape, so
  it's reusable for unit 2.3's demand-spike scenario too): `baseline_policy` is a naive, fixed
  round-robin job-to-machine queue that never reallocates work off a down machine;
  `reference_policy` is a well-known greedy heuristic (weighted-shortest-remaining-work-first,
  a WSPT variant, pairing the highest-capacity available machine with the highest-priority
  workable job each step) that adapts immediately to the down/up transition — documented as a
  heuristic, not a claimed exact optimum, per SPEC.md Section 9. `simulate_episode` is the
  generic runner that drives a policy through `engine.step` for a fixed horizon.
- **The acceptance criterion ("both score bounds work") in practice:** a pure greedy heuristic
  can occasionally underperform a naive fixed policy on a specific instance — an empirical
  sweep of 400 (seed, difficulty) scenarios found 1 case where `reference_policy` alone scored
  worse than `baseline_policy`. Since a reference bound that can fall below its own baseline
  would break KPI normalization (`score = clip((kpi_model - kpi_baseline) / (kpi_reference -
  kpi_baseline), 0, 1)`), `line_down_recovery.reference_episode()` runs both the heuristic's and
  the baseline's full episode and keeps whichever achieves the lower tardiness — provably never
  worse than the baseline bound, at the cost of occasionally tying it instead of improving on
  it. Re-swept 1000 seeds x 2 difficulties (2000 instances) after the fix: reference bound is
  never worse than baseline (0 counterexamples) and is strictly better on 1987/2000 (99.35%).
- Tests: `tests/test_policies.py` (hand-verified baseline round-robin-queue and down-machine-
  skip cases, hand-verified reference capacity-x-priority pairing case worked out by hand from
  the WSPT priority formula, down/unreleased/completed-job exclusion, no-double-booking,
  `simulate_episode` cross-checked against direct sequential `engine.step` calls plus a
  determinism check) and `tests/test_line_down_recovery.py` (generator determinism/distinct-
  seeds/invalid-difficulty, job/machine counts per difficulty, exactly-one-down-machine-within-
  horizon, all-jobs-released-at-zero, hand-verified `total_weighted_tardiness` unfinished-job
  penalty, a 500-seed x 2-difficulty sweep (1000 instances) asserting zero illegal actions and
  zero cases where reference is worse than baseline, plus a >90% strictly-better assertion so
  the bound is meaningfully non-degenerate, and an episode-level determinism check). Full suite:
  726 passed (was 705 before this unit).
- No task-schema/generator/harness wiring in this unit — per the roadmap unit's own scope
  (scenario + baseline/reference policies only; the `simulated` scorer, KPI-delta
  normalization, and L4/L5 harness modes are units 2.4/2.5), there is nothing yet for
  `harness/run.py` or `schemas/task.schema.json` to touch.

### 2026-08-03 — Unit 2.1: Simulator engine
- Reconciled stale state: `1.14` (PR #34) had already merged to `main` (verified the merge
  commit's CI run is green) but the roadmap checkbox was left at `[~]` — fixed to `[x]` now.
  **This confirms all of Phase 1 is complete.**
- Implemented `simulator/engine.py`'s core contract (`state, kpis = step(state, action)`),
  scenario-agnostic on purpose so it can serve both upcoming Phase 2 scenarios (2.2 line-down
  recovery, 2.3 demand spike) without redesign: state tracks per-job `remaining_work`/`release`/
  `due`/`weight`/`completed_at` and per-machine `capacity`/`down_until`, plus a `cumulative`
  block (`weighted_tardiness`, `overtime_cost`, `jobs_completed`, `jobs_completed_on_time`).
  Actions are a per-step `{machine_id: job_id}` assignment map plus an optional `overtime` flag
  per machine (extra capacity at `OVERTIME_MULTIPLIER`, costed at `OVERTIME_COST_PER_UNIT` per
  extra work unit). `step()` is a pure function — it deep-copies the input state rather than
  mutating it — and has no internal randomness, so determinism follows directly from having no
  hidden state; a machine's downtime window (`down_until`) is itself just a plain state field
  the engine reads, generically supporting the "machine goes down mid-shift" line-down-recovery
  scenario without the engine needing scenario-specific code. Illegal actions (unknown/down
  machine, unknown/unreleased/already-completed job, double-booking a job across two machines in
  the same step) raise `ValueError` rather than being silently ignored, since those are caller
  bugs, not simulation outcomes to score. Tardiness is only costed at the step a job actually
  completes (`weight * max(0, completed_at - due)`), matching unit 1.5's scheduling generator's
  own weighted-tardiness formula; jobs still incomplete when a scenario's horizon ends are that
  scenario's scorer's concern (built in 2.2/2.3), not this engine's, since the engine itself has
  no notion of a horizon.
- Tests: `tests/test_engine.py` — hand-verified single- and multi-step cases (on-time completion,
  late completion costing weighted tardiness, overtime boosting capacity and its cost, worked out
  by hand from the docstring's own formulas rather than re-deriving from the implementation),
  idle-machine-via-omission vs. explicit-`None` equivalence, input-state-immutability (`step()`
  never mutates its argument), a determinism check (two independent runs from freshly deep-copied
  initial states through the same 3-action sequence produce byte-identical state/KPI histories),
  a machine becoming available exactly at `down_until`, and one `ValueError` case each for
  unknown machine, unknown job, down machine, unreleased job, already-completed job, and
  double-booked job. Full suite: 705 passed (was 692 before this unit).
- No `--generator`/`--model` CLI wiring in this unit — per the roadmap unit's own scope (engine
  only; scenarios, baseline/reference policies, and the L4/L5 harness modes are 2.2–2.5), there
  is nothing yet for `harness/run.py` to invoke.

### 2026-08-03 — Unit 1.14: First leaderboard
- Reconciled stale state: `1.13` (PR #32) had already merged to `main` but the roadmap checkbox
  was left at `[~]` — fixed to `[x]` now. **This completes Phase 1** (all 14 units, 0.1 and
  1.1–1.14).
- Added `harness/aggregate.py`: reads every result record across `results/*.jsonl`, grouped by
  each record's own `model` field (not by filename, which is keyed by adapter rather than the
  specific model a config entry names). Each task's `domain`/`reasoning_tier`/`family` are
  re-derived from its `task_id`'s generator segment via `generator_metadata()` (a `seed=0`
  throwaway instance per generator, cached) rather than looked up from a stored copy — every
  generator hardcodes these fields as constants independent of seed/difficulty, so this can
  never drift from a generator's actual current definition, and doesn't depend on
  `data/public/` being present. `aggregate()` computes count/mean-score/parse-failure-rate
  overall, per domain, and per reasoning tier, for every model found. `write_markdown()` and
  `write_csv()` render the same aggregated structure two ways — a human-readable
  `results/leaderboard.md` and a machine-parseable `results/leaderboard.csv` (long format:
  one row per (breakdown, model, bucket)).
- Tests: `tests/test_aggregate.py` — `generator_of()` task-id parsing (including a rejection
  case), `generator_metadata()` hand-verified against four generators' actual hardcoded
  domain/tier fields plus a cache-identity check, hand-verified aggregation math (overall mean/
  parse-failure-rate, per-model separation, per-domain pooling across generators that share a
  cell — e.g. `mrp` + `inventory_policy` both filling `supply_chain_sop`, per-tier grouping,
  empty-input edge case), `load_results()` reading multiple jsonl files (including blank-line
  tolerance) from an isolated `tmp_path`, and markdown/csv rendering checks. All fixtures are
  synthetic and confined to `tmp_path` — no test touches the real `results/` directory. Full
  suite: 692 passed.
- **On the acceptance criterion ("a reproducible leaderboard exists in `results/`") without any
  live model credentials in this environment:** rather than leave `results/` empty (which would
  only prove the code compiles, not that the pipeline produces a real leaderboard artifact) or
  fabricate provider scores (which GOALS.md's non-negotiable rule rules out even in spirit), ran
  the actual `generate -> run -> score` pipeline for real (`harness.run.run(...)`, no mocking of
  the scoring path) against 8 hand-picked public-set tasks across 5 generators/domains, using a
  canned stand-in `Model` (no network call) under the deliberately unmistakable model name
  `SMOKE_TEST_NOT_A_REAL_MODEL`, then ran `python -m harness.aggregate` for real. This produced
  genuine `results/leaderboard.md` + `results/leaderboard.csv` files (mean score 0.625 across
  the 8 smoke-test tasks, with per-domain/per-tier breakdowns) that satisfy the acceptance
  criterion literally while being unmistakable about what they are and aren't. Added
  `results/README.md` explaining the distinction and instructing that `smoke_test.jsonl` should
  be deleted and `aggregate` re-run once a real credentialed model run exists — mirrors how
  units 0.1 and 1.13 handled the same "no credentials in this environment" limitation (confirm
  wiring reaches the real path; don't fabricate a result).

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
- No benchmark units built yet — Phase 0 (unit 0.1) is the loop's first task.
