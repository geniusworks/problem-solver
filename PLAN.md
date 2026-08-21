# Problem Solver — Forward Roadmap & Structural Consolidation

## Context

PR #1 turned the solver from an unmeasurable pipeline into one with a correctness oracle, an
experiment harness, and independent verification. Two full-codebase audits (structural + pipeline)
now show where it stands.

**The empirical reframe (updated after the Milestone D1 A/B).** The original reframe read this
project's early numbers as *"when the model produces a candidate it is ~9:1 correct; the dominant
failure is no candidate at all."* The D1 A/B (`dev/progress/milestone-d-extraction.md`) showed that
was a **problem-level rollup artifact**: a problem whose every candidate is wrong or errors returns
None from the solver and is recorded as `no_candidate`, erasing the wrong/error attempts underneath.
With robust extraction surfacing candidates and honest attempt-level accounting, the same 2024 d1–3
config produces **51 attempts: 13 solved / 21 wrong / 16 error / 1 no_candidate**. So the real
bottleneck is **code correctness — 41% wrong, 31% runtime errors — not extraction or "no candidate".**
Model capability and run-to-run variance are still in play, but the lever moved: from *getting a
candidate at all* to *getting a candidate that runs and is right*. Milestones D/E are re-pointed
accordingly (reduce runtime errors; then self-consistency/consensus for the wrong answers).

**What the audits found still wrong** (file:line):
- **Live correctness hole:** `shared/solver.py:491-503` still runs the stub `validate_solution`
  (`shared/llm/local.py:412-417`, `return True`) on the collaborative path and returns a candidate
  that bypasses `_verify_candidate` and the oracle. Gated off by default, but a landmine.
- **`success_rate` measures generation, not solving:** recorded `success=True` at
  `shared/solver.py:352` *before* verification. The model-ranking signal is hollow; the "running
  rate" migration made a meaningless quantity precise.
- **~1,400 lines unreachable:** `shared/llm/providers.py`, `shared/validator.py`, `shared/testing.py`,
  `shared/llm/hardware.py`, `learning/strategies.py` — kept alive only by tests that assert on them
  (`tests/integration/test_llm.py:10` instantiates an ABC and cannot pass).
- **Three subsystems that look done but do nothing:** strategy learning (constant `0.5`,
  `learning/optimizer.py:112`), collaborative improvement (no-op behind a `KeyError`,
  `shared/llm/collaborative.py:87,97-101`), submission (simulated stub `shared/submission.py:212` +
  real-but-orphaned `shared/validator.py:129`).
- **Two live databases:** `learning/solver.db` (25 rows) vs `./solver.db` (0 rows) —
  `StrategyOptimizer` writes to the wrong one (`learning/optimizer.py:55`).
- **9 inert `SolverConfig` fields** still enter `fingerprint()` (`provider`, `max_primary_models`,
  `samples_per_model`, `prompt_variant`, `enable_fallback_models`, `consensus_on`,
  `execution_timeout`, `submit_solutions`, `reference_model`) — reintroducing the hollow-A/B trap
  `tests/unit/test_model_resolution.py` was written to prevent. `consensus_on` is the dangerous one:
  its default `"answer"` advertises behaviour that doesn't exist (consensus still groups source text,
  `shared/solver.py:962-966`).
- **Docs describe the pre-oracle system:** `README.md`, `dev/docs/architecture.md`, both diagrams,
  `dev/progress/checkpoint.md` — zero mention of `experiment/`, `verification.py`, `ground_truth.py`,
  `overfit_detection.py`; `checkpoint.md:57,84` actively contradicts `solutions/README.md:35`.

**Decisions (2026-08-07):** platform-first (measurement before capability; submission code kept but
unwired); delete unreachable + no-op code now, re-add orchestration only with harness evidence;
trustworthy measurement is the first deliverable.

---

## Target structure (the design gut-check)

The repo has a solid new core wearing a large dead substrate. Target layout after consolidation:

```
shared/experiment/     Platform (config, results, runner) — the product. Best modules; keep.
shared/verification.py oracle + overfit gate; keep.
shared/ground_truth.py  keep.
shared/overfit_detection.py  keep.
shared/solver/         Decomposed pipeline (was one 1290-line method): fetch → parse → analyze
                       → generate → extract → execute → verify → repair → record. A package,
                       each stage independently testable. Dead classes (ModelRole, AttemptResult,
                       ModelSelector) and dead savers (_save_solution/_save_attempt) deleted.
shared/llm/            ONE provider: local Ollama HTTP (local.py) + prompts.py. Delete providers.py,
                       hardware.py, LMStudioProvider. One error hierarchy (shared/errors.py).
shared/aoc/            (new) fetch/cache/session — extracted from utils grab-bag.
shared/ledger.py       (new) record_solution/save_solution_file — correctness policy out of "utils".
learning/              ONE database, honest schema. Delete strategies.py + dead optimizer paths.
submission/            (kept, UNWIRED) the real AoC submitter from validator.py, isolated and
                       tested, clearly marked "not in the solve loop yet". Simulated stub deleted.
```

One canonical taxonomy for problem types (three exist today: `strategies.ProblemCategory`,
`problem_analysis.ProblemCategory`, `solver._get_problem_type` free strings). One `TestCase`, one
`PerformanceMetrics`, one `ExamplePurpose`.

---

## Milestone A — Trustworthy measurement (FIRST) — ✅ LANDED (PR #2)

Nothing is evaluable at n=1 against the observed variance. Smallest change, unblocks everything.

- Add `--trials N` to `experiment.py`; `run_experiment` runs each problem N times
  (`shared/experiment/runner.py:196`). Wire `AttemptRecord.sample_index` (`results.py:56`, already
  exists) and set a per-trial seed/index.
- Aggregate in `ExperimentResult`: solve rate as *k/N per problem* and a stability count (how often
  each problem flips). Add a `solved_at_least_once` / `solved_every_time` split — the honest way to
  report a variable pipeline.
- Produce a real baseline: `qwen2.5-coder:7b`, 2024 days 1–3, **5 trials**, committed to
  `dev/experiments/` with a short written summary in `dev/progress/`.

**Verify:** `experiment.py --problems 2024:1-3 --trials 5` emits per-problem k/5 and a variance
column; the summary states solve rate with a range, not a point.

## Milestone B — Make the instrument sound (small, high-trust) — ✅ LANDED

A platform with hollow config fields and a live oracle bypass can't be trusted for the experiments
to come.

> **Done.** (1) The collaborative path's stub-validator gate now routes through `_verify_candidate`.
> (2) Six inert fields removed from the fingerprint; three (`max_primary_models`,
> `enable_fallback_models`, `execution_timeout`) wired to real behaviour; `consensus_on` gone until
> Milestone E. (3) One database only — `StrategyOptimizer` reads `learning/solver.db`; the dead root
> `./solver.db` is deleted. (4) `success_rate` records from the verified verdict via a single helper,
> `_record_model_performance`, not at generation time. All verify criteria met (tests, `pylint -E`,
> `verify_solutions` 4/4).

1. **Close the correctness hole:** delete the stub-validator gate at `shared/solver.py:491-499`;
   route the collaborative path's acceptance through `_verify_candidate` like every other path (or
   delete the collaborative branch entirely — see Milestone C).
2. **Config honesty:** for each of the 9 inert fields, either (a) wire it to real behaviour now if
   trivial (`max_primary_models`, `execution_timeout`, `enable_fallback_models`), or (b) remove it
   from the dataclass until its feature exists. Nothing may enter `fingerprint()` without affecting
   behaviour. Delete `consensus_on` until answer-based consensus is real (Milestone E).
3. **Unify the databases:** one path only (`learning/solver.db`); fix `learning/optimizer.py:55`;
   delete root `./solver.db`.
4. **Fix `success_rate`:** record model performance from the *verified* outcome, not at generation
   time (`shared/solver.py:352`). Until model-ranking is re-earned, `_get_top_models` may simply
   return installed models in order — honest beats precise-but-hollow.

**Verify:** a test asserts two configs that differ only in an unwired field raise or share a
fingerprint; `learning/solver.db` is the only DB written; a solved/failed pair produces the right
`successes/attempts`.

## Milestone C — Structural consolidation (the integrity work)

Per "delete now, re-add with evidence." A pre-flight reachability audit (three tracing passes over
the current code) corrected the roadmap in several places — the line numbers below predate the A/B
refactors, and some "dead" claims were wrong. **C is split into a shipped deletion/isolation PR and
two follow-up PRs** for the live-code restructuring, so the risky changes get their own review.

### C1 — Deletion + isolation — ✅ SHIPPED (PR: milestone-c-consolidation)

- **Deleted solver dead code:** `ModelRole`/`AttemptResult`/`ModelSelector`,
  `_save_solution`/`_save_attempt`/`_count_attempts`/`_get_attempts_dir`, module-level
  `solve_problem()` (+ its `shared/__init__.py` export), and the imports they left dead.
- **Deleted unreachable modules:** `shared/llm/providers.py` (remote/`ProviderFactory` scaffolding;
  `shared/llm/__init__.py` re-export updated — it was load-bearing), `shared/llm/hardware.py`,
  `learning/strategies.py`, `shared/testing.py`, and `LMStudioProvider` (a NotImplementedError stub).
  Their prop-up tests (`test_llm.py`, `test_provider_gating.py`) went with them.
- **Relocated `PerformanceMetrics`** (the 3-field one) into `execution.py`, its real owner, and fixed
  the wrong annotation on `ExecutionResult.performance`.
- **Extracted `StrategyRecommender`** from the misnamed `SubmissionManager` (its only live method);
  **deleted the simulated `submit_solution` stub**.
- **Isolated the real, unwired submitter** into a top-level `submission/` package
  (`manager.py` + `validator.py`), kept for Milestone F, clearly marked not-in-the-solve-loop.
  Preserves the "keep submission code, defer wiring" decision.

**Corrections found during the audit (recorded so the roadmap stays honest):**
`shared/llm/collaborative.py` is **not** dead — `solver.py` uses it (gated), so it stays. `test_llm.py`
does **not** instantiate an ABC ("cannot pass" was false); it just tested dead code. `SubmissionError`
lives in `shared/errors.py`, not `validator.py`. The "~1,400 lines unreachable" figure held for
deletion but excludes the preserved submitter and collaborative path.

### C2 — De-grab-bag `shared/utils.py` — ✅ SHIPPED (PR: milestone-c2-utils-split)

The 898-line, 7-responsibility grab-bag — which also sat at the bottom of a
`utils → verification → ground_truth → utils` import cycle — is retired, split into four
single-purpose modules: `shared/paths.py` (leaf path primitives), `shared/aoc.py` (AoC session/HTTP/
fetch/cache), `shared/ledger.py` (oracle-gated record/save), and `shared/logging_setup.py`. Moving
the leaf primitives (`get_problem_dir` et al.) out to `paths.py` removed the back-edge and dissolved
the cycle; the ledger now imports verification/ground_truth at the top cleanly. Four confirmed-dead
functions (`get_github_username`, `get_repository_state`, `download_input`, `read_input`) were
deleted along the way. Single `aoc.py` module rather than an `aoc/` package — the same
"don't add package ceremony this size doesn't need" call as C3. Suite green (165), pylint -E clean,
verify_solutions 4/4.

### C3 — Decompose `solve_problem` — ✅ DONE (PR: milestone-c3-decompose)

Broke the ~480-line method into named stage methods on `BaseSolver` — `_prepare_problem` (setup),
`_generate_candidates` (self-consistency generation), `_execute_and_repair` (oracle + verify +
repair + fallback) — each returning a small bundle (`_Prep`, `_Candidates`) the orchestrator unpacks.
`solve_problem` is now a ~160-line orchestrator: setup → generate → consensus/collaborative (still
inline) → execute/repair. **Extracted methods, not a `shared/solver/` package** — the file didn't
justify the package + context-object ceremony. Behaviour-preserving (bundle+unpack), verified by the
186-test net; pylint -E clean; verify_solutions 5/5. The inline consensus/collaborative block is the
one remaining chunk that could be extracted next.

### Deferred to a later cleanup (not blocking)

- **Config sprawl:** delete `config/cache.yaml` and the now-dead `models.yaml`/`hardware.yaml` (the
  code reading them is gone); prune dead `.env.example` vars.
- **Collapse remaining duplicate types** (taxonomy, `TestCase`, `ExamplePurpose`); remove the
  builtin-shadowing `TimeoutError`/`RuntimeError` in `shared/errors.py`.

**Verify (C1, met):** full suite green (165; −23 were the deleted dead-module tests); `pylint -E`
clean; `dev/verify_solutions.py` 4/4.

## Milestone D — Generation robustness (the measured bottleneck)

Attack the no-candidate rate. Every change A/B'd through Milestone A's `--trials`.

### D1 — Robust extraction — ✅ DONE (PR: milestone-d-generation-robustness)

`_extract_code` accepted only ` ```python ` fences with a line-heuristic fallback that broke on
module-level `class`/`for`/`import`. Rewrote it around `ast.parse`: gather every fenced block (any
fence — ` ```python `, ` ```py `, bare ` ``` `, `~~~` — or none), plus the whole response as an
unfenced candidate; validate each region by parsing it; prefer the one that defines `solve()`.
Handles reasoning models' `thinking` prose+code. Returns None only when nothing parses. 12 tests.

### D2 — Token/cost accounting — ✅ DONE (same PR)

`AttemptRecord.input_tokens/output_tokens` were structurally zero everywhere. `OllamaProvider` now
sums both model calls (analysis + impl) into `last_token_usage`; `BaseSolver` threads it through
`_record_attempt` on the primary/repair/fallback/no-candidate paths.

### D3 — Poison examples — DOWNGRADED (finding, not the planned fix)

The plan called for dropping mis-paired example files (`2024 d5 p1 ex2` = `143` on an updates-only
fragment; `d6 p1 ex6` = `41` on the solution diagram). **But `years/` is gitignored** (cache
artifacts, not committable) **and the acceptance-veto harm is already guarded**: `_verify_candidate`
only lets examples veto when there is *no* ground truth (`solver.py:744-748`); when the accepted
answer is cached, only `full_answer == known_answer` decides. So a poison example cannot reject a
correct candidate on any problem we can actually score. The residual harm is repair-*feedback*
misdirection (`_build_execution_feedback` still cites the bad example). Left as a targeted follow-up
— suppress example-mismatch feedback when ground truth exists — to be justified by the D1 A/B first.

### D4 — A/B the double-generation — follow-up

`generate_solution` makes two model calls (analysis + impl); the analysis prose is bolted into the
impl prompt and can balloon it toward the `num_ctx`-worse zone. Wire a prompt variant and measure
single-call vs two-call through `--trials`.

**Verify:** a `--trials 5` run of the 2024 d1-3 baseline config on this branch, compared to the
recorded 12/30 baseline (all failures `no_candidate`), shows the no-candidate rate drop with no
regression into `wrong`; result JSONs now carry non-zero token counts.

## Milestone E — Orchestration as measured experiments (re-add with evidence)

Only now, and only what measures a positive delta through the harness.

- **Self-consistency sampling — IN PROGRESS (PR: milestone-e-self-consistency).** `samples_per_model`
  draws N candidates per model instead of one; at temperature > 0 the draws differ, giving several
  shots at the oracle in one run — the direct attack on the measured run-to-run variance (4 of 6
  problems flipped). Keyed the candidate pool by candidate id (with a candidate→model map for
  recording); `samples_per_model=1` is an exact identity. Folded in a prompt-hardening tweak for the
  "correct logic, wrong wrapper" 30% of errors (pin the entrypoint name to exactly `solve`, forbid
  example-usage blocks). A/B'd samp1 vs samp3 (both temperature 0.7, hardened) on 2024 d1-3.
- **Real answer-based consensus — ✅ DONE (PR: milestone-e-answer-consensus).** `_select_candidate`
  groups validated candidates by their *executed* answer and prefers the plurality (quorum
  `min_consensus_models`) when there is no oracle; with an oracle, quality still breaks the tie.
  Justified by an offline analysis of the samp3 data: plurality vote would have picked the correct
  answer for **10 of 11** solved problem-trials (`dev/progress/milestone-e-answer-consensus.md`). Its
  live A/B belongs with F, where unseen problems make the plurality answer the only signal.
- Anything else (roles, collaborative review, strategy learning) is re-added *only* if a harness
  A/B justifies it.

**Verify:** each variant is a `--trials` A/B with a reported delta and a committed result set.

## Milestone F — Solver phase (deferred, per "platform now, solver later")

- Wire `submission/` for genuinely unseen problems, gated on `submit_solutions`, respecting the
  cooldown parser. Requires a fresh `AOC_SESSION`. This is where answer-based consensus gets its
  live A/B.
- Scale evaluation: full 2024, plus an earlier public year, as a benchmark. **First data point in
  (`dev/progress/scale-2024-d4-7.md`):** samp3 on 2024 d4–7 solved only 1/8 (new: d6 p1). The 7B is
  capability-limited past the easy problems — 59% of attempts can't emit runnable code, 39% are
  confidently wrong. Broader coverage is gated on a **stronger model**, which is hardware-blocked on
  16 GB (32b swaps; mid-size models ~5 min/generation → 8 h+ sweeps). The platform's job here is
  done: it turned "the 7B is too weak" from assumption into a measured frontier.

---

## Next steps for the maintainer

**Milestones A–F status:** A–E done, codebase consolidated (C1–C3), F (submission) still deferred —
there is no unseen problem to submit against. The two questions that gated everything for months are
now **answered**, which re-points the roadmap entirely.

### Answered (2026-08-15 → 17), so no longer roadmap items

- **"Find a stronger model."** Done, and the answer was not the expected one: **generation beats
  size**. A 17 GB 2026 *generalist* (`qwen3.8:27b`) swept 2024 d4–7 **8/8**, where an 18 GB
  newer-generation MoE got 6/8 and a **larger** 19 GB 2024 code-specialist managed only 4/8 — below
  what 12B models achieved on half the RAM. Scaling an older generation up does not reproduce the
  gain. (`dev/progress/m2max-qwen38-27b-d4-7.md` and siblings.)
- **The central thesis — "does sampling+voting still add correctness at a *strong* model's own
  frontier?"** Measured: **42% → 75%**, and now decomposed — 1 sample+repair 42%, 3 samples no repair
  58%, 3 samples+repair **75%**. Sampling and repair contribute separately and **superadditively**.
  (`passk-ab-d13-d15.md`.)
- **The d4–7 comparison set is retired** (solved out at 100%); **d8–15 is the working instrument**
  (56%), and the frontier band within it is classified.

### 1. Generality — ✅ ANSWERED (2026-08-18/19)

**The findings generalise.** AoC 2025 (never previously measured) was fetched, scanned and tested:

- **Scan, 2025 d1–12:** 16/23 (70%), **+16 verified solutions** (`generality-2025-scan.md`). A real
  frontier exists out of sample; the **Part 1/Part 2 cliff recurs** (83% vs 55%).
- **Band classification:** only **2 of 10** problems are "sometimes" — 2025's frontier is **bimodal**
  (4 reliable / 2 sometimes / 4 walls) where 2024's was mostly near-misses, making it a *harder*
  venue for the sampling claim (`band-2025-classification.md`).
- **Replication of the central claim:** k1→k3 lifted both "sometimes" problems from **25–33% to
  100%**, while the wall held at 0 and the control stayed at 100% — all four cells as predicted,
  with the prediction registered in advance (`passk-replication-2025.md`).

**Ledger: 43 verified solutions across two years, 0 wrong.**

Remaining under this heading: **widen the replication.** Two "sometimes" problems × 3 trials is a
successful replication attempt, not a confirmation at scale. More frontier problems — 2024 d16–25
(uncached), or a third year — would firm up the effect size rather than just its direction.

### 2. Draw diversity — temperature RULED OUT; strategy-level diversity is the live lever

**One problem resists everything:** 2025 d9 p2, **0 of 10** problem-trials across
`samples_per_model` ∈ {1,3}, `max_repair_iterations` ∈ {0,2}, `temperature` ∈ {0.7,1.0} — the
project's most reproducible negative result, and the benchmark any decorrelation claim must clear.

> **Corrected 2026-08-20.** This said *two* problems, adding 2024 d15 p2 at "0/11, never solved
> once". That was wrong: **d15 p2 has solved 2 of 16 times (~12%)** — the tally summed only the
> arms where it failed. It is a very-low-rate "sometimes", not a wall, and it is in the ledger.
> Neither problem has **ever timed out** (0 timeout attempts on record); they fail by wrong answers
> and crashes. See `dev/progress/CORRECTION-d15p2-is-not-a-wall.md`.

**Tried and failed (2026-08-20):** raising temperature 0.7 → 1.0 at k3 moved neither wall and
slightly hurt a working problem (6/12 → 5/12, `temperature-diversity-negative.md`). The
correlated-draws *diagnosis* may still hold, but temperature is the wrong *instrument*: sampling
more wildly from the same flawed understanding yields noisier versions of the same approach.

The distinction to carry forward:

- **Parameter-level diversity** (temperature, top-p) — perturbs token choice *within* an approach.
  **Tested. Does not help.**
- **Strategy-level diversity** — changes *which* approach is attempted. **Untested, and now the
  best-motivated direction in the project.**

Ordered by cost:

**THE FILTER (adopted 2026-08-21, after five falsified hypotheses):** *interventions that add no new
information do not help, however well-targeted the wording.* Before running anything, ask **what does
the model learn that it did not already know?** If the answer is "nothing", expect a null. Sampling
works because it adds independent draws; repair works because it adds a traceback. Temperature added
variance without information and failed; reworded feedback added exhortation without information and
failed (`targeted-feedback-negative.md`).

1. **Targeted feedback — BUILT AND TESTED; both variants are NULL (2026-08-20/21).** Implemented and gated
   behind `SolverConfig.efficiency_feedback`, with tests, and it fires only on timeouts — but
   **neither target problem ever times out**, so it is inert on them and its A/B was stopped before
   it could produce a false negative. The "execution-bound" premise came from long *wall-clock*,
   which is generation plus repair, not execution. Re-aim it at the failure modes that actually
   occur (wrong answers, crashes) or find problems that genuinely time out. The
   repair prompt currently says only that the answer was not accepted; it should say *"this timed
   out on the real input — propose an asymptotically faster approach"*. This is a prompt change
   aimed exactly at the observed failure, testable against two known-resistant problems.
2. **Prompt variants across draws — DEMOTED by the filter.** Rewording without new information is
   the same class as the null above. Cheap, but now a low prior; run it only if the promoted options
   are blocked.
3. **Cross-generation model mixing — PROMOTED.** A second model's differing answer *is* new
   information. The M1's ensemble failed with two *same-tier, same-generation* models; mixing
   `qwen3.8:27b` with `qwen3-coder:30b` (different architecture *and* generation) is untested, and is
   arm 3 ("decorrelated portfolios") of the README thesis.
4. **Feed back a failing case the model has not seen — PROMOTED, best fit for the filter.** Both
   target problems pass the worked example and fail the real input, so the distinguishing case is
   precisely what the model never sees. Constructing one without leaking the expected answer is the
   hard part and the interesting design problem.

**Caution learned the hard way:** four mechanistic hypotheses in this line of work have now been
falsified by the next run. Treat each of the above as a *measurement to make*, not a fix to apply —
and A/B it against the two resistant benchmarks before believing it.

### 3. The economic arm of the thesis — blocked on an instrument fix

Arm 2 of the README thesis is a *cost* claim: many cheap draws beat one expensive pass at equal
spend. The pair to test it exists — `qwen3-coder:30b` is ~4× faster than `qwen3.8:27b` — as
**MoE at k=5 vs generalist at k=1 at matched wall-clock**. **Do not run it until the token-accounting
bug is fixed** (below): a cost claim measured with broken cost accounting is worthless.

### 4. Instrument gaps — logged, unfixed, each one small

- **Token accounting is stale across repair attempts** (`last_token_usage` reused): attempts report
  identical `(in, out)` counts while returning different answers. Blocks #3.
- **Solver crashes are scored as model failures.** An exception out of the solve path lands in the
  same bucket as "the model could not do it" — which is how a `KeyError` corrupted results for eight
  months undetected (`strategy-keyerror-d8.md`). Wants a distinct `HARNESS_ERROR` outcome.
- **Error-shaped answers are scored `wrong`.** Generated code that catches its own exception and
  prints `An error occurred: …` then `0` is recorded as a wrong answer, understating crashes.

### 5. Submission phase (Milestone F) — still deferred

`submission/` is real and tested in isolation but unwired, and both 2024 and 2025 are solved on the
maintainer's account, so there is no unseen answer to submit. Revisit for a live contest or a fresh
account. Wiring is small: gate a `submission.validate_solution(...)` call on `SUBMIT_SOLUTIONS=true`
after `_execute_and_repair`.

### Optional, unblocked (small cleanups)

See "Deferred to a later cleanup" under Milestone C: delete the dead `config/*.yaml`, prune dead
`.env.example` vars, collapse the last duplicate types. `OllamaProvider.__init__`'s default
`model="codellama:7b"` is also stale (inert — every call site passes `model` explicitly).

## Documentation

Docs are realigned to the current state and kept fresh per PR: `README.md` (platform overview +
findings), `dev/docs/architecture.md` (design), `dev/progress/checkpoint.md` (live status),
`dev/progress/*.md` (the committed baselines, A/Bs, and the capability frontier), and the
`dev/diagrams/*.mmd` sequence diagrams. Keep them in step as future work lands.

## Sequencing

A (measure) → B (sound instrument) → C (consolidate) → D (robustness) → E (orchestration) →
F (solver). **A–E are done**, and the two maintainer-gated blockers that followed them — a stronger
model, and the pass@k thesis test — are **both now answered** (see "Answered" above).

The work from here is no longer a milestone ladder but a research loop: **generalise the findings to
a second year (#1), attack the failure mode the data exposed (#2), then settle the cost claim (#3)
once the accounting supports it (#4).** F stays deferred until there is an unsolved target.
