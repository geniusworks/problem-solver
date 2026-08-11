# Problem Solver

An intelligent system that uses Advent of Code problems as its primary testbed, attempting one-shot autonomous solutions with orchestrated local LLMs and strategic problem analysis.

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
- `shared/llm/local.py`: Local LLM implementation (Ollama HTTP API)
- `shared/llm/prompts.py`: Dynamic prompt generation
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

### Advent of Code parts and examples

For each AoC day, the puzzle page has one or two
`<article class="day-desc">` blocks:

- **Part 1** uses the first article.
- **Part 2** uses the second article (when present).

Only the selected article is parsed and sent to the LLMs, so each part is solved in isolation.

Example: **2024 Day 1 – Historian Hysteria**

- The Part 1 article contains one `<pre><code>` block with the six-line example list of
  location IDs and prose ending with "a total distance of 11".
- The parser:
  - Treats the whole block as a single example input.
  - Infers the expected output `11` from the surrounding prose.
- Running:
  ```bash
  venv/bin/python solve.py --year 2024 --day 1 --part 1 --force --debug
  ```
  fetches only the Part 1 article, extracts that example + `11`, and prompts local models
  using only the Part 1 description.

This keeps prompts faithful to real competition conditions: no Part 2 text is visible while
solving Part 1.

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

### Technical Reference

- **Core documentation**
  - [dev/docs/architecture.md](dev/docs/architecture.md): High-level system architecture, data flow, and solver components.
  - [dev/docs/contributing.md](dev/docs/contributing.md): Contribution guidelines, development workflow, and testing expectations.

- **System diagrams**
  - [dev/diagrams/information-flow.mmd](dev/diagrams/information-flow.mmd): End-to-end information flow and solver orchestration.
  - [dev/diagrams/strategy-guidance.mmd](dev/diagrams/strategy-guidance.mmd): Strategy selection, guidance flow, and model roles.
  - [dev/diagrams/execution-repair-loop.mmd](dev/diagrams/execution-repair-loop.mmd): Execution-feedback repair loop and iterative improvement cycle.
  - [dev/diagrams/documentation-flow.mmd](dev/diagrams/documentation-flow.mmd): How documentation, progress tracking, and code stay in sync.

## Status Notes

**What works today (snapshot)**

- The end-to-end solving pipeline is enabled and exercised on real Advent of Code problems
  using local models and cached AoC inputs.
- AoC-aware HTML parsing and per-part article handling reliably extract examples and expected
  outputs from `<pre><code>` blocks and surrounding prose.
- Execution-based candidate selection, the iterative repair loop, and canonical solution
  recording (including non-force reuse of existing `YYYY_dayDD_partP.py` files) are
  implemented and form the core of the solver's behavior.
- The learning system tracks code quality and model performance, and a curated set of local
  models is validated against Ollama at startup to stay within typical developer hardware
  constraints.

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

See [dev/docs/contributing.md](dev/docs/contributing.md) for guidelines on:
- Code style
- Pull requests
- Testing requirements
- Documentation

## Credits

Developed by **Martin Diekhoff**.

## License

This project is licensed under the MIT License - see [LICENSE](LICENSE) for details.
