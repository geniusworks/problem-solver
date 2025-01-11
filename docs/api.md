# API Documentation

This document describes the key APIs and interfaces of the Problem Solver project.

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

## Error Handling

See [error-handling.md](error-handling.md) for detailed error class documentation.

## Configuration

### Environment Variables

See the main [README.md](../README.md) for environment variable documentation.

### Model Configuration

Models can be configured in `.env` with the following format:
```
MODEL_<name>_PROVIDER=provider_name
MODEL_<name>_RUNNER=runner_name
MODEL_<name>_CONTEXT_LENGTH=8192
MODEL_<name>_TEMPERATURE=0.7
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
```
