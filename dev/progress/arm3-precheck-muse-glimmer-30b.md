# Arm 3 pre-check: `muse-glimmer:30b` met the entry criterion on 2024 d14 p2, and the decider held it (10/10 against 1/10)

The entry criterion from `ensemble-precheck-negative.md`: measure each candidate alone on cells the
reference misses; run an ensemble only if it solves something the reference reliably misses. The
design and prediction below are committed before the entry check runs; the result will follow
them.

## Candidate

`muse-glimmer:30b`: Meta, 18 GB at 4-bit, tuned for tool use and failure recovery. Machine `m5pro-64`, ollama 0.40.11.

## Plumbing check, 2026-11-01: 6/6

`m5pro-arm3-plumb-muse-glimmer-30b`, fingerprint `a9ae29f29a7a`, 2024 d1 p1 then p2, `samples_per_model=1`,
`enable_thinking=false`, 3 trials, 642 s (`dev/experiments/20261101T232536Z_m5pro-arm3-plumb-muse-glimmer-30b_a9ae29f29a7a.json`). It emits runnable code with thinking off;
81–139 s per part. This is a check that the model works under the harness, not a measurement.

## Design

```
venv/bin/python experiment.py --problems 2024:14.2,2024:17.2,2024:21,2024:24.2,2025:10.2 --trials 3 \
  --config "name=m5pro-arm3-muse-glimmer-30b-k3,models=muse-glimmer:30b,temperature=0.7,samples_per_model=3,enable_thinking=false,enable_fallback_models=false"
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

## Selection bias (registered 2026-11-06, during the entry check, before any decider)

The entry cells were chosen because the reference failed them in earlier runs. Its rates there
are low partly by selection: a cell that was unlucky in three trials makes the list, and would
score higher on a fresh run. The candidate is measured fresh on the same cells, so the entry check
favours it. A lead there is a reason to run a decider, which re-measures both models on the cell,
not a result. Ornith's lead on 2024 d14 p2 (3/3 against 1/3) was of this kind: the decider put
ornith at 1 of 7 trials that reached Part 2 and the reference at 1/10 (`arm3-precheck-ornith-1-5-35b.md`).

## Result (2026-11-06): criterion met on 2024 d14 p2; the prediction failed

`m5pro-arm3-muse-glimmer-30b-k3`, fingerprint `52aa94a05ce9`, 3 trials, 35,389 s, GPU free
(`dev/experiments/20261106T091713Z_m5pro-arm3-muse-glimmer-30b-k3_52aa94a05ce9.json`). 18 of 28
reached cells solved; 0 wrong, 0 overfit; 1.58M tokens.

| cell | `muse-glimmer:30b` k3 | its first drafts | reference k3 | reference first drafts, k1 + k3 | candidate's failures |
|---|---|---|---|---|---|
| 2024 d14 p2 | **3/3** | **9/9** | 1/3 | 3/12 | none |
| 2024 d17 p2 | 1/3 (by a repair) | 0/9 | 1/3 | 2/12 | 8 crashes, 1 too low |
| 2024 d21 p1 | **1/3** | 1/9 | 0/3 at k1 | 0/3 (0/7 on record) | 8 crashes, 4 too low, 2 too high |
| 2024 d24 p2 | 0/3 | 0/9 | 0/3 | 0/10 | 20 wrong, 3 timeouts, 3 crashes |
| 2025 d10 p2 | 0/3 | 0/9 | 0/3 | 1/12 | 12 crashes, 11 too low, 2 too high, 2 timeouts |

Prerequisite Part 1s: 2024 d14, d17, d24 and 2025 d10, 3/3 each. 2024 d21 p2, reached once, was
solved by all three drafts.

- **The prediction failed on 2024 d14 p2**: predicted at most 1/3, solved 3/3, every draft
  correct. Per draft that is 9 of 9 against the reference's 3 of 12 over its two runs, one-sided
  Fisher p = 0.0007. Ornith met the criterion on the same cell with 3 of 9 drafts, which was
  not distinguishable from the reference's rate; this is.
- **First verified 2024 d21**, both parts (ledger 66 → 68). The reference has never solved d21
  p1 (0/7 on record). One trial in three does not meet the criterion. The selection bias above
  weighs less here: 0/7 is the reference's whole record on the cell, not a three-trial sample.
- **The rest of the prediction held:** 0/3 on 2024 d24 p2 and 2025 d10 p2, 1/3 on d17 p2.
- **Its failures differ in kind from the reference's.** On the entry cells muse failed mostly by
  crashing or by a wrong answer, with 5 timeouts in 76 failed attempts; the reference's failures
  on the hardest of them were mostly 60 s timeouts (`m5pro-band-k1-vs-k3-aoc.md`).
- **Slower than the reference** on these cells: 35,389 s against roughly 30,000 s.

## Decider: 2024 d14 p2 at k1, 10 trials (registered 2026-11-06, before the run)

```
B="temperature=0.7,samples_per_model=1,enable_thinking=false,enable_fallback_models=false"
venv/bin/python experiment.py --problems 2024:14.2 --trials 10 --config "name=m5pro-d14p2-muse-k1-n10,models=muse-glimmer:30b,$B"
```

The reference's side is the run already on record under the same defaults:
`m5pro-d14p2-ref-k1-n10`, fingerprint `1ac712678732`, 1/10 (`arm3-precheck-ornith-1-5-35b.md`).
Same rules as Ornith's decider: a trial whose Part One fails counts as a Part Two not solved.

- **Rule:** the lead holds if the candidate solves more Part Twos than the reference's 1/10,
  one-sided Fisher exact p < 0.05, which means at least 6/10.
- **Prediction: the lead holds.** Expected 7–10 of 10, from 9 of 9 drafts at k3 and 9 of 9 on
  d14 p1.
- About 1–1.5 h.

### Decider result (2026-11-06): 10/10 against 1/10; the lead holds

| | `muse-glimmer:30b` | `qwen3.8:27b` |
|---|---|---|
| run | `m5pro-d14p2-muse-k1-n10`, `a9ae29f29a7a` | `m5pro-d14p2-ref-k1-n10`, `1ac712678732` |
| 2024 d14 Part Two solved | **10/10** | **1/10** |
| reached (Part One solved) | 10/10 | 10/10 |
| solved by a first draft / by repair | 9 / 1 | 1 / 0 |
| wall-clock | 3,552 s | 6,113 s |
| tokens | 234k | 468k |

`dev/experiments/20261107T035120Z_m5pro-d14p2-muse-k1-n10_a9ae29f29a7a.json`; the fingerprint is
the plumbing check's, since the config is the same. One-sided Fisher exact p = 0.0001.

- **The prediction held**: 10/10, within the expected 7–10.
- **Across both runs muse solves 2024 d14 p2 with 18 of 19 first drafts**, against the
  reference's 4 of 22. This is the first cell where a candidate reliably solves what the
  reference reliably misses, the condition `ensemble-precheck-negative.md` set for running an
  ensemble.
- **At under 60% of the reference's time and half its tokens** on this cell.

The ensemble is next; its design and prediction are registered before it runs.
