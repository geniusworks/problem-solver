import types

import shared.solver as solver_module


class DummyLearningDatabase:
    last_instance = None

    def __init__(self, db_dir):  # type: ignore[override]
        self.db_dir = db_dir
        self.calls = []
        DummyLearningDatabase.last_instance = self

    def get_top_models(self, problem_type: str, role: str, limit: int = 3, min_success_rate: float = 0.5):  # type: ignore[override]
        self.calls.append((problem_type, role, limit, min_success_rate))
        return ["db-model-1", "db-model-2"]


def _make_solver(tmp_path) -> solver_module.BaseSolver:
    solver = solver_module.BaseSolver.__new__(solver_module.BaseSolver)  # type: ignore[arg-type]
    solver.workspace_dir = tmp_path
    solver.learning_dir = tmp_path / "learning"
    solver.learning_dir.mkdir(parents=True, exist_ok=True)
    solver.db = None
    solver.models = {"fallback-1": object(), "fallback-2": object()}
    return solver


def test_get_top_models_uses_learning_db_and_problem_type(monkeypatch, tmp_path):
    monkeypatch.setattr(solver_module, "LearningDatabase", DummyLearningDatabase)

    solver = _make_solver(tmp_path)

    result = solver._get_top_models("math", "primary", limit=2, min_success_rate=0.7)

    # Should return models from the DB implementation
    assert result == ["db-model-1", "db-model-2"]

    # Ensure LearningDatabase was constructed with learning_dir
    assert DummyLearningDatabase.last_instance is not None
    assert DummyLearningDatabase.last_instance.db_dir == solver.learning_dir

    # Ensure get_top_models was called with provided parameters
    assert DummyLearningDatabase.last_instance.calls == [("math", "primary", 2, 0.7)]


class DummyEmptyLearningDatabase(DummyLearningDatabase):
    def get_top_models(self, problem_type: str, role: str, limit: int = 3, min_success_rate: float = 0.5):  # type: ignore[override]
        self.calls.append((problem_type, role, limit, min_success_rate))
        return []


def test_get_top_models_falls_back_to_local_models_when_db_empty(monkeypatch, tmp_path):
    monkeypatch.setattr(solver_module, "LearningDatabase", DummyEmptyLearningDatabase)

    solver = _make_solver(tmp_path)

    result = solver._get_top_models("general", "primary", limit=1, min_success_rate=0.5)

    # Should fall back to local models when DB returns no entries
    assert result == ["fallback-1"]

    assert DummyEmptyLearningDatabase.last_instance is not None
    # Ensure DB was still queried
    assert DummyEmptyLearningDatabase.last_instance.calls == [("general", "primary", 1, 0.5)]
