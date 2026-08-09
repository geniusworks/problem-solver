# Baseline — 2024 days 1–3, qwen2.5-coder:7b, 5 trials

First multi-run measurement (Milestone A). Run 2026-08-09, config fingerprint
`1b47b1586437`, 98 min wall clock (~196 s per problem-run), fully verified against
cached accepted answers. Raw artifact: `dev/experiments/20260809T190101Z_baseline-qwen7b_1b47b1586437.json`
(gitignored; regenerate with the command below).

```
config                          solved  rate  any/all   wrong  unver  overfit
baseline-qwen7b (1b47b1586437)  12/30   40%   4/0 of 6  0      0      0
```

`any/all of 6` = distinct problems solved in **at least one** trial / solved in
**every** trial. **4 of 6 are solvable; 0 of 6 are reliable.**

| problem      | solved | sequence (5 trials)                                   | stable |
|--------------|--------|--------------------------------------------------------|--------|
| 2024 d1 p1   | 3/5 60% | none, solved, none, solved, solved                     | flips  |
| 2024 d1 p2   | 4/5 80% | solved, solved, solved, solved, none                   | flips  |
| 2024 d2 p1   | 4/5 80% | solved, none, solved, solved, solved                   | flips  |
| 2024 d2 p2   | 0/5  0% | none ×5                                                 | stable (unsolved) |
| 2024 d3 p1   | 1/5 20% | none, solved, none, none, none                         | flips  |
| 2024 d3 p2   | 0/5  0% | none ×5                                                 | stable (unsolved) |

## What this establishes

1. **Single runs are noise.** Four of six problems flip. Every prior "N/6" figure
   in this project — including the "3/6" headline from PR #1 — was one draw from
   these distributions. `solved_every_time` is **zero**: nothing is reliable yet.

2. **The failure mode is `no_candidate`, never `wrong`.** Zero wrong, zero overfit,
   zero unverified across all 30 runs. When the pipeline produces a parseable
   solution it is correct; it fails by producing nothing usable. This confirms the
   roadmap's ordering — the leverage is **generation/extraction robustness
   (Milestone D)**, not model capability or orchestration.

3. **A reachability ceiling to watch.** d2 p2 and d3 p2 are stably unsolved (0/5).
   Whether they are a robustness problem (never got a clean candidate) or a genuine
   capability ceiling is the question a post-Milestone-D re-run should answer.

## Reproduce

```
venv/bin/python experiment.py --problems 2024:1-3 --trials 5 \
    --config "name=baseline-qwen7b,models=qwen2.5-coder:7b"
```

This is the reference point. Milestone D's success criterion: the four flipping
problems move toward `solved_every_time`, and the no-candidate rate drops, with
zero regression into `wrong`.
