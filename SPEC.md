# White-Collar Operations Benchmark — Build Specification

**Working name:** `whitecollar-ops-bench` (provisional; naming is a later decision)
**Owner:** Renan / OSS Ventures
**Audience for this file:** Claude Code (this is an executable build spec, not a strategy memo)
**Version:** 0.1 (initial spec)

---

## 1. What this benchmark is, in one sentence

An open, contamination-resistant benchmark that measures how well LLMs perform the **white-collar cognitive work of manufacturing and operations** — the reasoning, planning, diagnosis, and decision-making done at a desk, explicitly excluding anything that touches a machine or the physical world.

## 2. Scope — be upfront about it

This is a deliberate, stated positioning. The benchmark is about the *office of the factory*, not the shop floor.

**In scope (white-collar operations cognition):**
- Production planning, scheduling, sequencing, line balancing, capacity/bottleneck reasoning
- Quality problem-solving: root-cause analysis, 8D, FMEA reasoning, SPC interpretation, non-conformance handling
- Continuous improvement / Lean: waste identification, OEE decomposition, kaizen/A3 structure, standard work
- Supply chain and S&OP: MRP logic, inventory policy (EOQ, safety stock, reorder point), demand/supply balancing, expediting decisions
- Methods & industrialization reasoning: routings, time studies, work-instruction logic
- Cost & performance analysis: cost of poor quality, scrap/rework economics, standard-cost variance, yield
- EHS / compliance / regulatory *interpretation* (ISO 9001, IATF 16949, APQP/PPAP structure)
- Interpretation of white-collar artifacts: MES/ERP screens, control plans, BOMs, PFMEA documents, spec sheets
- Shop-floor management *communication*: shift handover, escalation, instruction drafting

**Out of scope (the machine / physical layer — other benchmarks already cover this):**
- Robot or PLC/SCADA control, motion planning
- Raw sensor / telemetry / vibration-signal interpretation (this is FactoryBench's territory)
- Physical process control, chemistry, thermodynamics
- Computer-vision defect detection from images of physical parts
- Predictive maintenance from raw equipment signals

**The line to hold:** reading an ERP screen or a control-plan *document* is in scope (white-collar artifact work). Interpreting raw machine telemetry is out of scope (machine layer). When in doubt, ask: *"Is this something a person does at a desk with information, or something a machine/sensor produces?"* Only the former belongs here.

## 3. Why a Claude-only build is sound (read this before building anything)

The obvious risk of building a benchmark with Claude is **circularity**: if Claude invents the tasks *and* writes the "correct" answers *and* grades them, the benchmark just measures "how much does model X agree with Claude," not "how good is model X at operations." A benchmark like that has no credibility and should not be built.

This spec avoids that failure by a single, non-negotiable design rule:

> **Generation and grading are separated. Claude may generate tasks, but Claude's opinion is never the source of truth. Truth comes from computation, from a deterministic simulator, or from an authoritative external source.**

This mirrors why SWE-bench is trusted even though no human hand-wrote the answers: the *executable test suite* is the arbiter. We apply the same principle to operations. Concretely:

1. **Computation is the arbiter.** For most tasks, the correct answer is produced by a formula or algorithm (OEE math, MRP explosion, safety stock, Cp/Cpk, makespan). A Python scorer computes it. Claude generating the numbers in the problem does not give it the answer, and the scorer's correctness does not depend on any model's opinion.
2. **A simulator is the arbiter.** For decision and orchestration tasks, a small deterministic operations simulator computes the KPI outcome of the model's actions. A "good" decision is one that measurably improves the KPI versus a baseline. No opinion involved.
3. **Authoritative sources are the arbiter.** For knowledge/methodology tasks, the answer is fixed by a canonical, widely-published structure (the 8 disciplines of 8D, the APQP phases, the 7 wastes), keyed to a citation — Claude extracts and structures, it does not invent.
4. **Procedural generation kills contamination.** Tasks are generated from parameterized templates plus a random seed. This means we can produce unlimited fresh instances, so the official leaderboard can run on a held-out set that no model has ever seen.

**What we are trading away, honestly:** we are *not* doing a HealthBench-style corpus authored and validated by dozens of paid domain experts. That is the input we are giving up for speed and cost. We compensate in three ways: (a) the benchmark is overwhelmingly *verifiable-first*, which is more objective than expert rubrics anyway; (b) knowledge tasks are grounded in public authoritative structures; (c) an **optional, lightweight human spot-check** (Section 11) that Renan and a few portfolio SMEs can run raises the credibility ceiling without requiring an expert army. The one place this design is genuinely weak — open-ended judgment tasks graded by an LLM — is deferred to an optional, separately-reported family (Section 4, Family D). **v1 ships as verifiable-first with no LLM-as-judge in the headline score.**

## 4. Task families (ranked by how they get ground truth)

The soundness of the whole benchmark is this ranking. v1 headline score = Families A + B + C only.

### Family A — Computed (deterministic ground truth) — target ~55% of v1
Answer produced by a formula/algorithm. Grading is exact numeric (with tolerance), classification, or checklist. Zero judgment.

Representative task types:
- **OEE** and its decomposition (availability × performance × quality) from production logs
- **Line balancing / takt / cycle time**, station-count reasoning
- **MRP explosion**: net requirements from BOM + on-hand + demand + lead times
- **Inventory policy**: EOQ, reorder point, safety stock from demand distribution + lead time
- **SPC**: control limits, Cp/Cpk/Pp/Ppk, out-of-control-rule detection from a data series
- **Scheduling**: makespan / total tardiness for a given sequence; identify the optimal or improved sequence *(only for instances small enough to solve exactly, so the "optimal" is provably correct)*
- **Theory of Constraints**: bottleneck identification, throughput
- **Quality economics**: cost of poor quality, scrap/rework cost, first-pass yield, rolled throughput yield
- **FMEA arithmetic**: RPN = severity × occurrence × detection, prioritization
- **Standard-cost variance**: price/usage/efficiency variances

### Family B — Source-grounded (authoritative-document ground truth) — target ~20% of v1
Answer fixed by a canonical, publicly-documented structure or requirement, keyed to a citation. Kept **closed-form** (multiple-choice / classification / checklist) so grading stays objective.

Representative task types:
- Given a non-conformance scenario, which requirement/step applies (keyed to canonical structure)
- 8D: which discipline does a given action belong to
- APQP/PPAP: sequence and gate elements
- Lean: which of the 7/8 wastes is present (canonical taxonomy)
- SMED / 5S / kanban sizing rules
- FMEA severity/occurrence/detection scale reasoning

> **Licensing rule (important, do not skip):** ISO/IATF standards are copyrighted and paywalled. Do **not** reproduce standard text in tasks or answer keys. Build tasks around the *canonical structure and requirements* that are widely published in free sources, paraphrase all scenarios, and cite the free public source used. Where a task would require quoting a paywalled clause, drop it or rephrase to the commonly-documented principle. Record `source` and `source_url` for every Family B task.

### Family C — Simulated-outcome (world-model ground truth) — target ~25% of v1
The crown jewel for decision (L4) and orchestration (L5). A small **deterministic operations simulator** computes the KPI outcome of the model's chosen actions. Score = normalized KPI improvement versus a baseline policy, bounded by a reference (optimal or strong-heuristic) policy. No opinion involved. See Section 9.

### Family D — Rubric-judged (LLM-as-judge) — OPTIONAL, experimental, NOT in v1 headline
Only for genuinely open-ended outputs (write an A3, a root-cause narrative, a shift handover) where objective truth is impossible. If built, it is **reported separately** from the headline score, uses binary atomic rubric criteria derived from canonical methodology, and only ships if the judge clears the validation gate in Section 11. Recommendation: skip for v1; revisit for v2.

## 5. Task taxonomy (engineer coverage, don't leave it to chance)

Every task is tagged on three axes. Set explicit target counts per cell before generating.

**Axis 1 — Functional domain:** `production_scheduling`, `quality_problem_solving`, `continuous_improvement`, `supply_chain_sop`, `methods_industrialization`, `cost_performance`, `compliance_interpretation`, `artifact_interpretation`, `ops_communication`.

**Axis 2 — Reasoning tier** (adapted from Pearl's ladder + an orchestration level):
- **L1 Knowledge** — recall a standard, formula, definition
- **L2 Interpretation** — read data/artifact, extract the right facts
- **L3 Diagnosis** — root cause; "why is this happening"
- **L4 Decision** — choose an action under real constraints and competing objectives
- **L5 Orchestration** — agentic: interact with tools/data over multiple turns, adapt to a disruption

**Axis 3 — Answer format:** `numeric`, `classification`, `multiple_choice`, `checklist`, `structured`, `simulated`, (`open_rubric` only for Family D).

Include a **hard subset** per domain (calibrated so frontier models leave headroom) so the benchmark discriminates and does not saturate.

## 6. Repository structure (sound and simple)

```
whitecollar-ops-bench/
├── README.md                  # public-facing: what it is, scope, how to run
├── SPEC.md                    # this file
├── config.yaml                # global config: models, seeds, paths, tolerances
├── requirements.txt           # minimal deps (see Section 12)
├── taxonomy/
│   └── taxonomy.yaml           # domains, tiers, formats, per-cell target counts
├── schemas/
│   ├── task.schema.json        # task record schema (Section 7)
│   ├── result.schema.json      # per-run result schema
│   └── rubric.schema.json      # Family D only
├── generators/                 # one module per task type; parameterized + seeded
│   ├── base.py                 # Generator interface
│   ├── oee.py
│   ├── mrp.py
│   ├── inventory_policy.py
│   ├── spc.py
│   ├── scheduling.py
│   └── ...
├── scorers/                    # pure functions: (task, model_answer) -> score in [0,1]
│   ├── base.py                 # Scorer interface
│   ├── numeric.py              # tolerance-based
│   ├── classification.py       # exact / set match
│   ├── checklist.py            # per-item match + completeness
│   └── simulated.py            # KPI-delta normalization
├── simulator/                  # Family C operations simulator (pure Python)
│   ├── engine.py               # deterministic step(state, action) -> state, kpis
│   ├── scenarios/              # scenario definitions (line-down, demand spike, ...)
│   ├── policies.py             # baseline + reference policies for score bounds
│   └── tools.py                # tool interface exposed to the agent (L5)
├── data/
│   ├── public/                 # fixed public snapshot (JSONL, may be memorized — fine)
│   └── heldout/                # private seeds only; task instances are gitignored
├── harness/
│   ├── run.py                  # main runner: load tasks -> call model -> score -> log
│   ├── adapters/               # one thin adapter per model provider
│   │   ├── base.py             # Model interface: complete(prompt, tools) -> response
│   │   ├── anthropic.py
│   │   ├── openai.py
│   │   └── google.py
│   └── aggregate.py            # results -> leaderboard (markdown + csv), breakdowns
├── validation/
│   ├── spotcheck.py            # sample tasks for human review; record verdicts
│   └── judge_validation.py     # Family D only: kappa vs human labels, gate
├── results/                    # per-model result JSONL + leaderboard outputs
└── docs/
    ├── methodology.md          # how truth is established per family
    ├── contamination.md        # public vs held-out vs live-refresh policy
    └── positioning.md          # the white-collar scope statement (Section 2)
```

## 7. Data schemas (Claude Code: implement these first)

**Task record** (`data/**/*.jsonl`, one JSON object per line):

```json
{
  "id": "compute.oee.000123",
  "family": "computed",
  "domain": "continuous_improvement",
  "reasoning_tier": "L2",
  "answer_format": "numeric",
  "prompt": "A packaging line ran for a planned 480 min. Downtime was 52 min. It produced 3,900 units at an ideal rate of 10 units/min. 41 units were rejected. Report OEE as a decimal to 4 places.",
  "context": {
    "planned_time_min": 480,
    "downtime_min": 52,
    "units_produced": 3900,
    "ideal_rate_upm": 10,
    "rejects": 41
  },
  "ground_truth": { "value": 0.7594, "tolerance": 0.001, "tolerance_type": "absolute" },
  "scorer": "numeric",
  "generator": "oee",
  "seed": 123,
  "difficulty": "standard",
  "source": null,
  "source_url": null,
  "created": "2026-07-29",
  "public": true
}
```

**Result record** (`results/*.jsonl`):

```json
{
  "task_id": "compute.oee.000123",
  "model": "claude-opus-4-8",
  "harness_version": "0.1",
  "raw_response": "...",
  "parsed_answer": 0.7594,
  "score": 1.0,
  "latency_ms": 2100,
  "trajectory": null,
  "created": "2026-07-29T10:00:00Z"
}
```

**Rubric criterion** (Family D only — binary, weighted, anchored):

```json
{
  "criterion": "Identifies a systemic root cause, not a symptom",
  "axis": "diagnosis_quality",
  "weight": 3,
  "binary": true,
  "positive_anchor": "Traces to a process/standard gap (e.g., missing changeover checklist).",
  "negative_anchor": "Stops at a surface symptom (e.g., 'operator made a mistake')."
}
```

**Design rules for schemas:**
- JSONL everywhere — human-readable, diffable, git-friendly.
- Every task carries its `generator`, `seed`, and `scorer` so any instance is reproducible and re-gradable.
- Rubric criteria are **binary** (met / not met). Binary grading beats partial credit for agreement; do not use ternary or 1–5 scales.

## 8. Scoring architecture

All scorers return a float in `[0, 1]`. One scorer per `answer_format`:

- **numeric** → `1.0` if `|answer − truth| ≤ tolerance` (absolute or relative per task), else `0.0`. For multi-part numeric, average the parts.
- **classification / multiple_choice** → exact match (`1.0`/`0.0`).
- **checklist / structured** → fraction of required items correctly present; report both the fraction and an all-or-nothing variant.
- **simulated** → normalized KPI: `score = clip((kpi_model − kpi_baseline) / (kpi_reference − kpi_baseline), 0, 1)`, where `kpi_baseline` is a trivial policy and `kpi_reference` is the optimal or strong-heuristic policy. Always log raw `kpi_model` too.
- **open_rubric** (Family D) → weighted fraction of binary criteria met, via the validated judge; reported separately.

Answer parsing: require models to emit a final answer in a fixed, easily-parsed form (e.g., a `<answer>...</answer>` tag or a final JSON block). Parsing failures score `0.0` and are logged as a distinct failure category (do not silently drop them).

## 9. The operations simulator (Family C)

A small, dependency-free, **deterministic** Python engine. Given the same seed and the same action sequence, it must always produce the same KPIs.

**Core contract:**
```python
state, kpis = engine.step(state, action)   # pure, deterministic
```

**Scenario types to build (start with two, add more):**
- **Line-down recovery** — a machine goes down mid-shift; the agent reallocates orders/resources to minimize tardiness. KPI: total weighted tardiness.
- **Demand spike / rebalance** — demand jumps; the agent adjusts the plan under capacity constraints. KPI: service level + overtime cost.
- (later) **Supplier delay**, **quality hold cascade**, **changeover optimization**.

**Two evaluation modes per scenario:**
- **L4 (single decision)** — the agent sees the full situation and outputs a plan/decision once; the sim scores the outcome.
- **L5 (agentic orchestration)** — the agent interacts turn-by-turn through `simulator/tools.py` (query state, place actions), capped at N turns; the sim scores the final KPI. Log the full trajectory for failure-mode analysis.

**Score bounding (mandatory for interpretability):** every scenario must ship with a `baseline` policy (e.g., do-nothing or naive-greedy) and a `reference` policy (exact optimum where tractable, else a well-known strong heuristic, documented as such). These bound the `[0,1]` score. Without both bounds, the scenario is not ready.

## 10. Contamination policy (`docs/contamination.md`)

- **Public set** (`data/public/`) — a fixed, versioned snapshot committed to the repo. It *will* be memorized by future models over time. That is acceptable; its job is reproducibility and onboarding, not the official ranking.
- **Held-out set** (`data/heldout/`) — generated from **private seeds** kept out of git. Only the seeds' existence is tracked; instances are `.gitignore`d. The official leaderboard runs here.
- **Live refresh** — regenerate the held-out set with fresh seeds each release cycle (e.g., quarterly). Because generation is procedural, this is a script, not a re-authoring effort.
- **Provenance** — every task is date-stamped. Family B tasks additionally record `source` + `source_url`.
- This procedural-generation design is the single strongest contamination defense available and it is why the benchmark stays meaningful as models improve.

## 11. Validation protocol — the credibility gate

Two layers. The first is the only human step and it is deliberately small and optional-to-scale.

**Layer 1 — Human spot-check (optional but recommended; Renan + a few SMEs).**
`validation/spotcheck.py` draws a random stratified sample (e.g., 5–10 tasks per domain × family), presents each with its ground truth, and records two verdicts per reviewer: *is the task realistic?* and *is the ground truth correct?* Report the pass rate. A family with a low realism/correctness rate gets fixed or dropped. This can be run by Renan alone for a first pass, or spread across portfolio SMEs for a stronger claim. **The Claude-built pipeline is fully functional without this; the spot-check is what lets you publicly claim the benchmark is trustworthy, not just automated.**

**Layer 2 — Judge validation (only if Family D is built).**
`validation/judge_validation.py` compares the LLM-judge's binary decisions against a human-labeled sample using **Cohen's / weighted kappa** (chance-corrected — do not report raw exact-match agreement, which overstates reliability). Also check position/verbosity bias and cross-judge consistency. **Gate:** Family D ships only if kappa ≥ 0.7 (roughly HealthBench-level); otherwise it is dropped from the release. Because of self-preference risk when Claude judges Claude, Family D scores are always reported separately from the headline and never blended into the main ranking.

## 12. Tech stack and conventions

Chosen to be simple, reproducible, and easy to reason about (minimal moving parts):

- **Language:** Python 3.11+ only. One language, no build system.
- **Data:** JSONL + JSON Schema. No database.
- **Config:** a single `config.yaml` (models to run, seeds, tolerances, paths). Everything reproducible from config + seed.
- **Dependencies:** keep to a short list — the provider SDKs, `pydantic` (schema validation), `numpy` (numeric scorers), `pyyaml`, `scipy` only if needed for stats. No web framework, no heavy ML libs. The simulator is pure Python.
- **Model access:** each provider behind a thin adapter implementing one interface (`complete(prompt, tools=None) -> response`). Adding a model = adding one small file. This is the one abstraction worth having; keep everything else concrete.
- **Unified scaffold:** one harness, one prompt template per `answer_format`, documented in `docs/methodology.md`. Do **not** let per-model prompt tuning creep in — cross-model comparison must be apples-to-apples.
- **Reproducibility:** clean clone + `pip install -r requirements.txt` + one command must reproduce the public leaderboard. Pin versions.
- **Determinism:** generators and simulator seeded; model calls at temperature 0 where the provider allows.

## 13. Build phases (the workplan for Claude Code)

Each phase has explicit **acceptance criteria**. Do not advance until they pass. Phases 1 and 2 are the high-value core; Phase 1 alone is publishable.

### Phase 0 — Scaffolding & end-to-end skeleton
Set up the repo structure, schemas, `config.yaml`, one generator (`oee`), one scorer (`numeric`), and the harness with the Anthropic adapter. Wire a single dummy OEE task through generate → run → score → log.
**Acceptance:** one OEE task runs end-to-end from a clean clone and writes a valid result record; schema validation passes.

### Phase 1 — Family A (Computed): minimum lovable + publishable
Build 8–12 generators + scorers covering OEE, MRP, inventory policy, SPC, scheduling (small/exact-optimal only), TOC/bottleneck, quality economics, FMEA arithmetic, standard-cost variance. Generate a public set (~400–600 tasks) and a held-out set from private seeds. Add OpenAI + Google adapters. Run the frontier panel; produce the first leaderboard with per-domain and per-tier breakdowns.
**Acceptance:** (a) regenerating any generator with a new seed yields new, correct-by-construction tasks; (b) scorers are unit-tested against hand-verified cases; (c) a reproducible leaderboard exists; (d) contamination check passes (held-out instances absent from git). **This is the milestone that proves the method and produces a citable result.**

### Phase 2 — Family C (Simulated): decision & orchestration
Build the simulator engine, two scenarios (line-down recovery, demand rebalance), baseline + reference policies, the L4 single-decision mode, and the L5 agentic tool interface. Score via KPI normalization; log trajectories.
**Acceptance:** (a) simulator is deterministic (same seed + actions → same KPIs, tested); (b) every scenario has working baseline and reference bounds; (c) models can complete both L4 and L5 modes and receive normalized scores; (d) trajectories are logged for failure analysis.

### Phase 3 — Family B (Source-grounded)
Build closed-form knowledge/methodology tasks (8D, APQP/PPAP, 7 wastes, SMED/5S/kanban, FMEA scales) with answer keys + public-source citations. Enforce the licensing rule (Section 4).
**Acceptance:** (a) every task graded by exact/checklist match with no LLM judgment; (b) every task carries `source` + `source_url`; (c) no paywalled standard text reproduced anywhere.

### Phase 4 — Harness hardening & analysis
Finalize the unified scaffold, robust answer parsing (with a logged parse-failure category), the aggregation into per-family / per-tier / per-domain / hard-subset breakdowns, and a **failure-mode clustering** pass over trajectories and wrong answers (Claude summarizes recurring failure patterns).
**Acceptance:** full leaderboard with all breakdowns + a written failure-mode report ("models compute OEE reliably but collapse on L5 line-down recovery," etc.).

### Phase 5 — Validation
Run Layer-1 human spot-check tooling and record verdicts (Renan can do the first pass). If Family D was built, run Layer-2 judge validation and apply the gate.
**Acceptance:** spot-check pass rates recorded per family; any family below bar fixed or dropped; Family D either passes the kappa gate or is excluded from v1.

### Phase 6 — Publish
Write `README.md`, `docs/methodology.md`, `docs/contamination.md`, `docs/positioning.md` (the upfront white-collar scope). Package the public dataset for HuggingFace; document how third parties run the public set and how the held-out eval works. Draft the technical report.
**Acceptance:** a third party can reproduce the public leaderboard from a clean clone; docs state scope, method, and contamination policy clearly.

### Phase 7 — Living operation
Add refresh scripts (new held-out seeds per cycle), a versioning policy (v1.0 → v1.1 → v2), and a contribution guide. Add hooks so the simulator scenarios and computed generators can be reused as portfolio product-eval / RL environments (the OSS flywheel).
**Acceptance:** a single command regenerates a fresh held-out set; versioning and contribution docs exist.

## 14. Model panel (initial)

Run at least: Claude Opus 4.8 and Claude Sonnet 5, GPT-5.x, Gemini (latest), one strong open model (e.g., a DeepSeek or Qwen release), and a small/cheap model as a floor. All through the unified scaffold at temperature 0. Report cost and latency alongside score — for OSS's purposes, "good enough at low cost" is as interesting as the frontier.

## 15. Open-source & release plan

- **License:** permissive for tooling/harness (e.g., Apache-2.0); the public dataset released openly; the held-out set never published.
- **Hosting:** GitHub (code + public snapshot) and HuggingFace (dataset).
- **Leaderboard:** committed as markdown/CSV in `results/`; a submission path for external models against the held-out set (this is also what keeps the benchmark contamination-proof — others send models to you, not the other way around).
- **Narrative:** lead with the *gap*. A benchmark where frontier models score poorly on L4–L5 is more credible and more citable than one they ace. State the white-collar scope explicitly and proudly.

## 16. Risks and how this design handles them

- **Circularity (Claude grades Claude)** → truth is computation/simulation/source, not opinion; v1 has no LLM judge in the headline (Section 3).
- **Contamination** → procedural generation + private held-out seeds + live refresh (Section 10).
- **Saturation** → hard subsets, five reasoning tiers, living refresh.
- **Construct invalidity (high score ≠ real capability)** → tasks mirror real desk work; simulator ties score to real KPI outcomes; optional human spot-check certifies realism.
- **Scaffold confound** → one unified harness, no per-model prompt tuning (Section 12).
- **Looking like marketing** → open method, reproducibility, honest reporting of the gap, explicit scope.
- **Copyright on standards** → licensing rule in Section 4; cite free public sources, never reproduce paywalled text.

## 17. Immediate next actions for Claude Code

1. Create the repo skeleton and schemas (Section 6, 7).
2. Implement Phase 0 end-to-end with the OEE generator + numeric scorer + Anthropic adapter.
3. Unit-test the OEE scorer against 5 hand-verified cases.
4. Once Phase 0 passes, proceed to Phase 1 generators one at a time, testing each scorer before moving on.
5. Keep `docs/methodology.md` updated as each family is built, so the "how truth is established" story stays current.

**Guiding principle throughout:** simple, deterministic, reproducible, and truth that never depends on a model's opinion. When a design choice is unclear, prefer the option that makes the ground truth more objective and the pipeline easier to reason about.
