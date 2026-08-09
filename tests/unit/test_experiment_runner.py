"""The runner verifies independently of the solver.

If the solver's acceptance logic is wrong, that must surface as a claimed/verified
gap rather than as an inflated solve rate -- which is exactly how the pre-oracle
pipeline reported three wrong answers as validated solutions.
"""

from pathlib import Path

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


class _TracingSolver:
    """Exposes a per-model trace, as BaseSolver does."""

    def __init__(self, trace, result):
        self.attempts = []
        self._trace = trace
        self._result = result

    async def solve_problem(self, year, day, part, force=False):
        from shared.experiment.results import AttemptRecord

        for model, outcome in self._trace:
            self.attempts.append(
                AttemptRecord(
                    model=model, problem_id="p", config_fingerprint="f", outcome=outcome
                )
            )
        return self._result


class TestAttemptTrace:
    """attempts_to_solve is meaningless unless the real per-model trace is used."""

    async def test_trace_drives_attempts_to_solve(self, monkeypatch):
        import shared.experiment.runner as runner

        monkeypatch.setattr(runner, "get_known_answer", lambda y, d, p: "476")
        solver = _TracingSolver(
            [("a", Outcome.WRONG), ("b", Outcome.NO_CANDIDATE), ("c", Outcome.SOLVED)],
            result="476",
        )

        result = await runner.run_problem(solver, 2024, 2, 2, SolverConfig())

        assert result.attempts_to_solve == 3
        assert result.first_try is False
        assert result.winning_model == "c"

    async def test_first_try_when_the_first_model_wins(self, monkeypatch):
        import shared.experiment.runner as runner

        monkeypatch.setattr(runner, "get_known_answer", lambda y, d, p: "476")
        solver = _TracingSolver([("a", Outcome.SOLVED)], result="476")

        result = await runner.run_problem(solver, 2024, 2, 2, SolverConfig())

        assert result.first_try is True
        assert result.winning_model == "a"

    async def test_unverified_claim_is_downgraded(self, monkeypatch):
        """A solver bug must surface as a gap, not as an inflated solve rate."""
        import shared.experiment.runner as runner

        monkeypatch.setattr(runner, "get_known_answer", lambda y, d, p: "476")
        solver = _TracingSolver([("overconfident", Outcome.SOLVED)], result="86")

        result = await runner.run_problem(solver, 2024, 2, 2, SolverConfig())

        assert result.outcome is Outcome.WRONG
        assert result.attempts[0].outcome is Outcome.WRONG
        assert "claim not verified" in result.attempts[0].error
        assert result.attempts_to_solve is None
        assert result.winning_model is None

    async def test_solver_without_a_trace_still_works(self, monkeypatch):
        """Test doubles and older solvers expose no .attempts."""
        import shared.experiment.runner as runner

        monkeypatch.setattr(runner, "get_known_answer", lambda y, d, p: "476")

        result = await runner.run_problem(
            _StubSolver(result="476"), 2024, 2, 2, SolverConfig()
        )

        assert result.outcome is Outcome.SOLVED
        assert len(result.attempts) == 1


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


class TestTrialStamping:
    async def test_run_problem_stamps_trial_index(self):
        result = await run_problem(_StubSolver(result=None), 2024, 1, 1, SolverConfig(), trial=3)

        assert result.trial == 3
        assert result.attempts[0].sample_index == 3


class _CountingSolver:
    """Solves day 1 always, day 2 on alternating trials, day 3 never."""

    def __init__(self, *a, **k):
        self.attempts = []
        self._seen = {}

    async def solve_problem(self, year, day, part, force=False):
        self.attempts = []
        n = self._seen.get(day, 0)
        self._seen[day] = n + 1
        if day == 1:
            return "42"
        if day == 2:
            return "42" if n % 2 == 0 else "99"  # flips
        return None


class TestRunExperimentTrials:
    async def test_trials_produce_n_results_per_problem(self, monkeypatch):
        import shared.solver as solver_module
        import shared.experiment.runner as runner

        monkeypatch.setattr(solver_module, "BaseSolver", _CountingSolver)
        monkeypatch.setattr(runner, "get_known_answer", lambda y, d, p: "42")

        exp = await runner.run_experiment(
            [(2024, 1, 1), (2024, 2, 1), (2024, 3, 1)],
            SolverConfig(), Path("."), trials=4,
        )

        assert exp.trials == 4
        assert exp.attempted == 12          # 3 problems x 4 trials
        assert exp.distinct_problems == 3

        per = exp.per_problem()
        assert per["2024_day01_part1"]["solved"] == 4
        assert per["2024_day01_part1"]["stable"] is True
        assert per["2024_day02_part1"]["solved"] == 2   # alternates
        assert per["2024_day02_part1"]["stable"] is False
        assert per["2024_day03_part1"]["solved"] == 0

        assert exp.solved_at_least_once == 2   # days 1 and 2
        assert exp.solved_every_time == 1      # only day 1


class TestTrialAggregation:
    def _result(self, pid, outcome, trial):
        from shared.experiment.results import ProblemResult
        return ProblemResult(pid, 2024, 1, 1, "fp", outcome=outcome, trial=trial,
                             expected="42")

    def test_solve_rate_is_over_all_trials(self):
        from shared.experiment.results import ExperimentResult
        results = [
            self._result("p1", Outcome.SOLVED, 0),
            self._result("p1", Outcome.NO_CANDIDATE, 1),
        ]
        exp = ExperimentResult("c", "fp", {}, results, trials=2)

        assert exp.solve_rate == pytest.approx(0.5)  # 1 of 2 trials
        assert exp.distinct_problems == 1
        assert exp.solved_at_least_once == 1
        assert exp.solved_every_time == 0

    def test_single_trial_still_reports_cleanly(self):
        from shared.experiment.results import ExperimentResult
        exp = ExperimentResult("c", "fp", {}, [self._result("p1", Outcome.SOLVED, 0)], trials=1)

        per = exp.per_problem()["p1"]
        assert per == {
            "trials": 1, "solved": 1, "solve_rate": 1.0,
            "stable": True, "outcomes": ["solved"], "expected": "42",
        }
