# Project Checkpoint

The **live status snapshot** — where the project actually stands right now. The forward roadmap is
`PLAN.md` (repo root); the durable findings are `dev/progress/*.md`; cross-machine numbers are
`dev/benchmarks/cross-machine-results.md`; git history + merged PRs are the changelog. Keep this
file current as work lands so it never goes stale.

## Current status (2026-08-16)

### FIRST M2 MAX RESULT: the 30B tier did not beat 16 GB (2026-08-16)

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

