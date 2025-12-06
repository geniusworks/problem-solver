## Current Unified Roadmap Checklist

### 1. Solver Pipeline & AoC Integration
- [x] Remove the debug `exit()` and fix `learning_dir` initialization in `BaseSolver.solve_problem`.
- [x] Add an integration test that drives `solve.py` for 2024 Day 01 Part 1 (with a stub or local model) and verifies end-to-end behavior.
- [x] Clarify and, if needed, update AoC utilities (such as `get_problem_year_day`) for the 12-day AoC 2025 format.

### 2. Consensus, Validation, and Learning
- [ ] Test and refine the weighted consensus system with real problems and add unit tests for `_get_weighted_consensus_answer`.
- [ ] Verify and harden validator and reviewer/collaborative improvement flows with at least one integration-style test.
- [ ] Wire real code quality metrics from `CodeQualityAnalyzer` into the learning database and verify via tests.

### 3. Problem Classification & Model/Strategy Selection
- [ ] Implement a real `_get_problem_type` in `BaseSolver` using problem analysis/strategy signals.
- [ ] Integrate problem type into `get_top_models` and strategy recommendation.
- [ ] Add tests that confirm sample problems map to expected problem types and top-model sets.

### 4. Coverage & Monitoring
- [ ] Increase test coverage for solver, LLM integration, validator, quality, submission, and learning modules.
- [ ] Add basic memory/OOM safeguards for large models and verify behavior on the target hardware.

### 5. Long-Term Enhancements
- [ ] Plan and schedule analytics dashboards, automated strategy refinement, and problem similarity matching.
- [ ] Tune cold-start weights based on real usage data once enough attempts have been collected.