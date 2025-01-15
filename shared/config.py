"""Configuration and error classes for the problem solver."""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Base directory is two levels up from this file
BASE_DIR = Path(__file__).parent.parent

# Base URL for Advent of Code API
AOC_BASE_URL = "https://adventofcode.com"

# Session cookie from environment variable
PROBLEM_SITE_SESSION = os.getenv("PROBLEM_SITE_SESSION")

# URLs
# AOC_BASE_URL = "https://adventofcode.com"

# File patterns
INPUT_FILE = "input.txt"
EXAMPLES_DIR = "examples"  # Directory to store example files
PROBLEM_FILE = "problem.txt"
LOGIC_FILE = "logic.txt"
HTML_FILE = "problem.html"  # Cached HTML response
META_FILE = "problem_meta.json"  # Cache metadata including state

# HTTP settings
USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.1 Safari/605.1.15"
REQUEST_DELAY = 1  # seconds between requests to avoid rate limiting

# Testing
TEST_MODE = os.getenv("AOC_TEST_MODE", "false").lower() == "true"


class BaseError(Exception):
    """Base class for all custom exceptions."""

    pass


class ValidationError(BaseError):
    """Base class for validation-related errors."""

    pass


class SessionError(ValidationError):
    """Raised when there are issues with session management."""

    pass


class InputError(ValidationError):
    """Raised for errors related to input data."""

    pass


class SubmissionError(ValidationError):
    """Raised for errors during solution submission."""

    pass


class ProviderError(BaseError):
    """Base class for errors related to model providers."""

    pass


class RateLimitError(ProviderError):
    """Raised when a rate limit is exceeded."""

    pass


class ProviderTimeoutError(ProviderError):
    """Raised when a provider times out."""

    pass


class AuthenticationError(ProviderError):
    """Raised when authentication fails."""

    pass


class ServiceUnavailableError(ProviderError):
    """Raised when a service is unavailable."""

    pass


class ExecutionError(BaseError):
    """Base class for execution-related errors."""

    pass


class TimeoutError(ExecutionError):
    """Raised when execution exceeds time limit."""

    pass


class ResourceError(ExecutionError):
    """Raised when resource limits are exceeded."""

    pass


class CompilationError(ExecutionError):
    """Raised when code fails to compile."""

    pass


class RuntimeError(ExecutionError):
    """Raised when code fails during execution."""

    pass
