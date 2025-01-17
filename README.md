# Problem Solver

An intelligent problem solver for Advent of Code challenges, featuring a learning system that improves over time.

## Features

- **Automated Problem Solving**: Uses LLMs to generate solutions for Advent of Code problems.
- **Multi-Model Support**: Can use multiple LLM models and implement consensus mechanisms.
- **Learning System**: Tracks successful and failed attempts to improve future solutions.
- **Code Quality**: Includes tools for code formatting and validation.
- **Temporary File Management**: Centralized temporary file handling in `tmp/` directory.
- **Smart Caching**: Efficiently caches problem data and responses
- **Progress Tracking**: Tracks your progress through AoC challenges
- **Input Analysis**: Advanced strategies for parsing and validating input formats
- **Transformation Patterns**: Systematic approach to data transformation and validation
- **Pattern Recognition**: Smart detection and handling of common input patterns:
  - Multi-column data
  - Grid/matrix structures
  - Graph-like relationships
  - Sorting requirements
  - Paired data
- **Solution Templates**: Comprehensive templates with:
  - Problem analysis guidance
  - Input parsing strategies
  - Data structure selection
  - Performance considerations

## Project Structure

```
problem-solver/
├── config/            # Configuration files
├── dev/              # Development documentation and tracking
│   ├── api.md         # API documentation
│   ├── contributing.md # Contribution guidelines
│   ├── error-handling.md # Error handling documentation
│   └── progress/      # Development progress tracking
│       ├── checkpoint.md        # Current development state
│       └── checkpoint-history.md # Historical development records
├── learning/         # Learning-related files
├── shared/          # Shared modules
│   ├── llm/         # LLM integration
│   │   ├── models.py     # Model definitions
│   │   ├── ensemble.py   # Model ensemble management
│   │   ├── providers.py  # Model provider interfaces
│   │   ├── prompts.py    # Solution templates and prompts
│   │   └── hardware.py   # Hardware capability management
│   ├── quality/     # Code quality tools
│   └── strategies/  # Solution strategies
├── solve.py         # Main solver script
├── solutions/       # Successfully validated solutions
│   ├── README.md    # Solution history and records
│   └── *.py         # Solution files
├── tmp/            # Temporary files for solution attempts
└── years/          # Problem data by year
    └── YYYY/       # Year-specific data
        └── dayXX/  # Day-specific data
            ├── attempts/  # JSON records of all solution attempts
            ├── examples/  # Example inputs and outputs
            ├── input.txt  # Problem input
            ├── problem.txt  # Problem description
            ├── problem.html  # Problem description in HTML
            └── problem_meta.json  # Problem metadata
└── tmp/               # Temporary files (not tracked)
    └── temp/        # Temporary files

## Project Status

For a log of successful solutions and project progress, see [SOLUTIONS.md](SOLUTIONS.md).

## Getting Started

1. Clone the repository
2. Copy `.env.example` to `.env` and fill in your settings
3. Install dependencies: `pip install -r requirements.txt`
4. Initialize the learning database: `python learning/init_db.py`
5. Run the solver: `python solve.py --year YEAR --day DAY --part PART`

## Learning System

The solver includes a learning system that:
1. Tracks which strategies work best for different problems
2. Analyzes input formats and transformation patterns
3. Improves parsing accuracy through example validation
4. Maintains a knowledge base of common patterns

## Solution Strategies

The system includes various solution strategies:

### Input Processing
- **Input Structure Analysis**: Systematic approach to understanding input formats
- **Robust Input Parsing**: Handling edge cases and variations
- **Input-Output Correlation**: Mapping input structure to expected output
- **Data Transformation Patterns**: Common patterns for data restructuring

### Algorithm Categories
- Grid Traversal
- Pathfinding
- Simulation
- Pattern Matching
- State Machine
- Optimization
- Math
- Graph
- Dynamic Programming

## Configuration

- `.env`: Environment variables (API keys, session cookies)
- `shared/config.py`: General configuration settings
- `learning/schema.sql`: Database schema definition

## Development

### Adding New Strategies

1. Add strategy definition to `shared/strategies.py`
2. Update strategy weights in learning database
3. Test with various problem types

### Testing
The project uses pytest for testing. Install development dependencies:

```bash
pip install -r requirements-dev.txt
```

Run tests:
```bash
pytest
```

Tests are organized into:
- Unit tests (`tests/unit/`)
- Integration tests (`tests/integration/`)
- Test fixtures (`tests/fixtures/`)

### Documentation
- System architecture documentation in `dev/architecture.md`
- Configuration guide in `.env.example`
- YAML configuration files in `config/`

### Contributing

1. Fork the repository
2. Create a feature branch
3. Submit a pull request

See [dev/contributing.md](dev/contributing.md) for detailed guidelines.

## Recent Updates

### 2025-01-16
- Enhanced solution tracking with direct file links
- Added centralized solutions directory
- Improved solution file organization and accessibility
- Added automatic solution tracking in SOLUTIONS.md
- Enhanced GitHub username detection and repository state handling
- Added parsed data structure display for debugging
- Enhanced model debugging with parsed data structure display
- Improved visibility into input data interpretation
- Simplified debugging approach

## Notes

- Be a responsible AoC participant - minimize requests and cache data
- Personal progress data is not tracked in git
- The learning database is local to your machine

## Submission Policy

This tool strictly adheres to Advent of Code's principles:

- Solutions are only submitted after top 100 daily leaderboard slots are filled
- Leaderboard status is checked at: adventofcode.com/{year}/leaderboard/day/{day}
- Tool polls leaderboard status every minute until completion
- Full submission history is tracked and logged

## Setup

1. Ensure you have Python 3.11 installed:

   ```bash
   # On macOS with Homebrew
   brew install python@3.11

   # Verify installation
   python3.11 --version
   ```

   Note: Python 3.11 is required as some dependencies don't support newer versions yet.

2. Create and activate a virtual environment:

   ```bash
   # Create venv with Python 3.11
   python3.11 -m venv venv

   # Activate it
   source venv/bin/activate
   ```

3. Install dependencies:

   ```bash
   pip install -r requirements.txt
   ```

4. Initialize the learning system:

   ```bash
   python learning/init_db.py
   ```

## Usage

Basic usage:

```bash
python solve.py --year 2024 --day 1 --part 1
```

Options:
- `--force`: Force regenerate solution even if one exists
- `--debug`: Enable debug logging
- `--no-submit`: Generate solution but don't submit

## Error Handling

The system uses a structured error handling system:
- ValidationError: Input/session validation issues
- ProviderError: Model provider issues
- ConfigurationError: Setup/config problems

See [dev/error-handling.md](dev/error-handling.md) for details.

## API Documentation

See [dev/api.md](dev/api.md) for detailed API documentation.
