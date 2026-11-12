# m5pro-64: k1 against k3 on 2025 d9 p2, replication with Part 2 always reached — not re-established

**Result (2026-11-11): k1 13/35, k3 16/35; one-sided Fisher p = 0.31. Not re-established on
this problem under the registered readings.** The draws behaved as independent, at a per-draft
rate of 20%, below the 27% the prediction assumed. The design, prediction and readings below were
registered before launch (#58).

## Why a second test

The first registered test on this cell (`m5pro-d9p2-power-aoc.md`) gave k1 5/15 against k3 13/20
over trials that reached Part 2, one-sided Fisher p = 0.065: inconclusive, and it stays so. Its
power leaked through Part 1: five k1 trials failed Part 1 and never reached Part 2, so k1 had 15
trials instead of about 18. Part 1 failures also differed between the arms (5 against 0), so the
all-trials comparison mixed the two parts.

This test removes both problems and is analysed on its own. It is not an extension of the first:
its trials are not pooled with that run's, and its reading does not depend on that run's p.

## Design

- **Arms:** `samples_per_model=1` (k1) and `samples_per_model=3` (k3), **35 trials each**.
- **Config, both arms:** `models=qwen3.8:27b, temperature=0.7, enable_thinking=false,
  enable_fallback_models=false, gate_part_two=false`, other settings at their defaults
  (`problem_context=aoc`, `example_tests=page`). Fingerprints `80b37d599dd8` at k1 and
  `96c4abf665d6` at k3.
- **Problem:** `2025:9.2` alone. With `gate_part_two=false` no trial solves Part 1 first: Part 2 is
  posed with Part 1's statement, its accepted answer, the recorded oracle-verified Part 1 program
  (`years/2025/day09/2025_day09_part1.py`, the same in every trial and both arms) and an input
  preview. Every trial reaches Part 2.
- **Order:** seven blocks of five trials per arm, alternating k1, k3, k3, k1, k1, k3, k3, k1, k1,
  k3, k3, k1, k1, k3. Each block is its own run (names `m5pro-d9p2-rep-k1-b1` to `-b7` and
  `m5pro-d9p2-rep-k3-b1` to `-b7`), and the arms are pooled by name for the analysis. Alternating
  spreads any drift over the 16 hours (machine state, Ollama, time of day) across both arms; the
  first test ran k1 entirely before k3.
- **No stopping early, no extension.** All 70 trials run. A block that fails for a reason outside
  the model (a harness error, a crash of Ollama or the machine) is rerun whole and the failure is
  reported; trials are never dropped for their outcome.
- **Machine:** `m5pro-64`, Ollama 0.40.11, packages from `requirements.lock`; each result file
  records its environment.
- **Before launch:** `draft_index` recorded on every attempt (#57 merged), and a `--trials 3`
  plumbing check of `gate_part_two=false` on 2024 d1 p2, a problem outside this test. **Done
  2026-11-10:** 3/3 at k1 (`m5pro-precheck-gate-false`, fingerprint `80b37d599dd8`, commit
  `3612768`, Ollama 0.40.11, the same `qwen3.8:27b` digest as the first test); each trial made one
  Part 2 attempt and none on Part 1, and every attempt recorded `draft_index` and the example
  verdict.
- **Drafts are saved** (`--include-replay`): each attempt's code goes into the result file. The flag changes what is recorded, not the configuration or its fingerprint.
- **Expected time:** about 16 GPU-hours, from the first test's Part 2 times (about 490 s per k1
  trial and 1,150 s per k3 trial).

Each block, with `K` the draft count (1 or 3) and `B` the block number (1 to 7), in the order
above:

```
venv/bin/python experiment.py --problems 2025:9.2 --trials 5 --include-replay \
  --config "name=m5pro-d9p2-rep-kK-bB,samples_per_model=K,models=qwen3.8:27b,temperature=0.7,enable_thinking=false,enable_fallback_models=false,gate_part_two=false"
```

## Prediction (registered before launch)

From the first draft rate measured so far on this cell, p ≈ 0.27 (20 of 75 first drafts in the
first test), and independent draws:

| | predicted rate | expected, of 35 trials |
|---|---|---|
| k1 | about 27% (first draft about 27%, repair adding a little) | about 10, plausibly 5 to 15 |
| k3 | 1 − 0.73³ ≈ 61% | about 21, plausibly 16 to 27 |

The Part 1 program in the prompt is now the recorded one, not the trial's own, so the draft rate
may differ from the first test's; the independence check below uses this run's own rate.

**Power:** a one-sided Fisher exact test at α = 0.05 with 35 trials per arm detects 27% against
61% about 87% of the time; if the draft rate is nearer 20% (49% at k3), about 76%.

## Readings, fixed in advance

Rates are over all 35 trials per arm, which here are all trials that reached Part 2.

| outcome | reading |
|---|---|
| k3 above k1, one-sided Fisher p < 0.05 | **Sampling re-established on this cell** under the corrected harness. Triggers the conditional second reference model (`PLAN.md`), a maintainer decision. |
| k3 less than 10 points above k1 | **Not re-established** on this cell. |
| anything else | **Inconclusive**; report the interval, and arm 1's status is not restated. |

**Reported beside the reading, not deciding it:**
- Fisher's method combining this test's p with the first test's 0.065. It falls below 0.05
  whenever this test's p is below about 0.13, a lower bar than the reading's, which is why it does
  not decide. Fisher's method also assumes the two tests are independent and alike; the second
  differs in the Part 1 program.
- **Independence check:** the k3 rate against 1 − (1 − p̂)³, with p̂ this run's first-draft rate
  over both arms; with `draft_index`, also whether the three drafts of a k3 trial succeed
  independently of each other.
- **Example verdicts:** how often a failed draft passed the worked example, and how often the
  example's verdict disagrees with the oracle's.
- Time and tokens per solve in each arm.
- **Timeouts:** the share of failed drafts that hit the 60 s execution limit (19 of the first
  test's 75 first drafts, 25%), and, after the run, the saved timed-out drafts re-executed on the
  full input with a 600 s limit: how many were correct but slow. The limit stays at 60 s for the
  test itself; the re-execution says whether a longer one would have changed the draft rate.

**Added after launch (2026-11-11), not registered:** an outside review prompted two additions to
the write-up. Neither changes the run or the reading.
- **Selection without the oracle.** In each k3 trial, a selector that sees only the worked example
  takes a draft that passes it and produces an answer (a draft that times out gives none). Against
  the oracle: how often it takes a wrong draft, how often it passes over a correct one, and the
  solve rate it reaches beside the oracle's. Computed from the recorded example verdicts and
  `draft_index`; no GPU time (`PLAN.md`, "Beyond AoC", step 1).
- **Scope.** The headline is stated for this problem. Thirty-five trials measure the rates on
  2025 d9 p2, not across problems; wherever README or RESULTS state arm 1 generally, they name the
  problems it rests on.

## Result

Fourteen runs, `m5pro-d9p2-rep-k1-b1` to `m5pro-d9p2-rep-k3-b7`, launched at 22:42 PST on
2026-11-10 from commit `e73722e` (clean), detached, and finished at 14:57 PST on 2026-11-11 in the
registered order; no block failed or was rerun. Every file records Ollama 0.40.11 and the same
`qwen3.8:27b` digest as the first test, and the fingerprints registered above.

| | Part 2 solved | solved by a draft, before repair | drafts that solved |
|---|---|---|---|
| k1 | **13/35 (37%)** | 9/35 | 9/35 (26%) |
| k3 | **16/35 (46%)** | 14/35 | 19/105 (18%) |

**Registered reading: not re-established on this problem.** k3 is 8.6 points above k1 (95%
Newcombe interval −14 to +30 points), one-sided Fisher p = 0.31, under the registered 10 points.
Against the prediction, k1 came in at 13 (about 10 predicted) and k3 at 16 (about 21 predicted,
at the bottom of its plausible range).

**Why the predicted lift did not appear: the draft rate, not the draws.** Across both arms,
drafts solved 28 times in 140 (p̂ = 20%), below the 27% the prediction used. Independent draws at
20% predict 1 − 0.80³ = 49% at k3; the measured 46% lies inside its 95% Wilson interval (30% to
62%). At that rate three drafts are expected to solve 49% against 20% for one, 29 points before
repair; repair lifted k1 to 37%, leaving about 12 points, against the 34 the test was powered for. The per-draft rate also differed between the arms, 26% at k1 against 18%
at k3; that difference is within chance (two-sided Fisher p = 0.34).

**Within a trial, the three drafts were close to independent.** Correct drafts per k3 trial, against
a binomial at the k3 draft rate (18%):

| correct drafts in the trial | 0 | 1 | 2 | 3 |
|---|---|---|---|---|
| trials | 21 | 9 | 5 | 0 |
| expected if independent | 19.2 | 12.7 | 2.8 | 0.2 |

There are slightly more trials with two correct drafts than independence expects, a hint of
correlation within a trial that these counts cannot test.

**Repair narrowed the gap at k1.** It rescued 4 of the 26 k1 trials whose draft failed, against 2
of 12 in the first test; at k3 it ran on the 21 trials where all three drafts failed and rescued 2.

**Combined with the first test** (Fisher's method, reported, not deciding): p = 0.10.

**Time and tokens** (solved trials as the denominator): k1 1,145 s and 80,493 tokens per solve,
k3 2,720 s and 190,143. Three drafts cost about 2.4 times as much per solve here. The run took
16.3 hours (k1 4.2, k3 12.1), against about 16 estimated.

**Timeouts: none finished correctly within 600 s.** 45 of the 140 drafts (32%) ran past the
60 s limit on the full input. Re-executed from their saved code with a 600 s limit and an 8 GB
memory cap (`dev/rerun_timeouts.py`, the harness's sandbox, two at a time):

| at 600 s | drafts |
|---|---|
| stopped at the 8 GB memory cap (after 3 to 433 s) | 26 |
| still running at 600 s | 17 |
| finished with a wrong answer (285 s, 308 s) | 2 |
| finished with the right answer | **0** |

On this problem a ten-times longer limit would not have raised the draft rate within 600 s: 22
of the 26 capped drafts passed 8 GB within 10 s (median 5.4 s), and none of the rest finished
correctly. The 17 still running at 600 s are unresolved; whether any would have finished
correctly later is not known. The cap was added for the re-execution after six drafts run at
once froze the machine, because the sandbox did not cap memory on macOS (it has since 2026-11-11).
It measured resident size for the first 15 drafts and physical footprint, which counts compressed
pages, for the other 30.

**Example verdicts** (one worked example; every attempt, drafts and repairs):

| | examples passed | examples failed |
|---|---|---|
| oracle solved | 34 | 0 |
| oracle wrong | 43 | 68 |
| timed out on the full input | 94 | 44 |

The example never rejected a correct answer. It passed 137 of the 249 attempts the oracle
rejected: 94 that then timed out and 43 that answered wrong. Attempts without a candidate to
verify (22) carry no verdict, apart from one that failed validation before the example.

**Selection without the oracle** (added after launch, not registered). In each k3 trial, a
selector that sees only the example takes the first draft, in draft order, that passes it and
produces an answer:

| | trials |
|---|---|
| takes a correct draft | 12 |
| takes a wrong draft, though a correct one was among the three | 2 |
| takes a wrong draft, none of the three correct | 13 |
| takes nothing: no draft passed the example and answered | 8 |

It solves 12 of 35 trials, against 14 of 35 for the oracle choosing among the same drafts, and
would submit a wrong answer in 15. Of those 15, a choice among passing drafts by agreement could
have caught at most the 3 where the passing drafts disagreed. With one worked example and no
oracle, the selector took a wrong draft more often than a right one (15 against 12).

**What this does and does not show.** On 2025 d9 p2, with the verified Part 1 program in the
prompt, three drafts did not beat one draft with repair by the registered margin. The draws still
behaved as independent, so the prediction failed on the draft rate it assumed, not on the
mechanism: sampling's gain follows the per-draft rate, and at 20% against one draft with repair
that gain is about 12 points, which 35 trials per arm cannot separate from zero (the test was
powered for 34). The result is for this problem; it does not test other problems or models.
