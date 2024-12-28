# Advent of Code Solver

An intelligent code solution generator for Advent of Code challenges, using multiple LLM models for optimal performance and reliability.

## Features

- **Problem Analysis**: Automatically analyzes problem structure and requirements
- **Solution Generation**: Uses LLMs to generate and validate solutions
- **Test Validation**: Comprehensive test case validation before submission
- **Multi-Model Support**: Designed for consensus-based solution generation

## Setup

1. Clone the repository
2. Copy `.env.example` to `.env` and configure:
   - Add your AOC_SESSION for problem fetching
   - Configure model settings
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Install Ollama and required models:
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
1. Parse and analyze the problem
2. Generate a solution using LLM
3. Validate against test cases
4. Run against full input
5. (Coming soon) Submit and validate answer

## Components

- **Problem Parser**: Extracts problem details and test cases
- **Problem Analyzer**: Determines problem characteristics
- **Solution Generator**: Creates solutions using LLM
- **Solution Executor**: Tests and runs solutions
- **Model Provider**: Manages LLM interactions

## Development Status

- ✅ Problem parsing and analysis
- ✅ Solution generation with local models
- ✅ Test case validation
- ✅ Solution execution
- 🚧 Answer submission and validation
- 🚧 Multi-model consensus
- 🚧 Solution persistence

See [CHECKPOINT.md](CHECKPOINT.md) for detailed progress and plans.

## Contributing

1. Fork the repository
2. Create your feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.
