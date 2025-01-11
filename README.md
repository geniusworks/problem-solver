# Problem Solver

An automated problem-solving system for Advent of Code that:

1. Fetches problem descriptions and inputs
2. Analyzes requirements and examples
3. Generates solutions using LLM models
4. Tests solutions against examples and full input
5. Stores successful solutions with metadata
6. Validates solutions against AoC website

## Submission Policy

This tool strictly adheres to Advent of Code's principles:

- Solutions are only submitted after top 100 daily leaderboard slots are filled
- Leaderboard status is checked at: adventofcode.com/{year}/leaderboard/day/{day}
- Tool polls leaderboard status every minute until completion
- Full submission history is tracked and logged

## Features

- Multi-model LLM integration:
  - Local models (using Ollama runner):
    - Microsoft Phi-4 (fast, efficient inference)
    - Meta CodeLlama series (7B/13B/34B variants)
    - Mistral-7B-Instruct
  - Cloud models:
    - Anthropic Claude-3-Sonnet
- Hardware-aware resource management
- Comprehensive solution testing
- Detailed performance metrics
- Version-controlled solution storage
- Rate-limited API interactions

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

To run the application for a specific problem, use:

```bash
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
