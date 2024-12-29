# Advent of Code Solver

An intelligent code solution generator for Advent of Code challenges, using multiple LLM models for optimal performance and reliability.

## Important Note on AI Usage

This project is an exercise in creating problem-solving frameworks and exploring how LLMs can assist in coding challenges. It is NOT intended to:

1. Compete on global leaderboards (first 100 solvers)
2. Replace the learning experience of solving puzzles yourself
3. Circumvent the spirit of Advent of Code challenges

**Please Note**: 
- If you're learning programming or problem-solving, we strongly encourage you to attempt the puzzles yourself first
- This tool is best used for learning about AI/LLM frameworks, studying solution patterns, or analyzing different approaches
- We respect Advent of Code's competition rules and enforce a 2-hour embargo on new puzzles

## Features

- **Problem Analysis**: Automatically analyzes problem structure and requirements
- **Solution Generation**: Uses LLMs to generate and validate solutions
- **Test Validation**: Comprehensive test case validation
- **Multi-Model Support**: Designed for consensus-based solution generation
- **Solution Management**: Records successful solutions and model performance
- **Competition Rules**: Enforces waiting period for new puzzles

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
   - Adjust EMBARGO_HOURS if needed

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

To solve a problem:
```bash
python solve2.py --year 2021 --day 1 --part 1
```

The solver will:
1. Check if the puzzle is within embargo period
2. Parse and analyze the problem
3. Generate a solution using LLM
4. Validate against test cases
5. Run against full input
6. Optionally submit the solution (if enabled in .env)

## Solution Management

Solutions are stored in:
- `years/<year>/day<XX>/solutions/examples/`: Solutions that passed example tests
- `years/<year>/day<XX>/solutions/full/`: Solutions that passed both example and full input tests

Each solution includes:
- Generated code
- Prompt used
- Model metadata
- Test results
- Timestamp

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

## Contributing

1. Fork the repository
2. Create your feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.
