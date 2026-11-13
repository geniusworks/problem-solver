# m5pro-64: speed-directed repair on 2025 d9 p2 — inconclusive

**Status (2026-11-12): run and read.** Off 8/35, on 12/35: one-sided Fisher p = 0.21, 11 points
apart, so by the registered readings **inconclusive**, and `targeted_feedback` stays off for AoC
2026. The whole gap is in first drafts (4 against 10), which the flag cannot touch; repair rescued
4 trials with it off and 2 with it on, and none of the 43 repairs that followed a timeout or a
memory-cap stop solved, 7 of them with the speed guidance. Two "on" blocks were rerun under the
registered harness-failure rule (below). Design, prediction and readings below were registered
before launch (#72) and are unchanged.

> **2026-11-12, later: two "on" blocks meet the registered harness-failure rule.** Replaying this
> run through the solver showed that 6 attempts recorded as crashes ("Process failed: Unknown
> error") were timeouts: the memory watchdog in force since 2026-11-11 checks the 60 s timeout
> every 0.2 s, and the CPU-time limit, also 60 s, could kill a program that kept a core busy
> before the check came round. Re-executed under the fix (the CPU limit now sits 10 s above the
> timeout), all 6 time out at 60.1 to 60.2 s. One is in the off arm and five in the on arm; three
> of those five were followed by a repair, which therefore went without the speed guidance, in
> blocks on-b5 (trial 4) and on-b6 (trial 3). The rule fixed in advance makes such a block a
> harness failure, rerun whole. With the six counted as timeouts, the on arm had 13 timed-out
> attempts and the off arm 13, the speed guidance should have reached 8 repair prompts, and none
> of 43 repairs after a timeout or memory-cap stop solved. The reading below stands until the
> two blocks are rerun (approved by the maintainer).
>
> **Rerun the same day:** blocks on-b5 and on-b6 were rerun whole after the fix, and the figures
> on this page count the rerun in their place. Each block gave 2/5, as the original blocks did, so
> the arm stays at 12/35 and the reading stands. In the rerun every timed-out attempt carried the
> speed guidance and none was recorded as a crash. The superseded result files are kept outside
> the export (`dev/experiments/superseded/`, local like every result file). One race-affected
> attempt remains, in the off arm (off-b4 trial 1, recorded as a crash; its repair stopped again);
> the off arm takes no guidance, so the rule does not apply to it.

A first launch at 21:28 PST on 2026-11-11 was stopped within a minute, before any result was
written: its "off" block reported fingerprint `619ec3965b58` instead of `80b37d599dd8`, because
the `--config` parser read `targeted_feedback=false` as the truthy string "false". Fixed in #76
before the relaunch at 21:32, which reports the registered fingerprints.

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
  (`--include-replay` saved only code until 2026-11-12, so the check below reads the feedback each
  failed attempt recorded, which is the text the repair prompt was given.)
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

Run 2026-11-11 21:32 to 2026-11-12 06:26 PST on `m5pro-64` from `e613910`, clean tree, Ollama
0.40.11, the 14 blocks in the registered order. Blocks on-b5 and on-b6 were rerun on 2026-11-12,
15:35 to 16:44 PST, from `29767ef` (the timeout fix and the solver split, behaviour checked by
replay; the `--trials 3` pre-run check after the fix gave 6/6 from `edd1733`), and replace the originals. Every trial carries
its arm's fingerprint. 8.8 GPU-hours as counted, and 1.3 more in the two superseded blocks.

| | off | on |
|---|---|---|
| solved | 8/35 (23%) | 12/35 (34%) |
| by the first draft | 4 | 10 |
| by repair | 4 | 2 |

**Reading: inconclusive.** On is 11.4 points above off (95% Newcombe interval −10 to +31), with a
one-sided Fisher p = 0.21: not the p < 0.05 of "helps", and not under the 10 points of "not shown to
help". The flag stays off for AoC 2026.

**The gap did not come from the guidance.** `targeted_feedback` changes one thing, the feedback
written into a repair prompt (`shared/solver.py`, the execution-feedback builder); first drafts
are produced identically in both arms. First drafts solved 10 trials with it on and 4 off,
sampling variation between arms that differ only after the draft (one-sided Fisher p = 0.067 for
10 against 4), and that difference is more than the whole gap. Repair, where the flag acts,
rescued fewer trials with it on (2 of 25 failed drafts) than off (4 of 31). The off arm repeats the replication's one-draft arm, same fingerprint: 8/35
now, 13/35 then (one-sided p = 0.15).

### Did it fire

In the "on" arm the speed guidance was in the recorded feedback of all 11 timed-out attempts and
the wrong-answer guidance in all 29 wrong answers; the "off" arm's feedback carried neither.
Feedback on a trial's last attempt reaches no repair, so the speed guidance reached 7 repair
prompts and the wrong-answer guidance 22.

**What the registration did not foresee: most slow drafts now stop at the memory cap.** The cap
(8 GB of physical footprint, in force since 2026-11-11) stopped 16 attempts in the off arm and 21
in the on arm, against 12 and 11 timeouts. Drafts that grow without bound reach 8 GB before the 60 s
limit: in the replication's 600 s re-run, 26 of the 45 timed-out drafts hit the cap, most within
10 s. The speed guidance is keyed to the timeout, so
a memory-cap stop gets the plain error, with or without the flag. Among first drafts in the on
arm, 9 stopped at the cap and 2 timed out: the case the registration counted on, about 11
timed-out drafts per arm, did not occur. The guidance acted mostly on repairs that timed out.

### Where rescues came from

| first draft | off | rescued | on | rescued |
|---|---|---|---|---|
| solved | 4 | | 10 | |
| wrong answer | 23 | 4 | 14 | 2 |
| memory cap | 5 | 0 | 9 | 0 |
| timed out | 2 | 0 | 2 | 0 |
| crashed | 1 | 0 | 0 | |

The off arm's crashed draft is the race-affected attempt in off-b4: a timeout.

### What the repairs did after a time or memory stop

| | off | on |
|---|---|---|
| repairs after a timeout or memory-cap stop | 19 | 24 |
| solved | 0 | 0 |
| stopped again (cap or timeout) | 13 | 15 |
| answered wrong | 2 | 3 |
| crashed or returned no code | 4 | 6 |

Counting off-b4's race-affected draft as the timeout it was adds one off repair, which stopped
again: 0 of 44. The 7 repairs that received the speed guidance: 3 timed out again, 3 answered
wrong, 1 crashed.

### Would a higher memory cap have helped? (exploratory, not registered)

All 35 attempts the 8 GB cap stopped in the run as first recorded (before on-b5 and on-b6 were
rerun), drafts and repairs in both arms, were re-executed from their saved code, one at a time, under the same 60 s limit and a 24 GB cap (with an 8 GB
free-memory floor), on 2026-11-12:

```
venv/bin/python dev/rerun_timeouts.py --stopped-by memory --all-stages --timeout 60 --jobs 1 \
    --max-memory-gb 24 --min-free-gb 8 dev/experiments/*_m5pro-d9p2-speed-*.json
```

None finished correctly. 29 passed 24 GB as well, all within 10 to 36 s, and the other 6 were
still running at 60 s. The 8 GB cap cost no solve here: these programs fail by growing, not by
needing a little more room, and the fix would have to be the algorithm.

### Time, tokens and example verdicts

| | off | on |
|---|---|---|
| GPU time | 4.3 h | 4.5 h |
| time per solve | 1,932 s | 1,344 s |
| tokens per solve | 147,205 | 96,541 |

Per solve the on arm was cheaper because it had more solves, which came from first drafts.

The worked example passed 44 of the 81 attempts the oracle rejected in the off arm and 31 of 64 in
the on arm, and rejected 1 of the 20 correct attempts across both.

### What this means

On 2025 d9 p2 under the corrected harness, nothing measured here says the guidance helps, and
nothing rules out a moderate effect: the interval runs to +31 points. The more useful finding is
about the failure itself. Repair after a slow draft rescued none of 43 attempts here, none of 11
trials in the replication's one-draft arm, and a longer limit rescued none of 45 drafts there. The
drafts that fail by speed on this problem fail by an approach that does not scale, and neither
more time, more memory nor a repair told to find a faster algorithm turned one into a solve.
That is how the puzzles are built: Advent of Code states that "every problem has a solution that
completes in at most 15 seconds on ten-year-old hardware" (adventofcode.com/about), so a program
still running at the 60 s limit on this machine is not a near-miss but the wrong algorithm.
Whether the guidance should also fire on a memory-cap stop is a code change with its own test
before it could be used; it is not adopted for AoC 2026.

### Reproducing

The blocks were run by a local script holding the registered order; each block is the command
above with its name and flag, and so were the reruns of on-b5 and on-b6. Exported with `dev/export_results.py`; the tables are in
`dev/results/` under the run names `m5pro-d9p2-speed-off-b1` to `-on-b7`.
