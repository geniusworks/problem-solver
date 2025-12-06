import types

import pytest

import shared.solver as solver_module
import shared.quality.code_quality as cq
import learning


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
        self.calls.append(code)
        # Treat solutions containing "# improved" as strictly better
        if "# improved" in code:
            return DummyQualityMetrics(0.9)
        return DummyQualityMetrics(0.5)


class DummyPrimaryModel:
    def __init__(self, name: str, solution: str) -> None:
        self.name = name
        self._solution = solution

    async def generate_solution(self, parsed_problem, year: int, day: int, strategies, strategy_effectiveness) -> str:  # type: ignore[override]
        return self._solution


class DummyValidatorModel:
    def __init__(self, name: str) -> None:
        self.name = name
        self.calls = []

    async def validate_solution(self, solution: str, test_cases) -> bool:  # type: ignore[override]
        self.calls.append(solution)
        return True


class DummyCollaborativeImprovement:
    last_instance = None

    def __init__(self, reviewers, max_iterations: int = 3) -> None:  # type: ignore[override]
        self.reviewers = reviewers
        self.max_iterations = max_iterations
        self.calls = []
        DummyCollaborativeImprovement.last_instance = self

    async def improve_solution(self, best_answer: str):  # type: ignore[override]
        self.calls.append(best_answer)
        improved = best_answer + "\n# improved"
        return types.SimpleNamespace(solution=improved, author="reviewer-1")


class DummyLearningDatabase:
    def __init__(self, db_dir) -> None:  # type: ignore[override]
        self.db_dir = db_dir
        self.improvements = []

    def update_model_performance(self, *args, **kwargs) -> None:  # type: ignore[override]
        pass

    def record_improvement(self, problem_id: str, model_name: str, improvement_type: str, impact_score: float) -> None:  # type: ignore[override]
        self.improvements.append((problem_id, model_name, improvement_type, impact_score))

    def get_top_models(self, *args, **kwargs):  # type: ignore[override]
        return []


class DummyParsedProblem:
    def __init__(self) -> None:
        self.description = "Simple test problem"
        self.examples = [types.SimpleNamespace(input_data="example-input")]
        self.test_cases = []


@pytest.mark.asyncio
async def test_solver_uses_collaborative_improvement_when_no_consensus(monkeypatch, tmp_path):
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

    # Quality analyzer to force no consensus but enable improvement
    monkeypatch.setattr(cq, "CodeQualityAnalyzer", DummyCodeQualityAnalyzer)

    # Collaborative improvement and learning DB stubs
    import shared.llm.collaborative as collab_module

    monkeypatch.setattr(collab_module, "CollaborativeImprovement", DummyCollaborativeImprovement)
    monkeypatch.setattr(learning, "LearningDatabase", DummyLearningDatabase)

    # Ensure the global learning_dir used in collaborative block exists
    solver_module.learning_dir = tmp_path / "learning"

    def fake_get_top_models(self, problem_type: str, role: str, limit: int = 3, min_success_rate: float = 0.5):  # type: ignore[override]
        if role == "primary":
            return ["primary-1", "primary-2"]
        if role == "reviewer":
            return ["reviewer-1"]
        if role == "validator":
            return ["validator-1"]
        return []

    monkeypatch.setattr(solver_module.BaseSolver, "_get_top_models", fake_get_top_models)

    solver = solver_module.BaseSolver(tmp_path, debug=False)
    # Explicitly enable collaborative improvement for this test scenario
    solver.enable_collaborative_improvement = True

    primary_1 = DummyPrimaryModel(
        "primary-1",
        "def solve(input_data: str) -> str:\n    return 'A'\n",
    )
    primary_2 = DummyPrimaryModel(
        "primary-2",
        "def solve(input_data: str) -> str:\n    return 'B'\n",
    )
    validator = DummyValidatorModel("validator-1")
    reviewer = DummyValidatorModel("reviewer-1")

    solver.models = {
        "primary-1": primary_1,
        "primary-2": primary_2,
        "validator-1": validator,
        "reviewer-1": reviewer,
    }

    result = await solver.solve_problem(2022, 1, 1, force=True)

    assert result is not None
    assert "# improved" in result

    assert DummyCollaborativeImprovement.last_instance is not None
    assert DummyCollaborativeImprovement.last_instance.calls

    assert isinstance(solver.db, DummyLearningDatabase)
    assert solver.db.improvements
