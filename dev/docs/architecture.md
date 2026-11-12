# System Architecture Documentation

## Overview

Problem Solver is a research platform for measuring LLM orchestration, with Advent of Code as its
testbed; secondarily it is an AoC solver. This document outlines its architecture and core
components.

## Core Systems

### Problem Solving Pipeline

1. **Problem Fetching & Parsing** (`shared/parser.py`)
   - Problem text and input parsing (`shared/parser.py`)
     - HTML-first example extraction from AoC `<article class="day-desc">` content
     - AoC-aware part handling so Part 1 and Part 2 are solved atomically using the
       correct per-part article for examples and the final question
     - `shared/problem_context.py` then widens what the model reads to what a solver on the
       site has: for Part 2, Part 1's statement and accepted answer and the recorded Part 1
       program; for both, a preview of the input. The experiment runner attempts a Part 2
       only in a trial that solved Part 1. `problem_context=legacy` turns this off
       (`dev/progress/part2-prompt-omits-part1.md`)
     - Example tests are read off the page (`statement_examples`): a code block is an example
       input if it resembles the puzzle input, and its result is the last emphasised integer
       before the next one. `example_tests=parser` (and `problem_context=legacy`) keep the
       parser's pairing (`dev/progress/example-tests-mispaired.md`)
     - AoC-style example and expected-output inference from `<pre><code>` blocks and
       surrounding prose
     - Separate example storage (.examples.txt)
     - Fallback plain text parsing
   - Problem analysis and understanding (`shared/problem_analysis.py`)
   - Test case extraction and validation (see `tests/`)

2. **Solution Generation** (`shared/llm/`)
   - Provider (`shared/llm/local.py`) — the only provider is the local Ollama
     one (`OllamaProvider`), talking to Ollama's HTTP `/api/generate`. Reasoning
     models that split `thinking` from `response` are handled; `num_ctx` is a
     swept config field. The remote-provider and LM-Studio scaffolding was
     removed as unreachable.
   - Preflight check against Ollama `/api/tags` intersects the configured/curated
     model list with the tags actually installed (`_resolve_available_models`).
   - Dynamic prompt generation (`shared/llm/prompts.py`)
   - Strategy recommendation (`shared/strategy_recommender.py` +
     `shared/strategies.py`) — seeds generation with candidate strategies and
     their learning-DB effectiveness.
   - **Model fallback** — the top `max_primary_models` (by learning-DB metrics)
     are tried first; if all fail verification the remaining installed models are
     tried; every attempt records its *verified* outcome to the learning DB.

3. **Solution Execution** (`shared/execution.py`)
   - Resource-limited execution environment (no `.env` secrets; not a security boundary)
   - Resource monitoring and limits
   - Performance metrics collection
   - Execution-based candidate selection and iterative repair loop after consensus using
     example and full-input runs
   - **Enhanced execution feedback**: Test failures include expected vs actual output values
     to guide repair iterations
   - Non-force runs reuse existing validated canonical solution files (`YYYY_dayDD_partP.py`)
     by executing them once against the full input before falling back to a fresh multi-model
     solve when needed
   - Attempt tracking and analysis

4. **Learning System** (`learning/`)
   - One SQLite database (`learning/solver.db`) for model performance and
     strategy effectiveness — recorded from the *verified* outcome, not at
     generation time.
   - Model ranking reads each model's verified success rate; the strategy-weight
     half is an unimplemented stub (`learning/optimizer.py`).
   - Optional collaborative improvement phase, enabled via the
     `ENABLE_COLLABORATIVE_IMPROVEMENT` flag (off by default). Any candidate it
     produces goes through the same oracle verification as every other path.

5. **Measurement Platform** (`shared/experiment/`, `shared/verification.py`,
   `shared/ground_truth.py`, `shared/overfit_detection.py`) — the core product.
   - `SolverConfig` (a frozen, fingerprinted config), `ExperimentResult`/
     `ProblemResult`/`AttemptRecord`, and `run_experiment`/`run_problem` in
     `shared/experiment/`; driven by `experiment.py` (`--trials N` for
     repeat-trials, since the pipeline is non-deterministic). The result JSON is
     rewritten after every result, so a stopped run keeps what it finished, and records what the
     run ran on (Ollama version, model digests, package versions, machine, commit) outside the
     fingerprint (`shared/experiment/environment.py`). Each verified attempt also records how
     many worked examples it passed (`examples_passed`/`examples_total`), beside the oracle's
     verdict.
   - Generated code always runs in a child process started by `shared/sandbox.py`: an
     environment without `.env` secrets, CPU, file-size and process limits, and a memory cap
     (8 GB per process, `config/resources.yaml`). The cap is an address-space limit on Linux;
     macOS ignores that, so the runners also poll the child's physical footprint (resident plus
     compressed) and kill it above the cap. A full-input run, in the solve loop and in the oracle's
     own runner (`shared/verification.py`), happens in a fresh temporary directory holding only a
     copy of `input.txt`, so the accepted answers and verified solutions beside the real input are
     not reachable by relative path. It keeps network
     access and the user's file permissions, so it is not a security boundary.
   - A correctness **oracle**: candidates are judged against cached accepted AoC
     answers (`shared/ground_truth.py`) and worked examples, with an overfit gate
     (`shared/overfit_detection.py`). Claimed vs. verified is tracked separately;
     nothing is counted as solved without independent verification.

## Configuration Management

Configuration is layered to separate shared defaults from local settings:

### YAML Configuration (Shared Defaults)
- `config/resources.yaml`: the one live config file — execution/request limits and
  the submission toggle (`shared/config.py` reads it into `RESOURCES_CONFIG`).

### Environment Configuration (Local Settings)
- `AOC_SESSION` (the Advent of Code session cookie) and `AOC_CONTACT`
- `OLLAMA_HOST`, `SOLVER_MODELS`, `MAX_REPAIR_ITERATIONS`
- `ENABLE_COLLABORATIVE_IMPROVEMENT`, `SUBMIT_SOLUTIONS`, `LOG_LEVEL`

See `.env.example` for available environment variables.

## Core Components

### Shared Library (`shared/`)

#### Configuration (`config.py`)
- Loads and merges configuration from all sources
- Provides access to settings throughout the system

#### Error System (`errors.py`)
- Structured error hierarchy
- Provider-specific error handling
- Validation error types

#### Core utilities
- `paths.py`: problem path primitives — the repo's leaf layer, imports only
  config, so verification/ground_truth/ledger can depend on it without a cycle
- `aoc.py`: Advent of Code I/O — session/auth, HTTP, problem fetch + caching
- `ledger.py`: the solution ledger — `record_solution`/`save_solution_file`,
  oracle-gated so nothing is recorded without producing the accepted answer
- `logging_setup.py`: application logging configuration

#### Solution Management
- `execution.py`: sandboxed code execution + `PerformanceMetrics`
- `solver.py`: `BaseSolver.solve_problem`, a short orchestrator over four stages —
  `_prepare_problem` → `_generate_candidates` → `_reach_consensus` →
  `_execute_and_repair` — plus problem preparation, the attempt records and model
  selection. The other stages live in `solving/` (split out of a 1,433-line
  `solver.py` on 2026-11-12, behaviour unchanged): `generation.py` draws the
  candidate pool, where self-consistency (`samples_per_model`) fans out several
  candidates per model; `consensus.py` holds source consensus and the default-off
  collaborative improvement; `candidates.py` verifies one candidate against the
  oracle (`_verify_candidate`, the only copy) and selects among those accepted;
  `repair.py` runs the verify and repair rounds and the fallback models;
  `feedback.py` writes what a failed candidate's repair is told. `BaseSolver`
  takes them as mixins, and the stages reach the ledger writer and the accepted
  answer through it, so tests replace those in one place
- `submission/` (top-level package): the real AoC answer submitter, **isolated
  and deliberately unwired** — kept for the solver phase (Milestone F), not
  called from the solve loop

### Learning System (`learning/`)

The learning system records performance; model ranking reads it, and the strategy-weight half is
an unimplemented stub (`learning/optimizer.py`):

- `database.py`: Performance metrics storage
- `optimizer.py`: strategy weights (an unimplemented stub)
- `schema.sql`: Database schema

## Data Flow

1. Problem Input
   - Problem text fetched from AoC
   - Parsed into structured format
   - Test cases extracted

2. Solution Generation
   - Problem analyzed by LLM
   - Solution code generated
   - Validated against test cases

3. Solution Execution
   - Code executed in a resource-limited environment (see Solution Execution above)
   - Results validated
   - Performance metrics collected

4. Learning
   - Performance data stored from verified outcomes
   - Model ranking for the next problem reads it (experiments pin their models, so it is inert there)

## AoC Part Handling Example (2024 Day 1)

- The 2024 Day 1 page has two `<article class="day-desc">` blocks:
  - Part 1: one `<pre><code>` block with the six-line example and prose ending in
    "a total distance of 11".
  - Part 2: reuses the same example input but defines a new "similarity score" and gives
    answer `31`.
- `fetch_problem_text` selects the correct article **per part** and returns its HTML so
  `parse_problem_text` can:
  - Keep each `<pre><code>` block as a single example input.
  - Infer the expected output (e.g. `11` for Part 1, `31` for Part 2) from AoC-style prose
    and emphasized `<em>` numbers.
- `BaseSolver.solve_problem` always uses this part-specific parse, so Part 1 prompts never
  include Part 2 instructions. Under `problem_context=aoc` (the default) a Part 2 prompt also
  carries Part 1's statement, accepted answer and program; under `legacy` it carries Part 2 alone.

## Development Guidelines

1. Configuration
   - Use YAML for shared defaults
   - Use .env for local/machine-specific settings
   - Keep sensitive data in .env

2. Error Handling
   - Use appropriate error types
   - Include context in error messages
   - Log errors appropriately

3. Testing
   - Write tests for new components
   - Use test fixtures
   - Check both success and failure cases
