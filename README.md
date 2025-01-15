# Problem Solver

An intelligent problem solver for Advent of Code challenges, featuring a learning system that improves over time.

## Features

- **Automated Problem Solving**: Uses AI to analyze and solve AoC problems
- **Strategy Learning**: Learns from past solutions to improve future attempts
- **Smart Caching**: Efficiently caches problem data and responses
- **Progress Tracking**: Tracks your progress through AoC challenges

## Project Structure

```
problem-solver/
├── learning/            # Learning system for strategy optimization
│   ├── README.md       # Learning system documentation
│   ├── schema.sql      # Database schema definition
│   ├── database.py     # Database management
│   └── solver.db       # Learning database (not tracked in git)
├── shared/             # Shared utilities and core functionality
│   ├── database.py     # Database management
│   ├── learning.py     # Learning system implementation
│   ├── solver.py       # Core solver implementation
│   └── strategies.py   # Problem-solving strategies
├── years/              # Problem data and solutions by year
│   └── example/        # Example problem structure (tracked)
│   └── 20XX/          # Your solutions (not tracked)
└── .problem-solver/    # User-specific data (not tracked)
    └── temp/          # Temporary files
```

## Getting Started

1. Clone the repository
2. Copy `.env.example` to `.env` and fill in your settings
3. Install dependencies: `pip install -r requirements.txt`
4. Initialize the learning database: `python learning/init_db.py`
5. Run the solver: `python solve.py --year YEAR --day DAY --part PART`

## Learning System

The solver includes a learning system that:
1. Tracks which strategies work best for different problems
2. Records solution performance metrics
3. Uses past experience to guide future attempts

See [learning/README.md](learning/README.md) for details on the learning system.

## Configuration

- `.env`: Environment variables (API keys, session cookies)
- `shared/config.py`: General configuration settings
- `learning/schema.sql`: Database schema definition

## Development

### Adding New Strategies

1. Add strategy definition to `shared/strategies.py`
2. Update strategy weights in learning database
3. Test with various problem types

### Contributing

1. Fork the repository
2. Create a feature branch
3. Submit a pull request

See [docs/CONTRIBUTING.md](docs/CONTRIBUTING.md) for detailed guidelines.

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

See [docs/error-handling.md](docs/error-handling.md) for details.

## API Documentation

See [docs/api.md](docs/api.md) for detailed API documentation.
