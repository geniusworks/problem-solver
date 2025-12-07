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
   - Model Management (`shared/llm/models.py`)
     - Role-based model registry
     - Hardware-aware model selection
     - Performance tracking per role
     - Model characteristics and capabilities
   - Provider Integration (`shared/llm/local.py`)
     - Local Ollama provider with curated model list for typical developer hardware
     - Preflight check against Ollama `/api/tags` to intersect configured models with
       actually installed tags
   - Dynamic Prompt Generation (`prompts.py`)
   - Strategy Selection (`shared/strategies.py`)

3. **Solution Execution** (`shared/execution.py`)
   - Safe code execution environment
   - Resource monitoring and limits
   - Performance metrics collection
   - Execution-based candidate selection and iterative repair loop after consensus using
     example and full-input runs
   - Non-force runs reuse existing validated canonical solution files (`YYYY_dayDD_partP.py`)
     by executing them once against the full input before falling back to a fresh multi-model
     solve when needed
   - Attempt tracking and analysis

4. **Learning System** (`learning/`)
   - Strategy effectiveness tracking
   - Solution pattern library
   - Cross-problem pattern recognition
   - Performance optimization system
   - Model role performance tracking
   - Role-based model selection
   - Hardware compatibility management
   - Problem type classification feeding model and strategy selection
   - Code quality metrics recorded per attempt and used in model performance tracking
   - Optional collaborative improvement phase that can be enabled via the
     `ENABLE_COLLABORATIVE_IMPROVEMENT` environment flag (disabled by default for
     typical AoC runs)

## Configuration Management

Configuration is layered to separate shared defaults from local settings:

### YAML Configuration (Shared Defaults)
- `config/models.yaml`: Model capabilities and default parameters
- `config/hardware.yaml`: Hardware profiles and capabilities
- `config/resources.yaml`: Resource limits and timeouts
- `config/cache.yaml`: Cache behavior settings

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
- `execution.py`: Safe code execution
- `validator.py`: Solution validation
- `testing.py`: Solution testing framework

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
