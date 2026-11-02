# Arm 3 pre-check: `ornith-1.5:35b` meets the entry criterion on one cell, narrowly

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

## Result (2026-11-01): criterion met on 2024 d14 p2; the prediction failed

`m5pro-arm3-ornith-1-5-35b-k3`, fingerprint `dce8a73c2b46`, 3 trials, 5,714 s, GPU free
(`dev/experiments/20261102T005324Z_m5pro-arm3-ornith-1-5-35b-k3_dce8a73c2b46.json`). 13 of 25
reached cells solved; 0 wrong, 0 overfit.

| cell | `ornith-1.5:35b` k3 | its first drafts | reference k3 | reference first drafts, k1 + k3 |
|---|---|---|---|---|
| 2024 d14 p2 | **3/3** | 3/9 | 1/3 | 3/12 |
| 2024 d17 p2 | 0/3 | 0/9 | 1/3 | 2/12 |
| 2024 d21 p1 | 0/3 | 0/9 | 0/3 at k1 | 0/3 |
| 2024 d24 p2 | 0/3 | 0/9 | 0/3 | 0/10 |
| 2025 d10 p2 | 0/1 (2 not reached) | 0/3 | 0/3 | 1/12 |

Prerequisite Part 1s: 2024 d14, d17 and d24 3/3 each; **2025 d10 p1 1/3**, which the reference
solves every time (9 of 9 drafts at k3).

- **The prediction failed on 2024 d14 p2**: predicted at most 1/3, solved 3/3. Two trials were
  solved by a first draft and one by a repair. This meets the entry criterion as registered: at
  least 2 of 3 trials on a cell the reference solved in at most 1 of 3.
- **The margin is thin.** Per draft, the candidate is 3 of 9 and the reference 3 of 12 over both
  its runs; the reference solved the cell in 3 of 6 trials across k1 and k3. The trial-level
  3/3 against 1/3 is mostly the luck of three trials and one repair. The candidate may be better
  on this cell; the run does not show that the reference reliably misses it.
- **The rest of the prediction held:** 0/3 on d24 p2, d21 p1 and d17 p2, and 0/1 reached on 2025
  d10 p2.
- **It also fails where the reference does not:** 2025 d10 p1, 1/3 against 3/3. Its failures are
  mostly crashes (12 on d21 p1, 20 on d24 p2), where the reference's are mostly timeouts.
- **About 5 times the reference's pace** on these cells (5,714 s against roughly 30,000 s), at
  1.54M tokens.

**Before an ensemble:** 2024 d14 p2 for both models at k1, 10 trials each, to decide whether the
candidate solves it more often than the reference. The ensemble runs only if it does.

## Decider: 2024 d14 p2 at k1, 10 trials each (registered 2026-11-02, before the run)

```
B="temperature=0.7,samples_per_model=1,enable_thinking=false,enable_fallback_models=false"
venv/bin/python experiment.py --problems 2024:14.2 --trials 10 --config "name=m5pro-d14p2-ornith-k1-n10,models=ornith-1.5:35b,$B"
venv/bin/python experiment.py --problems 2024:14.2 --trials 10 --config "name=m5pro-d14p2-ref-k1-n10,models=qwen3.8:27b,$B"
```

Each Part Two runs after its Part One in the same trial, with the default two repair rounds. A
trial whose Part One fails counts as a Part Two not solved: an ensemble member that cannot reach
the cell does not help on it. Solves among trials reached are reported alongside.

- **Rule:** the candidate's lead holds if it solves more Part Twos than the reference, one-sided
  Fisher exact p < 0.05 (for example 7/10 against 2/10, or 6/10 against 1/10). Otherwise the
  ensemble is not run on the strength of this cell.
- **Prediction: the lead does not hold.** The per-draft rates on record, 3/9 and 3/12, are close.
  Expected: the candidate 3–7 of 10, the reference 2–6 of 10.

### Decider result

Not yet run.
