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
PROBLEM_SITE_BASE_URL = "https://adventofcode.com"

# Session cookie from environment variable
PROBLEM_SITE_SESSION = os.getenv("PROBLEM_SITE_SESSION")

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
