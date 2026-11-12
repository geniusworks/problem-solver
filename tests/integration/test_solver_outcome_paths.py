"""Every way a solve can end, driven through the real solver with scripted models and executor.

No Ollama, puzzle files, learning database or ledger: the model returns scripted programs, and
the executor reads a marker in each program to decide what running it produced. What is under
test is the orchestration -- which attempts are made, what each is recorded as, what feedback a
repair is given and what the solve returns -- which is what a refactor of shared/solver.py must
leave unchanged, and what earlier measurement bugs blurred (a harness error scored as a model
failure, a repair recorded with the draft's cost, a crash counted as a wrong answer).
"""

from typing import Dict, List, Optional

import pytest

import learning
import shared.ground_truth as ground_truth
import shared.quality.code_quality as code_quality
import shared.solver as solver_module
from shared.execution import ExecutionResult
from shared.experiment import Outcome, SolverConfig

ANSWER = "1234"
TIMEOUT = "Solution timed out after 60 seconds"
MEMORY_CAP = "Solution exceeded the memory cap of 8192 MB and was stopped"


def program(behaviour: str, tag: str = "") -> str:
    """A candidate whose marker tells the scripted executor what running it produces."""
    return f"def solve():\n    return 0\n# behaviour: {behaviour} {tag}\n"


class Example:
    def __init__(self) -> None:
        self.input_data = "1 2 3"
        self.expected_output = "6"
        self.description = "sum"


class Problem:
    def __init__(self) -> None:
        self.title = "--- Day 1: Test ---"
        self.description = "Sum the numbers."
        self.examples = [Example()]
        self.test_cases: list = []
        self.final_question = "What is the sum?"
        self.supplement = ""


class ScriptedExecutor:
    def __init__(self, workspace_dir, timeout=None) -> None:
        pass

    async def test_solution(self, solution_code: str, year: int, day: int, part: int,
                            test_cases=None, model_name: str = "", debug: bool = False,
                            force_full_input: bool = False):
        behaviour = solution_code.split("# behaviour: ")[1].split()[0]
        examples_ok = [ExecutionResult(output="6")]
        examples_bad = [ExecutionResult(output="", error="Test case 1 failed: expected '6', got '5'")]
        if behaviour == "harness":
            raise RuntimeError("executor bug")
        if behaviour == "solved":
            return examples_ok, ExecutionResult(output=ANSWER), ANSWER
        if behaviour == "wrong":
            return examples_ok, ExecutionResult(output="999"), "999"
        if behaviour == "wrong_example":
            return examples_bad, ExecutionResult(output="999"), "999"
        if behaviour == "timeout":
            return examples_ok, ExecutionResult(output="", error=TIMEOUT), None
        if behaviour == "memory":
            return examples_ok, ExecutionResult(output="", error=MEMORY_CAP), None
        if behaviour == "crash":
            return examples_bad, ExecutionResult(output="", error="Process failed: ValueError"), None
        if behaviour == "silent":
            return examples_ok, ExecutionResult(output=""), ""
        raise AssertionError(behaviour)


class ScriptedModel:
    """Drafts in order; each repair maps the code it is given to the code it returns."""

    def __init__(self, drafts: List[Optional[str]], repairs: Optional[Dict[str, str]] = None) -> None:
        self.drafts = list(drafts)
        self.repairs = repairs or {}
        self.feedback: List[str] = []
        self.last_token_usage = {"input_tokens": 100, "output_tokens": 10}

    async def generate_solution(self, problem, year, day, strategies=None,
                                strategy_effectiveness=None) -> str:
        draft = self.drafts.pop(0)
        if draft is None:
            raise RuntimeError("model returned no code")
        return draft

    async def improve_solution(self, solution: str, problem, feedback=None) -> str:
        self.feedback.append(feedback or "")
        return self.repairs.get(solution, solution)


class NoDatabase:
    def __init__(self, *args, **kwargs) -> None:
        pass

    def update_model_performance(self, *args, **kwargs) -> None:
        pass

    def record_improvement(self, *args, **kwargs) -> None:
        pass

    def get_top_models(self, *args, **kwargs) -> list:
        return []


class EqualQuality:
    def analyze(self, code):
        class Metrics:
            overall_score = 0.5
        return Metrics()


@pytest.fixture
def make_solver(monkeypatch, tmp_path):
    async def fetch(year, day, part=1):
        return "problem text", None, None

    async def ensure_files(year, day):
        return {}

    monkeypatch.setattr(solver_module, "fetch_problem_text", fetch)
    monkeypatch.setattr(solver_module, "ensure_problem_files", ensure_files)
    monkeypatch.setattr(solver_module, "ensure_problem_directory_structure", lambda *a, **k: {})
    monkeypatch.setattr(solver_module, "parse_problem_text", lambda text: Problem())
    monkeypatch.setattr(solver_module, "SolutionExecutor", ScriptedExecutor)
    monkeypatch.setattr(solver_module, "LearningDatabase", NoDatabase)
    monkeypatch.setattr(learning, "LearningDatabase", NoDatabase)
    monkeypatch.setattr(code_quality, "CodeQualityAnalyzer", EqualQuality)
    monkeypatch.setattr(solver_module.BaseSolver, "_resolve_available_models",
                        lambda self: list(self.config.models or ()))
    recorded: list = []
    monkeypatch.setattr(solver_module, "record_solution", lambda *a, **k: recorded.append(a))

    def build(models: Dict[str, ScriptedModel], answer: Optional[str] = ANSWER, **config):
        monkeypatch.setattr(ground_truth, "get_known_answer", lambda y, d, p: answer)
        settings = {"problem_context": "legacy", "example_tests": "parser",
                    "models": tuple(models), "enable_fallback_models": False}
        settings.update(config)
        solver = solver_module.BaseSolver(tmp_path, config=SolverConfig(**settings))
        solver.models = models  # type: ignore[assignment]
        monkeypatch.setattr(solver, "_get_top_models",
                            lambda problem_type, role, limit=3, min_success_rate=0.5:
                            list(models)[:1] if role == "primary" else [])
        solver.recorded = recorded  # type: ignore[attr-defined]
        return solver

    return build


async def solve(solver) -> Optional[str]:
    return await solver.solve_problem(2022, 1, 1, force=True)


def trace(solver) -> List[tuple]:
    return [(a.stage, a.repair_iteration, a.draft_index, a.outcome) for a in solver.attempts]


async def test_a_correct_draft_is_returned_and_recorded(make_solver):
    model = ScriptedModel([program("solved")])
    solver = make_solver({"m": model})

    result = await solve(solver)

    assert result == program("solved")
    assert trace(solver) == [("generate", 0, 0, Outcome.SOLVED)]
    assert model.feedback == []
    assert len(solver.recorded) == 1


async def test_a_wrong_answer_is_repaired(make_solver):
    model = ScriptedModel([program("wrong")], {program("wrong"): program("solved")})
    solver = make_solver({"m": model})

    result = await solve(solver)

    assert result == program("solved")
    assert trace(solver) == [("generate", 0, 0, Outcome.WRONG), ("repair", 1, 0, Outcome.SOLVED)]
    assert "the answer is still not accepted" in model.feedback[0]
    assert ANSWER not in model.feedback[0]  # the accepted answer never leaks into feedback


async def test_repairs_stop_after_the_configured_rounds(make_solver):
    model = ScriptedModel([program("wrong", "a")], {program("wrong", "a"): program("wrong", "b"),
                                                    program("wrong", "b"): program("wrong", "c")})
    solver = make_solver({"m": model}, max_repair_iterations=2)

    assert await solve(solver) is None
    assert trace(solver) == [("generate", 0, 0, Outcome.WRONG), ("repair", 1, 0, Outcome.WRONG),
                             ("repair", 2, 0, Outcome.WRONG)]
    assert len(model.feedback) == 2


async def test_a_timeout_is_an_error_and_gets_speed_guidance_only_when_enabled(make_solver):
    for enabled in (False, True):
        model = ScriptedModel([program("timeout", "a")], {program("timeout", "a"): program("solved")})
        solver = make_solver({"m": model}, targeted_feedback=enabled)

        assert await solve(solver) == program("solved")
        assert trace(solver)[0] == ("generate", 0, 0, Outcome.ERROR)
        assert TIMEOUT in solver.attempts[0].error
        assert ("PERFORMANCE failure" in model.feedback[0]) is enabled


async def test_a_memory_cap_stop_is_an_error_without_speed_guidance(make_solver):
    model = ScriptedModel([program("memory", "a")], {program("memory", "a"): program("solved")})
    solver = make_solver({"m": model}, targeted_feedback=True)

    assert await solve(solver) == program("solved")
    assert trace(solver)[0] == ("generate", 0, 0, Outcome.ERROR)
    assert "memory cap" in solver.attempts[0].error
    assert "PERFORMANCE failure" not in model.feedback[0]


async def test_wrong_answer_guidance_only_when_enabled(make_solver):
    for enabled in (False, True):
        model = ScriptedModel([program("wrong", "a")], {program("wrong", "a"): program("solved")})
        solver = make_solver({"m": model}, targeted_feedback=enabled)

        await solve(solver)
        assert ("That value is INCORRECT" in model.feedback[0]) is enabled


async def test_a_crash_whose_repair_changes_nothing_ends_as_no_candidate(make_solver):
    model = ScriptedModel([program("crash")])  # repair returns the same code
    solver = make_solver({"m": model})

    assert await solve(solver) is None
    assert trace(solver) == [("generate", 0, 0, Outcome.ERROR),
                             ("repair", 1, 0, Outcome.NO_CANDIDATE)]
    assert solver.attempts[1].error == "repair returned the code unchanged"


async def test_a_draft_that_produced_no_code_is_recorded_as_no_candidate(make_solver):
    model = ScriptedModel([None])
    solver = make_solver({"m": model})

    assert await solve(solver) is None
    assert trace(solver) == [("generate", 0, 0, Outcome.NO_CANDIDATE)]
    assert "no code" in solver.attempts[0].error


async def test_an_executor_failure_is_a_harness_error_not_a_model_failure(make_solver):
    model = ScriptedModel([program("harness")])
    solver = make_solver({"m": model})

    assert await solve(solver) is None
    assert trace(solver) == [("generate", 0, 0, Outcome.HARNESS_ERROR)]


async def test_a_run_that_prints_nothing_is_no_candidate(make_solver):
    model = ScriptedModel([program("silent")], {program("silent"): program("solved")})
    solver = make_solver({"m": model})

    assert await solve(solver) == program("solved")
    assert trace(solver)[0] == ("generate", 0, 0, Outcome.NO_CANDIDATE)


async def test_without_an_accepted_answer_passing_examples_is_unverified(make_solver):
    model = ScriptedModel([program("wrong")])
    solver = make_solver({"m": model}, answer=None)

    assert await solve(solver) == program("wrong")
    assert trace(solver) == [("generate", 0, 0, Outcome.UNVERIFIED)]


async def test_without_an_accepted_answer_a_failed_example_is_wrong(make_solver):
    model = ScriptedModel([program("wrong_example")], {program("wrong_example"): program("wrong")})
    solver = make_solver({"m": model}, answer=None)

    assert await solve(solver) == program("wrong")
    assert trace(solver) == [("generate", 0, 0, Outcome.WRONG), ("repair", 1, 0, Outcome.UNVERIFIED)]


async def test_several_drafts_each_keep_their_draft_index(make_solver):
    model = ScriptedModel([program("wrong", "0"), program("timeout", "1"), program("solved", "2")])
    solver = make_solver({"m": model}, samples_per_model=3)

    assert await solve(solver) == program("solved", "2")
    assert trace(solver) == [("generate", 0, 0, Outcome.WRONG), ("generate", 0, 1, Outcome.ERROR),
                             ("generate", 0, 2, Outcome.SOLVED)]
    assert model.feedback == []  # one draft passing ends the solve before any repair


async def test_drafts_that_agree_are_verified_as_a_consensus(make_solver):
    model = ScriptedModel([program("solved"), program("solved")])
    solver = make_solver({"m": model}, samples_per_model=2)

    assert await solve(solver) == program("solved")
    assert trace(solver) == [("consensus", 0, None, Outcome.SOLVED)]


async def test_a_fallback_model_is_tried_when_every_primary_fails(make_solver):
    primary = ScriptedModel([program("wrong", "p")], {program("wrong", "p"): program("wrong", "p2"),
                                                      program("wrong", "p2"): program("wrong", "p3")})
    fallback = ScriptedModel([program("solved", "f")])
    solver = make_solver({"m": primary, "f": fallback}, enable_fallback_models=True)

    assert await solve(solver) == program("solved", "f")
    assert trace(solver)[-1] == ("fallback", 0, 0, Outcome.SOLVED)
    assert [a.model for a in solver.attempts][-1] == "f"


async def test_with_fallback_off_no_other_model_is_tried(make_solver):
    primary = ScriptedModel([program("wrong", "p")])
    fallback = ScriptedModel([program("solved", "f")])
    solver = make_solver({"m": primary, "f": fallback}, max_repair_iterations=0)

    assert await solve(solver) is None
    assert fallback.drafts  # never asked


async def test_under_the_site_context_a_wrong_answer_is_told_too_high_or_low(make_solver, monkeypatch):
    # problem_context="aoc", as in every registered run; the page reads are scripted.
    from shared import problem_context

    monkeypatch.setattr(problem_context, "page_description", lambda y, d, p, description: description)
    monkeypatch.setattr(problem_context, "supplement", lambda y, d, p, part_one_code=None: "")
    monkeypatch.setattr(problem_context, "statement_examples", lambda y, d, p: None)
    model = ScriptedModel([program("wrong")], {program("wrong"): program("solved")})
    solver = make_solver({"m": model}, problem_context="aoc", example_tests="page")

    assert await solve(solver) == program("solved")
    assert trace(solver) == [("generate", 0, 0, Outcome.WRONG), ("repair", 1, 0, Outcome.SOLVED)]
    assert "Your answer 999 is too low." in model.feedback[0]
    assert ANSWER not in model.feedback[0]
