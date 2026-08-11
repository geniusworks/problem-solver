"""Shared utilities and core functionality for the Problem Solver.

This package contains core components including:
- Configuration management
- Error handling
- Database operations
- Execution handling
- Problem solving logic
- Solution validation
- LLM integration
"""

from .config import (
    BASE_DIR,
    CONFIG_DIR,
    WORKSPACE_DIR,
    LEARNING_DIR,
    AOC_SESSION,
    AOC_BASE_URL,
    HARDWARE_CONFIG,
)
from .errors import (
    BaseError,
    ValidationError,
    SessionError,
    InputError,
    SubmissionError,
    ProviderError,
    ExecutionError,
)
from .validator import validate_solution
from .execution import SolutionExecutor, TestCase

__all__ = [
    # Configuration
    'BASE_DIR',
    'CONFIG_DIR',
    'WORKSPACE_DIR',
    'LEARNING_DIR',
    'AOC_SESSION',
    'AOC_BASE_URL',
    'HARDWARE_CONFIG',
    
    # Error classes
    'BaseError',
    'ValidationError',
    'SessionError',
    'InputError',
    'SubmissionError',
    'ProviderError',
    'ExecutionError',
    
    # Core functionality
    'validate_solution',
    'SolutionExecutor',
    'TestCase',
]
