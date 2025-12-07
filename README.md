# Problem Solver

An intelligent system for solving algorithmic programming problems using LLMs and strategic problem analysis.

## Features

### Core Capabilities
- Automated problem parsing and analysis
- Strategic solution generation
- Input format validation and handling
- Performance optimization guidance

### Enhanced LLM Integration
- Dynamic prompt generation based on problem type
- Strategy-specific solution guidance
- Modular prompt architecture
- Adaptive parsing templates
- Role-based model selection
- Performance tracking and learning
- Hardware-aware model management

### Problem Analysis
- Automatic strategy identification
- Pattern recognition
- Input format analysis
- Solution validation

### Solution Generation
- Strategy-based implementation
- Input parsing optimization
- Performance consideration
- Debug output generation
- Comprehensive attempt recording
- Consensus-based validation
- Execution-feedback repair loop using examples and full input before giving up

### Execution and Monitoring
- Robust solution execution
- Performance metrics tracking
- Detailed logging and debugging
- Attempt history management
- Model performance analysis

## Strategic Objectives

### Autonomous Problem Solving
- Automated problem analysis and strategy identification
- Pattern recognition across problem types
- Self-guided debugging and optimization
- Robust input validation and parsing

### Multi-Model Collaboration
- Model specialization framework
- Role-based task distribution
- Performance-driven model selection
- Consensus-based validation
- Inter-model learning mechanisms
- Adaptive role assignment

### Learning and Optimization
- Strategy effectiveness tracking
- Solution pattern library
- Performance optimization system
- Cross-problem knowledge transfer

## Components

### Problem Analysis
- `shared/parser.py`: Problem parsing and example extraction
  - HTML-first example extraction from AoC `<article class="day-desc">` content
  - AoC-aware part handling (solves Part 1 and Part 2 atomically using the correct article)
  - AoC-style example and expected-output inference from `<pre><code>` blocks and surrounding prose
  - Separate example storage (.examples.txt)
  - Fallback plain text parsing
- `shared/problem_analysis.py`: Deep problem understanding
- `shared/strategies.py`: Solution strategy framework

### LLM Integration
- `shared/llm/base.py`: Base LLM provider interface
- `shared/llm/local.py`: Local LLM implementation (Ollama)
- `shared/llm/prompts.py`: Dynamic prompt generation
- `shared/llm/models.py`: Model management and selection
- `learning/database.py`: Model performance tracking

### Solution Management
- `solutions/`: Generated solution implementations
- `shared/quality/`: Code quality and validation tools
- `shared/execution.py`: Solution execution and monitoring
 

## Getting Started

1. Install dependencies:
   ```bash
   pip install -r requirements.txt        # Core dependencies
   pip install -r requirements-dev.txt    # Development tools
   ```

2. Set up Ollama:
   - Install Ollama from [ollama.ai](https://ollama.ai)
   - Pull recommended local models (install at least one; more improves ensemble quality):
     ```bash
     ollama pull qwen2.5-coder:7b
     ollama pull llama3.1:8b
     ollama pull mistral:7b
     ollama pull codellama:7b-instruct
     ollama pull gemma3:latest
     ollama pull deepseek-coder:6.7b
     ```
   - On startup, the solver checks which of these models are actually installed via the Ollama
     API and will raise a clear error message if none of the configured models are available.

3. Configure environment:
   - Create a `.env` file in the project root
   - Add your Advent of Code session token:
     ```bash
     AOC_SESSION=your_session_cookie  # Get this from adventofcode.com cookies after logging in
     ```
   To get your session cookie:
   1. Log in to adventofcode.com
   2. Open browser developer tools (F12)
   3. Go to Application/Storage -> Cookies
   4. Copy the value of the 'session' cookie

   Optional environment flags:
   - `ENABLE_COLLABORATIVE_IMPROVEMENT`: When set to `true` (or `1`, `yes`, `on`), the
     solver will, after attempting consensus between primary models, run an additional
     collaborative improvement phase using reviewer models. This is **disabled by
     default** for normal AoC runs to keep solve times predictable; integration tests
     exercise the collaborative path explicitly.

4. Run the solver:
   ```bash
   # Activate virtual environment
   source venv/bin/activate
   
   # Run test case (2024 Day 1 Part 1)
   python solve.py --year 2024 --day 1 --part 1
   ```
   
   Optional flags:
   - `--force`: Force new solution even if already solved
   - `--debug`: Enable debug logging
   
   Or invoke the venv Python explicitly without activating the shell:
   ```bash
   venv/bin/python solve.py --year 2024 --day 1 --part 1
   ```
   
5. Run tests (optional):
   ```bash
   PYTHONPATH=. venv/bin/pytest -q
   ```

## Solution File Structure

Solutions are stored with a standardized structure:
- Each solution uses 'input.txt' in its local directory for input data
- Solutions are designed to be portable and secure
- No absolute paths or system-specific code is included
- Runtime modifications are kept separate from model-generated code

## Development Process

The project uses a structured development process:
- Changes are tracked in checkpoint.md
- A 2-week history window is maintained for completed work
- Older history is archived in checkpoint-history.md
- Documentation and diagrams are kept in sync with code changes

## Development

### Project Structure
```
problem-solver/
├── config/          # Configuration files
├── dev/            # Development resources
│   ├── docs/       # Core development documentation
│   ├── diagrams/   # System flow diagrams
│   └── progress/   # Progress tracking
├── learning/       # Learning and optimization
├── shared/         # Core shared components
│   ├── llm/        # LLM integration
│   ├── parser.py   # Problem parsing
│   └── quality/    # Code quality tools
├── solutions/      # Generated solutions
├── tests/         # Test suite
└── years/         # Problem files by year
```

### Key Files
- `solve.py`: Main entry point
- `shared/llm/prompts.py`: Dynamic prompt generation
- `shared/strategies.py`: Solution strategies
- `shared/parser.py`: Problem parsing
- `dev/progress/checkpoint.md`: Development tracking
- `dev/docs/architecture.md`: System architecture

## Status Notes (2025-08-11)

- Defensive fixes to prevent `.lower()` on non-strings implemented in `shared/strategies.py`, `learning/optimizer.py`, and `shared/llm/performance.py`.
- Import hygiene: `shared/submission.py` now imports strategies from `shared/strategies`.
- Filename safety: `shared/utils.py` coerces `model_name` to string before lowercasing.
- Tests: historical snapshot at this date indicated 9/9 passing locally.
- At this time, weighted consensus validation, code quality scoring, and problem type classification were still in progress.

## Status Notes (2025-12-06)

- Solver pipeline is enabled and covered by integration tests, and has been exercised end-to-end
  on a real AoC problem (2024 Day 01 Part 1) using live Advent of Code input.
- Problem fetching and parsing now use AoC HTML articles per part, ensuring Part 1 and Part 2
  are solved atomically with correct example and expected-output extraction from `<pre><code>`
  blocks and surrounding prose.
- Weighted consensus and collaborative improvement flows are exercised by integration tests;
  problem type classification is implemented and feeds model selection and learning.
- After consensus (and optional collaborative improvement) fails to choose a solution, the
  solver runs an execution-based selection and repair loop: candidate solutions are validated
  against AoC examples and full input via `SolutionExecutor.test_solution`, with iterative
  calls to `improve_solution` before finally giving up.
- Code quality scoring is implemented via `CodeQualityAnalyzer` and integrated into
  `LearningDatabase.update_model_performance` calls.
- Local model list is curated for M1 16GB-class hardware and checked against Ollama at startup;
  if none of the configured models are installed, the solver raises a clear message listing the
  models to install.
- The current test suite passes locally (44/44) with `PYTHONPATH=. venv/bin/pytest`.

## Features in Development

### Meta-Learning
- Learning from past solutions
- Pattern recognition across problems
- Common pitfall detection
- Success pattern library

### Enhanced Validation
- Comprehensive test coverage
- Performance validation
- Input assumption verification
- Solution correctness checks

### Progressive Problem Solving
- Solution progress tracking
- Knowledge base building
- Cross-problem pattern recognition
- Strategy effectiveness analysis

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines on:
- Code style
- Pull requests
- Testing requirements
- Documentation

## License

This project is licensed under the MIT License - see [LICENSE](LICENSE) for details.
