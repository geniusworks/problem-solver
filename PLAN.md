# Problem Solver — Forward Roadmap & Structural Consolidation

## Context

PR #1 turned the solver from an unmeasurable pipeline into one with a correctness oracle, an
experiment harness, and independent verification. Two full-codebase audits (structural + pipeline)
now show where it stands.

**The empirical reframe.** Across recorded runs, **when the model produces a candidate it is ~9:1
correct** (9 solved, 1 wrong). The dominant failure is *no candidate at all* plus outcomes flipping
across byte-identical configs. So the bottleneck is **generation robustness and run-to-run
variance — not model capability, not orchestration sophistication.** "The 7B models are too weak"
was never measured; it was inferred from a broken instrument.

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

## Milestone A — Trustworthy measurement (FIRST)

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

## Milestone B — Make the instrument sound (small, high-trust)

A platform with hollow config fields and a live oracle bypass can't be trusted for the experiments
to come.

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

Per "delete now, re-add with evidence." Preserve git history; re-introduce with the harness later.

- **Delete unreachable modules:** `shared/llm/providers.py`, `shared/validator.py` *(after moving its
  real `submit_and_validate` to `submission/`)*, `shared/testing.py`, `shared/llm/hardware.py`,
  `learning/strategies.py`, and the tests that only prop them up
  (`tests/integration/test_llm.py`, the dead-config assertions in `tests/unit/test_config.py`).
- **Delete no-op subsystems:** strategy-learning write loop, `shared/llm/collaborative.py`,
  `shared/submission.py:submit_solution` (simulated). Keep `get_recommended_strategies` only if
  something reads its output honestly; otherwise inline a keyword default.
- **Delete solver dead code:** `ModelRole`/`AttemptResult`/`ModelSelector` (`solver.py:44-110`),
  `_save_solution`/`_save_attempt`/`_count_attempts` (`:1080-1250`), module-level `solve_problem()`
  (`:1271`), the 5× duplicated learning-write blocks.
- **Decompose `solve_problem`** into the staged `shared/solver/` package (see Target structure). Each
  stage typed and unit-tested.
- **De-grab-bag `shared/utils.py`** (898 lines, 7 responsibilities) into `shared/aoc/` (fetch/cache/
  session) and `shared/ledger.py` (record/save). Kill the mid-file re-imports (`:673-675`) and the
  `utils → verification → ground_truth → utils` cycle (`:310-312`) by moving the ledger's oracle
  calls up a layer.
- **Collapse duplicate types** to one each (taxonomy, `TestCase`, `PerformanceMetrics`,
  `ExamplePurpose`, error classes; remove the builtin-shadowing `TimeoutError`/`RuntimeError` in
  `shared/errors.py`).
- **Config sprawl:** delete `config/cache.yaml`, the dead `models.yaml`/`hardware.yaml` and the 9
  dead `.env.example` vars; add the 5 live ones (`SOLVER_MODELS`, `REFERENCE_MODEL`,
  `MAX_REPAIR_ITERATIONS`, `ENABLE_COLLABORATIVE_IMPROVEMENT`, `SUBMIT_SOLUTIONS`).

**Verify:** full suite green; `pylint -E` clean; `mypy` no new errors; fresh clone (no `years/`)
green; `dev/verify_solutions.py` 4/4. Line count of `shared/solver` core well under 400.

## Milestone D — Generation robustness (the measured bottleneck)

Attack the no-candidate rate. Every change A/B'd through Milestone A's `--trials`.

- **Robust extraction:** `_extract_code` (`shared/llm/local.py:226-258`) only accepts ` ```python `
  fences. Accept bare ` ``` `, `~~~`, and AST-scan the whole response for a `solve` def as a last
  resort — including the reasoning-model `thinking` fallback text.
- **Remove poison examples:** `years/2024/day05/examples/part1/example_2.json` (`143` paired with
  updates-only input), `day06/part1/example_6.json` (`41` on the solution diagram),
  `day06/part2/{1,6}.json`. These reach the model via `format_test_cases` *and* misdirect the repair
  loop via `_build_execution_feedback`. Fix the parser pairing or drop these example files.
- **A/B the double-generation:** `generate_solution` makes two model calls (Phase-1 analysis +
  Phase-3 impl); Phase-1 prose is bolted verbatim into the impl prompt and can balloon it into the
  `num_ctx`-worse zone. Wire `prompt_variant` and measure single-call vs two-call.
- **Token/cost accounting:** thread `eval_count`/`prompt_eval_count` (`local.py:397-404`) into
  `AttemptRecord.input_tokens/output_tokens` — today structurally zero in every result JSON.

**Verify:** a `--trials 5` baseline before/after shows the no-candidate rate drop with the solve
rate steady or up; result JSONs carry non-zero token counts.

## Milestone E — Orchestration as measured experiments (re-add with evidence)

Only now, and only what measures a positive delta through the harness.

- **Real answer-based consensus:** group by the *executed answer*, require ≥2 agreeing models,
  reinstate `consensus_on`. A/B vs single-model.
- **Self-consistency sampling:** N samples from one model at temperature>0, majority vote on the
  executed answer (`samples_per_model`). Likely the highest-value trick for weak models; cheap
  locally.
- Anything else (roles, collaborative review, strategy learning) is re-added *only* if a harness
  A/B justifies it.

**Verify:** each variant is a `--trials` A/B with a reported delta and a committed result set.

## Milestone F — Solver phase (deferred, per "platform now, solver later")

- Wire `submission/` for genuinely unseen problems, gated on `submit_solutions`, respecting the
  cooldown parser. Requires a fresh `AOC_SESSION`.
- Scale evaluation: full 2024, plus an earlier public year, as a benchmark.

---

## Documentation

Realign as each milestone lands, not in one pass. **Immediately** fix the actively-false bits:
`checkpoint.md:57,84` (contradicts the ledger), the dead `shared/llm/models.py` / `CONTRIBUTING.md`
links in `README.md`, and the stale `ollama run` comment (`shared/llm/local.py:30-32`). Rewrite
`architecture.md` and the diagrams to the Target structure once Milestone C lands. `checkpoint.md`
should record the PR #1 refactor and the new baseline numbers.

## Sequencing

A (measure) → B (sound instrument) → C (consolidate) → D (robustness) → E (orchestration) →
F (solver). A and B are small and come first because every later number depends on them. C is the
integrity payoff. D targets the actual bottleneck. E is the research. F is the product goal, and it
waits — deliberately — until the platform can prove whether any of it works.
