"""Configuration management for the problem solver."""

import json
import os
from pathlib import Path
from typing import Dict, Any

from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Base directory is two levels up from this file
BASE_DIR = Path(__file__).parent.parent

# Configuration directories
CONFIG_DIR = BASE_DIR / "config"
WORKSPACE_DIR = BASE_DIR / "workspace"
LEARNING_DIR = BASE_DIR / "learning"

# Base URL for problem site API
AOC_BASE_URL = "https://adventofcode.com"
PROBLEM_URL_TEMPLATE = f"{AOC_BASE_URL}/{{year}}/day/{{day}}"
LEADERBOARD_URL_TEMPLATE = f"{AOC_BASE_URL}/{{year}}/leaderboard/day/{{day}}"
INPUT_URL_TEMPLATE = f"{AOC_BASE_URL}/{{year}}/day/{{day}}/input"

# Session cookie from environment variable
AOC_SESSION = os.getenv("AOC_SESSION")

def load_hardware_config() -> Dict[str, Any]:
    """Load hardware configuration from JSON file."""
    config_file = CONFIG_DIR / "hardware.json"
    if not config_file.exists():
        return {}
    with open(config_file) as f:
        return json.load(f)

# Load hardware configuration
HARDWARE_CONFIG = load_hardware_config()

# Default timeouts
DEFAULT_EXECUTION_TIMEOUT = 60  # seconds
DEFAULT_PROVIDER_TIMEOUT = 30   # seconds

# Rate limiting
MAX_REQUESTS_PER_MINUTE = 20
REQUEST_COOLDOWN = 3  # seconds

# HTTP settings
USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.1 Safari/605.1.15"

# File patterns
INPUT_FILE = "input.txt"
EXAMPLES_DIR = "examples"  # Directory to store example files
PROBLEM_FILE = "problem.txt"
LOGIC_FILE = "logic.txt"
HTML_FILE = "problem.html"  # Cached HTML response
META_FILE = "problem_meta.json"  # Cache metadata including state

# Testing
TEST_MODE = os.getenv("AOC_TEST_MODE", "false").lower() == "true"
