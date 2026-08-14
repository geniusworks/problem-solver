"""Test configuration loading and management."""

import pytest
from pathlib import Path
from shared import config


def test_load_resource_config():
    """Test loading resource limits."""
    resource_config = config.get_resource_config()
    assert isinstance(resource_config, dict)
    assert "requests" in resource_config
    assert "rate_limit_delay" in resource_config["requests"]
