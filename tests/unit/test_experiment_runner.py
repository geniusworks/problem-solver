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
    drop_parts_without_puzzle,
    run_experiment,
    with_part_one_prerequisites,
    parse_problem_set,
    problem_id,
    run_problem,
)
from shared.experiment.results import ExperimentResult, ProblemResult
from shared.ground_truth import html_part_has_puzzle


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
    async def test_solver_exception_is_a_harness_error_not_a_model_failure(self):
        """One failing problem must not abort the sweep, and must not be
        scored against the model (dev/progress/strategy-keyerror-d8.md)."""
        solver = _StubSolver(raises=RuntimeError("ollama is down"))

        result = await run_problem(solver, 2024, 1, 1, SolverConfig())

        assert result.outcome is Outcome.HARNESS_ERROR
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


class TestResultsSurviveAStoppedRun:
    async def test_each_result_is_on_disk_before_the_next_starts(self, monkeypatch, tmp_path):
        import json
        import shared.solver as solver_module
        import shared.experiment.runner as runner

        path = tmp_path / "run.json"
        on_disk = []

        def report(result):
            saved = json.loads(path.read_text())
            on_disk.append((len(saved["results"]), saved["finished_at"]))

        monkeypatch.setattr(solver_module, "BaseSolver", _CountingSolver)
        monkeypatch.setattr(runner, "get_known_answer", lambda y, d, p: "42")

        exp = await runner.run_experiment(
            [(2024, 1, 1), (2024, 2, 1)], SolverConfig(), Path("."),
            trials=2, on_result=report, save_to=path,
        )

        assert on_disk == [(1, None), (2, None), (3, None), (4, None)]
        final = json.loads(path.read_text())
        assert len(final["results"]) == 4
        assert final["finished_at"] == exp.finished_at is not None
        assert not list(tmp_path.glob("*.partial"))

    async def test_a_run_stopped_mid_way_leaves_what_it_finished(self, monkeypatch, tmp_path):
        import json
        import shared.solver as solver_module
        import shared.experiment.runner as runner

        path = tmp_path / "run.json"

        class Stopped(Exception):
            pass

        def stop_after_three(result):
            if len(json.loads(path.read_text())["results"]) == 3:
                raise Stopped

        monkeypatch.setattr(solver_module, "BaseSolver", _CountingSolver)
        monkeypatch.setattr(runner, "get_known_answer", lambda y, d, p: "42")

        with pytest.raises(Stopped):
            await runner.run_experiment(
                [(2024, 1, 1), (2024, 2, 1)], SolverConfig(), Path("."),
                trials=2, on_result=stop_after_three, save_to=path,
            )

        saved = json.loads(path.read_text())
        assert len(saved["results"]) == 3
        assert saved["finished_at"] is None


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
            "trials": 1, "scored": 1, "solved": 1, "solve_rate": 1.0,
            "stable": True, "outcomes": ["solved"], "expected": "42",
        }


class TestPartsWithoutAPuzzle:
    """An event's last day may have one puzzle; its "Part Two" is not a problem.

    The harness attempted it and scored a `no_candidate`, so a scan printed 9/20
    for what was 9/19 (2024 d25), and an earlier one 16/24 for 16/23 (2025 d12).
    Which day is the last one varies by year, so detection reads the page.
    """

    FINISH_FORM = (
        '<article class="day-desc"><h2>--- Day 25 ---</h2></article>'
        "<p>Your puzzle answer was <code>3663</code>.</p>"
        '<article class="day-desc"><h2 id="part2">--- Part Two ---</h2></article>'
        '<form method="post" action="25/answer">'
        '<input type="hidden" name="level" value="2"/>'
        '<input type="hidden" name="answer" value="0"/>'
        '<p>If you like, you can <input type="submit" value="[{label}]"/>.</p></form>'
    )
    OPEN_PART_TWO = (
        '<article class="day-desc"><h2>--- Day 3 ---</h2></article>'
        "<p>Your puzzle answer was <code>42</code>.</p>"
        '<article class="day-desc"><h2 id="part2">--- Part Two ---</h2></article>'
        '<form method="post" action="3/answer">'
        '<input type="hidden" name="level" value="2"/>'
        '<p>Answer: <input type="text" name="answer" autocomplete="off"/>'
        '<input type="submit" value="[Submit]"/></p></form>'
    )
    SOLVED_PART_TWO = (
        '<article class="day-desc"><h2>--- Day 3 ---</h2></article>'
        "<p>Your puzzle answer was <code>42</code>.</p>"
        '<article class="day-desc"><h2 id="part2">--- Part Two ---</h2></article>'
        "<p>Your puzzle answer was <code>43</code>.</p>"
    )

    @pytest.mark.parametrize("label", ["Finish", "Deliver The Chronicle Again"])
    def test_finish_button_part_two_is_not_a_puzzle(self, label):
        assert not html_part_has_puzzle(self.FINISH_FORM.format(label=label), 2)

    def test_part_one_of_a_single_puzzle_day_is_a_puzzle(self):
        assert html_part_has_puzzle(self.FINISH_FORM.format(label="Finish"), 1)

    def test_unsolved_part_two_is_a_puzzle(self):
        assert html_part_has_puzzle(self.OPEN_PART_TWO, 2)

    def test_solved_part_two_is_a_puzzle(self):
        assert html_part_has_puzzle(self.SOLVED_PART_TWO, 2)

    def test_problem_set_drops_only_the_missing_part(self, monkeypatch):
        monkeypatch.setattr(
            "shared.experiment.runner.part_has_puzzle",
            lambda year, day, part: (day, part) != (25, 2),
        )
        kept, dropped = drop_parts_without_puzzle(parse_problem_set("2024:24-25"))
        assert kept == [(2024, 24, 1), (2024, 24, 2), (2024, 25, 1)]
        assert dropped == [(2024, 25, 2)]

    def test_uncached_page_is_assumed_to_be_a_puzzle(self, tmp_path, monkeypatch):
        monkeypatch.setattr("shared.ground_truth.get_problem_dir", lambda y, d: tmp_path)
        from shared.ground_truth import part_has_puzzle

        assert part_has_puzzle(2099, 25, 2)


class TestPartTwoFollowsPartOne:
    """The site shows Part Two only to a solver who has just solved Part One.

    Every run before 2026-10-13 posed Part Two cold
    (dev/progress/part2-prompt-omits-part1.md).
    """

    def test_a_lone_part_two_gains_its_part_one_first(self):
        assert with_part_one_prerequisites([(2024, 19, 2), (2024, 16, 1)]) == [
            (2024, 19, 1), (2024, 19, 2), (2024, 16, 1),
        ]

    @staticmethod
    def _patch(monkeypatch, part_one_outcomes):
        """run_experiment over a stub: Part One outcomes are scripted per trial."""
        import shared.experiment.runner as runner
        import shared.solver as solver_module
        from shared.experiment.results import AttemptRecord

        seen = []

        class _Solver:
            def __init__(self, *a, **k):
                self.part_one_programs = {}

        async def fake_run_problem(solver, year, day, part, config, force=True, trial=0):
            outcome = part_one_outcomes[trial] if part == 1 else Outcome.SOLVED
            seen.append((trial, part, dict(solver.part_one_programs)))
            result = ProblemResult(
                problem_id=problem_id(year, day, part), year=year, day=day, part=part,
                config_fingerprint=config.fingerprint(), trial=trial, outcome=outcome,
            )
            result.attempts.append(AttemptRecord(
                model="m", problem_id=result.problem_id,
                config_fingerprint=config.fingerprint(), outcome=outcome,
                code=f"# part {part} trial {trial}",
            ))
            return result

        monkeypatch.setattr(solver_module, "BaseSolver", _Solver)
        monkeypatch.setattr(runner, "run_problem", fake_run_problem)
        monkeypatch.setattr(runner, "part_has_puzzle", lambda *a: True)
        monkeypatch.setattr(runner, "get_known_answer", lambda *a: "42")
        return seen

    async def test_part_two_is_not_reached_when_the_trial_missed_part_one(self, monkeypatch, tmp_path):
        seen = self._patch(monkeypatch, [Outcome.WRONG, Outcome.SOLVED])

        exp = await run_experiment([(2024, 19, 2)], SolverConfig(), tmp_path, trials=2)

        outcomes = [(r.trial, r.part, r.outcome) for r in exp.results]
        assert outcomes == [
            (0, 1, Outcome.WRONG), (0, 2, Outcome.NOT_REACHED),
            (1, 1, Outcome.SOLVED), (1, 2, Outcome.SOLVED),
        ]
        # Part Two was posed once, with that trial's own Part One program.
        assert [s for s in seen if s[1] == 2] == [(1, 2, {(2024, 19): "# part 1 trial 1"})]
        # A Part Two that was never posed is in no denominator.
        assert (exp.attempted, exp.solved, exp.not_reached) == (3, 2, 1)
        per = exp.per_problem()["2024_day19_part2"]
        assert (per["trials"], per["scored"], per["solve_rate"]) == (2, 1, 1.0)

    async def test_legacy_context_poses_part_two_cold_as_before(self, monkeypatch, tmp_path):
        self._patch(monkeypatch, [Outcome.WRONG])
        legacy = SolverConfig(problem_context="legacy")

        exp = await run_experiment([(2024, 19, 2)], legacy, tmp_path)

        assert [(r.part, r.outcome) for r in exp.results] == [(2, Outcome.SOLVED)]

    def test_harness_errors_are_in_no_denominator(self):
        results = [
            ProblemResult("p", 2024, 1, 1, "fp", outcome=Outcome.SOLVED),
            ProblemResult("q", 2024, 2, 1, "fp", outcome=Outcome.HARNESS_ERROR),
        ]
        exp = ExperimentResult("c", "fp", {}, results)
        assert (exp.attempted, exp.harness_errors, exp.solve_rate) == (1, 1, 1.0)
