import types

import pytest

import shared.solver as solver_module
from shared.strategies import get_strategies_for_problem


def _make_solver(tmp_path) -> solver_module.BaseSolver:
    solver = solver_module.BaseSolver.__new__(solver_module.BaseSolver)  # type: ignore[arg-type]
    solver.workspace_dir = tmp_path
    solver.learning_dir = tmp_path / "learning"
    solver.learning_dir.mkdir(parents=True, exist_ok=True)
    solver.db = None
    # Seed models with the names that our FakeLearningDatabase returns so
    # that _get_top_models will keep them after filtering by availability.
    solver.models = {
        "grid-model-1": object(),
        "math-model-1": object(),
        "general-model-1": object(),
    }
    return solver


class DummyParsedProblem:
    def __init__(self, description: str, example_input: str = "example") -> None:
        self.description = description
        self.examples = [types.SimpleNamespace(input_data=example_input)]
        self.test_cases = []


def test_grid_like_description_classified_as_grid(tmp_path):
    solver = _make_solver(tmp_path)
    problem = DummyParsedProblem("You are given a grid of numbers and must traverse the grid.")

    characteristics = solver._analyze_problem_characteristics(problem)
    problem_type = solver._get_problem_type(characteristics)

    assert problem_type == "grid"


def test_graph_like_description_classified_as_graph(tmp_path):
    solver = _make_solver(tmp_path)
    problem = DummyParsedProblem("Find a path in the graph from start to end.")

    characteristics = solver._analyze_problem_characteristics(problem)
    problem_type = solver._get_problem_type(characteristics)

    assert problem_type == "graph"


def test_math_like_description_classified_as_math(tmp_path):
    solver = _make_solver(tmp_path)
    problem = DummyParsedProblem("Calculate the result using this formula.")

    characteristics = solver._analyze_problem_characteristics(problem)
    problem_type = solver._get_problem_type(characteristics)

    assert problem_type == "math"


def test_string_processing_description_classified_as_string(tmp_path):
    solver = _make_solver(tmp_path)
    problem = DummyParsedProblem("Process the string input and count occurrences of text patterns.")

    characteristics = solver._analyze_problem_characteristics(problem)
    problem_type = solver._get_problem_type(characteristics)

    assert problem_type == "string"


def test_optimization_description_classified_as_optimization(tmp_path):
    solver = _make_solver(tmp_path)
    problem = DummyParsedProblem("Find the minimum and maximum values to optimize the score.")

    characteristics = solver._analyze_problem_characteristics(problem)
    problem_type = solver._get_problem_type(characteristics)

    assert problem_type == "optimization"


def test_get_strategies_for_problem_returns_non_empty_and_varies_by_text():
    grid_text = "You are given a grid of numbers and must traverse the grid."
    math_text = "Calculate the sum of values using a complex formula."

    grid_strategies = get_strategies_for_problem(grid_text)
    math_strategies = get_strategies_for_problem(math_text)

    assert grid_strategies
    assert math_strategies
    assert set(grid_strategies) != set(math_strategies)


class FakeLearningDatabase:
    def __init__(self, db_dir) -> None:  # type: ignore[override]
        self.db_dir = db_dir

    def get_top_models(self, problem_type: str, role: str, limit: int = 3, min_success_rate: float = 0.5):  # type: ignore[override]
        if problem_type == "grid":
            return ["grid-model-1"]
        if problem_type == "math":
            return ["math-model-1"]
        return ["general-model-1"]


def test_grid_problem_uses_grid_specific_top_models(monkeypatch, tmp_path):
    monkeypatch.setattr(solver_module, "LearningDatabase", FakeLearningDatabase)

    solver = _make_solver(tmp_path)
    problem = DummyParsedProblem("You are given a grid of numbers and must traverse the grid.")

    characteristics = solver._analyze_problem_characteristics(problem)
    problem_type = solver._get_problem_type(characteristics)

    models = solver._get_top_models(problem_type, "primary", limit=2)

    assert models == ["grid-model-1"]


def test_math_problem_uses_math_specific_top_models(monkeypatch, tmp_path):
    monkeypatch.setattr(solver_module, "LearningDatabase", FakeLearningDatabase)

    solver = _make_solver(tmp_path)
    problem = DummyParsedProblem("Calculate the result using this formula.")

    characteristics = solver._analyze_problem_characteristics(problem)
    problem_type = solver._get_problem_type(characteristics)

    models = solver._get_top_models(problem_type, "primary", limit=2)

    assert models == ["math-model-1"]


class TestStrategyLookupNeverCrashesTheSolve:
    """`get_strategies_for_problem` must never raise on real problem text.

    CATEGORY_KEYWORDS can select a category that has no entry in
    SOLUTION_STRATEGIES (GRAPH, STATE_MACHINE and OPTIMIZATION have keywords but
    no strategies). The lookup used to be an unguarded SOLUTION_STRATEGIES[cat],
    so those categories raised KeyError out of _prepare_problem and failed the
    whole problem before the model was ever called -- a harness crash recorded
    as a model failure. 2024 d8 hit it on both parts because "antinode"
    substring-matches the GRAPH keyword "node".
    """

    def test_every_keyword_matchable_category_is_survivable(self):
        from shared.strategies import CATEGORY_KEYWORDS, SOLUTION_STRATEGIES

        for category, keywords in CATEGORY_KEYWORDS.items():
            # Text saturated with one category's keywords forces it to win.
            text = " ".join(keywords * 5)
            result = get_strategies_for_problem(text)  # must not raise
            assert isinstance(result, list)
            if category not in SOLUTION_STRATEGIES:
                # No strategies defined -> contributes nothing, quietly.
                assert all(isinstance(name, str) for name in result)

    def test_graph_wording_does_not_raise(self):
        """The exact shape that killed 2024 d8: 'antinode' contains 'node'."""
        text = (
            "Each antinode occurs at a point perfectly in line with two antennas. "
            "Count the antinode locations within the bounds of the map."
        )
        assert isinstance(get_strategies_for_problem(text), list)

    def test_optimization_wording_does_not_raise(self):
        """OPTIMIZATION keywords ('minimize', 'best', 'fewest_steps') are common AoC words."""
        text = "Find the best route that will minimize the cost and use the fewest steps."
        assert isinstance(get_strategies_for_problem(text), list)
