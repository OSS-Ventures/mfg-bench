# results/

Per-model result logs (`*.jsonl`, one JSON record per task per model — see
`schemas/result.schema.json`) and the leaderboard generated from them.

## Regenerating the leaderboard

```
python -m harness.aggregate
```

Reads every `results/*.jsonl` file, groups records by their own `model` field, and writes
`results/leaderboard.md` + `results/leaderboard.csv` with overall / per-domain / per-tier
breakdowns. Safe to re-run any time after adding new result files.

## `smoke_test.jsonl`

This is a **synthetic demonstration, not a real model benchmark result.** No provider API keys
(Anthropic, OpenAI, or Google) are available in the environment this was built in, so there is
no live-model data to aggregate yet. `smoke_test.jsonl` was produced by running the real
`generate -> run -> score` pipeline (`harness.run.run(...)`) against a handful of public-set
tasks with a canned stand-in `Model` (no network call), under the model name
`SMOKE_TEST_NOT_A_REAL_MODEL` — deliberately unmistakable so it can never be read as a genuine
score. Its purpose is to prove `harness/aggregate.py` end-to-end (unit 1.14's acceptance
criterion: "a reproducible leaderboard exists in `results/`").

**Once a real model is run** (`python -m harness.run --generator <g> --seed <n> --model
<anthropic|openai|google>`, with the corresponding API key set), delete `smoke_test.jsonl` and
re-run `python -m harness.aggregate` to replace this demonstration with a genuine leaderboard.
