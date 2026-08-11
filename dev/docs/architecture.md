# System Architecture Documentation

## Overview

The Problem Solver is an AI-powered system designed to solve Advent of Code problems. This document outlines its architecture and core components.

## Core Systems

### Problem Solving Pipeline

1. **Problem Fetching & Parsing** (`shared/parser.py`)
   - Problem text and input parsing (`shared/parser.py`)
     - HTML-first example extraction from AoC `<article class="day-desc">` content
     - AoC-aware part handling so Part 1 and Part 2 are solved atomically using the
       correct per-part article
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
   - Safe code execution environment
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
   - Strategy effectiveness tracking and problem-type classification feeding
     model/strategy selection.
   - Optional collaborative improvement phase, enabled via the
     `ENABLE_COLLABORATIVE_IMPROVEMENT` flag (off by default). Any candidate it
     produces goes through the same oracle verification as every other path.

5. **Measurement Platform** (`shared/experiment/`, `shared/verification.py`,
   `shared/ground_truth.py`, `shared/overfit_detection.py`) — the core product.
   - `SolverConfig` (a frozen, fingerprinted config), `ExperimentResult`/
     `ProblemResult`/`AttemptRecord`, and `run_experiment`/`run_problem` in
     `shared/experiment/`; driven by `experiment.py` (`--trials N` for
     repeat-trials, since the pipeline is non-deterministic).
   - A correctness **oracle**: candidates are judged against cached accepted AoC
     answers (`shared/ground_truth.py`) and worked examples, with an overfit gate
     (`shared/overfit_detection.py`). Claimed vs. verified is tracked separately;
     nothing is counted as solved without independent verification.

## Configuration Management

Configuration is layered to separate shared defaults from local settings:

### YAML Configuration (Shared Defaults)
- `config/resources.yaml`: Resource limits and timeouts (live)
- `config/models.yaml`, `config/hardware.yaml`, `config/cache.yaml`: legacy —
  the code that read them (the remote-provider registry, `HardwareManager`) has
  been deleted; these files are pending removal in a later cleanup.

### Environment Configuration (Local Settings)
- API keys and credentials
- Hardware-specific settings
- Local preferences
- Debug settings

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

#### Utilities (`utils.py`)
Core functionality including:
- Problem fetching and caching
- File management
- Session handling
- HTTP requests

#### Solution Management
- `execution.py`: safe code execution + `PerformanceMetrics` (relocated here
  from the deleted `testing.py`)
- `solver.py`: `BaseSolver.solve_problem`, the generate → verify → repair →
  fallback pipeline
- `submission/` (top-level package): the real AoC answer submitter, **isolated
  and deliberately unwired** — kept for the solver phase (Milestone F), not
  called from the solve loop

### Learning System (`learning/`)

The learning system optimizes solution strategies based on past performance:

- `database.py`: Performance metrics storage
- `optimizer.py`: Strategy selection and optimization
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
   - Code executed in safe environment
   - Results validated
   - Performance metrics collected

4. Learning
   - Performance data stored
   - Strategies optimized
   - Future approach adjusted

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
  include Part 2 instructions, and vice versa.

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
