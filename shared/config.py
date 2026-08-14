"""Configuration management for the problem solver."""

import json
import os
from pathlib import Path
from typing import Dict, Any, Optional

import yaml
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

def load_yaml_config(filename: str) -> Dict[str, Any]:
    """Load configuration from YAML file."""
    config_file = CONFIG_DIR / filename
    if not config_file.exists():
        return {}
    with open(config_file) as f:
        return yaml.safe_load(f)

# Load YAML configuration. Only resources.yaml is live (execution/request limits +
# the submission toggle). The former models.yaml / hardware.yaml / cache.yaml were
# read only by unused constants and their own unit tests, and have been removed.
RESOURCES_CONFIG = load_yaml_config("resources.yaml")

# Environment-based configuration (overrides)
SUBMIT_SOLUTIONS = os.getenv("SUBMIT_SOLUTIONS", "").lower() == "true" if os.getenv("SUBMIT_SOLUTIONS") else RESOURCES_CONFIG.get("submission", {}).get("enabled", False)
DEFAULT_EXECUTION_TIMEOUT = int(os.getenv("EXECUTION_TIMEOUT", 
    RESOURCES_CONFIG.get("execution", {}).get("timeout_seconds", 60)))
DEFAULT_PROVIDER_TIMEOUT = int(os.getenv("PROVIDER_TIMEOUT", 
    RESOURCES_CONFIG.get("requests", {}).get("timeout_seconds", 30)))
MAX_MEMORY_MB = int(os.getenv("MAX_MEMORY_MB",
    RESOURCES_CONFIG.get("execution", {}).get("max_memory_mb", 512)))
MAX_PROCESSES = int(os.getenv("MAX_PROCESSES",
    RESOURCES_CONFIG.get("execution", {}).get("max_processes", 1)))

# Rate limiting
MAX_REQUESTS_PER_MINUTE = int(os.getenv("MAX_REQUESTS_PER_MINUTE", 20))
REQUEST_COOLDOWN = int(os.getenv("REQUEST_COOLDOWN", 3))  # seconds

# HTTP settings
#
# Advent of Code's automation guidelines ask tools to identify themselves and to
# include a way to make contact, rather than impersonating a browser. Contact
# details are personal data and must never be committed: set AOC_CONTACT in .env
# (untracked), or override USER_AGENT wholesale.
_AOC_CONTACT = os.getenv("AOC_CONTACT", "").strip()
_DEFAULT_USER_AGENT = "problem-solver (AoC LLM solver; https://github.com/topics/advent-of-code)"
if _AOC_CONTACT:
    _DEFAULT_USER_AGENT = f"problem-solver (AoC LLM solver; contact: {_AOC_CONTACT})"

USER_AGENT = os.getenv("USER_AGENT", _DEFAULT_USER_AGENT)

def get_resource_config() -> Dict[str, Any]:
    """Return the full resources configuration dictionary."""
    return RESOURCES_CONFIG or {}

# File patterns
INPUT_FILE = "input.txt"
EXAMPLES_DIR = "examples"  # Directory to store example files
PROBLEM_FILE = "problem.txt"
LOGIC_FILE = "logic.txt"
HTML_FILE = "problem.html"  # Cached HTML response
META_FILE = "problem_meta.json"  # Cache metadata including state
ANSWERS_FILE = "answers.json"  # Ground-truth accepted answers, keyed by part

# Testing
TEST_MODE = os.getenv("AOC_TEST_MODE", "false").lower() == "true"
