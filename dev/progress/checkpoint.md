# Project Checkpoint

The **live status snapshot** — where the project actually stands right now. The forward roadmap is
`PLAN.md` (repo root); the durable findings are `dev/progress/*.md`; cross-machine numbers are
`dev/benchmarks/cross-machine-results.md`; git history + merged PRs are the changelog. Keep this
file current as work lands so it never goes stale.

## Current status (2026-08-17)

### ❌ TEMPERATURE IS NOT THE LEVER — a clean negative (2026-08-20)

temp 1.0 vs the existing 0.7 baseline, k3, 3 trials, on both resistant benchmarks
(`dev/progress/temperature-diversity-negative.md`; 9h, 0 wrong/unverified/overfit).
**6/12 → 5/12.** Neither target moved and one working problem got slightly worse (d15 p1 3/3 → 2/3).

> **Corrected 2026-08-20:** this said "neither *wall* moved (d15 p2 now 0/11…)". **2024 d15 p2 is not
> a wall** — it has solved 2 of 16 times (~12%); the tally had summed only the arms where it failed.
> Missing a ~12% problem in 3 trials is unremarkable (p ≈ 0.68), so d15 p2's 0/3 here is weak
> evidence. The 6/12 → 5/12 headline stands; only **2025 d9 p2 (0/10)** speaks to a genuine wall.
> `dev/progress/CORRECTION-d15p2-is-not-a-wall.md`

**This falsifies a hypothesis this project derived from its own data** — that the resistant failures
are *correlated draws* and temperature would decorrelate them. The diagnosis may stand; the
instrument does not. **Parameter-level** diversity (temperature/top-p) perturbs tokens *within* an
approach; these failures need **strategy-level** diversity — prompting for a different algorithm, or
a different model. Both untested, and better motivated now the cheap option is ruled out.

**Fourth falsified hypothesis in this line of work** (after "insight walls won't fall", "voting buys
execution reliability not ideas", and "failure mode predicts sometimes-solvability"). The pattern:
mechanistic stories about *why* these models fail keep failing to predict what helps; only direct
measurement has. An argument for keeping A/Bs expensive-but-first, not for theorising harder.

**Baseline reuse worth noting:** temperature is in the config fingerprint, so the 0.7 arm already
existed and only the 1.0 arm had to run — halving the cost. Same trick as the k1 pooling.

### ⭐⭐ THE CENTRAL CLAIM REPLICATES OUT OF SAMPLE (2026-08-19)

k3 on the 2025 band (`dev/progress/passk-replication-2025.md`; 5h, 0 wrong/unverified/overfit).
**All four cells behaved as predicted, with the prediction registered before the run:**

| problem | pass@1 | **pass@3** | role |
|---|---|---|---|
| **d9 p1** | 25% | **100%** | sometimes → rescued |
| d9 p2 | 0/4 | **0/3** | wall → held (**0/7** overall) |
| d11 p1 | 100% | **100%** | control → held |
| **d11 p2** | 33% | **100%** | sometimes → rescued |

**Stronger than a repeat of 2024, because 2025 was the unfavourable venue** — its bimodal frontier
was flagged in advance as working against sampling, and the effect replicated anyway. The three-way
structure (rescue / wall / control) is what makes it a mechanism rather than a rate artifact.

**Limits unchanged:** two "sometimes" problems × 3 trials — a replication attempt that succeeded, not
a confirmation at scale; and both arms include the repair loop (see the pass@k correction).

**The standing boundary has one confirmed member:** 2025 d9 p2 (0/10), immune to more draws.
**Diversity, not volume, is the open lever.** *(Originally claimed two, adding 2024 d15 p2 — which
has in fact solved 2 of 16 times. See `CORRECTION-d15p2-is-not-a-wall.md`.)*

### 2025 band classified: mostly walls, only 2 "sometimes" (2026-08-19)

`--trials 3` on the 2025 misses (`dev/progress/band-2025-classification.md`; 5h, ledger 41 → **43**).
**Only d9 p1 and d11 p2 are "sometimes" (1/3 each).** 2025's frontier is far more **bimodal** than
2024's — 4 reliable / 2 sometimes / 4 walls, versus 2024's 5-of-8 sometimes — which makes it a
**harder venue** for the sampling claim, and hints the 2024 band was unusually favourable to it.

**The pre-registered prediction failed on both halves:** crash-class d11 p2 *is* a "sometimes";
three of four wrong-answer problems are hard walls (0/4). **How a problem failed once does not
predict whether it is sometimes-solvable** — that must be measured. Third failed taxonomy in this
line of work; the durable lesson is that only repeated sampling classifies "sometimes".

**Next:** k1-vs-k3 on d9 p1 + d11 p2 — the first out-of-sample test of the *central* claim. Thin
band: a positive result is encouraging, a null result is under-powered rather than decisive.

### 🌍 THE FINDINGS GENERALISE: AoC 2025 out-of-sample, 16/23 (70%), ledger 41 (2026-08-18)

First evaluation on problems the project had never seen (`dev/progress/generality-2025-scan.md`;
samp1, 1 trial, 4h, 544k tokens, 0 wrong/unverified/overfit). **16 new verified solutions → ledger
25 → 41 correct, 0 wrong.**

All three structural claims held out of sample:
1. **A real frontier exists** — 70%, not 100% or 0%. 2025 is a working instrument. This was the
   outcome most at risk.
2. **The Part 1/Part 2 cliff recurs** — 83% vs 55%; **six of seven scoreable misses are Part 2s**,
   the 2024 shape on unrelated puzzles.
3. **Day 9 fell in both years, both parts** — unrelated puzzles, but both failed by computing
   *wrong answers* rather than crashing. Fiddly-bookkeeping failures look like a recurring class.

**Failure split (7 scoreable misses):** 4 wrong-answer (d2 p2, d4 p2, d9 p1/p2), 3 crash (d10 p2,
d11 p2, d12 p1) — close to 2024's shape. Since 2024's pass@k result showed sampling converts *wrong*
far more readily than *systematic* failure, that yields a **pre-registered prediction**: sampling
should pay on the wrong-answer group and not the crash group.

**Caveat, stated in the doc:** 70% > 2024's 56% is almost certainly **set composition** — 2025 d1–12
includes easy early days, 2024 d8–15 does not. Structure transfers; the rate is not comparable.

**The first genuinely unseen problem:** 2025 d12 p2 has no cached answer (the account never solved
it). The harness attempted it, scored nothing, and kept it out of the totals — the Milestone F
scenario in miniature, and the first real target the deferred submission path has ever had. Nothing
was submitted.

**Next:** classify a 2025 frontier band (`--trials 3` on the misses), then a k1-vs-k3 A/B there —
which would be the first out-of-sample test of the project's *central* claim, not just its
structural ones.

### ⭐ THE CENTRAL THESIS IS MEASURED: pass@1 42% → pass@3 75% (2026-08-17)

The experiment the project has been building toward since the M1
(`dev/progress/passk-ab-d13-d15.md`). `qwen3.8:27b` on its *own* frontier band (2024 d13/d15,
selected beforehand by independent 3-trial classification), k1 vs k3, 3 trials each, theory curve
registered in writing before the k3 arm ran:

| problem | pass@1 (24 pooled draws) | pass@3 | predicted | delta |
|---|---|---|---|---|
| d13 p1 | 83% | 100% | 100% | — |
| **d13 p2** | **17%** | **100%** | 42% | **+58** |
| d15 p1 | 33% | 100% | 70% | +30 |
| **d15 p2** | **33%** | **0%** | 70% | **−70** |
| **overall** | **42%** | **75%** | 71% | +4 |

**The thesis holds** — and the two extremes matter more than the average:
- **d13 p2**: 1-of-6 single draws → **3-of-3** at k3. The mechanism in pure form. Also a problem we
  twice called an "insight wall": **sampling reaches insight problems, not only fiddly ones.**
- **d15 p2**: 33% per draw, 70% predicted, **0/3 measured** (p≈0.03 if draws were independent).
  **Sampling multiplies draws, not diversity** — the model repeats the same too-slow approach. This
  was described as the most execution-bound problem in the band — **incorrect**: that inference came
  from long *wall-clock*, which is generation plus repair. No attempt on it has ever hit an execution
  timeout (`CORRECTION-d15p2-is-not-a-wall.md`).

**The next lever is therefore diversity, not more samples**: temperature, prompt variants, model
mixing. That is a strategy question, not a compute question.

**Precision correction (same day):** both arms ran with the default `max_repair_iterations=2`, so
these are *k samples + repair*, not pure pass@k — k1 was "1 sample + up to 2 feedback repairs", k3
was "3 samples + up to 2 repair rounds each" (up to 9 generations). The comparison stays valid
(repair identical in both arms) and the gain is if anything conservative, since the 42% baseline
already contains repair's contribution. **Experiment now running** separates sampling from repair:
`parallel3` (3 blind draws, repair=0) vs `sequential3` (1 draw + 2 feedback refinements) — equal
generation budget, opposite topology.

Limits held plainly: n=3 trials/problem; **k5 deliberately not run** (maintainer scope call) so
there is no dose-response curve or saturation point; one model, one temperature, four problems; and
`p` itself rests on 6 draws each (pooling moved two estimates materially).

### FRONTIER FOUND on d8–15: `qwen3.8:27b` 9/16, ledger 22 (2026-08-17)

With d4–7 solved out, the scan moved to **2024 d8–15** and found a real frontier: **9/16 (56%)**
(`dev/progress/m2max-qwen38-frontier-scan-d8-15.md`; samp1, 1 trial, 3h, 373k tokens). **Seven new
verified solutions in one run — the largest jump in project history — ledger 14 → 21, then 22** after
d13 p1's overfit rejection was overturned. Oracle: **22 correct, 0 wrong**.

**The failure band, and it splits by kind** — which gives the pass@k A/B a real prediction to test:
- *Implementation-fiddly:* **d9 p1** (the scan's only `no_candidate` — 900 s, nothing extractable),
  **d9 p2**, **d15 p2** (2,282 s, longest of the scan).
- *Insight-required:* **d11 p2** (memoised counting), **d13 p2** (algebra over brute force).
- *Under-specified:* **d14 p2** ("find the Christmas tree") — excluded from the A/B on principle; the
  oracle can score it but the problem never defines the target.

Prediction: sampling should buy the fiddly problems and not the insight ones — voting improving
*execution reliability* rather than manufacturing *ideas*. If d11 p2 or d13 p2 falls to sampling
instead, that is the more surprising and more valuable result.

**Two instrument defects found and fixed** (both were scoring harness behaviour as model failure):
1. **`KeyError: ProblemCategory.GRAPH` crashed whole problems before the model was called**
   (`strategy-keyerror-d8.md`). `SOLUTION_STRATEGIES[category]` was unguarded while GRAPH,
   STATE_MACHINE and OPTIMIZATION have keywords but no strategies; substring scoring meant d8's
   "anti**node**" matched `node`. Live since 2025-12-06 → **the M1's "d8–12 leg: 2/10" is really 2 of
   8 attempted**, corrected in place. d8 is the only affected day in d1–15; once fixed, **both parts
   of d8 solved on the first draw.**
2. **The overfit gate rejected a correct, general solution** (`overfit-gate-false-positive.md`):
   d13 p1 produced the right full-input answer and was refused for containing an example literal —
   which sat in a *docstring*. The check ran on raw source and never asked *where*. Comments and
   docstrings are now stripped before the identical checks run; both real cheat fixtures still trip
   it. Exposure is model-specific: `qwen3.8:27b` writes its reasoning into comments, so the habit
   that helps it solve hard problems is what tripped a gate reading prose as code.

**Next:** `--trials 3` at samp1 on the five-problem band to separate *sometimes* from *never* (only
*sometimes* can show a pass@k effect), then the controlled samp1 vs samp3 vs samp5 A/B — the thesis
test the project has been building toward.

### THE d4–7 SET IS SOLVED OUT: `qwen3.8:27b` 8/8, ledger 14 (2026-08-16)

**`qwen3.8:27b` (17 GB, released 2026-08-14) scored a perfect 8/8 on 2024 d4–7**
(`dev/progress/m2max-qwen38-27b-d4-7.md`; 2h 40m, 24 attempts, 287k tokens, ollama 0.32.14). It
cracked **d6 p2 — the last problem nothing had ever solved** → ledger **14 correct / 0 wrong**.
**The comparison set no longer has a frontier in it and is retired as a capability instrument.**

**The generation ladder, complete — every rung smaller than the last:**

| model | size | class | solved | per-attempt | wall |
|---|---|---|---|---|---|
| `qwen2.5-coder:32b` dense, 2024 | 19 GB | specialist | 4/8 | 22% | 7,918 s |
| `qwen3-coder:30b` MoE, newer | 18 GB | specialist | 6/8 | 45% | **2,346 s** |
| `qwen3.8:27b` dense, 2026 | **17 GB** | **generalist** | **8/8** | **83%** | 9,602 s |

Size runs *backwards* to capability; the winner is smallest and is not a coder, so the effect is
general model quality rather than code specialization. Cost caveat: Qwen3.8 is the slowest — the MoE
is still the best capability-per-second.

**Strongest pass@k evidence yet (Q2, partially answered).** Attempt ordering gives **pass@1 = 6/8,
pass@3 = 8/8**, and the two problems sampling bought were **d5 p2 and d6 p2 — the two hardest on the
set**; every easy problem solved 3/3. The MoE showed the same shape (d4 p2 1/3, d5 p2 1/4). Two
models, two architectures, the predicted pattern. Still not the controlled A/B (one trial, pass@1
inferred from first draws).

**Two prior claims corrected** (originals left in place with the correction, per house style):
- *"d5 p2 / d6 p2 are efficiency-bound"* — two different walls, conflated. d5 p2 fell to a **better
  algorithm** (topological sort); d6 p2 fell to a **plain brute force running inside the timeout**
  on faster hardware. Right about one, wrong about the other.
- *"Day 5's input is a model-independent parsing trap"* — overstated; it is **generation-dependent**.
  Both 2024-era models tripped on it, Qwen3.8 parsed both parts cleanly. The "orchestration lever"
  framing is correspondingly weaker.

**Also observed:** with `enable_thinking=false`, Qwen3.8 **relocates its reasoning into code
comments** — the d6 p2 solution contains a dead `simulate_guard` (ending in `pass`) where the model
debugged itself in comments, then a corrected `simulate_guard_correct` below. A free self-correction
pass inside one generation, which `_extract_code` handles fine. Worth an A/B.

**Next:** the frontier has to move — scan `2024:8-20` (or 2025) to find a band where the strongest
model is *uncertain*, which is simultaneously the next capability question and the prerequisite for
the real pass@k A/B (`--trials 5`, samp1 vs samp3 vs samp5).

### `qwen3-coder:30b` 6/8, d5 p2 cracked, ledger 13 (2026-08-16) — superseded above

**`qwen3-coder:30b` (18 GB MoE) samp3 on 2024 d4–7 → 6/8 (75%)** — the project's best, beating the
M1's 5/8 and the dense 32B's 4/8 *on the same machine, runtime and config, the same day*
(`dev/progress/m2max-qwen3coder30b-d4-7.md`; 39 min, 29 attempts, 261k tokens). It cracked **d5 p2,
which no model or config had ever solved** → **first new ledger entry since the M1: `2024 d5 p2 =
5502`, `verify_solutions` now 13 correct / 0 wrong**, via a genuine Kahn's-algorithm topological
sort (overfit gate clean). It also took d4 p2 and d7 p2, both of which the dense 32B missed.

Four findings, all recorded in the doc:
1. **Generation beats size** — the smaller, newer, 3.4× cheaper MoE beat the bigger older dense
   model by two problems under a controlled comparison. "Model capability" means *generation*.
2. **The "efficiency-bound ceiling" is retired.** d5 p2 fell to a *better algorithm*, not a faster
   machine — earlier models never proposed the topological sort. d6 p2 is the only one left, and it
   failed here via 6/6 immediate `TypeError`s, not timeouts.
3. **Failure style differs and matters:** dense 32B = 27 wrong / 5 error (confidently wrong); MoE =
   4 wrong / 11 error (crashes). For a proposer–verifier loop crashes are the cheaper failure —
   detectable, with an actionable traceback for repair.
4. **A cross-model parsing trap:** day 5's two-section input broke *both* models (32B on `'93|48'`
   7/7 on d5 p2; MoE on `'75,47,61,53,29'` 3/4 on d5 p1 — the one problem it missed that everything
   else solves, despite solving d5 p2 minutes later). Model-independent and attackable by
   prompt/harness — **a real orchestration lever, the first one this hardware push has surfaced.**

**Unplanned Q2 evidence:** the MoE solved d4 p2 on 1/3 draws and d5 p2 on 1/4, while easy problems
went 3/3 — the exact shape the pass@k thesis predicts. samp1 would likely have scored 4/8, not 6/8.
Suggestive only (one trial, inferred counterfactual); the controlled samp1-vs-samp3 A/B at
`--trials 5` is still owed, but the frontier band now exists.

### Ollama upgraded to 0.32.14; runtime verified clean (2026-08-16)

Upgraded from 0.32.11 (which refuses to pull `qwen3.8:27b`) and **verified behaviour-neutral: 6/6
on a 3-trial control** with `qwen2.5-coder:32b` on d1 (`dev/progress/ollama-0.32.14-runtime-check.md`).
`qwen3.8:27b` (17 GB) is now resident. **All existing results ran on 0.32.11 and are unaffected.**

Two things came out of it, both recorded:
- **`--trials 1` is not evidence — including for smoke tests.** The first post-upgrade check was a
  one-shot smoke and returned **0/2** on problems that *7B models* solve, immediately after a
  plausible cause. It looked like a clear runtime regression; `--trials 3` on the identical config
  returned **6/6**. The project's founding finding (4 of 6 problems flip across byte-identical
  configs) applied to experiments but had been quietly exempted for smoke tests, and the exempted
  instrument manufactured a false regression. **`AGENTS.md` now requires `--trials 3` for pre-run
  checks.**
- **Token accounting is stale across repair attempts** (new bug, unfixed): three attempts reported
  identical `(4283, 876)` tokens while returning different answers (`0`, `0`, `87471881`), so
  `last_token_usage` is reused rather than refreshed per generation. It matters because arm 2 of the
  central thesis is an *economic* claim measured in tokens — repair-heavy pass@k costs are currently
  understated. Wall-clock is unaffected.

**Next:** `qwen3.8:27b` smoke (`--trials 3`, and specifically whether it honours
`enable_thinking=false` — it is a reasoning-capable generalist, and `deepseek-r1:14b` was dropped
for ignoring that flag), then its full d4–7 run as the next rung of the generation ladder. Then the
Q2 pass@k A/B on the band `qwen3-coder:30b` exposed.

### The 32B result that this superseded (2026-08-16)

**`qwen2.5-coder:32b` samp3 on 2024 d4–7 → 4/8 (50%), below the M1's 5/8**
(`dev/progress/m2max-qwen25coder32b-d4-7.md`; 2h 12m, 41 attempts, 317k tokens, ledger untouched at
12/12). It solved every Part 1 and no Part 2, cracking neither d5 p2 nor d6 p2 — so the handoff's Q1
is answered **no** for this model. Its solved set is the M1 leaders' set minus **d4 p2**, where it
produced 9 wrong answers with no convergence on a problem the 6.6 GB `qwen3.5:9b` solves.
Attempt-level split: **9 solved / 27 wrong / 5 error** — generation and extraction were healthy, the
code was simply wrong. Two record corrections came out of it: (a) "d5 p2 / d6 p2 are
efficiency-bound" holds only for the 16 GB models — this one never parsed d5 p2's input at all
(`invalid literal for int(): '93|48'`, 7/7 attempts), so its binding failure there is parsing, not
speed; (b) **size within a generation is not the capability lever** — the 1/8 → 5/8 lift came from
newer models, and scaling the 2024 generation up does not reproduce it.

**Next:** `qwen3-coder:30b` (resident, untested) completes the planned Q1. The sharper experiment is
**generation vs size** — `qwen3.8:27b` (released 2026-08-14, 18 GB, *smaller* than the 32B but two
generations newer) — **blocked on an Ollama upgrade**: 0.32.11 refuses the pull. Upgrading changes a
recorded machine variable, so it is deferred until the current-runtime runs finish; maintainer's
call. **Q2 (pass@k) needs a wider frontier scan first:** on d4–7 the 32B is bimodal (4 solved every
draw, 4 never), so there is no "sometimes" band for voting to act on. A follow-up worth doing:
generated code that catches its own exception and prints `An error occurred: …` then `0` is scored
**wrong** rather than **error**, understating crashes at the attempt level.

### Machine: work has moved to the M2 Max / 32 GB (2026-08-15)
Bring-up is done and the M1 is retired as a run host (no further experiments planned there). State
on the new machine: **oracle 12 correct / 0 wrong**, **tests 186 passed** (the 24 previously-skipped
tests are data-dependent and now run), `years/` 2024 d1–15 + 2025 copied from the M1, and all five
tier-32 models resident — including `qwen3-coder:30b`, whose Ollama tag the handoff doc was unsure
of and which resolves fine. Started from a **cold learning DB** (M1 copy preserved as
`learning/solver.m1-warm-20260815.db`). Three environment defects were fixed to get here, two of
which were latent on the M1 too — see `dev/benchmarks/m2max-handoff.md` §3 and the PR. **Next: Q1**
(`qwen2.5-coder:32b` samp3 on 2024 d4–7 — does it beat the M1's 5/8 and crack d5 p2 / d6 p2?).

A pre-run holistic audit (2026-08-15) tightened honesty and currency before the first M2 Max data
point: **removed the fabricated `init_db` seed rows** (an invented 0.5 success rate for a model
never run — fake data in the measurement store; cold start is `_get_top_models`' fallback, and a
fresh DB is now genuinely empty), corrected `README.md`'s claim that cached problems "run fully
offline" (false on a fresh clone; `years/` is gitignored) and its bare-`pip` setup steps, marked
the stronger-model lever **UNBLOCKED** in `PLAN.md`/`README.md`, filled the real `m2max-32` specs
into `dev/benchmarks/cross-machine-results.md` (M2 Max, 12-core, macOS 26.6.1, ollama 0.32.11),
added an honest-status note to `learning/README.md` (strategy-learning tables have never been
populated by a real run), and made **docs currency a standing rule** with a doc map in `AGENTS.md`.
The stale curated fallback `OllamaProvider.AVAILABLE_MODELS` (early-2025 7B pool) was then rebuilt
from the measured record — gemma4:12b, qwen3.5:9b, qwen2.5-coder:7b, then the unmeasured 32 GB tier
last until Q1 ranks it — and the `SOLVER_MODELS` pin was emptied in `.env.example` so the curated
default actually applies (a pinned 7B had been silently overriding it on every machine set up from
the example).

The **32B smoke test passed** (2026-08-16): `qwen2.5-coder:32b` samp1 on 2024 d1 → **2/2 verified**
(p1 170.6s, p2 191.3s, 362s wall). The M1's hardware blocker is gone — the 32B loads and generates
without swapping, extraction handles its output, and both answers matched the oracle. At ~180s per
problem-part, Q1 (8 parts × 3 samples + repair) projects to **2–4 h**. Two defects the smoke test
exposed, both fixed before Q1: **`autopep8==2.0.4` was broken on Python 3.14** (imports `lib2to3`,
removed from the stdlib in 3.13 — every `fix_code()` raised and the formatter silently degraded to
unformatted code, an M1↔M2 difference beyond model and hardware; bumped to >=2.3.2), and **the test
suite was writing into the live measurement store** (`solve.py` resolves its workspace to the repo
root, so the entrypoint test's writes landed in `learning/solver.db` — the M1's DB carried a
fabricated `dummy-model` at 79/79, a perfect record for a model that never ran, in the very table
`_get_top_models` ranks on; harmless to live runs via the installed-models filter, but contamination
of a research artifact). An autouse conftest guard now redirects any `LearningDatabase` aimed at the
real directory to a temp dir, and the dummy rows are scrubbed.

### Where the project is
- **PR #1 (merged):** added a correctness oracle (`shared/verification.py`, `shared/ground_truth.py`,
  `shared/overfit_detection.py`), the experiment harness (`shared/experiment/`, `experiment.py`),
  and independent verification. Fixed the harness bugs that had made every prior measurement
  untrustworthy — most importantly, generation now goes through Ollama's HTTP API instead of the
  interactive `ollama run` CLI (whose terminal redraws were corrupting generated code), and prompts
  are no longer silently truncated to ~2048 tokens.
- **Milestone A (PR #2, merged):** repeat-trials in the harness (`--trials N`), reporting a pipeline
  as a distribution rather than a point estimate.
- **Milestone B (PR #3, merged) — the instrument is now sound:** closed the last oracle-bypass (the
  collaborative path's stub-validator gate now routes through `_verify_candidate` like every other
  path); made the config honest (six inert fields removed from the fingerprint, three wired to real
  behaviour — `max_primary_models`, `enable_fallback_models`, `execution_timeout`); unified the two
  learning databases onto `learning/solver.db`; and fixed `success_rate` to record from the
  *verified* outcome instead of at generation time. Model performance is now defined by one helper,
  `_record_model_performance`, against the oracle verdict.
- **Milestone C1 (PR #4, merged) — deletion + isolation:** removed ~1,400 lines of dead/misplaced
  code (solver selector/saver clusters + module entrypoint, `providers.py`, `hardware.py`,
  `learning/strategies.py`, `testing.py`, `LMStudioProvider`, the simulated submit stub); relocated
  `PerformanceMetrics` to `execution.py`; extracted `StrategyRecommender` from the misnamed
  `SubmissionManager`; isolated the real, unwired AoC submitter into a top-level `submission/`
  package.
- **Milestone C2 (PR #5, merged) — utils de-grab-bag:** retired the 898-line `shared/utils.py` into
  `paths.py` (leaf) + `aoc.py` (AoC I/O) + `ledger.py` (oracle-gated record/save) +
  `logging_setup.py`, breaking the `utils → verification → ground_truth → utils` import cycle.
- **Milestone D1+D2 (PR #6, merged) — generation robustness + token accounting:** rewrote
  `_extract_code` around `ast.parse` (fence-agnostic, prefers a `solve()`-defining region, handles
  reasoning `thinking` text); threaded real Ollama token counts into `AttemptRecord`. The A/B
  corrected the project's central claim (see below).
- **PR #7 (merged) — failure diagnostics:** persist `verdict.feedback` into `AttemptRecord.error`
  so the wrong-vs-error split is categorisable from any run without `--include-replay`.
- **Milestone E — self-consistency (this PR):** `samples_per_model` draws N candidates per model;
  at temperature>0 they diverge, giving several shots at the oracle. First orchestration win with
  evidence (see below). Folded in a prompt-hardening tweak (effect unmeasured). C3 (decompose
  `solve_problem`) remains a follow-up.

### Verified reality (not claims — measured)
- Recorded solutions: **12 verified correct** (2024 d1 p1/p2, d2 p1, d3 p1, d4 p1, d4 p2, d5 p1,
  d6 p1, d7 p1, d7 p2, d10 p1, d11 p1). See `solutions/README.md`. The earlier "6/10" figure was
  never true; three recorded solutions were wrong and are quarantined in `solutions/rejected/`.
- **gemma4:12b and qwen3.5:9b are co-leaders at 5/8 — RESOLVED as a tie**
  (`dev/progress/gemma4-samp3-confirmation.md`, `model-bakeoff-gemma4-vs-9b.md`). The deciding test
  (gemma4 samp3 vs the 9b's 5/8) came back **5/8**: gemma4 matched but did not beat the 9b, and did
  not crack d5 p2 / d6 p2. gemma4's edge is *per-draw efficiency* (it hit 5/8 at samples=1), not a
  higher ceiling. Two sub-findings: (a) a single-sample Part-2 solve can be luck — gemma4 samp1 got
  d7 p2, samp3 lost it but gained d6 p1, same 5/8; (b) the two leaders *appeared* to miss *different*
  Part 2s (gemma4→d4 p2, 9b→d7 p2), suggesting a 6/8 union — **but the ensemble test refuted it**
  (`ensemble-samp3-d4-7.md`): `gemma4:12b|qwen3.5:9b` samp3 got **5/8, not 6/8**, at ~2.2× wall,
  because neither model reproduced d7 p2 (that "crack" was a lucky draw, not a robust competency).
  (`deepseek-r1:14b` was tested and dropped — reasoning-native, ignores `think=false`, incompatible
  with our pipeline; no Q6 qwen3.5 tag exists.)
- **qwen3.5:9b (thinking off) — previous baseline, confirmed decisively**
  (`dev/progress/9b-confirmation-d4-7.md`): on 2024 d4–7 at samples=3 it solved **5/8 vs the 7B's
  1/8**, and cracked **d7 p2 — a genuine Part 2** the 7B never reached. It fits at 5.8 GB / 100% GPU,
  so the capability ceiling was pushed **without new hardware.** Two long-standing questions answered:
  the 7B *is* too weak past the easy problems, and we *can* do better on 16 GB. Remaining ceiling:
  d4–6 Part 2s stay `no_candidate` even for the 9b. Cost: ~4.5× slower. Reasoning models over-reason
  without the `enable_thinking=false` toggle (PR #18).
- **First multi-run baseline** (`dev/progress/baseline-2024-d1-3.md`): qwen2.5-coder:7b, 2024 d1–3,
  5 trials — **12/30 solved (40%); 4 of 6 problems solvable, 0 of 6 reliable.** Four of six flip
  across identical runs; single-run numbers are noise.
- **CORRECTED (Milestone D1 A/B, `dev/progress/milestone-d-extraction.md`):** the baseline's
  "every failure is `no_candidate`, models are correct when they produce anything" was a
  **problem-level rollup artifact**. With robust extraction surfacing candidates and token/outcome
  accounting made honest, the same 2024 d1–3 config produced **51 attempts: 13 solved / 21 wrong /
  16 error / 1 no_candidate**. Models produce candidates freely; the real bottleneck is **code
  correctness** — 41% wrong, 31% runtime errors — not extraction. Problem-level solved barely moved
  (12→13/30) because extraction converts no-candidate into mostly wrong/error, occasionally solved.
- **Self-consistency WIN (Milestone E A/B, `dev/progress/milestone-e-self-consistency.md`):** clean
  isolation, samp1 vs samp3 (only `samples_per_model` differs), 2024 d1–3, 3 trials. **39% → 61%
  solve rate; 0 → 3 of 6 problems reliable (solved every trial).** The three flipping problems all
  went 2/3 → 3/3. Cost: 2.4× wall clock, ~2× tokens. Zero regression.
- **CAPABILITY CEILING measured (scale eval `scale-2024-d4-7.md` + benchmark `benchmark-2024-d1-12.md`):**
  the samp3 config on the never-scored days solved **1 of 8 (d4–7)** and **2 of 10 (d8–12)** — d6 p1,
  d10 p1, d11 p1 added to the ledger (`verify_solutions` 7/7). Across d1–12: almost every win is a
  Part 1 (only d1 p2 among Part 2s); failures are wrong reasoning or un-runnable code, not variance.
  This **answers the project's oldest question with evidence: qwen2.5-coder:7b is genuinely too weak
  past the easy problems.** Self-consistency fixes *variance* on reachable problems; it cannot add
  capability. Zero wrong/overfit recorded across all of d1–12 — the oracle held. Broader coverage
  needs a stronger model (hardware-blocked here), not more orchestration.

### Next (per PLAN.md)

Milestones A–E are done and the codebase is consolidated (C1–C3). The platform is complete; on
**M1 16 GB** the leading models are `gemma4:12b` and `qwen3.5:9b` (both 5/8 on the hard d4–7 vs the
7B's 1/8; 12 verified solutions). All 2024/2025 are solved, so there is no live submission target.
The cheap M1 solve-rate levers are now spent: extraction robust, self-consistency handles variance,
thinking-off fixed the reasoning model, a 5× timeout recovered nothing (`9b-timeout-investigation.md`),
and the **diverse-ensemble lever was tested and did not pay off** — `gemma4:12b|qwen3.5:9b` samp3 got
**5/8, not the predicted 6/8**, at ~2.2× wall (`ensemble-samp3-d4-7.md`); the apparent complementary
Part 2 (9b's d7 p2) was a lucky draw that didn't reproduce, so there was no robust competency to pool.
d5 p2 / d6 p2 remain a genuine capability/efficiency limit on 16 GB. **All M1 16 GB results are
consolidated in `dev/benchmarks/cross-machine-results.md`.** Where that leaves the priorities:

1. **A stronger model — now UNBLOCKED: maintainer has an M2 Max / 32 GB.** That fits the tier that
   swamps 16 GB (`qwen2.5-coder:32b`, `Qwen3-Coder-30B-A3B`). Run those at samples=3 on d4–7 and add
   the rows to `dev/benchmarks/cross-machine-results.md` under a new `m2max-32` machine id. Two
   decisive questions, not one: (a) does a bigger model crack **d5 p2 / d6 p2**, which no 16 GB model
   has? and (b) the project's **central open thesis** (see README "Does orchestrated voting scale?"):
   does sampling + voting still add correctness at a *strong* model's own frontier — i.e. **pass@k >
   pass@1** on problems it solves only sometimes? That means running the strong model at samples=1 vs
   samples=N on problems at *its* edge, not just counting total solves. (A remote/cloud `OLLAMA_HOST`
   is the alternative.)
2. **M1 orchestration levers — exhausted for now.** gemma4-vs-9b leader = **5/8 tie**; the
   diverse-ensemble follow-up = **5/8, no gain** (`ensemble-samp3-d4-7.md`). The remaining honest
   M1 idea is *more samples on a specific marginal problem* (raise pass@k on d7 p2, which both models
   solve only occasionally) — low-confidence, but the one untried cheap lever. Otherwise the frontier
   moves to bigger models (priority 1).
3. **Algorithm-efficiency prompting — low-confidence, cheap to try** on M1 for the timeout-bound Part 2s.
4. **Submission phase (F) — deferred.** No unsolved target; revisit for AoC 2026 or a fresh account.

Reasonable stopping point: the platform has demonstrated its result on this hardware — a measured
model win, 12 oracle-verified solutions, everything reproducible.
Cleanup status: dead `config/*.yaml` and the builtin-shadowing error classes were removed (PR #26).
The four same-named "duplicate" types (`ProblemCategory`, `ExamplePurpose`, `TestCase`,
`PerformanceMetrics`) were investigated and found **genuinely distinct** — different members/fields
and value types across layers, and `execution.PerformanceMetrics` is deliberately separate from
`performance.PerformanceMetrics` (collapsing would reintroduce a bug C1 fixed). Not a mechanical
dedup; left as-is (a cosmetic rename to drop the name collision is the only safe option, low value).

