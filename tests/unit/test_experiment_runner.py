"""The runner verifies independently of the solver.

If the solver's acceptance logic is wrong, that must surface as a claimed/verified
gap rather than as an inflated solve rate -- which is exactly how the pre-oracle
pipeline reported three wrong answers as validated solutions.
"""

import pytest

from shared.experiment import Outcome, SolverConfig
from shared.experiment.runner import (
    compare,
    parse_problem_set,
    problem_id,
    run_problem,
)
from shared.experiment.results import ExperimentResult, ProblemResult


class TestParseProblemSet:
    def test_day_range_expands_to_both_parts(self):
        assert parse_problem_set("2024:1-3") == [
            (2024, 1, 1), (2024, 1, 2),
            (2024, 2, 1), (2024, 2, 2),
            (2024, 3, 1), (2024, 3, 2),
        ]

    def test_single_day_expands_to_both_parts(self):
        assert parse_problem_set("2024:5") == [(2024, 5, 1), (2024, 5, 2)]

    def test_explicit_part(self):
        assert parse_problem_set("2024:3.2") == [(2024, 3, 2)]

    def test_comma_separated_mix(self):
        assert parse_problem_set("2024:1.1, 2023:7.2") == [(2024, 1, 1), (2023, 7, 2)]

    def test_malformed_spec_is_rejected(self):
        with pytest.raises(ValueError):
            parse_problem_set("2024")

    def test_problem_id_is_zero_padded(self):
        assert problem_id(2024, 3, 1) == "2024_day03_part1"


class _StubSolver:
    """Stands in for BaseSolver; returns whatever it was constructed with."""

    def __init__(self, result=None, raises=None):
        self._result = result
        self._raises = raises
        self.calls = []

    async def solve_problem(self, year, day, part, force=False):
        self.calls.append((year, day, part, force))
        if self._raises:
            raise self._raises
        return self._result


class TestRunProblem:
    async def test_solver_exception_becomes_an_error_outcome(self):
        """One failing problem must not abort the sweep."""
        solver = _StubSolver(raises=RuntimeError("ollama is down"))

        result = await run_problem(solver, 2024, 1, 1, SolverConfig())

        assert result.outcome is Outcome.ERROR
        assert "ollama is down" in result.attempts[0].error

    async def test_no_candidate_when_solver_returns_none(self):
        result = await run_problem(_StubSolver(result=None), 2024, 1, 1, SolverConfig())

        assert result.outcome is Outcome.NO_CANDIDATE

    async def test_wrong_answer_is_recorded_as_wrong_not_solved(self, monkeypatch):
        """The claim/verify split: the solver returned it, the oracle rejects it."""
        import shared.experiment.runner as runner

        monkeypatch.setattr(runner, "get_known_answer", lambda y, d, p: "476")
        solver = _StubSolver(result="86")  # bare answer, reuse path

        result = await run_problem(solver, 2024, 2, 2, SolverConfig())

        assert result.outcome is Outcome.WRONG
        assert result.answer == "86"
        assert result.expected == "476"

    async def test_matching_answer_is_solved(self, monkeypatch):
        import shared.experiment.runner as runner

        monkeypatch.setattr(runner, "get_known_answer", lambda y, d, p: "476")

        result = await run_problem(_StubSolver(result="476"), 2024, 2, 2, SolverConfig())

        assert result.outcome is Outcome.SOLVED

    async def test_answer_without_ground_truth_is_unverified(self, monkeypatch):
        import shared.experiment.runner as runner

        monkeypatch.setattr(runner, "get_known_answer", lambda y, d, p: None)

        result = await run_problem(_StubSolver(result="12345"), 2024, 9, 1, SolverConfig())

        assert result.outcome is Outcome.UNVERIFIED
        assert result.outcome is not Outcome.SOLVED

    async def test_wall_clock_is_recorded(self):
        result = await run_problem(_StubSolver(result=None), 2024, 1, 1, SolverConfig())

        assert result.wall_clock_seconds >= 0.0

    async def test_config_fingerprint_is_attached(self):
        config = SolverConfig(name="x", max_repair_iterations=4)

        result = await run_problem(_StubSolver(result=None), 2024, 1, 1, config)

        assert result.config_fingerprint == config.fingerprint()
        assert result.attempts[0].config_fingerprint == config.fingerprint()


class TestCompare:
    def test_renders_a_row_per_config(self):
        a = ExperimentResult("baseline", "aaa", {}, [
            ProblemResult("p1", 2024, 1, 1, "aaa", outcome=Outcome.SOLVED),
        ])
        b = ExperimentResult("wide", "bbb", {}, [
            ProblemResult("p1", 2024, 1, 1, "bbb", outcome=Outcome.WRONG),
        ])

        table = compare([a, b])

        assert "baseline" in table and "wide" in table
        assert "aaa" in table and "bbb" in table

    def test_handles_no_experiments(self):
        assert compare([]) == "(no experiments)"
