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
  - HTML-first example extraction
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
   - Pull required models:
     ```bash
     ollama pull codellama:7b
     ```

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
- Tests: current suite passes locally (9/9). Run with the venv and `PYTHONPATH=.` (see below).
- Still in progress: weighted consensus validation, code quality scoring, and problem type classification (currently returns `"general"`).

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
