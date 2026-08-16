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


_REAL_LEARNING_DIR = Path(__file__).resolve().parent.parent / "learning"


@pytest.fixture(autouse=True)
def _never_write_the_real_learning_db(monkeypatch, tmp_path_factory):
    """No test may write the project's live measurement store.

    `learning/solver.db` is a research artifact: every row is supposed to be a
    measured outcome. But `solve.py` resolves its workspace to the repo root, so
    the entrypoint integration test drove real writes into it -- the M1's
    database ended up with a fabricated `dummy-model` at 79 attempts / 79
    successes, a perfect record for a model that never ran, sitting in the table
    `_get_top_models` ranks on. (It was filtered out of live runs by the
    installed-models intersection, so this was contamination, not a wrong
    result.)

    Any LearningDatabase aimed at the real directory -- explicitly or via the
    `db_dir=None` default -- is redirected to a per-test temp dir. Tests that
    already pass their own tmp_path are untouched.
    """
    from learning.database import LearningDatabase

    redirect = tmp_path_factory.mktemp("learning-db")
    original_init = LearningDatabase.__init__

    def guarded_init(self, db_dir=None):
        if db_dir is None or Path(db_dir).resolve() == _REAL_LEARNING_DIR:
            db_dir = redirect
        original_init(self, Path(db_dir))

    monkeypatch.setattr(LearningDatabase, "__init__", guarded_init)


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
