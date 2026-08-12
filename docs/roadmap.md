# Roadmap — the build queue

Ordered list of **iteration-sized units**. Each loop iteration picks the first unchecked unit,
builds it to its acceptance criteria, and ticks the box. Keep units small enough to finish,
test, and merge in one iteration. If a unit is too big, split it here and re-order.

Legend: `[ ]` todo · `[~]` in progress (PR open) · `[x]` done (merged).

---

## Phase 0 — Scaffolding & end-to-end skeleton
_Goal: one OEE task runs end-to-end from a clean clone and writes a valid result record._

- [x] **0.1 — OEE generator + numeric scorer (end-to-end).** Implement `generators/oee.py`
  (parameterized + seeded, correct-by-construction) and `scorers/numeric.py` (tolerance-based,
  absolute/relative). Wire one generated OEE task through generate → run → score → log using
  the existing `harness/run.py` skeleton and the Anthropic adapter.
  **Acceptance:** (a) `python -m harness.run --generator oee --seed 123 --model anthropic`
  produces a valid result record (validates against `schemas/result.schema.json`); (b) the
  generated task validates against `schemas/task.schema.json`; (c) `scorers/numeric.py`
  unit-tested against ≥5 hand-verified cases; (d) OEE ground truth is correct-by-construction
  (the generator computes the answer, not the model).

## Phase 1 — Family A (Computed): minimum lovable + publishable
_Build one generator+scorer unit at a time; test each scorer before moving on._

- [x] **1.1 — Numeric scorer hardening + multi-part support.** Generalize `numeric` scorer for
  multi-part answers (average parts) and relative tolerance. Robust `<answer>` parsing;
  parse-failures score 0 and are logged as a distinct category.
  **Acceptance:** unit tests cover single/multi-part, absolute/relative tolerance, and parse
  failure; parse-failure count is surfaced in results.
- [x] **1.2 — MRP explosion generator + scorer.** Net requirements from BOM + on-hand + demand
  + lead times. **Acceptance:** correct-by-construction; ≥5 hand-verified scorer tests.
- [x] **1.3 — Inventory policy generator + scorer.** EOQ, reorder point, safety stock from
  demand distribution + lead time. **Acceptance:** as above.
- [x] **1.4 — SPC generator + scorer.** Control limits, Cp/Cpk/Pp/Ppk, out-of-control-rule
  detection from a data series. **Acceptance:** as above (may add `scipy` if needed).
- [x] **1.5 — Scheduling generator + scorer.** Makespan / total tardiness for a sequence;
  optimal only for instances small enough to solve exactly. **Acceptance:** "optimal" is
  provably correct by exhaustive/exact solve; ≥5 hand-verified tests.
- [x] **1.6 — TOC / bottleneck generator + scorer.** Bottleneck identification, throughput.
- [x] **1.7 — Quality economics generator + scorer.** COPQ, scrap/rework cost, first-pass
  yield, rolled throughput yield.
- [x] **1.8 — FMEA arithmetic generator + scorer.** RPN = S×O×D, prioritization.
- [x] **1.9 — Standard-cost variance generator + scorer.** Price/usage/efficiency variances.
- [x] **1.10 — classification / checklist scorers.** Exact/set match and per-item fraction
  (report fraction + all-or-nothing). **Acceptance:** unit-tested.
- [x] **1.11 — taxonomy targets + public-set generation.** Fill `taxonomy/taxonomy.yaml`
  per-cell target counts; generate a public set (~400–600 tasks) into `data/public/`.
  **Acceptance:** counts match targets; all tasks schema-valid; regeneration is deterministic.
- [x] **1.12 — Held-out set from private seeds.** Generate `data/heldout/` from seeds kept out
  of git; instances `.gitignore`d. **Acceptance:** contamination check — no held-out instances
  tracked by git.
- [x] **1.13 — OpenAI + Google adapters.** One thin adapter each behind the `Model` interface.
- [x] **1.14 — First leaderboard.** `harness/aggregate.py` → markdown + csv with per-domain and
  per-tier breakdowns. **Acceptance:** a reproducible leaderboard exists in `results/`.

## Phase 2 — Family C (Simulated): decision & orchestration
- [x] **2.1 — Simulator engine.** Deterministic `engine.step(state, action) -> state, kpis`.
  **Acceptance:** same seed + actions → same KPIs (tested).
- [x] **2.2 — Scenario: line-down recovery** + baseline & reference policies. KPI: total
  weighted tardiness. **Acceptance:** both score bounds work.
- [x] **2.3 — Scenario: demand spike / rebalance** + baseline & reference policies. KPI:
  service level + overtime cost.
- [x] **2.4 — L4 single-decision mode + simulated scorer.** KPI-delta normalization to [0,1].
- [x] **2.5 — L5 agentic tool interface** (`simulator/tools.py`), capped turns, trajectory
  logging. **Acceptance:** models complete L4 and L5 and receive normalized scores.

## Phase 3 — Family B (Source-grounded)
- [x] **3.1 — 8D / APQP-PPAP closed-form tasks** + answer keys + free public-source citations.
- [x] **3.2 — 7/8 wastes, SMED / 5S / kanban sizing** closed-form tasks + citations.
- [ ] **3.3 — FMEA S/O/D scale reasoning** closed-form tasks + citations.
  **Acceptance (all 3):** exact/checklist grading only; every task carries `source` +
  `source_url`; no paywalled standard text reproduced anywhere.

## Phase 4 — Harness hardening & analysis
- [ ] **4.1 — Unified scaffold + robust parsing + parse-failure category (finalize).**
- [ ] **4.2 — Full aggregation:** per-family / per-tier / per-domain / hard-subset breakdowns.
- [ ] **4.3 — Failure-mode clustering** over trajectories + wrong answers → written report.

## Phase 5 — Validation
- [ ] **5.1 — Layer-1 human spot-check tooling** (`validation/spotcheck.py`): stratified sample,
  records realism + ground-truth-correctness verdicts, reports pass rate.
- [ ] **5.2 — (only if Family D built) Layer-2 judge validation** + kappa ≥ 0.7 gate.

## Phase 6 — Publish
- [ ] **6.1 — README + docs/methodology.md + docs/contamination.md + docs/positioning.md.**
- [ ] **6.2 — Package public dataset for HuggingFace + reproduction instructions.**
- [ ] **6.3 — Draft technical report.**

## Phase 7 — Living operation
- [ ] **7.1 — Refresh scripts** (new held-out seeds per cycle) + versioning policy + CONTRIBUTING.
- [ ] **7.2 — Reuse hooks** so generators/scenarios can serve as product-eval / RL environments.
