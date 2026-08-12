# Milestone D1/D2 A/B — 2024 d1–3, qwen2.5-coder:7b, 5 trials

Run 2026-08-11 on the `milestone-d-generation-robustness` branch (robust extraction +
token accounting). Same behaviour as the Milestone A baseline — same model, same
problems, same defaults — so the only difference from the recorded 12/30 baseline is
this branch's code. Fingerprint `a888a46ad995` (differs from the baseline's
`1b47b1586437` only because Milestone B removed inert config fields from the schema, not
because runtime behaviour changed). 81 min wall clock. Raw artifact:
`dev/experiments/20260812T032709Z_robust-extraction_a888a46ad995.json` (gitignored).

## Problem-level: essentially flat

```
config                          solved  rate  any/all of 6
baseline (1b47b1586437)         12/30   40%   4 / 0
robust-extraction (a888a46...)  13/30   43%   4 / 0
```

+1 of 30 is within run-to-run variance. Same 4 problems solvable, still 0 reliable.
**Taken alone, this looks like a null result.** It is not — the problem-level view is
hiding what changed.

## Attempt-level: the real story (and a correction to the baseline's headline)

The 30 problem-runs produced **51 model attempts** (generate + repair + fallback).
Their outcomes:

| outcome        | count | share |
|----------------|-------|-------|
| solved         | 13    | 25%   |
| wrong          | 21    | 41%   |
| error          | 16    | 31%   |
| no_candidate   | 1     | 2%    |

The baseline's headline — *"the failure mode is `no_candidate`, never `wrong`; when the
pipeline produces a parseable solution it is correct"* — was a **problem-level rollup
artifact**. A problem whose every candidate is wrong or errors still returns None from
the solver, which the runner records as `no_candidate`. So "no wrong answers" never meant
the models were right; it meant wrong candidates were rejected and rolled up under a
label that erased them.

Two of this PR's changes made the truth visible:
- **Robust extraction (D1)** now surfaces candidates that the old ```python-only extractor
  silently dropped. Only **1 of 51** attempts is `no_candidate` — extraction is no longer
  the bottleneck.
- **Token accounting (D2)** populates **51/51** attempts with real counts (208k input /
  46k output tokens total); every result JSON before this carried structural zero.

## What this means for the roadmap

**The measured bottleneck is not extraction — it is code correctness.** 41% of candidates
run and produce the wrong answer; 31% crash at runtime. That is where the leverage is now,
and it is a different problem from the one Milestone D was scoped around:

- **Runtime errors (31%)** — the repair loop exists but clearly isn't converting most
  errors into working code. A `--include-replay` run to categorise the 16 error signatures
  (I/O handling? parsing? the `solve(data)` vs file-path contract?) is the next diagnostic.
- **Wrong answers (41%)** — genuine reasoning/implementation misses. This is where
  Milestone E's self-consistency sampling and answer-based consensus should help, and now
  there is an honest attempt-level metric to A/B them against.

D1 and D2 are kept: extraction is strictly more robust (and proven not to be the
bottleneck), and token accounting is the cost half of every future A/B. But the headline
result of this run is the reframe: **stop optimising for `no_candidate`; the models
produce candidates freely, and the fight is now wrong-vs-error-vs-right.**

## Reproduce

```
venv/bin/python experiment.py --problems 2024:1-3 --trials 5 \
    --config "name=robust-extraction,models=qwen2.5-coder:7b" --include-replay
```

(`--include-replay` recommended next time — it persists code and error text so the
error/wrong split can be categorised, which this run cannot.)
