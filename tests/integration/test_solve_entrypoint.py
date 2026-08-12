import solve as solve_module
import shared.solver as solver_module
import pytest
import shared.quality.code_quality as cq


class DummyExample:
    """A worked example whose expected output the dummy solution reproduces.

    The solver refuses to accept a candidate for a problem with no oracle, so a
    realistic parsed problem must carry one. Previously this test passed only
    because a single candidate short-circuited as "consensus" and was returned
    without ever being executed.
    """

    def __init__(self) -> None:
        self.input_data = "anything"
        self.expected_output = "2970687"
        self.description = "returns the accepted answer"


class DummyParsedProblem:
    def __init__(self) -> None:
        self.description = "Dummy problem description"
        self.examples = [DummyExample()]
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

    def __init__(self, model: str, debug: bool = False, temperature=None,
                 num_ctx=None) -> None:
        self.model_name = model
        self.debug = debug
        self.temperature = temperature
        self.num_ctx = num_ctx

    async def generate_solution(
        self,
        parsed_problem,
        year: int,
        day: int,
        strategies,
        strategy_effectiveness,
    ) -> str:
        # Must print the answer, as the prompt template requires of real
        # generated solutions -- a solve() that only returns produces empty
        # output and fails verification.
        return (
            "def solve():\n"
            "    return '2970687'\n"
            "\n"
            'if __name__ == "__main__":\n'
            "    print(solve())\n"
        )

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
    # This test drives solve.async_main(), which resolves the workspace to the
    # repo root rather than tmp_path, so it needs the cached puzzle data for
    # 2024 day 1. That data lives under years/, which is gitignored -- skip
    # rather than fail on a fresh clone.
    from shared.ground_truth import get_known_answer
    from shared.paths import get_problem_dir

    if get_known_answer(2024, 1, 1) is None:
        pytest.skip("no cached ground truth for 2024 day 1 part 1")
    if not (get_problem_dir(2024, 1) / "input.txt").exists():
        pytest.skip("no cached puzzle input for 2024 day 1")

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
