import types

import pytest

import shared.solver as solver_module
import shared.quality.code_quality as cq
import learning


class DummyQualityMetrics:
    def __init__(self, overall: float, complexity: float, maintainability: float, error: float) -> None:
        self.overall_score = overall
        self.cyclomatic_complexity = complexity
        self.maintainability_index = maintainability
        self.error_handling_score = error


class DummyCodeQualityAnalyzer:
    def __init__(self) -> None:
        self.calls = []

    def analyze(self, code: str) -> DummyQualityMetrics:  # type: ignore[override]
        self.calls.append(code)
        return DummyQualityMetrics(overall=0.8, complexity=3.0, maintainability=75.0, error=0.6)


class RecordingLearningDatabase:
    last_instance = None

    def __init__(self, db_dir) -> None:  # type: ignore[override]
        self.db_dir = db_dir
        self.update_calls = []
        RecordingLearningDatabase.last_instance = self

    def update_model_performance(self, model_name, metrics, success, problem_type="general", role="primary"):  # type: ignore[override]
        self.update_calls.append((model_name, metrics, success, problem_type, role))

    def record_improvement(self, *args, **kwargs) -> None:  # type: ignore[override]
        # Not needed for this test, but BaseSolver may call it in other flows
        pass

    def get_top_models(self, *args, **kwargs):  # type: ignore[override]
        return []


class DummyParsedProblem:
    def __init__(self) -> None:
        self.description = "Simple test problem"
        self.examples = [
            types.SimpleNamespace(
                input_data="example-input",
                expected_output="2970687",
                description="matches the accepted answer",
            )
        ]
        self.test_cases = []


class DummyPrimaryModel:
    def __init__(self, name: str) -> None:
        self.name = name

    async def generate_solution(self, parsed_problem, year: int, day: int, strategies, strategy_effectiveness) -> str:  # type: ignore[override]
        return (
            "def solve():\n"
            "    return '2970687'\n"
            "\n"
            'if __name__ == "__main__":\n'
            "    print(solve())\n"
        )


class DummySubmissionManager:
    def __init__(self, workspace_dir):  # type: ignore[override]
        self.workspace_dir = workspace_dir

    def get_recommended_strategies(self, problem_text, characteristics):  # type: ignore[override]
        return [], {}


@pytest.mark.asyncio
async def test_solver_records_quality_metrics_in_learning_db(monkeypatch, tmp_path):
    async def fake_fetch_problem_text(year: int, day: int, part: int = 1):
        return "Dummy problem text", None, None

    async def fake_ensure_problem_files(year: int, day: int):
        return {
            "problem": tmp_path / "problem.txt",
            "examples": tmp_path / "examples",
            "input": tmp_path / "input.txt",
        }

    def fake_ensure_problem_directory_structure(workspace_dir, year: int, day: int):
        day_dir = tmp_path
        attempts_dir = tmp_path / "attempts"
        examples_dir = tmp_path / "examples"
        attempts_dir.mkdir(parents=True, exist_ok=True)
        examples_dir.mkdir(parents=True, exist_ok=True)
        return {"day": day_dir, "attempts": attempts_dir, "examples": examples_dir}

    monkeypatch.setattr(solver_module, "fetch_problem_text", fake_fetch_problem_text)
    monkeypatch.setattr(solver_module, "ensure_problem_files", fake_ensure_problem_files)
    monkeypatch.setattr(
        solver_module,
        "ensure_problem_directory_structure",
        fake_ensure_problem_directory_structure,
    )
    monkeypatch.setattr(solver_module, "parse_problem_text", lambda text: DummyParsedProblem())

    # Use dummy submission manager to avoid touching real submission/learning logic
    monkeypatch.setattr(solver_module, "SubmissionManager", DummySubmissionManager)

    # Patch quality analyzer and learning database to lightweight stubs
    monkeypatch.setattr(cq, "CodeQualityAnalyzer", DummyCodeQualityAnalyzer)
    monkeypatch.setattr(learning, "LearningDatabase", RecordingLearningDatabase)

    # Avoid hitting the real DB-backed model selection inside _get_top_models
    def fake_get_top_models(self, problem_type: str, role: str, limit: int = 3, min_success_rate: float = 0.5):  # type: ignore[override]
        if role == "primary":
            return ["primary-1"]
        return []

    monkeypatch.setattr(solver_module.BaseSolver, "_get_top_models", fake_get_top_models)

    # Avoid writing solution files/README during the test
    monkeypatch.setattr(solver_module, "record_solution", lambda *args, **kwargs: None)

    solver = solver_module.BaseSolver(tmp_path, debug=False)

    # The executor runs candidates against the real puzzle input, so it must
    # exist under the workspace. Without it the full-input run errors and no
    # candidate can be accepted -- which the consensus short-circuit used to
    # hide by returning before any execution happened.
    input_path = tmp_path / "years" / "2022" / "day01" / "input.txt"
    input_path.parent.mkdir(parents=True, exist_ok=True)
    input_path.write_text("example-input\n")

    primary_model = DummyPrimaryModel("primary-1")
    solver.models = {"primary-1": primary_model}

    # Run the solver once to trigger quality analysis and learning update
    result = await solver.solve_problem(2022, 1, 1, force=True)

    assert result is not None

    db = RecordingLearningDatabase.last_instance
    assert db is not None
    assert db.update_calls

    model_name, metrics, success, problem_type, role = db.update_calls[0]

    assert model_name == "primary-1"
    assert success is True
    assert role == "primary"

    # Problem type should be a non-empty string based on characteristics
    assert isinstance(problem_type, str)
    assert problem_type

    # Metrics should reflect the DummyCodeQualityAnalyzer outputs
    assert metrics["quality_score"] == pytest.approx(0.8 * 10.0)
    assert metrics["complexity_score"] == pytest.approx(3.0)
    assert metrics["maintainability_score"] == pytest.approx(75.0)
    assert metrics["error_handling_score"] == pytest.approx(0.6)
    assert metrics["cost"] == pytest.approx(0.0)
    assert isinstance(metrics["response_time"], float)
    assert metrics["response_time"] >= 0.0
