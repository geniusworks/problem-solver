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
- **Milestone C1 (this PR) — deletion + isolation:** removed ~1,400 lines of dead/misplaced code
  (solver selector/saver clusters + module entrypoint, `providers.py`, `hardware.py`,
  `learning/strategies.py`, `testing.py`, `LMStudioProvider`, the simulated submit stub); relocated
  `PerformanceMetrics` to `execution.py`; extracted `StrategyRecommender` from the misnamed
  `SubmissionManager`; isolated the real, unwired AoC submitter into a top-level `submission/`
  package. A reachability audit corrected several stale plan claims (collaborative.py is live and
  stays; `SubmissionError` lives in `errors.py`). Suite 165 green. The `utils` split (C2) and
  `solve_problem` decomposition (C3) are separate follow-up PRs.

### Verified reality (not claims — measured)
- Recorded solutions: **4 verified correct** (2024 d1 p1/p2, d2 p1, d3 p1). See `solutions/README.md`.
  The earlier "6/10" figure was never true; three recorded solutions were wrong and are quarantined
  in `solutions/rejected/`.
- **First multi-run baseline** (`dev/progress/baseline-2024-d1-3.md`): qwen2.5-coder:7b, 2024 d1–3,
  5 trials — **12/30 solved (40%); 4 of 6 problems solvable, 0 of 6 reliable.** Four of six flip
  across identical runs; single-run numbers are noise.
- **Every failure is `no_candidate`, never `wrong` or `overfit`.** When the pipeline emits a
  parseable solution it is correct. The bottleneck is producing a candidate, not model capability.

### Next (per PLAN.md)
- **Milestone C2 (this PR) — DONE:** retired the `shared/utils.py` grab-bag into `paths.py` (leaf) +
  `aoc.py` (AoC I/O) + `ledger.py` (oracle-gated record/save) + `logging_setup.py`, and broke the
  `utils → verification → ground_truth → utils` import cycle. Deleted 4 dead helpers.
- **Milestone C3 — decompose `solve_problem`:** into typed, tested stage-methods (not a package).
  Maintainability hygiene; moves no *measured* number, so it does not block D.
- **Milestone D — generation robustness (the measured bottleneck):** attack the `no_candidate` rate
  (robust extraction, poison examples, token accounting). Recommended priority over C3, since the
  baseline says generation robustness — not code structure — is what stands between the platform and
  results.


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