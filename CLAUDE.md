# CLAUDE.md — conventions for every session in this repo

This repo is built by an autonomous build loop (see `.loop/build-loop.md`). Whether you are a
loop iteration or a human-invoked session, follow these conventions.

## Read order at session start
1. `GOALS.md` — the north star (mission, scope, the non-negotiable generation≠grading rule).
2. `docs/roadmap.md` — the ordered work queue with acceptance criteria + checkboxes.
3. `docs/state.md` — the living progress log (what's done / in-flight / next).
4. `SPEC.md` — the authoritative build spec when you need detail.

## The non-negotiable rule
Generation and grading are separated. **Claude's opinion is never the source of truth.** Truth
comes from computation, a deterministic simulator, or an authoritative cited source. If a unit
of work would make a model's opinion the arbiter of the headline score, it does not ship in v1.

## Engineering conventions
- **Language:** Python 3.11+ only. No build system.
- **Data:** JSONL + JSON Schema. No database. Validate every task/result against `schemas/`.
- **Determinism:** generators and the simulator are seeded; the same seed reproduces the same
  instance. Model calls at temperature 0 where the provider allows.
- **Scorers are pure functions:** `(task, model_answer) -> float in [0, 1]`. No side effects.
- **One coherent unit per iteration.** Do not bundle unrelated changes. If a roadmap unit is
  too large for one iteration, split it and update `docs/roadmap.md`.
- **Test before commit.** Every new generator/scorer ships with unit tests against
  hand-verified cases. Run `pytest` and the schema validation locally; do not commit red.
- **Keep docs current.** Update `docs/methodology.md` ("how truth is established") as each
  family grows, and check off the roadmap unit + append to `docs/state.md` when done.

## Git & authorship convention (applies to ALL pushes, loop or human)
- **Commit author = Renan** (`renan@oss.ventures`). Set once per environment:
  `git config user.name "Renan" && git config user.email "renan@oss.ventures"`.
- Every commit message ends with a `Co-Authored-By: Claude` trailer (Claude is the secondary
  author). Result: Renan primary, Claude co-author.
- **Never push to `main` directly.** Work on a `claude/<unit-slug>` branch, open a PR that
  references the issue, and let CI gate the merge (auto-merge on green).
- Keep `main` green. If `main` CI is red, fixing it is the highest-priority unit.

## What "done" looks like for a unit
The unit's acceptance criteria in `docs/roadmap.md` are met, tests are green, schemas validate,
the roadmap checkbox is ticked, `docs/state.md` is updated, and the PR is merged.
