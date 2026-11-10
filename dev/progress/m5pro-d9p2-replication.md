# m5pro-64: k1 against k3 on 2025 d9 p2, replication with Part 2 always reached — ready, launch held

**Status (2026-11-10): ready, not started; the maintainer is holding the launch to a time still to
be set.** Design, prediction and readings were registered (#58) and the plumbing check passed.
The launch is the 14 blocks below, detached (`nohup`), about 16 hours; it needs the maintainer's
go, and the launch updates this line. Results will replace this line and fill the section marked
*pending*.

**Checking on it, and resuming, once launched.** `pgrep -f m5pro-d9p2-rep` shows whether a block is running;
the launcher logs to `dev/experiments/m5pro-d9p2-rep.log`. Each finished block leaves
`dev/experiments/<timestamp>_m5pro-d9p2-rep-kK-bB_<fingerprint>.json` (fingerprints
`80b37d599dd8` at k1, `96c4abf665d6` at k3). If the run stopped with nothing running, a block with
a result file holding 5 trials is done; every other block is rerun whole, in the order below, with
the maintainer's go. A partial result file from a stopped block is not used.

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
- **Drafts are saved** (`--include-replay`): each attempt's prompt, response and code go into the
  result file. The flag changes what is recorded, not the configuration or its fingerprint.
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

## Result

*pending*
