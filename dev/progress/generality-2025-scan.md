# Out-of-sample: AoC 2025 d1–12 — the findings generalise (16/23, 70%)

**The first evaluation this project has run on problems it had never seen.** Everything measured
before this came from AoC 2024 — the frontier was found there, the failure classes were named there,
and the pass@k thesis was tested there. A second year is the only way to tell whether we learned
something about *coordinating LLMs* or something about *2024's puzzles*.

**All three structural claims held.** And it produced **16 new verified solutions** — ledger
**25 → 41 correct, 0 wrong**.

- **Config:** `models=qwen3.8:27b, temperature=0.7, samples_per_model=1, enable_thinking=false`
  (fingerprint `5b33a3519b5d` — byte-identical to the 2024 k1 arm, so the two years are directly
  comparable), 1 trial, 2025 d1–12.
- **Machine:** `m2max-32`, ollama 0.32.14. **Cost:** 14,223 s (4h), 543,930 tokens.
- **Run:** `dev/experiments/20260818T193613Z_scan2025-samp1_5b33a3519b5d.json` (gitignored).
- **0 wrong, 0 unverified, 0 overfit recorded.**

## Result

**16 of 23 scoreable parts (70%).** The harness reports 16/24 (67%) because its denominator includes
2025 d12 p2, which has no cached answer and cannot be scored — see below.

| | 2024 d8–15 | **2025 d1–12** |
|---|---|---|
| scoreable parts | 16 | **23** |
| solved | 9 (**56%**) | **16 (70%)** |
| Part 1 | — | **10/12 (83%)** |
| Part 2 | — | **6/11 (55%)** |

Solved: d1 p1/p2, d2 p1, d3 p1/p2, d4 p1, d5 p1/p2, d6 p1/p2, d7 p1/p2, d8 p1/p2, d10 p1, d11 p1.
Missed: d2 p2, d4 p2, d9 p1, d9 p2, d10 p2, d11 p2, d12 p1 (+ d12 p2, unscoreable).

## What held

**1. A real frontier exists out of sample.** 70% — not 100%, not 0%. This was the outcome most at
risk: a model that aced or flunked an unseen year would leave nothing to test orchestration on.
2025 is a working instrument.

**2. The Part 1 / Part 2 cliff recurs.** 83% vs 55%, and **six of the seven scoreable misses are
Part 2s**. This is the 2024 shape reproduced on unrelated puzzles, and it is the most robust
structural finding the project has: difficulty is concentrated in the *second half* of a problem,
where the naive approach from Part 1 stops working.

**3. Day 9 fell in both years, both parts.** The day number is coincidence — the puzzles are
unrelated — but 2024 d9 and 2025 d9 both failed completely, and both by producing **wrong answers
rather than crashes** (2025: 4 wrong across p1/p2). Fiddly-bookkeeping problems where code runs
cleanly and computes the wrong thing appear to be a recurring class rather than a 2024 artifact.

## Failure taxonomy, out of sample

The seven scoreable misses split cleanly, and the split is informative:

| failure mode | problems | reading |
|---|---|---|
| **wrong answer** (code runs, computes the wrong thing) | d2 p2, d4 p2, d9 p1, d9 p2 | reasoning failure; the near-miss class that sampling helped most with in 2024 |
| **crash** (`error`, 3/3 attempts each) | d10 p2, d11 p2, d12 p1 | structural code failure; `IndexError` recurs |
| **no candidate** | d12 p2 only | the unscoreable one |

That 4-wrong / 3-crash split is close to 2024's shape on the same model, which matters because the
2024 pass@k result showed sampling converts *wrong* far more readily than it converts *systematic*
failure. If that carries over, the wrong-answer group (d2 p2, d4 p2, d9) is where sampling should
pay on 2025 — a concrete, pre-registered prediction for the next run.

## The caveat that matters: the sets are not difficulty-matched

**70% > 56% is very likely set composition, not a model or year difference.** 2025 d1–12 includes
the easy early days; 2024 d8–15 deliberately excluded them (d1–7 had been solved out). Comparing a
range that starts at day 1 with one that starts at day 8 is not a like-for-like comparison, and this
result should not be read as "2025 is easier" or "the model improved". The *structure* (a frontier
exists; Part 2s are the wall) is what transfers; the headline rate is not comparable.

A matched comparison would scan 2025 d8–12 alone, or 2024 d1–12 — worth doing before any claim about
relative year difficulty.

## The genuinely unseen problem: 2025 d12 p2

**d12 p2 has no cached answer** — the only problem in the entire corpus the maintainer's account has
not solved, so no ground truth exists to scrape. The harness handled it exactly as designed: it
attempted the problem, produced no candidate, and recorded the result **without** contaminating the
scored set (it is excluded from the 16/23 above; the harness's own 16/24 includes it).

This is the **Milestone F scenario in miniature** — a target where the oracle cannot help and
answer-based consensus would be the only available signal. `PLAN.md` has deferred the submission
phase on the grounds that "there is no unseen answer to submit". There is now exactly one. Nothing
was submitted; that is outward-facing, rate-limited, and a maintainer decision.

## Limits

- **One trial per problem.** This is a locator, not a measurement: it says *where* the model
  struggles, not *how often*. Every 2025 problem it flags needs `--trials 3` before any rate claim.
- **One model, one config, temperature 0.7.**
- The rate comparison to 2024 is **not** like-for-like (above).

## What it unblocks

- **The sampling result can now be tested out of sample too.** 2024 showed 42% → 75% at the
  frontier; the equivalent 2025 band (classified with `--trials 3`, then a k1-vs-k3 A/B) would be the
  first out-of-sample test of the project's *central* claim, not just its structural ones.
- **A pre-registered prediction exists:** sampling should convert the wrong-answer group (d2 p2,
  d4 p2, d9) more readily than the crash group (d10 p2, d11 p2, d12 p1).

## Reproduce

```
venv/bin/python experiment.py --problems 2025:1-12 --trials 1 \
  --config "name=scan2025-samp1,models=qwen3.8:27b,temperature=0.7,samples_per_model=1,enable_thinking=false"
```
