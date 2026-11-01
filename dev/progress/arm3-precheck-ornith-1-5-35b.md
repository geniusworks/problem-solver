# Arm 3 pre-check: `ornith-1.5:35b` (registered, not yet run)

The entry criterion from `ensemble-precheck-negative.md`: measure each candidate alone on cells the
reference misses; run an ensemble only if it solves something the reference reliably misses. The
design and prediction below are committed before the entry check runs; the result will follow
them.

## Candidate

`ornith-1.5:35b`: 22 GB at 4-bit; maker and architecture not stated on its page. Machine `m5pro-64`, ollama 0.40.11.

## Plumbing check, 2026-11-01: 6/6

`m5pro-arm3-plumb-ornith-1-5-35b`, fingerprint `6f184b2a30df`, 2024 d1 p1 then p2, `samples_per_model=1`,
`enable_thinking=false`, 3 trials, 142 s (`dev/experiments/20261101T232314Z_m5pro-arm3-plumb-ornith-1-5-35b_6f184b2a30df.json`). It emits runnable code with thinking off;
20–31 s per part. This is a check that the model works under the harness, not a measurement.

## Design

```
venv/bin/python experiment.py --problems 2024:14.2,2024:17.2,2024:21,2024:24.2,2025:10.2 --trials 3 \
  --config "name=m5pro-arm3-ornith-1-5-35b-k3,models=ornith-1.5:35b,temperature=0.7,samples_per_model=3,enable_thinking=false,enable_fallback_models=false"
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

## Result

Not yet run.
