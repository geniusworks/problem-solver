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

This document is the consolidated result. The 31 write-ups in [`dev/progress/`](dev/progress/) are
the audit trail; every figure here was recomputed from the run artifacts. For the project itself —
what it is, how the pipeline works, how to run it — see the [README](README.md).

**Corpus:** 57 recorded experiment runs · 1,475 candidate attempts · ~121 GPU-hours · 16.3M tokens ·
**43 oracle-verified solutions across two AoC years, 0 wrong in the ledger.**

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
| **1. pass@k** | the gap between "sometimes solves" and "solves" never closes at a model's own frontier | ✅ **confirmed and replicated** |
| **2. economics** | many cheap draws + a verifier beat one expensive pass at equal cost | ⚖️ **splits by which cost you pay** |
| **3. portfolios** | diverse models decorrelate error | ⚠️ **untested — no suitable model pair** |

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

*(`passk-ab-d13-d15.md`, `passk-replication-2025.md`, `topology`/`parallel3` arms.)*

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

*(`economic-arm-moe-vs-generalist.md`.)*

### Arm 3 — Untested, for want of a suitable model pair

Two ensemble attempts both failed at the **entry condition**, not at the mechanism:

- a same-tier, same-generation pair whose apparently complementary solves were sampling noise;
- a cross-generation pair whose second model turned out to solve a **strict subset** of the first's
  problems — it solved nothing the stronger model couldn't, and *failed* one the stronger model
  handles reliably.

An ensemble can only pool what its members *differentially* solve. Neither pair had that. The entry
criterion is now explicit: **measure each member individually on the targets first; only run an
ensemble if one solves something the others reliably miss.**

*(`ensemble-samp3-d4-7.md`, `ensemble-precheck-negative.md`.)*

---

## Two findings the thesis did not predict

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

---

## What the measurements cost in credibility, and why that matters

Roughly half the work behind these numbers was discovering that earlier measurements were wrong.
Eight instrument defects, each of which made results *look better or worse than reality*:

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
problems that resist every configuration (0/13) would be odd things to have memorized badly. This is
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
- **One strong model** for the headline results; three models compared for the generation finding.
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
- **One hardware configuration.** Faster hardware would refine the capability numbers (larger models
  fit, and execution-timeout "speed walls" move) and the wall-clock economics of arm 2, and would
  unblock the still-missing tests — k=5 for a dose-response curve, an arm-3 model pair, and AoC 2026
  as a clean contamination check. It is *not* expected to change the orchestration mechanism, which
  holds the model and machine fixed.

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
