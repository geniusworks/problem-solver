# Results: measuring whether coordinating LLM attempts beats a single one

**A research platform, and what it measured.** Local language models propose Python solutions to
Advent of Code problems; an exact oracle executes each candidate against the real puzzle input and
compares it to the accepted answer. Because that check is cheap and exact, orchestration strategies
can be A/B'd for a real delta over repeat trials.

## The short answer

- **The biggest effect was the harness.** Until 2026-10-13 every Part 2 was posed without its
  Part 1 statement, and the model appeared to fall off a cliff between the two parts. With the
  statement in the prompt, single drafts on 13 Part 2s the reference had failed went from 2 of 53
  trials solved to 29 of 37; in the controlled test, 2024 d19 p2, from 6/20 to 19/19. What looked
  like a capability limit was mostly missing information. The puzzles are public, so the added
  text may also cue recall; that is not yet separated (see contamination).
- **Sampling helps where a single draft succeeds part of the time, and the draws behave as
  independent.** Under the original harness, three attempts with repair took the model's
  "sometimes" problems from 42% to 75%, replicated on a second year (combined p ≈ 0.005). Under the
  corrected harness most problems are solved by nearly every draft or by nearly none, three drafts
  gave no measurable lift (9/19 against 11/21), and a powered test on the one mid-rate problem is
  still to run.
- **Choosing the right model beat mixing models.** One of six candidate models solved a problem
  10 of 10 times that the reference solved 1 of 10, and no problem was found the other way, so a
  mix had nothing to add. Repair also depends on the model: 2 of the reference's 145 solves came
  from repair, against 14 of 131 for that candidate.
- **Cheap draws win on time and lose on tokens.** A fast weak model taking four times the draws
  costs 0.64× the wall-clock per solution and at least 3.09× the tokens, and does not reach the
  strong model's ceiling.
- **What still fails is mostly speed.** On the hardest problems the commonest failure is a
  program that runs past the 60 s timeout on the full input, often after passing the example.

**Corpus (2026-11-09):** 89 recorded experiment runs · 3,098 candidate attempts · ~195 GPU-hours ·
38.1M tokens (tables in `dev/results/`; runs that left only a log are not counted; the
token total includes draft counts copied onto repair records before 2026-10-12, see the defect
table) · **69 oracle-verified solutions across two AoC years, 0 wrong in the ledger.**

> **Read the contamination section before the capability numbers.** AoC 2024/2025 solutions predate
> the models used here and are public, so the *capability* results are descriptive of this testbed
> rather than clean measurements. The *orchestration* comparisons — which hold the problems fixed
> and vary the strategy — are largely unaffected.

This document is the consolidated result. The write-ups in [`dev/progress/`](dev/progress/) are
the audit trail, with dated notes where a later run changed a finding. The headline figures
here are recomputed from the run tables in `dev/results/` by `dev/recompute_results.py`, which CI
runs against this file. For the project itself — what it is, how the pipeline works,
how to run it — see the [README](README.md).

---

## The thesis, and what happened to each arm

The project argued three reasons that coordinating several attempts should beat one:

| arm | claim | verdict |
|---|---|---|
| **1. pass@k** | the gap between "sometimes solves" and "solves" never closes at a model's own frontier | ⚠️ **measured and replicated under the original harness; not yet re-established under the corrected one** |
| **2. economics** | many cheap draws + a verifier beat one expensive pass at equal cost | ⚖️ **splits by which cost you pay** |
| **3. portfolios** | diverse models decorrelate error | ➖ **not supported where measured**: the one complementary pair was one-way, so choosing the better model gave the gain |

Each arm is below, after the finding that changed how the others had to be read.

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
| 2025 d9 p2 | 0/22, three models (the reference 0/16) | **3/5** at three drafts |
| 13 other Part 2s the reference had failed, one draft | 2/53 | **29/37** |

The d19 row is the controlled A/B: same machine, a day apart, 20 trials each, the context the
only setting changed, prediction registered. The 13-problem row is broader and less controlled:
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
| 2024 alone | 10/24 → 9/12 | **p ≈ 0.061 — marginal** |
| 2025 replication | 2/8 → 6/6 | **p ≈ 0.009** |
| **combined** (Fisher's method) | | **p ≈ 0.005** |

Neither year alone is decisive; together they are. A 20-trial test on 2024 d19 p2 then showed why
it works: first drafts were correct 16 times in 80 (20%), three independent drafts at that rate
solve 49% of trials, and three drafts solved 50% (`m5pro-d19p2-power.md`). The draws behave as
independent, so sampling's gain follows from the per-draft rate.
*(`passk-ab-d13-d15.md`, `topology-parallel3.md`, `passk-replication-2025.md`.)*

**Under the corrected harness: not yet re-established.** Both bands above were Part 2s posed
without Part 1, and their repair prompts carried mispaired example tests (see the defect table).
Re-run with both fixed, the reference's "sometimes" cells gave 9/19 at one draft and 11/21 at
three, no measurable lift (`m5pro-band-k1-vs-k3-aoc.md`). At the draft level those cells split in
two: solved by 8–9 of 9 drafts, or by 0–1 of 9; the 1-of-6 problem above is solved 3 of 3 at one
draft. Independence predicts exactly this: three draws lift a 10% draft rate little and a 90% one
has no room to rise. One cell, 2025 d9 p2 (3 of 9 drafts), sits where independent draws predict a
real gain, and it has no one-draft comparison yet. That powered test is the open item for this arm.

### Arm 2 — Cheap draws win on time, lose on tokens, and stop at a ceiling

At a matched wall-clock budget, a fast weak model taking many draws vs a slow strong model taking few:

| config | solved | **s / verified solution** | **tokens / verified solution** |
|---|---|---|---|
| `qwen3.8:27b` k=3 (slow, strong) | **8/8** | 1,389 s | **38,460** |
| `qwen3-coder:30b` k=12 (fast, weak) | 7/8 | **891 s** (0.64×) | ≥119,068 (≥3.09×) |

**The answer depends on which cost you actually pay.** For local GPU inference, where cost is
*time*, many cheap draws win by 36% per verified solution. For a token-metered API they lose by
at least 3.09× (a lower bound: the five repair records' own cost was not recorded, see the defect
table). And volume does not close the capability gap — 7/8 vs 8/8.

**The useful form of the claim:** *cheap draws beat one expensive pass when the binding cost is time,
not tokens, and only up to the cheap model's ceiling.* *(`economic-arm-moe-vs-generalist.md`,
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
- `ornith-1.5:35b` met the criterion on 2024 d14 p2 (3/3 against 1/3); the decider put both at
  1/10 (`arm3-precheck-ornith-1-5-35b.md`);
- `gemma4:31b` did not meet it (`arm3-precheck-gemma4-31b.md`);
- **`muse-glimmer:30b` met it and held**: 2024 d14 p2 with 18 of 19 first drafts across two runs,
  10/10 against the reference's 1/10 in the decider, p = 0.0001. It also gave the first verified
  2024 d21 (`arm3-precheck-muse-glimmer-30b.md`).

**The portfolio test.** A mix of 3 drafts from each model is 6 drafts, so it was to be compared
with each model alone at 6; with independent draws, it can beat both only summed over cells where
the better model differs. Muse alone on 14 cells the reference solves (34/42 Part 2 trials) gave
two cells where the reference looked ahead. Neither held: on 2024 d15 p2 the reference solved
0/10, and on d20 p2 it was 9/10 against muse's 6/10, p = 0.15 (`arm3-portfolio-test.md`). No cell
favours the reference, so the ensemble was not run.

**Result:** on these cells the complementarity runs one way. Muse covers what the reference solves
and adds 2024 d14 p2; choosing muse gives the gain a mix could. This does not show that a mix
cannot beat its best member: differences smaller than 9/10 against 4/10 go undetected at 10
trials, and the cells were chosen from the reference's record, not sampled. Of the four leads that
three trials produced, three did not survive ten.

---

## Findings the thesis did not predict

### Repair depends on the model

With true example feedback and too-high/too-low hints, the reference's repairs rescued none of its
hard cells (`m5pro-band-k1-vs-k3-aoc.md`); across all its runs under the corrected harness, 2 of
its 145 solved cells were solved by repair. `muse-glimmer:30b`, in the same harness, solved 14 of
its 131 by repair, among them 3 of its 6 solves of 2024 d20 p2 (`arm3-portfolio-test.md`).

### On the hardest cells the limit is often speed

On the cells the reference fails under the corrected harness, the commonest failure is a run past
the 60 s execution timeout on the full input: 27 of 51 failed attempts on 2024 d24 p2 and 2025 d10
p2 (`m5pro-band-k1-vs-k3-aoc.md`), 9 of 12 on 2025 d9 p2 (`part2-prompt-omits-part1.md`). Many of
those programs passed the worked example first: 11 of the 27 (15 had no example result to compare)
and 6 of the 9. `gemma4:31b` timed out on 19 of 27 attempts at 2025 d10 p2. `muse-glimmer:30b`
timed out rarely (7 of 76 failed attempts on its four entry cells) and failed by crashing or
answering wrong instead (`arm3-precheck-*.md`). Larger models did not move these cells:
`gemma4:31b` and `ornith-1.5:35b` solved neither 2024 d24 p2 nor 2025 d10 p2.

### Model *generation* beats model *size*, decisively

Three models of the same class on the same problems, each **smaller** than the last:

| model | size | class | solved |
|---|---|---|---|
| `qwen2.5-coder:32b` (late 2024) | 19 GB | code specialist | 4/8 |
| `qwen3-coder:30b` (newer, MoE) | 18 GB | code specialist | 6/8 |
| **`qwen3.8:27b` (2026)** | **17 GB** | **generalist** | **8/8** |

The 2024 specialist scored *below* what 12B models had achieved on half the RAM. The winner is the
smallest model and is not a coding model at all. On genuinely hard problems the relationship is
stronger than a gap: the generalist's solve set is a **strict superset** of the specialist's.

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

Read together they gave the project its filter for what to try next:

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

---

## Training-data contamination: the largest threat to validity

**Advent of Code is a contaminated benchmark for any recent model, and this work does not control for
it.** The problems used here are AoC **2024 and 2025**; the headline model, `qwen3.8:27b`, was
released in **August 2026**. Community solutions to both years have been public on GitHub, Reddit and
personal blogs since the events ran. It is likely that solutions to these problems — or close
paraphrases — were in the model's training data.

It is the first objection a reader should raise, and it affects the findings unevenly:

**Weakened by contamination — the capability claims.**
The 8/8 sweep of 2024 d4–7, the "generation beats size" ladder, and the 69-solution ledger all
measure *something*, but they cannot distinguish "this model is more capable" from "this model has
seen more of this benchmark". A newer model is both stronger *and* more likely to have ingested the
2024/2025 corpus, and those two explanations are entangled here. **Treat the capability numbers as
descriptive of this testbed, not as a capability measurement.**

**Largely robust to contamination — comparisons that change only the strategy.**
Arm 1 compares *configurations of the same model on the same problems with the same prompt*.
Whatever the model memorized, it memorized identically in both arms, so contamination cannot
explain a difference between k=1 and k=3. Arm 2 compares two models, so its 7/8 against 8/8 shares
the capability caveat; its time-against-tokens split is a cost ratio per solution and less
exposed. The mechanism findings — that sampling converts "sometimes" into "solved", that volume
buys stochastic but not systematic failures — do not depend on the problems being unseen.

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
  aggregates and more robust.
- **Two AoC years**, 2024 and 2025 — a single problem domain with a cheap exact checker, which is
  the regime where this approach works at all.
- **Rates are not comparable across years**: the problem ranges are not difficulty-matched.
- **Arm 2's wall-clock ratio is approximate** — identical configs vary ~16% run-to-run.
- The pass@k arms ran with the repair loop at its default, so they measure *k samples + repair*
  rather than textbook pass@k over independent draws.
- **k=5 was not run**, so there is no dose-response curve or saturation point.
- **Adaptive model selection is inert in these experiments.** The live solver ranks models for
  each new problem by their oracle-verified success rate in the learning database, falling back to
  the installed set on a cold start. Every experiment here pins its models with `--config`, so the
  ranking has nothing to choose between and the headline comparisons are unaffected by it. The
  strategy-weight half of the same mechanism is an unimplemented stub.
- **Hardware:** arms 1 and 2 were measured on one machine; a third, M5 Pro / 64 GB (2026-10-12),
  re-measured arm 1 under the corrected harness and measured arm 3. Faster hardware moves the
  capability numbers (larger models fit, execution-timeout "speed walls" move) and arm 2's
  wall-clock economics. Still missing: k=5 for a dose-response curve, and AoC 2026 as a clean
  contamination check.

## Practical recommendations

For a verifier-gated setup like this one (a cheap, exact check picks among candidates), from what
was measured with local models of about 30B:

1. **Spend extra draws where a single draft succeeds part of the time.** Independent draws predict
   that at roughly 25–75% per draft three draws lift the solve rate sharply, and near 0% or near
   100% buy little. The lift was measured under the original harness and is not yet tested at power
   under the corrected one. Measure the per-draft rate first.
2. **Don't count on repair to rescue hard problems.** Feedback with true example results and
   too-high/too-low hints rescued nothing for the reference on its hard cells (2 of its 145 solves
   came from repair); another model's repairs did better (14 of 131). A fresh draft or a different
   model is the more reliable second try.
3. **Check whether failures are timeouts.** Many hard-cell failures are timeouts on the full input,
   often after passing the example. Asking for an efficient algorithm, or allowing more execution time,
   addresses a different limit from a bigger model.
4. **Choose a second model by measurement, not by its maker.** Of six candidates, one reliably
   solved something the reference missed, and no cell was found where the reference reliably beat
   it, so a mix had nothing to add. Measure each model alone on your failure cases and on your
   successes; often one model should replace the other rather than join it.
5. **Confirm any lead with more trials before acting on it.** Three trials found three leads that
   did not survive ten (Ornith on 2024 d14 p2, the reference on 2024 d15 p2 and d20 p2).
6. **Without a cheap checker, none of this is measured.** Consensus here only ranks candidates;
   the oracle decides. Majority voting without a checker is a different arrangement.

## Where this generalizes, and where it doesn't

The mechanism needs a **cheap, exact verifier**. Sampling and repair convert into correctness only
because a check can collapse many guesses to one verified answer. Where that check exists — unit
tests, a compiler, a proof checker, a simulator — the findings should transfer. Where correctness is
subjective or expensive to verify, the coordination has little to grip, and the expectation
is that none of this applies.

## Reproducing

Every result lists its exact command in its `dev/progress/` write-up. Configurations are
fingerprinted, so two runs with different behavior cannot share a hash — the mechanism that caught
a duplicate experiment before it wasted three hours, and that forced behavior changes to be
config-gated so they could be A/B'd at all.

Puzzle inputs, problem text and scraped answers are **not** in this repository (see the README's
[data policy](README.md#data-privacy-and-advent-of-codes-rules)); a fresh clone cannot run the
oracle until you supply your own AoC session.
