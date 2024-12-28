# Advent of Code Solver

An intelligent code solution generator for Advent of Code challenges, using multiple LLM models for optimal performance and reliability.

## Features

- **Multi-Model Approach**: Combines local and cloud models for optimal performance
- **Hardware-Aware**: Automatically adapts to available system resources
- **Quality Assurance**: Integrated code quality and performance metrics
- **Adaptive Learning**: Improves model selection based on historical performance

## Setup

1. Clone the repository
2. Copy `.env.example` to `.env` and configure:
   - Add your API keys (Anthropic, OpenAI)
   - Set your AOC_SESSION
   - Configure hardware profile
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Install Ollama and required models:
   ```bash
   # Install models based on your hardware profile
   ollama pull codellama-7b-instruct  # Base model
   ollama pull mistral-7b-instruct    # Additional model
   ```

## Hardware Profiles

The system supports different hardware profiles:

- **M1 16GB**:
  - Uses 7B parameter models locally
  - Optimized for memory efficiency
  - Single model concurrent operation

- **M2 32GB**:
  - Supports up to 13B parameter models
  - Allows concurrent model operation
  - Higher performance capabilities

Configure your profile in `.env`:
```env
HARDWARE_PROFILE=m1_16gb  # or m2_32gb
MAX_MODEL_SIZE=13         # Maximum model size in billions
CONCURRENT_MODELS=1       # How many models to run at once
```

## Model Roles

The system uses different models for specific roles:

1. **Primary Solution Generator**:
   - Fast local models for initial solutions
   - Hardware-appropriate size selection
   - Optimized for speed and accuracy

2. **Code Reviewer**:
   - Cloud models for high-quality review
   - Focuses on improvements and optimizations
   - Handles complex edge cases

3. **Solution Validator**:
   - Fast local models for validation
   - Verifies correctness and performance
   - Provides quick feedback

## Quality Metrics

Integrated code quality tools:
- Style checking (Pylint)
- Complexity analysis (Radon)
- Type checking (Mypy)
- Security analysis (Bandit)

## Usage

```bash
# Run solver for a specific problem
python solve2.py --year <year> --day <day> --part <part>

# Run with test data
python solve2.py --year <year> --day <day> --part <part> --test

# Example
python solve2.py --year 2021 --day 1 --part 1
```

## Project Status

The solver is currently under development with the following features:
- Automated problem input retrieval
- LLM-powered solution generation using Ollama
- Test case validation before submission
- Support for both test and actual problem inputs

### Next Steps
- Improve LLM prompt engineering for more reliable solutions
- Add tracking of successfully solved problems
- Enhance logging and progress reporting
- Implement quality checks for generated code

## Contributing

1. Fork the repository
2. Create your feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.
