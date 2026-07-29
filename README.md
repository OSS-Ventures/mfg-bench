# mfg-bench

An open, MIT-licensed benchmark for the **white-collar cognitive work of manufacturing and
operations** — the reasoning, planning, diagnosis, and decision-making done at a desk
(quality management, supply chain, production planning, continuous improvement, cost analysis,
compliance interpretation), **explicitly excluding** the machine / physical layer (robot/PLC
control, raw sensor telemetry, physical process control, vision defect detection).

> **Status: bootstrapping.** The scaffold and the autonomous build loop are in place; the
> benchmark itself is built unit-by-unit from `docs/roadmap.md`. See `docs/state.md` for
> current progress.

## Why it's credible: generation ≠ grading

Claude generates tasks, but **Claude's opinion is never the source of truth.** Ground truth
comes from **computation** (a formula/algorithm), a **deterministic simulator**, or an
**authoritative cited source**. This is the same principle that makes SWE-bench trustworthy
(the test suite is the arbiter), applied to operations. See `GOALS.md` and `SPEC.md`.

## Task families (v1 headline = A + B + C)

- **A — Computed:** deterministic formula/algorithm truth (OEE, MRP, EOQ, SPC/Cpk, scheduling,
  FMEA arithmetic, cost variance…). ~55%.
- **B — Source-grounded:** canonical public structures, closed-form, cited (8D, APQP/PPAP,
  7 wastes, SMED/5S/kanban…). ~20%.
- **C — Simulated-outcome:** a deterministic ops simulator scores the KPI of the model's
  decisions/orchestration (L4/L5). ~25%.
- **D — Rubric-judged (LLM-as-judge):** optional, experimental, reported separately, gated on
  kappa ≥ 0.7. Not in the v1 headline.

## Repository map

```
GOALS.md            North star (read first).        SPEC.md    Full build spec (authority).
CLAUDE.md           Conventions for every session.  config.yaml  Global config.
docs/roadmap.md     The ordered build queue.        docs/state.md  Living progress log.
.loop/              The autonomous build loop (prompt + budget ledger).
schemas/            task / result / rubric JSON schemas.
generators/ scorers/ simulator/ harness/            The benchmark machinery (filled by the loop).
taxonomy/           Coverage plan across domain × tier × format.
data/public/        Public snapshot (may be memorized).  data/heldout/  Private-seed set (gitignored).
```

## How it's built: the autonomous loop

A Routine fires every 4 hours (fresh session). Each firing reads `GOALS.md` + the roadmap,
checks its self-governed budget (`.loop/budget.yaml`), advances **one coherent unit**, opens a
documented issue + PR, and auto-merges on green CI. The repo *is* the state; the loop is
stateless. Full contract: `.loop/build-loop.md`.

## Running (once Phase 0 lands)

```bash
pip install -r requirements.txt
pytest -q
# python -m harness.run --generator oee --seed 123 --model anthropic   # after unit 0.1
```

## License

MIT — see `LICENSE`.
