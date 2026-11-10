# m5pro-64: k1 against k3 on 2025 d9 p2 under the corrected harness — inconclusive

**Result (2026-11-09): k1 5/15, k3 13/20 over trials that reached Part 2; one-sided Fisher
p = 0.065. Inconclusive under the registered readings.** The draws behaved as independent. The
design, prediction and readings below were committed before launch (`f5d8d4b`).

## Why this cell

Arm 1 (sampling) was measured and replicated under the original harness, which posed Part 2
without Part 1. Re-run under the corrected harness, the reference's "sometimes" cells split into
solved by nearly every draft or by nearly none, and three drafts showed no measurable lift (9/19
against 11/21, `m5pro-band-k1-vs-k3-aoc.md`). Independent draws predict exactly that: three draws
lift a 10% draft rate little and a 90% one has no room to rise. 2025 d9 p2 is the one cell
measured at a mid-range draft rate, where independence predicts a real gain.

**Prior evidence, corrected harness** (`dev/results/`, recomputed 2026-11-09): first drafts
solved 3 of 11 (27%); repairs 0 of 10; trials 0/2 reached at k1 (one not reached), 2/3 at k3, plus
1/2 at k3 in a run that left only a log (`part2-prompt-omits-part1.md`).

## Design

- **Arms:** `samples_per_model=1` (k1) and `samples_per_model=3` (k3), 20 trials each, k1 first.
- **Config, both arms:** `models=qwen3.8:27b, temperature=0.7, enable_thinking=false,
  enable_fallback_models=false`, current defaults (`problem_context=aoc`, `example_tests=page`;
  fingerprints `1ac712678732` at k1 and `839b40f0bfa8` at k3, as in the rescan and band runs).
- **Problem:** `2025:9.2`. Under the corrected harness each trial solves Part 1 first and poses
  Part 2 with it; a trial whose Part 1 fails is `not_reached` for Part 2.
- **Machine:** `m5pro-64`, Ollama 0.40.11, packages from `requirements.lock`; each result file
  records its environment.
- **Pre-run check:** `--trials 3` on 2024 d1 after the 2026-11-09 setup changes (autopep8 2.3.2,
  venv rebuilt from the lock, example verdicts recorded). It also confirms that
  `examples_passed`/`examples_total` are filled.
- **Expected time:** about 14 GPU-hours (k1 about 850 s per trial, k3 about 1,640 s).

```
venv/bin/python experiment.py --problems 2025:9.2 --trials 20 \
  --config "name=m5pro-d9p2-power-aoc-k1,samples_per_model=1,models=qwen3.8:27b,temperature=0.7,enable_thinking=false,enable_fallback_models=false"
venv/bin/python experiment.py --problems 2025:9.2 --trials 20 \
  --config "name=m5pro-d9p2-power-aoc-k3,samples_per_model=3,models=qwen3.8:27b,temperature=0.7,enable_thinking=false,enable_fallback_models=false"
```

## Prediction (registered before launch)

From the prior first-draft rate p ≈ 0.27 and independent draws, with repair contributing nothing:

| | predicted rate | expected, of about 18 reached trials |
|---|---|---|
| k1 | about 27% | about 5, plausibly 1 to 9 |
| k3 | 1 − 0.73³ ≈ 61% | about 11, plausibly 7 to 15 |

**Power:** at those rates and about 18 reached trials per arm, a one-sided Fisher test at
α = 0.05 detects the difference about 70% of the time. Lower than the 80% planned, because the
prior draft rate (27%) came in under the planning figure (one in three). The run is kept at 20
trials per arm as approved; the trial count is not extended after seeing results.

## Readings, fixed in advance

Rates are over trials that reached Part 2; the all-trials rates are reported beside them.

| outcome | reading |
|---|---|
| k3 above k1, one-sided Fisher p < 0.05 | **Sampling re-established on this cell** under the corrected harness. |
| k3 less than 10 points above k1 | **Not re-established** on this cell. |
| anything else | **Inconclusive** at this size; report the interval, no restatement of arm 1. |

**Independence check:** the k3 rate against 1 − (1 − p̂)³, with p̂ the first-draft rate this run
measures across both arms. Within the 95% interval: draws behave as independent here too.

**Example verdicts (first data for `PLAN.md`, "Beyond AoC", step 1):** reported, not tested:
how often a failed draft passed the worked example (the passed-example-then-timeout pattern), and
how often the examples' verdict disagrees with the oracle's.

## Result

Runs `20261109T174241Z_m5pro-d9p2-power-aoc-k1_1ac712678732` and
`20261109T204015Z_m5pro-d9p2-power-aoc-k3_839b40f0bfa8`, launched at commit `f5d8d4b` (clean),
Ollama 0.40.11, the model digest and packages recorded in each file. Pre-run check: 2024 d1,
`--trials 3`, 6/6, example verdicts filled (`m5pro-precheck-2026-11-09`).

| | Part 1 | Part 2, trials that reached it | Part 2, all trials | Part 2 solved by a first draft |
|---|---|---|---|---|
| k1 | 15/20 | **5/15 (33%)** | 5/20 | 3/15 |
| k3 | 20/20 | **13/20 (65%)** | 13/20 | 13/20 |

**Registered reading: inconclusive.** k3 is 32 points above k1 (95% Newcombe interval −1 to +56
points), one-sided Fisher p = 0.065, short of 0.05 and more than 10 points apart. Arm 1 is
neither re-established nor ruled out on this cell, and its status is not restated.

Two comparisons beside the registered one, reported and not tested as readings: over all trials,
13/20 against 5/20 (p = 0.012), which also counts k1's five Part 1 failures; and by first draft,
13/20 against 3/15 (p = 0.010). The registered test used trials that reached Part 2, so these do
not change the reading.

**Power fell short of the design.** Part 1 failed in 5 of the k1 trials (no candidate), against
about 2 assumed, so k1 reached Part 2 15 times instead of about 18. k3 solved Part 1 in all 20,
consistent with three drafts lifting Part 1 too.

**Independence check: consistent.** Across both arms, first drafts solved Part 2 20 times in 75
(p̂ = 27%; k1 3 of 15, k3 17 of 60). Independent draws then predict 1 − 0.73³ = 61% at k3; the
measured 65% (13/20) lies inside its 95% Wilson interval (43% to 82%). A k3 draft succeeded as
often as a k1 draft, so three drafts behaved as three independent tries.

**Repair** rescued 2 of the 12 k1 trials whose first draft failed. In k3, repair ran only on the 7 trials where all three drafts
failed, and rescued none.

**Time and tokens** (Part 2 only, solved trials as the denominator): k1 1,467 s and 98,510 tokens
per solve, k3 1,771 s and 125,331. Three drafts cost about a fifth more per solve here and solved
more trials. The run took 11.9 hours (k1 3.0, k3 9.0), against about 14 estimated.

**Example verdicts** (one worked example per part):

| | examples passed | examples failed |
|---|---|---|
| Part 1, oracle solved | 51 | 0 |
| Part 1, oracle wrong | 0 | 39 |
| Part 2, oracle solved | 21 | 1 |
| Part 2, oracle wrong | 22 | 34 |
| Part 2, timed out on the full input | 37 | 11 |

On Part 1 the example agreed with the oracle on all 90 verified attempts. On Part 2 it passed 59
of the 104 attempts the oracle rejected: 37 that then timed out on the full input (the
passed-example-then-timeout pattern) and 22 that gave a wrong answer. It rejected one correct
answer. Every Part 2 error was a timeout (48 of 48). Attempts without a candidate to verify (14)
carry no verdict.
