# Problem Solver

An intelligent problem solver for Advent of Code challenges.

## Features

- **Automated Problem Solving**: Uses AI to analyze and solve AoC problems
- **Strategy Learning**: Learns from past solutions to improve future attempts
- **Smart Caching**: Efficiently caches problem data and responses
- **Progress Tracking**: Tracks your progress through AoC challenges

## Project Structure

```
problem-solver/
├── learning/            # Learning system for strategy optimization
│   ├── schema.sql      # Database schema definition
│   └── solver.db       # Learning database (not tracked in git)
├── shared/             # Shared utilities and core functionality
│   ├── database.py     # Database management
│   ├── learning.py     # Learning system implementation
│   ├── solver.py       # Core solver implementation
│   └── strategies.py   # Problem-solving strategies
├── years/              # Problem data and solutions by year
│   └── example/        # Example problem structure
└── .problem-solver/    # User-specific data (not tracked in git)
    └── temp/           # Temporary files
```

## Getting Started

1. Clone the repository
2. Copy `.env.example` to `.env` and fill in your settings
3. Install dependencies: `pip install -r requirements.txt`
4. Run the solver: `python solve.py --year YEAR --day DAY --part PART`

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
2. Clone the repository
3. Create and activate a virtual environment:

   ```bash
   # Create venv with Python 3.11
   python3.11 -m venv venv

   # Activate it
   source venv/bin/activate  # On Unix/macOS
   .\venv\Scripts\activate   # On Windows
   ```
4. Copy `.env.example` to `.env` and configure:

   - Add your PROBLEM_SITE_SESSION for problem fetching
   - Configure model settings
   - Set SUBMIT_SOLUTIONS to true/false
5. Install dependencies:

   ```bash
   pip install -r requirements.txt
   ```
6. Install Ollama and required models:

   ```bash
   # Install required models
   ollama pull codellama-7b-instruct  # Primary model
   ```

## Usage

To run the application for a specific problem:

```bash
# First activate the virtual environment
source venv/bin/activate  # On Unix/macOS
.\venv\Scripts\activate   # On Windows

# Then run the solver
python solve.py --year <year> --day <day> --part <part>
```

The solver will:

1. Parse and analyze the problem 
2. Generate a solution using LLM 
3. Validate against test cases 
4. Run against full input 
5. Optionally submit the solution (if enabled in .env)

## Solution Management

Solutions are stored in:

- `years/<year>/day<XX>/solutions/`: Timestamped files with solution metadata (JSON)

Each solution includes:

- Generated code
- Prompt used
- Model information
- Test results
- Performance metrics
- Validation feedback and analysis

## Solution Validation

The system uses an intelligent validation approach that:

1. Focuses on generating correct solutions rather than trial-and-error
2. Provides structured feedback to guide solution generation:
   - Validation of input assumptions
   - Edge case handling
   - Arithmetic precision
   - Loop boundary conditions
   - Collection processing completeness

3. Stores validation history with:
   - Error categorization
   - Suggested improvements
   - Solution evolution tracking

This approach ensures solutions are:
- Mathematically correct
- Handle all edge cases
- Process input completely
- Use precise operations

## Performance Tracking

Solutions are tracked with detailed performance metrics, including:

- Execution time
- Memory usage
- Model inference time
- Number of iterations

## Learning System

The solver includes a learning system that improves its strategy selection over time:

### Database Structure

The learning system uses SQLite (stored in `workspace/learning/solver.db`) with three main tables:

1. `strategy_results`: Records each solution attempt
   - Problem ID (year/day/part)
   - Strategies used
   - Success/failure status
   - Performance metrics
   - Failure points

2. `strategy_weights`: Tracks strategy effectiveness
   - Strategy weights
   - Success rates
   - Performance metrics
   - Last updated timestamp

3. `problem_characteristics`: Stores problem patterns
   - Problem characteristics
   - Successful strategies
   - Solution metrics
   - Attempt history

### Features

- **Strategy Learning**: Learns which strategies work best for different problem types
- **Performance Tracking**: Records execution time and memory usage
- **Pattern Recognition**: Identifies similar problems to inform strategy selection
- **Failure Analysis**: Tracks and analyzes failure patterns
- **Continuous Improvement**: Updates strategy weights based on success rates

### Directory Structure

```
workspace/
├── learning/
│   └── solver.db       # SQLite database for learning system
└── years/
    └── YYYY/
        └── dayNN/
            └── solutions/
```

## Directory Structure

```
years/
├── YYYY/                   # Year (e.g., 2024)
│   ├── dayNN/             # Day folder (e.g., day01)
│   │   ├── attempts/      # Solution attempts
│   │   │   └── attempt_YYYYMMDD_HHMMSS.json  # Attempt metadata
│   │   ├── examples/      # Example test cases
│   │   │   ├── metadata.json          # Example metadata
│   │   │   └── example_N.json         # Individual examples
│   │   ├── solutions/     # Final solutions
│   │   │   ├── part1.py  # Working solution for part 1
│   │   │   └── part2.py  # Working solution for part 2
│   │   ├── input.txt     # Puzzle input
│   │   └── problem.txt   # Problem description
```

### File Purposes

#### Example Files (`examples/*.json`)
Problem definition files that contain:
- Input data for each example
- Expected output
- Description and purpose
- What concepts it demonstrates
- References to it in the problem text

Example files are created when a problem is first fetched and parsed. They define the test cases that solutions must pass.

#### Attempt Files (`attempts/*.json`)
Solution attempt records that track:
- The code that was tried
- Which model generated it
- Whether it passed the examples
- Whether it passed the full input
- What strategies were used
- Performance metrics

Attempt files are created each time a model tries to solve the problem. They help track model performance and solution evolution.

#### Solution Files (`solutions/*.py`)
Clean, documented Python files containing working solutions. Only created when an attempt successfully passes all tests and is submitted.

## Strategy Patterns

The system employs sophisticated strategy patterns for continuous improvement and adaptation:

### Strategy Optimization

The strategy optimizer uses a weighted scoring system to evaluate and adjust strategies:

- **Weight Distribution**
  - 60% Success rate (prioritizing correctness)
  - 20% Execution time optimization
  - 20% Memory usage efficiency

- **Failure Response**
  - Records specific failure points
  - Groups failures by strategy combinations
  - Analyzes patterns to identify problematic approaches
  - Updates strategy weights based on performance metrics

### Model Selection and Adaptation

Models are continuously evaluated and re-ranked based on:

- **Performance Metrics**
  - Average response time
  - Code quality scores
  - Success rate per problem type
  - Cost per successful solution
  - Resource utilization

- **Selection Criteria**
  - Historical performance on similar problems
  - Current success rate and trend
  - Resource availability and constraints
  - Balance between local and cloud models

### Corrective Learning

The system makes intelligent adjustments after incorrect solutions:

1. **Strategy Adjustment**
   - Analyzes failure patterns
   - Updates strategy weights
   - Prioritizes successful strategies from similar problems
   - Maintains historical performance data

2. **Model Re-ranking**
   - Recalculates success rates
   - Updates running averages for quality metrics
   - Adjusts model selection preferences
   - Optimizes resource allocation

3. **Pattern Recognition**
   - Identifies similar problem patterns
   - Tracks strategy effectiveness by problem type
   - Builds knowledge base of successful approaches
   - Applies transfer learning between related problems

### Adaptive Architecture

The system's architecture ensures continuous improvement through:

- **Multiple Feedback Loops**
  - Strategy effectiveness tracking
  - Model performance monitoring
  - Resource usage optimization
  - Solution quality assessment

- **Data-Driven Evolution**
  - Starts with reasonable defaults
  - Improves with real-world usage
  - Maintains explainability
  - Adapts to changing conditions

This design allows the system to:
- Learn from both successes and failures
- Optimize resource utilization
- Improve solution quality over time
- Maintain robust performance across different problem types

## Learning and Development

This project demonstrates:

- LLM integration in software development
- Problem-solving frameworks
- Test-driven development
- Code generation patterns
- Solution validation techniques

We encourage users to:

1. Study the generated solutions to understand different approaches
2. Experiment with different models and prompts
3. Contribute improvements to the framework
4. Share insights about AI-assisted coding

## Development Status

See [CHECKPOINT.md](CHECKPOINT.md) for detailed progress and plans.

## Environment Variables

Configure the following in your `.env` file:

- `PROBLEM_SITE_SESSION`: Your session token for problem fetching
- `SUBMIT_SOLUTIONS`: Set to `true` to enable solution submissions (default: `false`)
- `MODEL_SETTINGS`: Configuration for model providers and runners
- Additional model-specific settings (see `.env.example` for details)

## Contributing

1. Fork the repository
2. Create your feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

See our [Contributing Guidelines](docs/CONTRIBUTING.md) for more details.

## Documentation

- [Error Handling](docs/error-handling.md)
- [API Documentation](docs/api.md)
- [Development Status](CHECKPOINT.md)

## License

This project is licensed under the MIT License - see the LICENSE file for details.
