# Problem Solver API Documentation

## Project Structure

The project is organized into several key components:

### Core Components

- `shared/`: Core functionality shared across the project
  - `config.py`: Configuration management
  - `errors.py`: Error class definitions
  - `database.py`: Database operations
  - `execution.py`: Code execution handling
  - `solver.py`: Main problem-solving logic
  - `validator.py`: Solution validation
  - `utils.py`: Utility functions
  - `llm/`: Language model integration
    - `models.py`: Model definitions
    - `ensemble.py`: Model ensemble management
    - `providers.py`: Model provider interfaces
    - `hardware.py`: Hardware capability management

- `learning/`: Learning system for strategy optimization
  - `database.py`: Learning database operations
  - `optimizer.py`: Strategy optimization logic
  - `init_db.py`: Database initialization
  - `schema.sql`: Database schema

### Configuration

Configuration is managed through several mechanisms:

1. Environment Variables (`.env`):
   - Problem site session token
   - Model API keys
   - Hardware capabilities

2. JSON Configuration (`config/`):
   - `hardware.json`: Hardware capability configuration

3. Python Configuration (`shared/config.py`):
   - Path configurations
   - Default timeouts
   - Rate limiting settings

### Error Handling

Error handling is centralized in `shared/errors.py` with a hierarchy of custom exceptions:

- `BaseError`
  - `ValidationError`
    - `SessionError`
    - `InputError`
    - `SubmissionError`
  - `ProviderError`
    - `RateLimitError`
    - `ProviderTimeoutError`
    - `AuthenticationError`
    - `ServiceUnavailableError`
  - `ExecutionError`
    - `TimeoutError`
    - `ResourceError`
    - `CompilationError`
    - `RuntimeError`

### Learning System

The learning system (`learning/`) manages strategy optimization and feedback:

- Strategy effectiveness tracking
- Problem pattern recognition
- Performance metrics collection
- Database persistence

## Usage

For detailed usage instructions, refer to the README.md file in the project root.

## Core Components

### Problem Solver

```python
class ProblemSolver:
    """Main class for handling problem-solving workflow."""
    
    def solve(year: int, day: int, part: int) -> Solution:
        """
        Solve a specific problem using configured models.
        
        Args:
            year: Problem year
            day: Problem day (1-25)
            part: Problem part (1 or 2)
            
        Returns:
            Solution object containing the solution and metadata
        """
```

### Model Registry

```python
class ModelRegistry:
    """Manages available LLM models and their configurations."""
    
    def get_model(name: str) -> Model:
        """Get a model instance by name."""
        
    def list_models() -> List[str]:
        """List available models."""
```

### Solution Manager

```python
class SolutionManager:
    """Handles solution storage and retrieval."""
    
    def save_solution(solution: Solution) -> None:
        """Save a solution with metadata."""
        
    def get_solution(year: int, day: int, part: int) -> Optional[Solution]:
        """Retrieve a specific solution."""
```

## Data Models

### Solution

```python
@dataclass
class Solution:
    code: str                 # Generated solution code
    result: str              # Solution output
    model_name: str          # Model used
    timestamp: datetime      # Generation time
    metadata: Dict[str, Any] # Additional metadata
```

### ProblemInput

```python
@dataclass
class ProblemInput:
    description: str    # Problem description
    example: str       # Example input/output
    input_data: str    # Actual problem input
    constraints: List[str]  # Problem constraints
```

## Usage Examples

### Basic Usage

```python
from problem_solver import ProblemSolver

solver = ProblemSolver()
solution = solver.solve(year=2024, day=1, part=1)
print(f"Solution: {solution.result}")
```

### Custom Model Configuration

```python
from problem_solver import ModelRegistry

registry = ModelRegistry()
model = registry.get_model("codellama-7b")
model.configure(temperature=0.8, max_tokens=2000)
```

### Solution Management

```python
from problem_solver import SolutionManager

manager = SolutionManager()
manager.save_solution(solution)
previous_solution = manager.get_solution(2024, 1, 1)
