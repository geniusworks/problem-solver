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

## Components

### Problem Analysis
- `parser.py`: Problem parsing and structure analysis
- `problem_analysis.py`: Deep problem understanding and categorization
- `strategies.py`: Solution strategy identification and application

### LLM Integration
- `llm/base.py`: Base LLM provider interface
- `llm/local.py`: Local LLM implementation (Ollama)
- `llm/prompts.py`: Dynamic prompt generation and management

### Solution Management
- `solutions/`: Generated solution implementations
- `quality/`: Code quality and validation tools
- `tempfiles.py`: Temporary file management

## Getting Started

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. Set up Ollama:
   - Install Ollama from [ollama.ai](https://ollama.ai)
   - Pull required models:
     ```bash
     ollama pull codellama:7b
     ```

3. Run the solver:
   ```bash
   python main.py [problem_file]
   ```

## Development

### Project Structure
```
problem-solver/
├── shared/           # Core shared components
│   ├── llm/         # LLM integration
│   ├── parser/      # Problem parsing
│   └── quality/     # Code quality tools
├── solutions/       # Generated solutions
├── tests/          # Test suite
└── years/          # Problem files by year
```

### Key Files
- `main.py`: Main entry point
- `shared/llm/prompts.py`: Dynamic prompt generation
- `shared/strategies.py`: Solution strategies
- `shared/parser.py`: Problem parsing

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
