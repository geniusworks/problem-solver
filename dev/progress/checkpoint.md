# Project Checkpoint

**Instructions for AI Assistant**:
READ/SUMMARIZE: Provide status overview only (skip "SESSION WRAP-UP steps")

SESSION WRAP-UP steps:
- [ ] Update "Current Status" (with today's date):
    - Update component statuses and active work
    - Review and update known issues
    - Refresh immediate next steps
    - Update active priorities

- [ ] Manage "Development Progress":
    - Move completed items >2 weeks old to dev/progress/checkpoint-history.md (preserve dates)
    - Update in-progress and planned items
    - Ensure alignment with strategic objectives
    - Add today's work under new dated entry in checkpoint-history.md
    - Add new "Key Decisions" with today's date to history

- [ ] Maintain Documentation:
    - Update README.md for structural changes
    - Update dev/diagrams/* for system changes
    - Update dev/docs/development-guidelines.md for process changes
    - Update dev/docs/architecture.md if architecture changed
    - Require user approval for strategic changes:
        - Strategic Objectives updates (README.md ↔ checkpoint.md)
        - Development Roadmap updates (checkpoint.md ↔ README.md)

- [ ] Commit Changes:
    - Group changes logically (documentation, code, configuration)
    - Commit with clear, descriptive messages
    - Push changes to repository

Note: Execute the above steps only on explicit wrap-up request.

## Checkpoint Integrity Guidelines

**Core Principles**:
- Reflect all significant changes in this document
- Maintain clear project context and direction
- Move historical context to checkpoint-history.md

**Quick Action Checklist**:
- [ ] Compare current state with documentation
- [ ] Clarify any detected divergences
- [ ] Update checkpoint with full understanding
- [ ] Preserve core principle consistency

## Current Status (2026-08-11)

**Authoritative roadmap: `PLAN.md` at the repo root.** This section is the live status snapshot;
the historical/architecture sections below are pre-refactor and are rewritten as Milestone C lands.

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
- **gemma4:12b is the leading model candidate (`dev/progress/model-bakeoff-gemma4-vs-9b.md`):** in a
  d4–7 bake-off it matched the 9b's *best* result (5/8) at **1/3 the samples** (samples=1 vs the 9b's
  samples=3) and less wall clock, solving the hard Part 2 d7 p2 on a single draw. samples=1 is noisy
  (the 9b drew low, 2/8, vs its known 5/8), so this is "promising, probably better," not proven —
  a gemma4 samples=3 confirmation vs the 9b's 5/8 is the deciding test. (`deepseek-r1:14b` was tested
  and dropped — reasoning-native, ignores `think=false`, incompatible with our pipeline; no Q6
  qwen3.5 tag exists.)
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
The cheap M1 solve-rate levers are **exhausted**: extraction robust, self-consistency handles
variance, thinking-off fixed the reasoning model, a 5× timeout recovered nothing
(`9b-timeout-investigation.md`) — the remaining hard Part 2s (d5 p2, d6 p2) are a genuine capability
limit on 16 GB. **All M1 16 GB results are consolidated in `dev/benchmarks/cross-machine-results.md`,
keyed by machine for cross-hardware comparison.** Where that leaves the priorities:

1. **A stronger model — now UNBLOCKED: maintainer has an M2 Max / 32 GB.** That fits the tier that
   swamps 16 GB (`qwen2.5-coder:32b`, `Qwen3-Coder-30B-A3B`). Run those at samples=3 on d4–7 and add
   the rows to `dev/benchmarks/cross-machine-results.md` under a new `m2max-32` machine id. Decisive
   question: does a bigger model crack **d5 p2 / d6 p2**, which no 16 GB model has? (A remote/cloud
   `OLLAMA_HOST` is the alternative.)
2. **Confirm the M1 leader:** `gemma4:12b` samples=3 on d4–7 vs the 9b's 5/8 (in progress).
3. **Algorithm-efficiency prompting — low-confidence, cheap to try** on M1 for the timeout-bound Part 2s.
4. **Submission phase (F) — deferred.** No unsolved target; revisit for AoC 2026 or a fresh account.

Reasonable stopping point: the platform has demonstrated its result on this hardware — a measured
model win, 11 oracle-verified solutions, everything reproducible.
Optional, unblocked: the small deferred cleanups (dead `config/*.yaml`, remaining duplicate types).


### Active Development

#### Model Selection and Performance Tracking
- [x] Implemented role-based model selection (PRIMARY, REVIEWER, VALIDATOR)
- [x] Added performance tracking in SQLite database
- [x] Integrated with existing learning system
- [x] Implemented code quality scoring for model performance metrics and wired it into the
      learning database
- [x] Added problem type classification and integrated it into model/strategy selection

#### Model Registry Updates
- Updated model list to focus on efficient coding models that fit M1 16GB constraints:
  - qwen2.5-coder:7b (4.7GB) - Primary code generation and completion
  - llama3.1:8b (4.9GB) - Strong general reasoning and problem solving
  - mistral:7b (4.4GB) - Fast, robust general performer
  - codellama:7b-instruct (3.8GB) - Legacy but solid code model and fallback
  - gemma3:latest (3.3GB) - Compact, good general model
  - deepseek-coder:6.7b - Additional code-focused model for diversity
- Added ALIBABA to ModelProvider enum for Qwen models
- Removed or de-emphasized larger models that exceed practical memory constraints
- Updated model naming and configuration to match Ollama conventions and curated list

### Component Status
- Core solver: Stable, actively improving
- Model integration: Working, needs monitoring
- Documentation: Under reorganization

### Known Issues
- Need to validate performance characteristics of the curated model set under sustained
  AoC workloads.
- Some larger models (>13B effective size) may still cause OOM or poor performance on
  16GB systems if accidentally used; these have been removed from the default list but may
  exist locally.

### Next Steps
1. Implement proper code quality scoring system
2. Add comprehensive problem type classification
3. Gather real performance metrics for each model
4. Consider adding memory monitoring to prevent OOM situations
5. Test model combinations for optimal role assignments

## Development Roadmap

### Strategic Objectives
[ ] Achieve autonomous problem analysis and solving
    - Enhance automatic strategy identification
    - Improve pattern recognition across problem types
    - Develop robust input validation and parsing
    - Enable self-guided debugging and optimization

[ ] Implement collaborative multi-model system
    - Design model specialization framework
    - Enhance consensus-based validation
    - Develop inter-model learning mechanisms
    - Create adaptive model selection

[ ] Build comprehensive learning and optimization
    - Implement strategy effectiveness tracking
    - Create solution pattern library
    - Develop performance optimization system
    - Enable cross-problem knowledge transfer

### Planned
[ ] Add analytics dashboard for model performance
[ ] Implement automated strategy refinement
[ ] Enhance problem similarity matching
[ ] Fine-tune cold-start weights based on usage data

### Current Focus
[x] Enable and test the full solver pipeline end-to-end for at least one AoC problem (2024 Day 01).
[x] Exercise and refine weighted consensus, validation, and reviewer/collaborative flows (integration tests + real 2024 Day 01 run).
[x] Implement and wire up problem type classification and code quality scoring.
[ ] Improve test coverage for solver, LLM integration, validator, quality, and learning modules.

### Completed ✓ (Last 2 weeks)
[x] Improve input file handling and security (2025-01-18)
    - Changed to use simple 'input.txt' in solutions
    - Added runtime path substitution
    - Separated model code from runtime code
[x] Enhance solution template implementation (2025-01-17)
    - Updated prompts.py with improved solution template
    - Added structured problem analysis guidance
    - Enhanced input pattern recognition and handling
[x] Enhance LLM prompt generation (2025-01-17)
    - Refactored prompt generation code for better organization
    - Improved strategy integration in templates
    - Added dynamic prompt sections based on problem analysis