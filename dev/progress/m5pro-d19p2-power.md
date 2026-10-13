# m5pro-64: k1 vs k3 on 2024 d19 p2, 20 trials per arm — **6/20 → 10/20, on the independence curve**

**Headline: one draft solved 6 of 20 trials, three drafts solved 10 of 20.** Both registered
predictions held (k1 between 2 and 7; k3 above k1 and at least 7). The lead is not significant on
its own (one-sided Fisher p = 0.17), which the registration named in advance as the inconclusive
outcome. What the run does settle is the mechanism on this problem: the k3 rate is what three
independent drafts at the measured draft rate predict, and repair contributed nothing to it.

- **Config:** `models=qwen3.8:27b, temperature=0.7, enable_thinking=false,
  enable_fallback_models=false`, 2024 d19 p2 only, 20 trials per arm, run back to back.
  k1: `samples_per_model=1`, fingerprint `62ee65d6b521`. k3: `samples_per_model=3`, fingerprint
  `d0e67ebf4cee`.
- **Machine:** `m5pro-64`, ollama 0.34.4. Solver with repair accounting fixed
  (`repair-accounting-unwired.md`).
- **Runs:** `dev/experiments/20261013T033144Z_m5pro-d19p2-k1-n20_62ee65d6b521.json`,
  `dev/experiments/20261013T061703Z_m5pro-d19p2-k3-n20_d0e67ebf4cee.json` (gitignored).
- **Registered in:** `m5pro-passk-2024-d16-25.md`, committed before launch.
- 0 wrong / 0 unverified / 0 overfit in both arms. Ledger unchanged at 54.

## Result

| | k1 | k3 | registered |
|---|---|---|---|
| trials solved | **6/20 (30%)** | **10/20 (50%)** | k1 2 to 7; k3 > k1 and ≥ 7 |
| first drafts correct | 5/20 (25%) | 11/60 (18%) | — |
| solves that came from a first draft | 5 | 10 | — |
| solves that came from repair | 1 | 0 | — |
| repair attempts converted | 1/18 | 0/34 | — |
| wall-clock | 3,370 s | 9,915 s | — |
| tokens | 165,827 | 496,907 | — |
| per verified solve | 562 s, 27.6k tokens | 992 s, 49.7k tokens | — |

One-sided Fisher exact, k3 above k1: **p = 0.17**. Pooled with the earlier draws on this problem
(k1 7/24, k3 12/23): **p = 0.095**.

## What it shows

- **The draws behave as independent.** First drafts were correct 16 times in 80 across both arms
  (20%). Three independent drafts at that rate solve 1 − 0.8³ = **49%** of trials; k3 solved
  **50%**, every one of them from a first draft. The independence curve that the registration
  could only assume from 1/4 is now measured on this problem and fits.
- **Repair does almost nothing here.** 1 conversion in 52 repair attempts. The dominant failure
  is a program that prints `0` (60 of 80 first drafts, 49 of 52 repairs), and a repair of such a
  draft prints `0` again. The repair that solved a trial in the three-trial run
  (`m5pro-passk-2024-d16-25.md`) was the exception; that run's 2/3 was one draw and one lucky
  repair.
- **Sampling buys reliability, not efficiency.** k3 raised the per-trial solve rate from 30% to
  50% and cost 1.8× as much per verified solution in both time and tokens. That is the shape arm 2
  already reports.
- **The effect is smaller than on the earlier bands** (2024 d13–15: 42% → 75%; 2025: 2/8 → 6/6).
  A 20% draft rate gives sampling less to work with than the 25–33% problems there, and the curve
  says k=5 would reach 67% and k=10 89% on this problem.

## First artifacts with real repair cost

These are the first runs whose repair records carry their own tokens and time; no repair record
matches a draft's count.

| | k1 arm | k3 arm |
|---|---|---|
| mean tokens per first draft | 6,952 | 7,119 |
| mean tokens per repair | 1,488 | 2,051 |
| repair share of tokens | 16% | 14% |

A repair cost about a quarter of a draft here. The old records charged each repair a full draft,
so on this problem and model the old totals overstated repair cost roughly fourfold. One problem
and one model; `repair-accounting-unwired.md` carries the note.

## Standing of arm 1

Unchanged: confirmed and replicated on the two earlier bands. This is a third test that agrees in
direction and in mechanism and does not reach significance alone. It is the only one of the three
with enough trials to check the independence assumption directly, and the assumption held.
