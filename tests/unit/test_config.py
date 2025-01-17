"""Test configuration loading and management."""

import pytest
from pathlib import Path
from shared import config


def test_load_model_defaults():
    """Test loading model defaults from YAML."""
    defaults = config.get_model_defaults()
    assert isinstance(defaults, dict)
    assert "temperature" in defaults
    assert "max_tokens" in defaults
    assert "timeout_seconds" in defaults


def test_load_hardware_config():
    """Test loading hardware configuration."""
    hw_config = config.get_hardware_config()
    assert isinstance(hw_config, dict)
    assert "profiles" in hw_config


def test_load_resource_config():
    """Test loading resource limits."""
    resource_config = config.get_resource_config()
    assert isinstance(resource_config, dict)
    assert "requests" in resource_config
    assert "rate_limit_delay" in resource_config["requests"]
