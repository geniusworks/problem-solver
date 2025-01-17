"""Pytest configuration and shared fixtures."""

import pytest
from pathlib import Path


@pytest.fixture
def test_data_dir() -> Path:
    """Return the test data directory."""
    return Path(__file__).parent / "fixtures"


@pytest.fixture
def problem_fixtures_dir(test_data_dir: Path) -> Path:
    """Return the problem fixtures directory."""
    return test_data_dir / "problems"


@pytest.fixture
def solution_fixtures_dir(test_data_dir: Path) -> Path:
    """Return the solution fixtures directory."""
    return test_data_dir / "solutions"
