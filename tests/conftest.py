"""Pytest configuration and shared fixtures."""

import pytest
from pathlib import Path


# Variables `shared.config` / `SolverConfig.from_env()` read. `shared.config`
# calls load_dotenv() at import time, so a developer's .env is in os.environ
# before any test runs -- and scripts/setup.sh writes one with a concrete
# SOLVER_MODELS. That silently overrode the model list tests patch, so the suite
# was red on a fresh clone. Tests that exercise env handling set these
# themselves; everyone else must see a clean environment.
_SOLVER_ENV_VARS = (
    "SOLVER_MODELS",
    "MAX_REPAIR_ITERATIONS",
    "ENABLE_COLLABORATIVE_IMPROVEMENT",
    "SUBMIT_SOLUTIONS",
)


@pytest.fixture(autouse=True)
def _isolate_solver_env(monkeypatch):
    """Keep the developer's .env out of every test's configuration."""
    for var in _SOLVER_ENV_VARS:
        monkeypatch.delenv(var, raising=False)


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
