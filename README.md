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
- Consensus-based validation
- Inter-model learning mechanisms
- Adaptive model selection

### Learning and Optimization
- Strategy effectiveness tracking
- Solution pattern library
- Performance optimization system
- Cross-problem knowledge transfer

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
- `execution.py`: Solution execution and monitoring
- `attempts/`: Attempt history and metrics

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
│   ├── progress/   # Progress tracking
│   └── *.mmd      # Mermaid diagrams
├── learning/       # Learning and optimization
├── shared/         # Core shared components
│   ├── llm/       # LLM integration
│   ├── parser/    # Problem parsing
│   └── quality/   # Code quality tools
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
