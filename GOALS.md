# GOALS — mfg-bench

> **Read this first, every iteration.** This is the north star. When a design choice is
> unclear, prefer the option that makes ground truth more objective and the pipeline easier
> to reason about.

## Mission (one sentence)

An open, MIT-licensed, contamination-resistant benchmark that measures how well LLMs perform
the **white-collar cognitive work of manufacturing and operations** — planning, diagnosis,
and decision-making done at a desk — explicitly excluding anything that touches a machine or
the physical world.

## Scope — hold this line

**In scope** (white-collar operations cognition): production planning & scheduling, quality
problem-solving (RCA/8D/FMEA/SPC), continuous improvement / Lean (OEE, waste, A3), supply
chain & S&OP (MRP, inventory policy), methods & industrialization, cost & performance
analysis, compliance *interpretation* (ISO 9001, IATF 16949, APQP/PPAP), interpretation of
white-collar artifacts (ERP/MES screens, control plans, BOMs, PFMEA docs), shop-floor
management *communication*.

**Out of scope** (the machine / physical layer): robot/PLC/SCADA control, motion planning,
raw sensor/telemetry/vibration interpretation, physical process control, chemistry/
thermodynamics, computer-vision defect detection, predictive maintenance from raw signals.

**The test when in doubt:** *"Is this something a person does at a desk with information, or
something a machine/sensor produces?"* Only the former belongs here.

## The one non-negotiable design rule

> **Generation and grading are separated. Claude may generate tasks, but Claude's opinion is
> never the source of truth. Truth comes from computation, from a deterministic simulator, or
> from an authoritative external source.**

This is what keeps the benchmark from being circular ("how much does model X agree with
Claude"). It is the reason the project is credible. Never violate it.

## Task families, ranked by how they get ground truth

The soundness of the whole benchmark is this ranking. **v1 headline score = Families A + B + C only.**

- **Family A — Computed** (deterministic formula/algorithm truth). Target ~55% of v1.
  Exact numeric (with tolerance), classification, or checklist grading. Zero judgment.
- **Family B — Source-grounded** (canonical public structure, keyed to a citation). Target ~20%.
  Kept closed-form (multiple-choice / classification / checklist). Never reproduce paywalled
  standard text; paraphrase and cite a free public `source` + `source_url`.
- **Family C — Simulated-outcome** (deterministic operations simulator computes the KPI of the
  model's actions). Target ~25%. Score = normalized KPI improvement vs a baseline, bounded by
  a reference policy. The crown jewel for L4 (decision) and L5 (orchestration).
- **Family D — Rubric-judged (LLM-as-judge)** — OPTIONAL, experimental, **NOT in v1 headline**.
  Reported separately if built, and only if it clears the kappa ≥ 0.7 validation gate.

## Task taxonomy (three axes — engineer coverage, don't leave it to chance)

- **Domain:** production_scheduling, quality_problem_solving, continuous_improvement,
  supply_chain_sop, methods_industrialization, cost_performance, compliance_interpretation,
  artifact_interpretation, ops_communication.
- **Reasoning tier:** L1 Knowledge, L2 Interpretation, L3 Diagnosis, L4 Decision,
  L5 Orchestration.
- **Answer format:** numeric, classification, multiple_choice, checklist, structured,
  simulated, (open_rubric — Family D only).

Include a **hard subset** per domain so frontier models leave headroom and the benchmark does
not saturate.

## Definition of done for v1

1. Families A + B + C implemented, each generator/scorer unit-tested against hand-verified cases.
2. A reproducible leaderboard (public set) buildable from a clean clone + one command.
3. Held-out set generated from private seeds, instances gitignored (contamination defense).
4. Per-family / per-tier / per-domain / hard-subset breakdowns + a written failure-mode report.
5. Human spot-check tooling run (Layer 1); realism/correctness pass rates recorded per family.
6. Public docs: README, methodology, contamination policy, positioning (the scope statement).

## Guardrails that never change

- **Simple, deterministic, reproducible.** Python 3.11+, JSONL + JSON Schema, one `config.yaml`,
  seeded generators/simulator, temperature 0 where the provider allows. No database, no web
  framework, no heavy ML libs.
- **One unified harness, no per-model prompt tuning.** Cross-model comparison must be
  apples-to-apples.
- **Every task is reproducible:** it carries its `generator`, `seed`, and `scorer`.
- **Licensing:** MIT. Never commit paywalled standard text. Family B tasks cite free public sources.
- **Contamination:** public set may be memorized (fine); the held-out set is never published.

_Full detail lives in `SPEC.md`. This file is the summary the loop reads first; `SPEC.md` is
the authority when they disagree, except where this file states a project decision (MIT license,
repo name `mfg-bench`)._
