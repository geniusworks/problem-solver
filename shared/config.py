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

# Load YAML configurations (defaults)
MODELS_CONFIG = load_yaml_config("models.yaml")
RESOURCES_CONFIG = load_yaml_config("resources.yaml")
HARDWARE_CONFIG = load_yaml_config("hardware.yaml")
CACHE_CONFIG = load_yaml_config("cache.yaml")

# Model defaults
DEFAULT_TEMPERATURE = float(MODELS_CONFIG.get("defaults", {}).get("temperature", 0.1))
DEFAULT_MAX_TOKENS = int(MODELS_CONFIG.get("defaults", {}).get("max_tokens", 2000))
DEFAULT_TIMEOUT = int(MODELS_CONFIG.get("defaults", {}).get("timeout_seconds", 60))

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

# Hardware settings
HARDWARE_PROFILE = os.getenv("HARDWARE_PROFILE")
MAX_MODEL_SIZE = int(os.getenv("MAX_MODEL_SIZE", 
    HARDWARE_CONFIG.get("max_model_size", 7)))
CONCURRENT_MODELS = int(os.getenv("CONCURRENT_MODELS", 
    HARDWARE_CONFIG.get("concurrent_models", 2)))

# Rate limiting
MAX_REQUESTS_PER_MINUTE = int(os.getenv("MAX_REQUESTS_PER_MINUTE", 20))
REQUEST_COOLDOWN = int(os.getenv("REQUEST_COOLDOWN", 3))  # seconds

# HTTP settings
USER_AGENT = os.getenv("USER_AGENT", "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.1 Safari/605.1.15")

def get_model_config(model_name: str) -> Dict[str, Any]:
    """Get configuration for a specific model."""
    return MODELS_CONFIG.get("models", {}).get(model_name, {})

def get_cache_config(cache_type: str) -> Dict[str, Any]:
    """Get configuration for a specific cache type."""
    return CACHE_CONFIG.get(f"{cache_type}_cache", {})

def get_model_defaults() -> Dict[str, Any]:
    """Return model default settings from models.yaml."""
    return MODELS_CONFIG.get("defaults", {}) or {}

def get_hardware_config() -> Dict[str, Any]:
    """Return the full hardware configuration dictionary."""
    return HARDWARE_CONFIG or {}

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

# Testing
TEST_MODE = os.getenv("AOC_TEST_MODE", "false").lower() == "true"
