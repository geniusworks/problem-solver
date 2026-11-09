# m5pro-64: k1 against k3 on 2025 d9 p2 under the corrected harness — registered, not yet run

**Status (2026-11-09): design and prediction registered before launch.** Results will replace
this line and fill the sections marked *pending*.

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

*pending*
