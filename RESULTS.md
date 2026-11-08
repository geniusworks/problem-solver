# Results: measuring whether coordinating LLM attempts beats a single one

**A research platform, and what it measured.** Local language models propose Python solutions to
Advent of Code problems; an exact oracle executes each candidate against the real puzzle input and
compares it to the accepted answer. Because that check is cheap and exact, orchestration strategies
can be A/B'd for a real delta over repeat trials.

**The finding.** Letting a local model make several attempts at a problem and fix its
own errors solved far more of them than a single attempt did — **42% → 75%** on the problems it finds
hardest — and the same pattern held on a second year the models had never been tested on. Because the
puzzles are public, the raw *"how capable is the model"* numbers carry a caveat (below); the *"does
coordinating attempts help"* comparisons pit the model against itself and are unaffected.
*Narrowed 2026-11-01:* under the corrected prompts, most problems are solved by nearly every draft
or by nearly none, and three drafts beat one only where a single draft succeeds part of the time
(arm 1 below). *Measured 2026-11-08:* mixing models from different makers did not beat choosing
the better one (arm 3).

This document is the consolidated result. The write-ups in [`dev/progress/`](dev/progress/) are
the audit trail; every figure here was recomputed from the run artifacts. For the project itself —
what it is, how the pipeline works, how to run it — see the [README](README.md).

**Corpus (2026-11-08):** 88 recorded experiment runs · 3,086 candidate attempts · ~195 GPU-hours ·
38.0M tokens (result files in `dev/experiments/`; runs that left only a log are not counted; the
token total includes draft counts copied onto repair records before 2026-10-12, see the defect
table) · **68 oracle-verified solutions across two AoC years, 0 wrong in the ledger.**

*Found and fixed 2026-10-13: every Part 2 in this report was posed without the Part 1 statement
(`dev/progress/part2-prompt-omits-part1.md`). Arm-to-arm comparisons are unaffected as
measurements; the Part 1/Part 2 cliff and the Part 2 walls are not established as capability
findings until re-run. First re-runs, 2026-10-13: with the statement in the prompt, 2024 d19 p2
went from 6/20 to 19/19 and 2024 d16 p2 from 0/7 to 3/3. 2025 d9 p2, 0/22 before, is 3/5 at three
drafts under the new defaults (2026-10-31). The reference's 15 other failing Part 2s went from
13/71 to 32/40 (2026-11-01, `dev/progress/m5pro-rescan-part2-aoc.md`), so the cliff is not
established.*

*Since this report was first written (2026-08-23), runs on a third machine, `m5pro-64`, took the
ledger to 68, narrowed arm 1 and measured arm 3; the dated notes below mark each change. Live
status: `dev/progress/checkpoint.md`.*

> **Read the contamination section before the capability numbers.** AoC 2024/2025 solutions predate
> the models used here and are public, so the *capability* results are descriptive of this testbed
> rather than clean measurements. The *orchestration* comparisons — which hold the model and problems
> fixed and vary only the strategy — are largely unaffected.

---

## The thesis, and what happened to each arm

The project argued three reasons that coordinating several attempts should beat one. All three have
now been tested.

| arm | claim | verdict |
|---|---|---|
| **1. pass@k** | the gap between "sometimes solves" and "solves" never closes at a model's own frontier | ✅ **confirmed and replicated**; narrowed 2026-11-01: it pays only where a single draft succeeds part of the time |
| **2. economics** | many cheap draws + a verifier beat one expensive pass at equal cost | ⚖️ **splits by which cost you pay** |
| **3. portfolios** | diverse models decorrelate error | ➖ **not supported where measured**: the one complementary pair was one-way, so choosing the better model gave the gain (2026-11-08) |

### Arm 1 — Sampling works at the frontier, and why it works is measured

On problems the strongest model solves only *sometimes* — its own frontier, identified beforehand by
an independent classification:

| approach | solve rate |
|---|---|
| 1 attempt, with self-repair from execution feedback | **42%** |
| 3 attempts, no feedback | **58%** |
| **3 attempts, each with execution feedback** | **75%** |

Sampling helps, repair helps, and **together they exceed the sum of their parts.** The sharpest
case: a problem solved by **1 of 6** single attempts was solved by **3 of 3** runs combining both.

**Replicated out of sample.** Repeated on AoC 2025 — never previously measured, and a *less*
favorable venue (its frontier is mostly all-or-nothing rather than near-misses) — the two uncertain
problems went **25–33% → 100%**, while a problem that never solves stayed unsolved and a problem
that always solves was unaffected. Sampling rescued exactly the uncertain cases and nothing else,
which is the signature of a mechanism rather than a rate artifact.

**The statistics:**

| evidence | rates | one-sided Fisher exact |
|---|---|---|
| 2024 alone | 10/24 → 9/12 | **p ≈ 0.061 — marginal** |
| 2025 replication | 2/8 → 6/6 | **p ≈ 0.009** |
| **combined** (Fisher's method) | | **p ≈ 0.005** |

**Neither year alone is decisive; together they are.** The 2024 headline standing by itself would
not survive review — the replication is what makes the claim reportable.

*(`passk-ab-d13-d15.md`, `topology-parallel3.md`, `passk-replication-2025.md`.)*

**Narrowed 2026-11-01, under the corrected prompts.** Both years' bands were measured with Part 2
posed without its Part 1 statement and with repair prompts carrying mispaired example tests (see
the defect table). Re-run under the site's conditions on a third machine, the reference's
"sometimes" cells gave 9/19 at one draft and 11/21 at three, no measurable lift
(`m5pro-band-k1-vs-k3-aoc.md`). At the draft level those cells split in two: solved by 8–9 of 9
drafts, or by 0–1 of 9. Independent draws predict exactly this: three draws lift a 10% draft rate
little and a 90% one has no room to rise. The mechanism stands; the band it acts on is smaller
than the 42% → 75% suggested, and under the corrected prompts one cell (2025 d9 p2, 3 of 9 drafts)
sits where sampling pays.

**Repair depends on the model.** With true example feedback and too-high/too-low hints, the
reference's repairs rescued none of its hard cells (`m5pro-band-k1-vs-k3-aoc.md`); across all its
runs under the corrected prompts, 2 of its 145 solved cells were solved by repair. The candidate
`muse-glimmer:30b`, in the same harness, solved 14 of its 131 by repair, among them 3 of its 6
solves of 2024 d20 p2 (`arm3-portfolio-test.md`).

### Arm 2 — Cheap draws win on time, lose on tokens, and stop at a ceiling

At a matched wall-clock budget, a fast weak model taking many draws vs a slow strong model taking few:

| config | solved | **s / verified solution** | **tokens / verified solution** |
|---|---|---|---|
| `qwen3.8:27b` k=3 (slow, strong) | **8/8** | 1,389 s | **38,460** |
| `qwen3-coder:30b` k=12 (fast, weak) | 7/8 | **891 s** (0.64×) | 128,730 (3.35×) |

**The answer depends on which cost you actually pay.** For local GPU inference, where cost is
*time*, many cheap draws win by 36% per verified solution. For a token-metered API they lose by
3.35×. And volume does not close the capability gap — 7/8 vs 8/8.

**The useful form of the claim:** *cheap draws beat one expensive pass when the binding cost is time,
not tokens, and only up to the cheap model's ceiling.*

*Correction 2026-10-12: 3.35× counts tokens copied onto the MoE arm's five repair records. On
drafts alone the ratio is 3.10×, a lower bound; the finding's direction and size stand
(`repair-accounting-unwired.md`).*

*(`economic-arm-moe-vs-generalist.md`.)*

### Arm 3 — Measured: the better model, not the mix

*Until 2026-11-08 this section read "Untested, for want of a suitable model pair".*

An ensemble can only pool what its members *differentially* solve. The entry criterion: measure
each candidate alone on cells the reference misses, and go on only if it solves something the
reference reliably misses, confirmed by a 10-trial decider. Six candidates were tried:

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
trials, and the cells were chosen from the reference's record, not sampled.

---

## Findings the thesis did not predict

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

### On the hardest cells the limit is often speed

On the cells the reference fails under the corrected prompts, the commonest failure is a program
that passes the worked example and then runs past the 60 s execution timeout: 27 of 51 failed
attempts on 2024 d24 p2 and 2025 d10 p2 (`m5pro-band-k1-vs-k3-aoc.md`), 9 of 12 on 2025 d9 p2
(`part2-prompt-omits-part1.md`). `gemma4:31b` timed out on 19 of 27 attempts at 2025 d10 p2.
`muse-glimmer:30b` timed out rarely (7 of 76 failed attempts on the same cells) and failed by
crashing or answering wrong instead (`arm3-precheck-*.md`).

### Interventions that add no new information do not help

Five hypotheses were falsified by the next run:

1. *Insight problems won't fall to sampling* — falsified (1/6 → 3/3 on an algebra-reformulation problem).
2. *Voting buys execution reliability, not ideas* — falsified by the same problem.
3. *Failure mode predicts whether a problem is sometimes-solvable* — falsified; a crash-class problem
   was "sometimes", three wrong-answer problems were walls.
4. *Correlated draws → raise the temperature* — falsified: 0.7 → 1.0 moved nothing and slightly hurt
   a working problem.
5. *Better-worded repair feedback will help* — falsified, with the guidance verified to have fired
   on 49 of 70 attempts.

Read together they are sharper than any one of them:

> **Interventions that add no new information do not help, however well-targeted the wording.**
> Temperature added variance without information. Reworded feedback added exhortation without
> information. The two things that *have* worked add real information: **sampling** contributes
> genuinely independent draws, **repair** contributes an actual traceback.

This is now the filter for what to try next: *what does the model learn that it did not already know?*

**A standing boundary:** one problem (2025 d9 p2) has resisted **every** configuration — k ∈ {1,3},
repair ∈ {0,2}, temperature ∈ {0.7,1.0}, reworded feedback — across 13 problem-trials. Volume buys
*stochastic* failures; it does not buy *systematic* ones. The same split appeared independently in
arm 2: four times the draws bought a ~25%-per-draw parsing failure and did not buy a problem that
emitted identical `TypeError`s every time.

> **Corrected 2026-10-31.** The 13 trials above posed Part Two without the Part One statement.
> With it, the reference solves 2025 d9 p2 in 3 of 5 trials at k3
> (`dev/progress/part2-prompt-omits-part1.md`), so it is no longer a standing boundary. The arm-2
> `TypeError` case is a separate result and is unaffected.

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
| That token fix stopped at the provider; the solver kept copying the draft's tokens and time onto every repair record *(found 2026-10-12)* | **642 of 642 repair records wrong, in runs after the "fix" too**; arm 2's 3.35× is really "at least 3.10×" |
| Part 2 prompts carried only the "Part Two" article: no rules, no input format *(found 2026-10-13)* | **on 2024 d19 p2 a draft was right only if it guessed the format (16 of 26 that did, 0 of 54 that did not)**; the Part 1/Part 2 cliff and the Part 2 walls are unestablished until re-run |
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

This is stated first among the limits because it is the objection a reader should raise, and because
it affects the findings unevenly:

**Weakened by contamination — the capability claims.**
The 8/8 sweep of 2024 d4–7, the "generation beats size" ladder, and the 43-solution ledger all
measure *something*, but they cannot distinguish "this model is more capable" from "this model has
seen more of this benchmark". A newer model is both stronger *and* more likely to have ingested the
2024/2025 corpus, and those two explanations are entangled here. **Treat the capability numbers as
descriptive of this testbed, not as a capability measurement.**

**Largely robust to contamination — the orchestration comparisons.**
Arms 1 and 2 compare *configurations of the same model on the same problems*. Whatever the model
memorized, it memorized identically in both arms, so contamination cannot explain a difference
between k=1 and k=3, or between two sampling budgets. The mechanism findings — that sampling
converts "sometimes" into "solved", that sampling and repair are superadditive, that volume buys
stochastic but not systematic failures — do not depend on the problems being unseen.

**A partial argument against pure memorization, offered as weak evidence only.**
The frontier band consists of problems the model solves *sometimes* — 17%, 25%, 33% per draw.
Memorized solutions would be expected to reproduce reliably rather than intermittently, and the
problem that resisted every configuration (2025 d9 p2, 0/22 by 2026-10-12, all under the defective Part 2 prompt;
3/5 since) would have been an odd thing to have memorized badly. This is
suggestive, not dispositive: partial or paraphrased memorization could plausibly produce exactly this
intermittency.

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
  narrowed arm 1 under the corrected prompts and measured arm 3. Faster hardware moves the
  capability numbers (larger models fit, execution-timeout "speed walls" move) and arm 2's
  wall-clock economics. Still missing: k=5 for a dose-response curve, and AoC 2026 as a clean
  contamination check.

## Practical recommendations

For a verifier-gated setup like this one (a cheap, exact check picks among candidates), from what
was measured with local models of about 30B:

1. **Spend extra draws where a single draft succeeds part of the time.** At roughly 25–75% per
   draft, three draws lift the solve rate sharply; near 0% or near 100% they buy little. Measure
   the per-draft rate first.
2. **Don't count on repair to rescue hard problems.** Feedback with true example results and
   too-high/too-low hints rescued nothing for the reference on its hard cells (2 of its 145 solves
   came from repair); another model's repairs did better (14 of 131). A fresh draft or a different
   model is the more reliable second try.
3. **Check whether failures are timeouts.** Many hard-cell failures pass the example and run out of
   time on the full input. Asking for an efficient algorithm, or allowing more execution time,
   addresses a different limit from a bigger model.
4. **Choose a second model by measurement, not by its maker.** Of six candidates, one reliably
   solved something the reference missed, and no cell was found where the reference reliably beat
   it, so a mix had nothing to add. Measure each model alone on your failure cases and on your
   successes; often one model should replace the other rather than join it.
5. **Confirm any lead with more trials before acting on it.** Three trials found two leads that
   did not survive ten (Ornith on 2024 d14 p2, the reference on 2024 d15 p2).
6. **Without a cheap checker, none of this is measured.** Consensus here only ranks candidates;
   the oracle decides. Majority voting without a checker is a different arrangement.

## Where this generalizes, and where it doesn't

The mechanism needs a **cheap, exact verifier**. Sampling and repair convert into correctness only
because a check can collapse many guesses to one verified answer. Where that check exists — unit
tests, a compiler, a proof checker, a simulator — the findings should transfer. Where correctness is
subjective or expensive to verify, the coordination has little to grip, and the honest expectation
is that none of this applies.

## Reproducing

Every result lists its exact command in its `dev/progress/` write-up. Configurations are
fingerprinted, so two runs with different behavior cannot share a hash — the mechanism that caught
a duplicate experiment before it wasted three hours, and that forced behavior changes to be
config-gated so they could be A/B'd at all.

Puzzle inputs, problem text and scraped answers are **not** in this repository (see the README's
[data policy](README.md#data-privacy-and-advent-of-codes-rules)); a fresh clone cannot run the
oracle until you supply your own AoC session.
