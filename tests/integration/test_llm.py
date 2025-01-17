"""Test LLM integration and providers."""

import pytest
from shared.llm.providers import ModelProvider
from shared.llm.hardware import HardwareManager


async def test_model_provider_initialization():
    """Test model provider initialization with config."""
    provider = ModelProvider()
    assert provider.temperature == 0.1  # Default from models.yaml
    assert provider.max_tokens > 0


async def test_hardware_manager():
    """Test hardware capability detection."""
    hw = HardwareManager()
    profile = hw.get_current_profile()
    assert isinstance(profile, dict)
    assert "gpu_memory" in profile
