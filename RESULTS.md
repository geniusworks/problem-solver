# Results: measuring whether coordinating LLM attempts beats a single one

*Report as of 2026-11-11. Its headline figures are recomputed from the run tables by
`dev/recompute_results.py`, which CI runs against this file.*

## Abstract

**Question.** Does coordinating several attempts by a language model (sampling more drafts,
repairing from execution feedback, mixing models) solve more problems than a single attempt, and
at what cost?

**Method.** Local models of about 30B parameters, run through Ollama, write Python solutions to
Advent of Code 2024 and 2025 puzzles. An exact oracle runs each candidate on the real puzzle input
and compares its output with the accepted answer. Configurations are compared over repeat trials
on the same problems; the decisive comparisons were registered (design, prediction and reading
committed before launch). The corpus is 109 runs, 3,654 candidate attempts and about 225
GPU-hours.

**Results.** (1) The largest effect was a defect in the harness: Part 2 prompts omitted the Part 1
statement, and restoring it took single drafts on one problem from 6/20 to 19/19 with nothing else
changed. (2) Under the original harness, three drafts with repair raised the solve rate on the
reference model's "sometimes" problems from 42% to 75%, replicated on a second year; under the
corrected harness that lift was not re-established: on the one problem with a mid-range per-draft
rate, a registered replication gave 13/35 against 16/35 (one-sided p = 0.31). The most consistent
finding about the question itself: in all three registered tests, three drafts did about as well
as independent tries predict from the single-draft rate (52% predicted, 49% measured over 75
three-draft trials), so what extra attempts buy can be estimated in advance, and it is large only
where one attempt succeeds part of the time. (3) One candidate model solved a problem the reference rarely solved (10/10
against 1/10), and no problem was found the other way, so a mix of the two was not run. (4) Repair
contributed 13 of the reference model's 306 solves.

**Limits.** The puzzles and their solutions are public and predate the models, so capability
figures describe this testbed. The headline results rest on one model family, one benchmark and
few problems; several comparisons are single trials; multi-draft rates are selected by the oracle.
Each is detailed under [Scope and limits](#scope-and-limits) and
[contamination](#training-data-contamination-the-largest-threat-to-validity).

## The short answer

- **The biggest effect was the harness.** Until 2026-10-13 every Part 2 was posed without its
  Part 1 statement, and the model appeared to fall off a cliff between the two parts. With the
  statement in the prompt, single drafts on 13 Part 2s the reference had failed went from 2 of 53
  trials solved to 29 of 37; in the controlled test, 2024 d19 p2, from 6/20 to 19/19. The 13 were
  chosen because they had failed, and two smaller settings changed alongside, so the controlled
  test is the cleaner measure. What looked like a capability limit was mostly missing
  information. The puzzles are public, so the added text may also cue recall; that is not yet
  separated (see contamination).
- **Extra attempts pay off as independent tries predict; sampling gained under the original
  harness and was not re-established under the corrected one.** Across the three registered tests,
  three drafts solved 49% of 75 trials where the single-draft rates predicted 52%, so the gain from
  more attempts follows from how often one attempt succeeds. Under the original harness, three attempts with
  repair took the model's "sometimes" problems from 42% to 75%, replicated on a second year
  (combined one-sided p ≈ 0.005). Under the corrected harness most problems are solved by nearly
  every draft or by nearly none, three drafts gave no measurable lift (9/19 against 11/21), and on
  the one mid-rate problem, 2025 d9 p2, the lift was not re-established: an inconclusive powered
  test (p = 0.065), then a registered
  replication at 13/35 against 16/35 (one-sided p = 0.31; 95% Newcombe interval −14 to +30
  points). The draws stayed independent; at 20% per draft, three drafts were expected to add about
  12 points over one draft with repair, which 35 trials per arm cannot separate from zero.
- **A second model helped by being chosen, not mixed.** One of six candidate models solved a
  problem 10 of 10 times that the reference solved 1 of 10, and no problem was found where the
  reference's lead held at ten trials, so a mix had nothing to add on the problems measured and
  was not run. Repair also depends on the model: 13 of the reference's 306 solves came
  from repair, against 14 of 131 for that candidate.
- **Cheap draws win on time and lose on tokens.** A fast weak model taking four times the draws
  costs 0.64× the wall-clock per solution and at least 3.09× the tokens, and solved 7 of 8
  problem-parts against 8 (one trial).
- **What still fails is mostly speed.** On the hardest problems the commonest failure is a
  program that runs past the 60 s timeout on the full input, often after passing the example. On
  2025 d9 p2, none of 45 such drafts finished correctly within 600 s under an 8 GB memory cap.
- **Every multi-draft rate is oracle-selected.** A trial counts as solved when any draft or repair
  matches the accepted answer, so these are the rates of a perfect verifier. Choosing by the worked
  example alone, on 2025 d9 p2, solved 12 of 35 three-draft trials and took a wrong answer in 15.

**Corpus (2026-11-11):** 109 recorded experiment runs · 3,654 candidate attempts · ~225 GPU-hours ·
45.8M tokens (tables in `dev/results/`; runs that left only a log are not counted; the
token total includes draft counts copied onto repair records before 2026-10-12, see the defect
table) · **69 oracle-verified solutions across two AoC years, 0 wrong in the ledger.**

> **Read the contamination section before the capability numbers.** AoC 2024/2025 solutions predate
> the models used here and are public, so the *capability* results are descriptive of this testbed
> rather than clean measurements. The *orchestration* comparisons, which hold the model, prompt and
> problems fixed and vary the strategy, are less exposed: both arms share whatever was memorized.
> Memory can still shift the per-draft rate that sets a strategy's gain, so their effect sizes
> may not carry over to unseen problems; AoC 2026 is the test.

This document is the consolidated result. The write-ups in [`dev/progress/`](dev/progress/) are
the audit trail, with dated notes where a later run changed a finding. For the project itself —
what it is, how the pipeline works, how to run it — see the [README](README.md).

---

## Setup

| | |
|---|---|
| Reference model | `qwen3.8:27b` (27.3B, Q4_K_M) via Ollama; digest recorded in every result file since 2026-11-09 |
| Decoding | temperature 0.7, thinking off; `samples_per_model` drafts per trial (k1 or k3), up to 2 repair rounds |
| Checking | each candidate runs on the full puzzle input in a sandbox (no `.env` secrets; 60 s; 8 GB memory cap from 2026-11-11) and is compared with the accepted answer |
| Machines | M2 Max / 32 GB (Ollama 0.32.11, then 0.32.14) for arms 1 and 2 under the original harness; M5 Pro / 64 GB (Ollama 0.34.4, then 0.40.11) since 2026-10-12 |
| Trials | three per cell unless stated; the registered tests 20 or 35 per arm |
| Data | every run exported to `dev/results/`: runs (configuration, fingerprint, and since 2026-11-09 commit, Ollama version, model digests, machine), trials, attempts (with each execution error's kind); headline figures recomputed by `dev/recompute_results.py` |
| Identity | the fingerprint identifies the configuration; the code and prompt templates are identified by the commit each run records |

Per-run machine, Ollama and package versions are in `dev/benchmarks/cross-machine-results.md`.
Generation is not seeded: the pipeline is non-deterministic by design, and repeat trials are the
control for it.

### Terms and measures

- **Problem-part, or cell:** one part (Part 1 or Part 2) of one day's puzzle, for example
  2025 d9 p2. Rates are reported per cell or pooled over named cells.
- **Draft:** one program generated from the problem prompt. **k1** and **k3** are trials with one
  and three drafts (`samples_per_model`). **Repair:** a further attempt that is shown the failed
  program's execution result; up to two rounds.
- **Trial:** one complete solve attempt on a cell: its drafts, then repairs if every draft failed.
  A trial is **solved** when any of its drafts or repairs outputs the accepted answer on the full
  input. Because the oracle does this choosing, multi-draft rates are those of a perfect verifier.
  "Correct" is per instance: the account's one input and its accepted answer, plus an overfit
  gate against programs that copy example values; it is not a proof of correctness on every
  input.
- **Reached Part 2:** under the corrected harness a trial solves Part 1 first; if that fails, its
  Part 2 is *not reached* and is excluded from Part 2 rates unless stated. The 2025 d9 p2
  replication posed Part 2 directly with a verified Part 1 program, so every trial reached it.
- **Per-draft rate:** the share of first-pass drafts that are correct. If drafts succeed
  independently at rate *p*, a k3 trial is solved by a draft with probability 1 − (1 − *p*)³; the
  **independence check** compares that prediction with the measured k3 rate.
- **Frontier, "sometimes" band, wall:** cells the model solves in some trials and not others; and
  cells it had never solved.
- **Original and corrected harness:** before and after 2026-10-13, when Part 2 prompts gained the
  Part 1 statement, answer and program (`problem_context=aoc`).
- **Registered test:** design, prediction and the reading of each outcome were committed to the
  repository before the run started. Everything else is exploratory.

### Statistical methods

Two solve rates are compared with a **one-sided Fisher exact test** in the predicted direction,
at α = 0.05 for registered tests. Differences are given in percentage points with a **95% Newcombe
hybrid-score interval** (Newcombe, 1998), and single proportions with a **Wilson interval**
(Wilson, 1927); lower bounds are rounded down. Two p-values are combined by **Fisher's method**
where stated, which assumes independent tests. Power was computed exactly for the Fisher test.
p-values of exploratory comparisons are descriptive and not corrected for multiplicity. Trials are
the unit of analysis; attempts within a trial are not independent, so attempt-level rates are
descriptive.

## The thesis, and what happened to each arm

The project argued three reasons that coordinating several attempts should beat one:

| arm | claim | verdict |
|---|---|---|
| **1. pass@k** | the gap between "sometimes solves" and "solves" never closes at a model's own frontier | ⚠️ **measured and replicated under the original harness; not re-established under the corrected one: on its one mid-rate problem, inconclusive (p = 0.065), then not re-established in a registered replication (p = 0.31)** |
| **2. economics** | many cheap draws + a verifier beat one expensive pass at equal cost | ⚖️ **splits by which cost you pay** (one trial on 8 problem-parts) |
| **3. portfolios** | diverse models decorrelate error | ➖ **not supported where measured**: the one complementary pair was one-way, so choosing the better model gave the gain |

Why each arm was expected to hold, as argued before it was measured:

1. **pass@k.** A model samples from a distribution. On problems it can *sometimes* solve, the
   modal answer is not reliably right, but the right one appears among several draws, and a
   verifier can pick it out. A stronger model needs fewer draws, but the gap should reappear at its
   own harder frontier.
2. **Economics.** Where correctness is checkable, many cheap draws plus selection could beat one
   expensive pass at equal or lower cost, a trade that improves as the cost per draw falls.
3. **Portfolios.** Different models have different blind spots; an ensemble wins where their
   mistakes are uncorrelated.


## The harness hid Part 1, and that looked like a capability limit

An Advent of Code Part Two is written as an amendment to Part One and rarely restates the setup.
The harness took only the "Part Two" article, so every Part 2 prompt lacked the rules, the input
format and the worked example. The defect surfaced in the saved drafts of a power test on 2024 d19
p2: of 80 first drafts, the 16 correct ones were exactly the correct subset of the 26 that guessed
the input's format; none of the 54 that did not guess it was correct.

The fix (`problem_context=aoc`, now the default) gives the model what a solver on the site has:
Part One's statement and accepted answer, the trial's own Part One program, and a preview of the
input. Re-run under it:

| | original harness | corrected harness |
|---|---|---|
| 2024 d19 p2, one draft, only the context changed | 6/20 | **19/19** (one-sided Fisher p = 2.6e-6) |
| 2024 d16 p2 | 0/7 | **3/3** |
| 2025 d9 p2 | 0/22, three models, one or three drafts (the reference 0/16) | **31/58** three-draft trials that reached Part 2, three runs |
| 13 other Part 2s the reference had failed, one draft | 2/53 | **29/37** |

The d19 row is the controlled A/B: same machine, a day apart, 20 trials each, the context the
only setting changed, prediction registered; the difference is 70 points (95% Newcombe interval
+42 to +85). The 13-problem row (75 points, +56 to +85) is broader and less controlled:
its "before" trials ran on two machines between August and October, its "after" run also changed
the example source and the analysis temperature, and it counts only trials whose Part 1 was
solved (5 were not). Counting every trial at any number of drafts, those Part 2s were 13/71 on
record and 32/40 after; 11 of the 13 earlier solves came from three-draft trials.

Ten Part 2s the reference had never solved were solved, and the ledger went from 56 to 66. The
Part 1/Part 2 cliff seen in both years' scans is not established; the "walls" that had become
the project's most reproducible results were mostly this defect. One Part 2 remains unsolved by
every model tried, 2024 d24 p2, and most of its failures are timeouts
(`part2-prompt-omits-part1.md`, `m5pro-rescan-part2-aoc.md`).

Arm-to-arm comparisons made under the original harness stand as measurements of that pipeline;
what they rescued or failed to rescue on Part 2s is what had to be re-measured.

## The three arms

### Arm 1 — Sampling at the frontier

**Under the corrected harness: not re-established.** The bands measured under the original
harness (below) were Part 2s posed without Part 1, and their repair prompts carried mispaired
example tests (see the defect table). Re-run with both fixed, the reference's "sometimes" cells
gave 9/19 at one draft and 11/21 at three, no measurable lift (+5 points, 95% Newcombe interval
−24 to +33; `m5pro-band-k1-vs-k3-aoc.md`). At the draft level those cells split in
two: solved by 8–9 of 9 drafts, or by 0–1 of 9; the 1-of-6 problem below is solved 3 of 3 at one
draft. Independence predicts exactly this: three draws lift a 10% draft rate little and a 90% one
has no room to rise. One cell, 2025 d9 p2 (3 of 9 drafts), sat where independent draws predict a
real gain, so it got a registered test at 20 trials per arm (`m5pro-d9p2-power-aoc.md`):

| 2025 d9 p2, trials that reached Part 2 | one draft | three drafts | one-sided Fisher exact |
|---|---|---|---|
| solved | 5/15 (33%) | 13/20 (65%) | **p = 0.065 — inconclusive** |

The difference, 32 points (95% Newcombe interval −2 to +56), missed the registered p < 0.05, so
after this test the arm was neither re-established nor ruled out. Fewer k1 trials reached Part 2
than planned (15, not about 18): Part 1 failed five times at one draft and never at three. The
draws behaved as independent again: first drafts solved Part 2 20 times in 75 (27%), which
predicts 61% at three drafts; 65% was measured.

A registered replication then removed the Part 1 leak: every trial was posed Part 2 with the
verified Part 1 program, 35 trials per arm, the arms alternating in blocks of five
(`m5pro-d9p2-replication.md`):

| 2025 d9 p2, every trial | one draft | three drafts | one-sided Fisher exact |
|---|---|---|---|
| solved | 13/35 (37%) | 16/35 (46%) | **p = 0.31 — not re-established** |

k3 is 8.6 points above k1 (95% Newcombe interval −14 to +30), under the registered 10. The draws
were independent once more: drafts solved 28 times in 140 (20%), which predicts 49% at three drafts;
46% was measured. The prediction failed on the draft rate it assumed (27%), not on independence.
At 20% per draft, three drafts were expected to solve 49% against one draft's 20%; repair lifted
one draft to 37% (it rescued 4 of 26 failed drafts), leaving about 12 points expected and 9
measured, a gap that 35 trials per arm cannot separate from zero: the test was powered for the
34 points the 27% rate predicted. Combining both tests' one-sided p-values by Fisher's method gives
p = 0.10, reported, not deciding.

**Under the original harness: measured, replicated, and explained.** On problems the strongest
model solved only *sometimes* — its own frontier, identified beforehand by an independent
classification:

| approach | solve rate |
|---|---|
| 1 attempt, with self-repair from execution feedback | **42%** |
| 3 attempts, no feedback | **58%** |
| **3 attempts, each with execution feedback** | **75%** |

Each partial configuration beat one attempt with repair, and **the combination beat both.** The
corner with one draft and no repair was not run, so the two levers cannot be separated. The
sharpest case: a problem solved by **1 of 6** single attempts was solved by **3 of 3** runs
combining both.

Repeated on AoC 2025 — never previously measured, and a *less* favorable venue (its frontier was
mostly all-or-nothing rather than near-misses) — the two uncertain problems went **25% → 100%**
(2 of 8 → 6 of 6), while a problem that never solved stayed unsolved and a problem that always
solved was unaffected.

| evidence | rates | one-sided Fisher exact |
|---|---|---|
| 2024 alone | 10/24 → 9/12 (+33 points, 95% interval −1 to +57) | **p ≈ 0.061 — marginal** |
| 2025 replication | 2/8 → 6/6 (+75 points, +23 to +93) | **p ≈ 0.009** |
| **combined** (Fisher's method) | | **p ≈ 0.005** |

2024 alone was marginal; 2025 alone gave p ≈ 0.009 on 14 trials; combined, p ≈ 0.005. Both
tests had their predictions written down before the k3 arm ran. A 20-trial registered test on
2024 d19 p2 then showed why it worked: first drafts were correct 16
times in 80 (20%), three independent drafts at that rate solve 49% of trials, and three drafts
solved 50% (`m5pro-d19p2-power.md`). The draws behave as independent, so sampling's gain follows
from the per-draft rate.
*(`passk-ab-d13-d15.md`, `topology-parallel3.md`, `passk-replication-2025.md`.)*

**The independence check across the three registered tests.** In each, the first-pass drafts of
both arms give a per-draft rate *p*; independent draws then predict 1 − (1 − *p*)³ for a
three-draft trial, compared here with the three-draft arm's rate *before repair* (a trial solved by
one of its three drafts), which is what the prediction is about:

| test | drafts correct | predicted at three drafts | measured, drafts only |
|---|---|---|---|
| 2024 d19 p2, original harness (`m5pro-d19p2-power.md`) | 16/80 (20%) | 49% | 50% (10/20) |
| 2025 d9 p2, power test (`m5pro-d9p2-power-aoc.md`) | 20/75 (27%) | 61% | 65% (13/20) |
| 2025 d9 p2, replication (`m5pro-d9p2-replication.md`) | 28/140 (20%) | 49% | 40% (14/35) |
| **all three, 75 three-draft trials** | | **52%** (39 expected) | **49%** (37) |

Each prediction lies inside the 95% Wilson interval of its measured rate; two measured rates are
above the prediction and one below, with no systematic gap. (The replication's registered check counted its two repair
rescues as well, 46%.) This is the project's most consistent finding about its question: what
extra drafts buy follows from the single-draft rate, so it can be estimated before the compute
is spent, and it is large only where one draft succeeds part of the time. It rests on one model and
two problems, and the intervals are wide (each test is 20 or 35 trials per arm).

### Arm 2 — Cheap draws win on time and lose on tokens

At a matched wall-clock budget, a fast weak model taking many draws vs a slow strong model taking
few, one trial on 8 problem-parts (2024 d4–7):

| config | solved | **s / verified solution** | **tokens / verified solution** |
|---|---|---|---|
| `qwen3.8:27b` k=3 (slow, strong) | **8/8** | 1,389 s | **38,460** |
| `qwen3-coder:30b` k=12 (fast, weak) | 7/8 | **891 s** (0.64×) | ≥119,068 (≥3.09×) |

**The answer depends on which cost you actually pay.** For local GPU inference, where cost is
*time*, many cheap draws win by 36% per verified solution. For a token-metered API they lose by
at least 3.09× (a lower bound: the five repair records' own cost was not recorded, see the defect
table). The weak model also solved one problem-part fewer (7/8 against 8/8), a single-trial
observation, not a measured ceiling.

**The useful form of the claim:** *cheap draws beat one expensive pass when the binding cost is time,
not tokens*, measured once on 8 problem-parts. *(`economic-arm-moe-vs-generalist.md`,
`repair-accounting-unwired.md`.)*

### Arm 3 — Choose the better model; a mix had nothing to add

An ensemble can only pool what its members *differentially* solve. So the entry criterion was to
measure each candidate alone on cells the reference misses, and go on only if it solves something
the reference reliably misses. Because those cells were chosen for the reference's failures, a
fresh candidate is favoured by selection; every lead therefore went to a 10-trial decider that
re-measured both models. Six candidates were tried:

- three earlier pairs failed at entry: complementary solves that were sampling noise, a second model
  that solved a **strict subset** of the first's problems, and one that solved the **same set**
  (`ensemble-samp3-d4-7.md`, `ensemble-precheck-negative.md`, `arm3-precheck-qwen36-35b.md`);
- `ornith-1.5:35b` met the criterion on 2024 d14 p2 (3/3 against 1/3); in the decider it solved
  1 of the 7 trials that reached Part 2, the reference 1/10 (`arm3-precheck-ornith-1-5-35b.md`);
- `gemma4:31b` did not meet it (`arm3-precheck-gemma4-31b.md`);
- **`muse-glimmer:30b` met it and held**: 2024 d14 p2 with 18 of 19 first drafts across two runs,
  10/10 against the reference's 1/10 in the decider (+90 points, 95% Newcombe interval +48 to
  +98; one-sided Fisher p = 0.0001). It also gave the first verified 2024 d21
  (`arm3-precheck-muse-glimmer-30b.md`).

**The portfolio test.** A mix of 3 drafts from each model is 6 drafts, so it was to be compared
with each model alone at 6; with independent draws, it can beat both only summed over cells where
the better model differs. Muse alone on 14 cells the reference solves (34/42 Part 2 trials) gave
two cells where the reference looked ahead. Neither held: on 2024 d15 p2 the reference solved
0/10, and on d20 p2 it was 9/9 against muse's 6/7 over trials that reached Part 2, one-sided
p = 0.44 (9/10 against 6/10 over all trials; `arm3-portfolio-test.md`). No cell was found where
the reference's lead held at 10 trials, so the ensemble was not run.

**Result:** on these cells the complementarity runs one way. Muse solves most of what the reference
solves and adds 2024 d14 p2; choosing muse gives the gain a mix could. This does not show that a mix
cannot beat its best member: differences smaller than 9/10 against 4/10 go undetected at 10
trials, and the cells were chosen from the reference's record, not sampled. Of the four leads that
three trials produced, three did not survive ten.

---

## Findings the thesis did not predict

### Repair depends on the model

With true example feedback and too-high/too-low hints, the reference's repairs rescued none of its
band cells (`m5pro-band-k1-vs-k3-aoc.md`), 2 of 12 failed first drafts on 2025 d9 p2
(`m5pro-d9p2-power-aoc.md`) and 4 of 26 in that test's replication (`m5pro-d9p2-replication.md`);
across all its runs under the corrected harness, 13 of
its 306 solved cells were solved by repair. `muse-glimmer:30b`, in the same harness, solved 14 of
its 131 by repair, among them 3 of its 6 solves of 2024 d20 p2 (`arm3-portfolio-test.md`).

Counted per repair attempt rather than per solve, so that a model with more failed drafts does not
simply get more chances: under the corrected harness the reference's repairs succeeded 13 times in
368, muse's 14 times in 80. On the problems both models repaired, 12 in 358 against 8 in 67. Repair
attempts within one trial are not independent, so these are descriptive rates, not a test.

### On the hardest cells the limit is often speed

On the cells the reference fails under the corrected harness, the commonest failure is a run past
the 60 s execution timeout on the full input: 27 of 51 failed attempts on 2024 d24 p2 and 2025 d10
p2 (`m5pro-band-k1-vs-k3-aoc.md`), and 138 of 249 on 2025 d9 p2 in its replication
(`m5pro-d9p2-replication.md`; 48 of 104 in the power test, where wrong answers were the larger
share). Many of those programs passed the worked example first: 11 of the 27 (15 had no example
result to compare), and 94 of the 138. `gemma4:31b` timed out on 19 of 27 attempts at 2025 d10
p2. `muse-glimmer:30b` timed out rarely (5 of 76 failed attempts on its four entry cells) and
failed by crashing or
answering wrong instead (`arm3-precheck-*.md`). On 2025 d9 p2 a longer limit did not rescue
them: the 45 drafts that timed out in the replication, re-run with 600 s under an 8 GB memory cap,
gave no correct answer (26 hit the cap, 17 were still running, 2 answered wrong;
`m5pro-d9p2-replication.md`). Larger models did not move these cells:
`gemma4:31b` and `ornith-1.5:35b` solved neither 2024 d24 p2 nor 2025 d10 p2.

### The newest, smallest model scored highest

Three models of similar size on the same 8 problem-parts (2024 d4–7, one trial each), each
**smaller** than the last:

| model | size | class | solved |
|---|---|---|---|
| `qwen2.5-coder:32b` (late 2024) | 19 GB | code specialist | 4/8 |
| `qwen3-coder:30b` (newer, MoE) | 18 GB | code specialist | 6/8 |
| **`qwen3.8:27b` (2026)** | **17 GB** | **generalist** | **8/8** |

The 2024 specialist scored *below* what 12B models had achieved on half the RAM. The winner is the
smallest model and is not a coding model at all. Generation, specialisation and architecture
change together across the three, and each ran once, so this describes these models; it does not
isolate generation as the cause. In a separate three-trial run on four harder cells (2024 d15 and
2025 d9, original harness), `qwen3-coder:30b` solved a **strict subset** of what the generalist
solved, 3/12 against 6/12 (`ensemble-precheck-negative.md`).

Two problems the project had written off as impossible fell to this: one to a *better algorithm*
(a topological sort), one to a *plain brute force* that finally ran inside the timeout. They had
been described for months as a single "efficiency ceiling"; they were two different walls.

### Interventions that add no new information did not help

Under the original harness, five hypotheses were falsified by the next run:

1. *Insight problems won't fall to sampling* — falsified (1/6 → 3/3 on an algebra-reformulation problem).
2. *Voting buys execution reliability, not ideas* — falsified by the same problem.
3. *Failure mode predicts whether a problem is sometimes-solvable* — falsified; a crash-class problem
   was "sometimes", three wrong-answer problems were walls.
4. *Correlated draws → raise the temperature* — falsified: 0.7 → 1.0 moved nothing and slightly hurt
   a working problem.
5. *Better-worded repair feedback will help* — falsified, with the guidance verified to have fired
   on 49 of 70 attempts.

Read together they gave the project its filter for what to try next, a heuristic drawn from
these five nulls and not itself tested:

> **Interventions that add no new information do not help, however well-targeted the wording.**
> Temperature added variance without information. Reworded feedback added exhortation without
> information. The things that worked added information: **sampling** contributes independent
> draws, **repair** an actual traceback, and **the Part 1 statement** the problem itself.

The harness fix redrew the evidence under three of them. The problem behind 1 and 2 (2024 d13 p2)
is solved 3 of 3 at one draft, and the 2025 "walls" behind 3 have been solved at least sometimes.
Hypotheses 4 and 5 remain nulls measured on the original harness; 5 also ran with mispaired example
tests. The rule itself held up: the largest gain the project found came from giving the model
information it had been denied. The same split appeared in arm 2, which is unaffected by the
Part 2 defect: four times the draws bought a ~25%-per-draw parsing failure and did not buy a
problem that emitted identical `TypeError`s every time.

---

### Earlier findings, on smaller models

Measured on the 16 GB machine with smaller models, before the reference model and before the
harness fix; each is a committed A/B in `dev/progress/`.

- **Single runs are noise.** Across byte-identical configurations, 4 of 6 baseline problems
  flipped between solved and unsolved, so every comparison here uses repeat trials.
- **Several drafts helped.** At temperature 0.7, three drafts per model lifted the solve rate on
  2024 d1–3 from 39% to 61% and took 0 → 3 of 6 problems to solved in every trial, with the oracle
  choosing among the drafts (`milestone-e-self-consistency.md`).
- **Plurality of executed answers as a selector without the oracle** picked the correct answer 10
  of 11 times on that sample (`milestone-e-answer-consensus.md`).
- **Model capability dominated the hard problems.** On 2024 d4–7 the original 7B baseline solved 1
  of 8; two newer models that also fit 16 GB, `qwen3.5:9b` and `gemma4:12b`, solved 5 of 8
  (`scale-2024-d4-7.md`, `9b-confirmation-d4-7.md`, `model-bakeoff-gemma4-vs-9b.md`).
- **Reasoning models needed thinking switched off.** Left to think, `qwen3.5:9b` emitted tens of
  thousands of characters of reasoning and never reached code; `enable_thinking=false` made it a
  direct coder.

## What the measurements cost in credibility, and why that matters

Roughly half the work behind these numbers was discovering that earlier measurements were wrong.
Twelve instrument defects, each of which made results *look better or worse than reality*:

| defect | effect |
|---|---|
| Unguarded `KeyError` in strategy lookup | **harness crashes scored as model failures** — for eight months; one recorded benchmark reported 2/10 when two problems never ran |
| Overfit gate matched example text in **docstrings** | **rejected a correct, general solution** |
| `init_db` seeded invented performance rows | fabricated data in a measurement store |
| Tests wrote into the live results database | a fake model with a perfect 79/79 record |
| Repair attempts reported the previous generation's tokens | **cost understated exactly where repair is heaviest** |
| Repair ignored the configured temperature | a temperature experiment reached only ~1/3 of generations |
| `success_rate` recorded at generation time, `success=True` for anything that parsed | **the sole signal model ranking used measured "returned code", not "solved the problem"** |
| `StrategyOptimizer` read a second, dead database (0 rows) | strategy effectiveness computed over no data at all |
| That token fix stopped at the provider; the solver kept copying the draft's tokens and time onto every repair record *(found 2026-10-12)* | **642 of 642 repair records wrong, in runs after the "fix" too**; arm 2's 3.35× is really "at least 3.09×" |
| Part 2 prompts carried only the "Part Two" article: no rules, no input format *(found 2026-10-13)* | **on 2024 d19 p2 a draft was right only if it guessed the format (16 of 26 that did, 0 of 54 that did not)**; re-run with the statement, the Part 1/Part 2 cliff and most Part 2 walls dissolved (above) |
| Example tests paired with an illustration instead of the example input *(found 2026-10-13, fixed 2026-10-14)* | a verified program failed its own example test on 25 of 46 audited problems (3 after the fix); solves are unaffected (the oracle decides), **every repair prompt on those problems carried a false failure** |
| A last day's "Part Two" with no puzzle was attempted and scored as a miss *(found 2026-10-12)* | denominators off by one in two scans (16/24, 9/20), and **a nonexistent problem written up as "the first genuinely unseen problem"** |

Each is fixed with regression tests. The sharpest lesson came from a tally accumulated in prose
("0/8… 0/11… never solved once") that turned out to have silently dropped the runs where the problem
*did* solve. It had solved 2 of 16 times, and the contradiction was visible all along: the problem was
in the verified ledger, which it could only be by solving.

The rule adopted: **a tally maintained by addition in prose is not a measurement.** Recompute from
the artifacts.

Three further instrument gaps, found in November 2026, changed no reported solve rate. The
`--config` parser read `targeted_feedback=false` as the string "false", which is truthy, so the
flag could not be switched off from the command line; the one recorded run that set it asked for
it on (`targeted-feedback-negative.md`), and it was caught by a fingerprint mismatch before the
speed-repair test produced any data. Each attempt
record's draft number had held the trial number instead, so drafts within a trial could not be
told apart; it is recorded correctly from 2026-11-10 (`draft_index`). And generated code had no
memory cap on macOS: a runaway draft could slow the machine for up to its 60 s limit, which can
inflate wall-clock times, and six such drafts re-run at once froze it. Every execution path has
stopped a process past 8 GB since 2026-11-11.

---

## Training-data contamination: the largest threat to validity

**Advent of Code is a contaminated benchmark for any recent model, and this work does not control for
it.** The problems used here are AoC **2024 and 2025**; the headline model, `qwen3.8:27b`, was
released in **August 2026**. Community solutions to both years have been public on GitHub, Reddit and
personal blogs since the events ran. It is likely that solutions to these problems — or close
paraphrases — were in the model's training data.

It is the first objection a reader should raise, and it affects the findings unevenly:

**Weakened by contamination — the capability claims.**
The 8/8 sweep of 2024 d4–7, the three-model comparison, and the 69-solution ledger all
measure *something*, but they cannot distinguish "this model is more capable" from "this model has
seen more of this benchmark". A newer model is both stronger *and* more likely to have ingested the
2024/2025 corpus, and those two explanations are entangled here. **Treat the capability numbers as
descriptive of this testbed, not as a capability measurement.**

**Largely robust to contamination — comparisons that change only the strategy.**
Arm 1 compares *configurations of the same model on the same problems with the same prompt*.
Whatever the model memorized, it memorized identically in both arms, so contamination does not
by itself create a difference between k=1 and k=3; it can shift the per-draft rate, which sets the
size of sampling's gain. Arm 2 compares two models, so its 7/8 against 8/8 shares
the capability caveat; its time-against-tokens split is a cost ratio per solution and less
exposed. The mechanism findings — that draws behave as independent, so sampling's gain follows
the per-draft rate; that volume buys stochastic but not systematic failures — do not depend on
the problems being unseen.

**Not covered by that argument — comparisons that change the prompt or the model.**
- *The Part 2 prompt fix.* Adding the Part 1 statement changes the input, not just the strategy.
  The added text carries the rules and input format the model lacked, and it is also the puzzle's
  published wording, which can cue recall of solutions seen in training. The before/after rates
  show the fix works on these puzzles; they cannot show how much is information and how much is
  recall. The saved drafts do show why the old prompt failed: on 2024 d19 p2 none of the 54 first
  drafts that guessed the input format wrong was correct, which is missing information, not
  missing capability. A test that separates information from recall is designed in
  `dev/progress/part2-context-heldout-plan.md`.
- *Model choice (arm 3).* `muse-glimmer:30b` solved 2024 d14 p2 10 of 10 times against the
  reference's 1 of 10. Two models trained on different data may have memorized different puzzles,
  so this compares capability and shares the caveat above.

**A partial argument against pure memorization, offered as weak evidence only.**
Under the original harness the frontier band consisted of problems the model solved *sometimes* —
17%, 25%, 33% per draw (under the corrected harness most of those cells are solved by nearly every
draft or by nearly none, which weakens this argument further).
Memorized solutions would be expected to reproduce reliably rather than intermittently. This is
suggestive, not dispositive: partial or paraphrased memorization could
plausibly produce exactly this intermittency.

**What would actually settle it**, and none of it was done here:
- Evaluate on problems published *after* the model's training cutoff — AoC 2026, in December, would
  be genuinely unseen and is the cheapest clean test available to this project.
- Or use a benchmark with a held-out or contamination-audited split.
- Or compare per-problem solve rates against public solution availability, which would at least
  detect a gross correlation.

## Scope and limits

- **Training-data contamination is uncontrolled** (see the section above) — the single largest threat
  to the capability claims, and the first thing a reader should discount.
- **One strong model** for the headline results; three models compared for the generation finding;
  six candidates measured against it for arm 3.
- **Three trials per cell** in most experiments; solve counts are directional, cost ratios are
  aggregates and more robust. Arm 2 and the generation comparison ran **one trial** on 8
  problem-parts each. The two registered arm-1 tests on 2025 d9 p2 ran 20 and 35 trials per arm.
- **Registered and exploratory results are reported side by side.** Registered tests had their
  design, prediction and reading committed before launch (the d19 p2 power test, the two 2025 d9
  p2 tests, the arm-3 deciders); the original-harness arm-1 tests registered their predictions
  before the k3 arm ran. Everything else, including the three-trial leads and the Fisher
  combinations, is exploratory and uncorrected for the number of comparisons made.
- **Multi-draft rates are oracle-selected.** A trial counts as solved when any draft or repair
  matches the accepted answer, and repair hints (too high, too low) come from that answer. Without
  the oracle the rates are lower: choosing by the worked example alone solved 12 of 35
  three-draft trials on 2025 d9 p2, against 14 for the oracle.
- **Two AoC years**, 2024 and 2025 — a single problem domain with a cheap exact checker, which is
  the regime where this approach works at all.
- **Rates are not comparable across years**: the problem ranges are not difficulty-matched.
- **Few problems carry the main results.** The controlled harness test is one problem; the
  corrected-harness sampling tests are one problem at 20 and 35 trials per arm; the original
  bands are four and two "sometimes" problems. Trials on one problem measure repeatability there,
  not generality across problems.
- **No independent replication.** One maintainer ran every experiment on three machines of one
  hardware family; the 2025 replication and the registered tests guard against chance, not
  against a shared mistake in the harness, of which twelve were found.
- **Arm 2's wall-clock ratio is approximate** — identical configs vary ~16% run-to-run.
- The pass@k arms ran with the repair loop at its default, so they measure *k samples + repair*
  rather than textbook pass@k over independent draws.
- **k=5 was not run**, so there is no dose-response curve or saturation point.
- **Adaptive model selection is inert in these experiments.** The live solver ranks models for
  each new problem by their oracle-verified success rate in the learning database, falling back to
  the installed set on a cold start. Every experiment here pins its models with `--config`, so the
  ranking has nothing to choose between and the headline comparisons are unaffected by it. The
  strategy-weight half of the same mechanism is an unimplemented stub.
- **Hardware:** arms 1 and 2 were measured on one machine, the M2 Max / 32 GB; a third, M5 Pro /
  64 GB (2026-10-12), re-measured arm 1 under the corrected harness and measured arm 3. Faster
  hardware moves the capability numbers (larger models fit, execution-timeout "speed walls" move) and arm 2's
  wall-clock economics. Still missing: k=5 for a dose-response curve, and AoC 2026 as a clean
  contamination check.

## Practical recommendations

For a verifier-gated setup like this one (a cheap, exact check picks among candidates), from what
was measured with local models of about 30B:

1. **Extra draws can only pay where a single draft succeeds part of the time.** Independent draws predict
   that at roughly 25–75% per draft three draws lift the solve rate sharply, and near 0% or near
   100% buy little. The lift was measured under the original harness; under the corrected one, on
   the one mid-rate problem (20% per draft), it was not re-established (37% → 46%, p = 0.31):
   repair already lifted the single draft there. Measure the per-draft rate first, and compare
   against one draft with repair, not one draft alone.
2. **Don't count on repair to rescue hard problems.** Feedback with true example results and
   too-high/too-low hints rarely rescued the reference (13 of its 306 solves came from repair);
   another model's repairs did better (14 of 131). A fresh draft or a different
   model is the more reliable second try.
3. **Check whether failures are timeouts.** Many hard-cell failures are timeouts on the full input,
   often after passing the example. Asking for an efficient algorithm addresses a different limit
   from a bigger model; more execution time did not help on 2025 d9 p2 (none of 45 timed-out
   drafts finished correctly within 600 s). Cap memory as well as time: those drafts grow past
   8 GB in seconds.
4. **Choose a second model by measurement, not by its maker.** Of six candidates, one reliably
   solved something the reference missed, and no cell was found where the reference reliably beat
   it, so a mix had nothing to add. Measure each model alone on your failure cases and on your
   successes; often one model should replace the other rather than join it.
5. **Confirm any lead with more trials before acting on it.** Three trials found three leads that
   did not survive ten (Ornith on 2024 d14 p2, the reference on 2024 d15 p2 and d20 p2).
6. **Without a cheap checker, none of this is measured.** Consensus here only ranks candidates;
   the oracle decides. Majority voting without a checker is a different arrangement.

## Where this generalizes, and where it doesn't

**Two conditions, read together.** Two measured findings combine into one statement about when
extra attempts pay. First, what extra attempts can add is set by how often one attempt succeeds:
three drafts did about as well as independent tries predict (52% predicted, 49% measured over 75
trials), so the room is large only in the middle and small near 0% or 100%. Second, that room is
realised only if something can pick the right attempt out: with the exact oracle, three drafts
solved 14 of 35 replication trials before repair; choosing by the worked example alone solved 12
and took a wrong answer in 15. So extra attempts help where one attempt succeeds part of the time
*and* a check can tell right from wrong. This is a synthesis of two findings, measured on one
model and two problems, not a separately tested claim.

The rest of this section is argued, not measured: every experiment here used one benchmark with an exact
checker. The mechanism needs a **cheap, exact verifier**. Sampling and repair convert into
correctness only because a check can collapse many guesses to one verified answer. Where that
check exists — unit tests, a compiler, a proof checker, a simulator — the findings may transfer,
though a partial checker lets wrong candidates through: on 2025 d9 p2 the worked example alone
passed 137 of the 249 attempts the oracle rejected. Where correctness is subjective or expensive
to verify, the coordination has little to grip, and the expectation is that none of this applies.

## Related work

Sampling several programs and counting a problem solved when any passes a check is pass@k
evaluation (Chen et al., 2021). Choosing among samples without ground truth has been done by
agreement between samples (self-consistency; Wang et al., 2023), by filtering on the problem's
example tests (AlphaCode; Li et al., 2022) and by agreement on model-generated tests (CodeT;
Chen et al., 2023). Here an exact oracle does the choosing, so the multi-draft rates are upper
bounds on what such selectors reach; the example-only selector measured on 2025 d9 p2 is the
filter-on-examples case, and one worked example let through more wrong drafts than right ones.
Under the original harness three fresh drafts beat one draft with repair (58% against 42%), and
repair produced few of the reference model's solves; that is in line with Olausson et al. (2024),
who find self-repair gains modest once the cost of repair is counted. Contamination of code
benchmarks by public solutions is a known threat; the planned AoC
2026 run follows the usual remedy of evaluating on problems released after the models.

The contribution here is not a new method. It is a set of repeated, partly registered
measurements of these levers on one model's own frontier, an account of the harness defects that
had to be removed before the measurements meant anything, and the negative results that followed.

## Data and code availability, and reproducing

- **Code and configuration:** this repository; each result's write-up in `dev/progress/` gives
  its exact command, and every result file records the commit, Ollama version, model digest and
  package versions it ran with (since 2026-11-09). Packages are pinned in `requirements.lock`.
- **Data:** per-run, per-trial and per-attempt outcomes, timings, token counts, example verdicts
  and execution-error kinds for all 109 runs are in `dev/results/`, with each run's commit, Ollama
  version, model digests and machine where recorded (since 2026-11-09).
  `venv/bin/python dev/recompute_results.py` recomputes this document's headline figures from
  those tables, and CI fails when the two disagree.
- **Not public:** puzzle text, puzzle inputs and accepted answers (Advent of Code asks that they
  not be redistributed), and therefore the raw result files, whose saved prompts contain puzzle
  text. A fresh clone cannot run the oracle until you supply your own AoC session (see the
  README's [data policy](README.md#data-privacy-and-advent-of-codes-rules)). Re-executing saved
  drafts, as in the 600 s timeout re-run, needs those inputs and cannot be repeated from the
  repository alone.
- **Determinism:** generation is unseeded, so a re-run reproduces rates within sampling error,
  not individual outcomes.

Configurations are fingerprinted, so two runs with different behavior cannot share a hash — the
mechanism that caught a duplicate experiment before it wasted three hours, and that forced
behavior changes to be config-gated so they could be A/B'd at all.

## References

- Chen, B., Zhang, F., Nguyen, A., Zan, D., Lin, Z., Lou, J.-G., & Chen, W. (2023). CodeT: Code
  generation with generated tests. *ICLR 2023*. arXiv:2207.10397.
- Chen, M., Tworek, J., Jun, H., et al. (2021). Evaluating large language models trained on code.
  arXiv:2107.03374.
- Fisher, R. A. (1925). *Statistical Methods for Research Workers*. Oliver and Boyd. (Exact test;
  combination of probabilities.)
- Li, Y., Choi, D., Chung, J., et al. (2022). Competition-level code generation with AlphaCode.
  *Science*, 378(6624), 1092–1097.
- Newcombe, R. G. (1998). Interval estimation for the difference between independent proportions:
  comparison of eleven methods. *Statistics in Medicine*, 17(8), 873–890.
- Olausson, T. X., Inala, J. P., Wang, C., Gao, J., & Solar-Lezama, A. (2024). Is self-repair a
  silver bullet for code generation? *ICLR 2024*. arXiv:2306.09896.
- Wang, X., Wei, J., Schuurmans, D., Le, Q., Chi, E. H., Narang, S., Chowdhery, A., & Zhou, D.
  (2023). Self-consistency improves chain of thought reasoning in language models. *ICLR 2023*.
  arXiv:2203.11171.
- Wilson, E. B. (1927). Probable inference, the law of succession, and statistical inference.
  *Journal of the American Statistical Association*, 22(158), 209–212.
