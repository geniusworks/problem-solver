import solve as solve_module
import shared.solver as solver_module
import pytest
import shared.quality.code_quality as cq


class DummyParsedProblem:
    def __init__(self) -> None:
        self.description = "Dummy problem description"
        self.examples = []
        self.test_cases = []


class DummyCodeQualityMetrics:
    overall_score = 1.0
    cyclomatic_complexity = 1.0
    maintainability_index = 1.0
    error_handling_score = 1.0


class DummyCodeQualityAnalyzer:
    def analyze(self, code: str) -> DummyCodeQualityMetrics:
        return DummyCodeQualityMetrics()


class DummyModel:
    AVAILABLE_MODELS = ["dummy-model"]

    def __init__(self, model: str, debug: bool = False) -> None:
        self.model_name = model
        self.debug = debug

    async def generate_solution(
        self,
        parsed_problem,
        year: int,
        day: int,
        strategies,
        strategy_effectiveness,
    ) -> str:
        return "def solve(input_data: str) -> str:\n    return '42'\n"

    async def validate_solution(self, solution: str, test_cases) -> bool:
        return True


class DummyArgs:
    def __init__(self) -> None:
        self.year = 2024
        self.day = 1
        self.part = 1
        self.force = True
        self.debug = False


async def test_solve_entrypoint_end_to_end(monkeypatch, tmp_path, capsys):
    monkeypatch.setattr(solve_module, "parse_args", lambda: DummyArgs())

    async def fake_fetch_problem_text(year: int, day: int, part: int = 1):
        return "Dummy problem text", None, None

    async def fake_ensure_problem_files(year: int, day: int):
        return {
            "problem": tmp_path / "problem.txt",
            "examples": tmp_path / "examples",
            "input": tmp_path / "input.txt",
        }

    monkeypatch.setattr(solver_module, "fetch_problem_text", fake_fetch_problem_text)
    monkeypatch.setattr(solver_module, "ensure_problem_files", fake_ensure_problem_files)
    monkeypatch.setattr(solver_module, "parse_problem_text", lambda text: DummyParsedProblem())

    monkeypatch.setattr(solver_module, "OllamaProvider", DummyModel)
    monkeypatch.setattr(
        solver_module.BaseSolver,
        "_resolve_available_models",
        lambda self: DummyModel.AVAILABLE_MODELS,
    )
    monkeypatch.setattr(cq, "CodeQualityAnalyzer", DummyCodeQualityAnalyzer)
    monkeypatch.setattr(solver_module, "record_solution", lambda *args, **kwargs: None)
    monkeypatch.setattr(
        solver_module.BaseSolver,
        "_get_top_models",
        lambda self, problem_type, role, limit=3, min_success_rate=0.5: ["dummy-model"],
    )

    exit_code = await solve_module.async_main()
    captured = capsys.readouterr()

    assert exit_code == 0
    assert "Solution:" in captured.out
