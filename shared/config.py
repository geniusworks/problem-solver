"""Configuration settings for Advent of Code solver."""
import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Base directory is two levels up from this file
BASE_DIR = Path(__file__).parent.parent

# Get session cookie from environment variable
AOC_SESSION = os.getenv('AOC_SESSION')

# URLs
AOC_BASE_URL = "https://adventofcode.com"

# File patterns
INPUT_FILE = "input.txt"
EXAMPLE_FILE = "example.txt"
PROBLEM_FILE = "problem.txt"
LOGIC_FILE = "logic.txt"
ATTEMPTS_LOG = "attempts.log"

# HTTP settings
USER_AGENT = "github.com/geniusworks/advent-of-code-solver"
REQUEST_DELAY = 1  # seconds between requests to avoid rate limiting

# Testing
TEST_MODE = os.getenv('AOC_TEST_MODE', 'false').lower() == 'true'

class AocError(Exception):
    """Base exception for Advent of Code solver."""
    pass

class SessionError(AocError):
    """Raised when there are issues with the session cookie."""
    pass

class InputError(AocError):
    """Raised when there are issues with input data."""
    pass
