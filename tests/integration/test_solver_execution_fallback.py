import types

import pytest

import shared.solver as solver_module
import shared.quality.code_quality as cq
import learning
from shared.execution import ExecutionResult


class DummyQualityMetrics:
    def __init__(self, score: float) -> None:
        self.overall_score = score
        self.cyclomatic_complexity = 0.0
        self.maintainability_index = 0.0
        self.error_handling_score = 0.0


class DummyCodeQualityAnalyzer:
    def __init__(self) -> None:
        self.calls = []

    def analyze(self, code: str) -> DummyQualityMetrics:  # type: ignore[override]
        # Give all candidates the same quality so consensus cannot distinguish
        self.calls.append(code)
        return DummyQualityMetrics(0.5)


class DummyParsedProblem:
    def __init__(self) -> None:
        self.description = "Simple test problem"
        self.examples = []
        self.test_cases = []


class DummyPrimaryModel:
    def __init__(self, name: str, solution: str) -> None:
        self.name = name
        self._solution = solution

    async def generate_solution(  # type: ignore[override]
        self, parsed_problem, year: int, day: int, strategies, strategy_effectiveness
    ) -> str:
        return self._solution


class DummyValidatorModel:
    async def validate_solution(self, solution: str, test_cases) -> bool:  # type: ignore[override]
        return True


class DummyLearningDatabase:
    def __init__(self, db_dir) -> None:  # type: ignore[override]
        self.db_dir = db_dir
        self.update_calls = []
        self.improvements = []

    def update_model_performance(self, *args, **kwargs) -> None:  # type: ignore[override]
        self.update_calls.append((args, kwargs))

    def record_improvement(self, *args, **kwargs) -> None:  # type: ignore[override]
        self.improvements.append((args, kwargs))

    def get_top_models(
        self, problem_type: str, role: str, limit: int = 3, min_success_rate: float = 0.5
    ):  # type: ignore[override]
        # Let BaseSolver fall back to local models
        return []


class RecordingExecutor:
    last_instance = None

    def __init__(self, workspace_dir):  # type: ignore[override]
        self.workspace_dir = workspace_dir
        self.calls = []
        RecordingExecutor.last_instance = self

    async def test_solution(  # type: ignore[override]
        self,
        solution_code: str,
        year: int,
        day: int,
        part: int,
        test_cases=None,
        model_name: str = "",
        debug: bool = False,
    ):
        # Mark candidates containing "# good" as the only ones that pass
        self.calls.append((model_name, solution_code))

        if "# good" in solution_code:
            example_results = [ExecutionResult(output="OK", error=None)]
            full_result = ExecutionResult(output="1234", error=None)
            full_answer = "1234"
        else:
            example_results = [ExecutionResult(output="", error="boom")]
            full_result = ExecutionResult(output="", error="boom")
            full_answer = None

        return example_results, full_result, full_answer


@pytest.mark.asyncio
async def test_solver_uses_execution_based_selection_when_no_consensus(
    monkeypatch, tmp_path
):
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
    monkeypatch.setattr(
        solver_module, "parse_problem_text", lambda text: DummyParsedProblem()
    )

    # Use stub quality analyzer and learning database
    monkeypatch.setattr(cq, "CodeQualityAnalyzer", DummyCodeQualityAnalyzer)
    monkeypatch.setattr(learning, "LearningDatabase", DummyLearningDatabase)

    # Use recording executor so we don't run real code
    monkeypatch.setattr(solver_module, "SolutionExecutor", RecordingExecutor)

    # Avoid writing solution files/README during the test
    monkeypatch.setattr(solver_module, "record_solution", lambda *args, **kwargs: None)

    # Cold-start model selection: have BaseSolver use local models directly
    def fake_get_top_models(
        self, problem_type: str, role: str, limit: int = 3, min_success_rate: float = 0.5
    ):  # type: ignore[override]
        if role == "primary":
            return ["primary-1", "primary-2"]
        if role == "reviewer":
            return []
        if role == "validator":
            return []
        return []

    monkeypatch.setattr(solver_module.BaseSolver, "_get_top_models", fake_get_top_models)

    solver = solver_module.BaseSolver(tmp_path, debug=False)
    # Ensure collaborative improvement is disabled so we exercise execution-based fallback
    solver.enable_collaborative_improvement = False

    primary_1 = DummyPrimaryModel("primary-1", "def solve():\n    return 1\n  # bad")
    primary_2 = DummyPrimaryModel(
        "primary-2",
        "def solve():\n    return 2\n  # good",
    )

    solver.models = {
        "primary-1": primary_1,
        "primary-2": primary_2,
    }

    result = await solver.solve_problem(2022, 1, 1, force=True)

    # We should have picked the execution-validated candidate (the one marked as "# good")
    assert result is not None
    assert "# good" in result

    # The recording executor should have been invoked at least once
    assert RecordingExecutor.last_instance is not None
    assert RecordingExecutor.last_instance.calls
