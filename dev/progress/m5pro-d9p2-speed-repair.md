# m5pro-64: speed-directed repair on 2025 d9 p2 — registered, not yet run

**Status (2026-11-11): design, prediction and readings registered before launch.** Results will
replace this line and fill the section marked *pending*.

## Why this test

On the hardest cells under the corrected harness the commonest failure is a program that passes
the worked example and then runs past the 60 s limit on the full input. On 2025 d9 p2, 94 of the
replication's 138 timeouts had passed the example first (`m5pro-d9p2-replication.md`). A longer
limit does not rescue them: re-run at 600 s under an 8 GB memory cap, none of the 45 timed-out
drafts finished correctly. Repair does not rescue them either. In the replication's one-draft arm,
11 of 35 first drafts timed out, and repair rescued **none** of those 11 trials; its 4 rescues all
came from drafts that answered wrong.

Today a timed-out draft's repair prompt says only that the full-input run errored. The solver
already carries guidance for this case (`_efficiency_guidance` in `shared/solver.py`, behind
`targeted_feedback`): it says the failure is one of performance, that the approach works on the
example but does not scale, not to resubmit the same algorithm, and to find an asymptotically
faster one and state both complexities. It has never run where it matters: its one test was under
the original harness, where 2025 d9 p2 did not time out (`targeted-feedback-negative.md`). PLAN's
condition for testing it, the passed-example-then-timeout pattern in the recorded verdicts, is met
on this cell.

**What the flag also changes.** `targeted_feedback` turns on wrong-answer guidance too
(`_wrong_answer_guidance`: a clean-running wrong answer usually means a misread requirement). That
part was a null under the original harness (6/12 → 5/12). This test measures the flag as it
exists, both parts together; the secondary measures below separate where any rescue came from.

## Design

- **Arms:** `targeted_feedback=false` (off) and `targeted_feedback=true` (on), **35 trials each**.
- **Config, both arms:** `samples_per_model=1, models=qwen3.8:27b, temperature=0.7,
  enable_thinking=false, enable_fallback_models=false, gate_part_two=false`, other settings at
  their defaults (`problem_context=aoc`, `example_tests=page`, `max_repair_iterations=2`).
  Fingerprints `80b37d599dd8` (off; the replication's one-draft arm) and `a94e453a5791` (on).
  One draft per trial, so the guidance acts through repair alone.
- **Problem:** `2025:9.2` alone, posed as in the replication: Part 1's statement, accepted answer,
  the recorded oracle-verified Part 1 program and an input preview. Every trial reaches Part 2.
- **A fresh control arm.** The replication's one-draft arm has the same fingerprint, but it ran
  before the memory cap (2026-11-11) and at different times; both arms run now, interleaved.
- **Order:** seven blocks of five trials per arm, alternating off, on, on, off, off, on, on, off,
  off, on, on, off, off, on. Each block is its own run (`m5pro-d9p2-speed-off-b1` to `-b7`,
  `m5pro-d9p2-speed-on-b1` to `-b7`), pooled by name for the analysis.
- **No stopping early, no extension.** All 70 trials run. A block that fails for a reason outside
  the model (a harness error, a crash of Ollama or the machine) is rerun whole and the failure is
  reported; trials are never dropped for their outcome. If an "on" block has a timed-out draft
  whose repair prompt lacks the guidance, the flag did not take effect: the block is a harness
  failure and is rerun.
- **Machine:** `m5pro-64`, Ollama 0.40.11, packages from `requirements.lock`, the 8 GB memory cap
  in force; each result file records its environment.
- **Before launch:** none beyond today's state. The guidance is covered by unit tests
  (`tests/unit/test_targeted_feedback.py`: it fires on a timeout, not on a crash or a wrong answer,
  and adds the scaling note only when the example passed), and the memory cap's pre-run check gave
  6/6 on 2026-11-11 from `370ec58`.
- **Drafts are saved** (`--include-replay`), so each repair prompt can be checked for the guidance.
- **Expected time:** about 8–9 GPU-hours, from the replication's one-draft trials (about 430 s
  each); repairs under guidance may run longer.

Each block, with `T` `false` or `true`, `A` `off` or `on`, and `B` the block number (1 to 7):

```
venv/bin/python experiment.py --problems 2025:9.2 --trials 5 --include-replay \
  --config "name=m5pro-d9p2-speed-A-bB,samples_per_model=1,models=qwen3.8:27b,temperature=0.7,enable_thinking=false,enable_fallback_models=false,gate_part_two=false,targeted_feedback=T"
```

## Prediction (registered before launch)

From the replication's one-draft arm: 13/35 solved, 9 by the draft and 4 by repair, 11 drafts
timed out and none of those trials was rescued.

| | predicted | expected, of 35 trials |
|---|---|---|
| off | about 37% | about 13, plausibly 8 to 19 |
| on | about 46% | about 16, plausibly 10 to 22 |

The "on" figure assumes the guidance rescues about a third of the roughly 11 trials whose draft
times out, and leaves wrong-answer rescues unchanged. That is a guess, not an estimate: nothing
measured on this cell bounds it.

**Power:** a one-sided Fisher exact test at α = 0.05 with 35 trials per arm detects 37% against
46% only about 14% of the time; against 60% about 56%, against 70% about 85%. **This test can
detect a large effect, not the predicted one.** A modest gain will most likely read as
inconclusive. Doubling to 70 trials per arm (about 17 GPU-hours) would raise power against 60% to
about 83%, and was not chosen: the decision this test serves is whether the guidance is worth
switching on for AoC 2026, which a large effect would justify and a modest one would not.

## Readings, fixed in advance

Rates are over all 35 trials per arm.

| outcome | reading | for AoC 2026 |
|---|---|---|
| on above off, one-sided Fisher p < 0.05 | **Speed-directed repair helps on this cell.** | Switching `targeted_feedback` on for the AoC 2026 runs becomes a maintainer decision before the freeze; it changes their fingerprint. |
| on less than 10 points above off | **Not shown to help** on this cell. | The flag stays off. |
| anything else | **Inconclusive**; report the interval. | The flag stays off. |

**Reported beside the reading, not deciding it:**
- **Did it fire:** in the "on" arm, how many repair prompts carried the speed guidance and how many
  the wrong-answer guidance.
- **Where rescues came from:** in each arm, trials rescued by repair, split by whether the draft
  timed out or answered wrong. The speed guidance can act only on the first group.
- **What the repairs did:** of repairs after a timeout, how many timed out again, answered wrong
  or solved.
- Time and tokens per solve in each arm.
- The example verdicts, as in the replication.

## Result

*pending*
