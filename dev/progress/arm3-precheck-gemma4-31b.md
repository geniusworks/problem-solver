# Arm 3 pre-check: `gemma4:31b` did not meet the entry criterion

The entry criterion from `ensemble-precheck-negative.md`: measure each candidate alone on cells the
reference misses; run an ensemble only if it solves something the reference reliably misses. The
design and prediction below are committed before the entry check runs; the result will follow
them.

## Candidate

`gemma4:31b`: Google, 19 GB at 4-bit; its 12B sibling has run under the harness. Machine `m5pro-64`, ollama 0.40.11.

## Plumbing check, 2026-11-01: 6/6

`m5pro-arm3-plumb-gemma4-31b`, fingerprint `3a14d36c92ea`, 2024 d1 p1 then p2, `samples_per_model=1`,
`enable_thinking=false`, 3 trials, 363 s (`dev/experiments/20261101T231711Z_m5pro-arm3-plumb-gemma4-31b_3a14d36c92ea.json`). It emits runnable code with thinking off;
50–72 s per part. This is a check that the model works under the harness, not a measurement.

## Design

```
venv/bin/python experiment.py --problems 2024:14.2,2024:17.2,2024:21,2024:24.2,2025:10.2 --trials 3 \
  --config "name=m5pro-arm3-gemma4-31b-k3,models=gemma4:31b,temperature=0.7,samples_per_model=3,enable_thinking=false,enable_fallback_models=false"
```

Each Part Two runs after its Part One in the same trial. The reference on these cells under the
same defaults (`m5pro-band-k1-vs-k3-aoc.md`, k3; `m5pro-rescan-part2-aoc.md`, k1 for d21):

| cell | `qwen3.8:27b` |
|---|---|
| 2024 d14 p2 | 1/3 at k3 (1 of 9 drafts) |
| 2024 d17 p2 | 1/3 at k3 (1 of 9 drafts) |
| 2024 d21 p1 | 0/3 at k1 (0/4 on record) |
| 2024 d24 p2 | 0/3 at k3 (0 of 9 drafts) |
| 2025 d10 p2 | 0/3 at k3 (0 of 9 drafts) |

## Prediction (registered 2026-11-01, before the entry check)

**The candidate does not meet the entry criterion**, as neither earlier candidate did
(`ensemble-precheck-negative.md`, `arm3-precheck-qwen36-35b.md`). Met means: solved in at least 2
of 3 trials, on a cell above. Specifically:

- 2024 d24 p2 and 2025 d10 p2: 0/3. The reference's failures there are mostly 60 s timeouts,
  which a different maker's model is no more likely to avoid.
- 2024 d14 p2, d17 p2 and d21 p1: at most 1/3 each.
- A Part 2 not reached because its Part 1 failed counts as not solved.

## Result (2026-11-05): criterion not met; the prediction held

`m5pro-arm3-gemma4-31b-k3`, fingerprint `7eba430258b5`, 3 trials, 21,340 s, GPU free
(`dev/experiments/20261105T093746Z_m5pro-arm3-gemma4-31b-k3_7eba430258b5.json`). 13 of 27
reached cells solved; 0 wrong, 0 overfit. A first attempt on 2026-11-01 was stopped after 3 of 30
cells; its partial file (`20261102T022846Z_…`) is not counted.

| cell | `gemma4:31b` k3 | its first drafts | reference k3 | failures |
|---|---|---|---|---|
| 2024 d14 p2 | 1/3 | 1/9 | 1/3 | 19 too low, 1 timeout |
| 2024 d17 p2 | 0/3 | 0/9 | 1/3 | 16 too low, 11 timeouts |
| 2024 d21 p1 | 0/3 | 0/9 | 0/3 at k1 | 23 too high, 1 too low, 2 crashes, 1 unchanged |
| 2024 d24 p2 | 0/3 | 0/9 | 0/3 | 18 wrong, 4 timeouts, 3 crashes |
| 2025 d10 p2 | 0/3 | 0/9 | 0/3 | 19 timeouts, 7 crashes, 1 too high |

Prerequisite Part 1s: 2024 d14, d17, d24 and 2025 d10, 3/3 each.

- **The prediction held on every cell**: 0/3 on 2024 d24 p2 and 2025 d10 p2, at most 1/3 on
  the rest. Its one solve, 2024 d14 p2 in trial 2, was a first draft; no repair was accepted.
- **Its wrong answers lean one way per cell.** 2024 d21 p1 is too high in 23 of 27 attempts,
  d14 p2 too low in 19 of 20, d17 p2 too low in all 16 wrong answers. Repairs given the
  too-high/too-low hint did not move them past the answer.
- **2025 d10 p2 fails on speed** as the reference's does: 19 of 27 attempts timed out at 60 s.
- **Faster than the reference** on these cells (21,340 s against roughly 30,000 s), at 1.86M
  tokens. Every Part 2 was reached.

No decider and no ensemble for this candidate. One candidate remains, `muse-glimmer:30b`.
