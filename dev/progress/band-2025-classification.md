# 2025 frontier band: mostly walls, only two "sometimes" — a harder venue than 2024

**Classifying the 2025 misses at `--trials 3` found only two problems the model solves
*sometimes*.** 2025's frontier is far more **bimodal** than 2024's: reliable problems are perfectly
reliable, failures are mostly total, and very little sits in between. That makes it a **harder test
of the sampling claim**, because sampling can only convert problems that are sometimes-solvable.

- **Config:** `models=qwen3.8:27b, temperature=0.7, samples_per_model=1, enable_thinking=false`
  (fingerprint `5b33a3519b5d` — identical to the 2025 scan and both 2024 samp1 arms, so all draws
  pool), 3 trials, 2025 d2/d4/d9/d10/d11 (the days containing every scoreable miss).
- **Cost:** 18,414 s (5h). **0 wrong / 0 unverified / 0 overfit.**
- **Run:** `dev/experiments/20260819T061605Z_band2025-samp1_5b33a3519b5d.json` (gitignored).
- **Ledger:** +2 → **43 correct, 0 wrong** (d9 p1 and d11 p2 banked when they solved).

## Result

| problem | k/3 | classification |
|---------|-----|----------------|
| d2 p1 | 3/3 (100%) | reliable (control) |
| d2 p2 | 0/3 | wall |
| d4 p1 | 3/3 (100%) | reliable (control) |
| d4 p2 | 0/3 | wall |
| **d9 p1** | **1/3 (33%)** | **sometimes** |
| d9 p2 | 0/3 | wall |
| d10 p1 | 3/3 (100%) | reliable (control) |
| d10 p2 | 0/3 | wall |
| d11 p1 | 3/3 (100%) | reliable (control) |
| **d11 p2** | **1/3 (33%)** | **sometimes** |

Pooled with the scan draw, d2 p2 / d4 p2 / d9 p2 / d10 p2 are each **0/4**.

## The shape differs from 2024, and that matters

| | 2024 d8–15 band | 2025 band |
|---|---|---|
| reliable (100%) | — | **4 of 10** |
| **sometimes** | **5 of 8** | **2 of 10** |
| walls (0%) | 2 | **4 of 10** |

2024's frontier was mostly *near-misses* — five problems in the 33–67% range, which is exactly the
regime where extra draws pay. 2025's is **all-or-nothing**: every Part 1 tested is 3/3, four of six
Part 2s are 0/3.

This is the more demanding setting for the project's central claim. It also suggests the 2024 band
may have been *unusually favourable* to sampling — not because it was chosen to be, but because
d8–15 happened to contain a cluster of near-misses. Worth remembering when quoting 42% → 75%.

## The pre-registered prediction failed — on both halves

From the 2025 scan's failure taxonomy, this doc's predecessor predicted:

> *sampling should pay on the wrong-answer group (d2 p2, d4 p2, d9) and not the crash group
> (d10 p2, d11 p2)*

Measured:

- **crash-class `d11 p2` is a "sometimes"** (1/3) — it failed `error` 3/3 in the scan, then solved.
- **three of four wrong-answer problems are hard walls** (d2 p2, d4 p2, d9 p2, all 0/4). Only
  d9 p1 showed variance.

**How a problem failed once does not predict whether it is sometimes-solvable.** That has to be
measured per problem. This is the third time in this line of work that a tidy taxonomy of failure
kinds has not survived the next run — after "insight walls won't fall to sampling" (falsified by
2024 d13 p2) and "voting buys execution reliability, not ideas" (falsified by the same problem).

The general lesson worth keeping: **the only reliable classifier of "sometimes" is repeated
sampling.** Failure-mode labels are useful for *explaining* a result and unreliable for *predicting*
one.

## What it sets up, and its limit

The out-of-sample sampling test is runnable — **d9 p1 and d11 p2, both 33%**, predicting
**pass@3 ≈ 70%** if draws are independent (the same prediction that held on 2024's d13 p2 and failed
on d15 p2).

**Stated up front: a two-problem band is thin.** A positive result would be encouraging but not
strong; a null result would be **under-powered rather than decisive**. Any conclusion drawn from it
must carry that caveat, and the honest framing is a *replication attempt* on a harder venue, not a
second independent confirmation.

## Reproduce

```
venv/bin/python experiment.py --problems 2025:2,2025:4,2025:9,2025:10,2025:11 --trials 3 \
  --config "name=band2025-samp1,models=qwen3.8:27b,temperature=0.7,samples_per_model=1,enable_thinking=false"
```
