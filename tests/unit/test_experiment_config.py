"""SolverConfig is the unit of comparison between experiments."""

import pytest

from shared.experiment import Outcome, SolverConfig
from shared.experiment.results import AttemptRecord, ExperimentResult, ProblemResult


class TestFingerprint:
    def test_identical_configs_share_a_fingerprint(self):
        assert SolverConfig().fingerprint() == SolverConfig().fingerprint()

    def test_behaviour_change_changes_the_fingerprint(self):
        base = SolverConfig()
        assert base.with_overrides(max_repair_iterations=5).fingerprint() != base.fingerprint()
        assert base.with_overrides(consensus_on="code").fingerprint() != base.fingerprint()
        assert base.with_overrides(samples_per_model=3).fingerprint() != base.fingerprint()

    def test_renaming_does_not_change_the_fingerprint(self):
        """Otherwise a rename looks like a different experiment."""
        base = SolverConfig(name="a", notes="first run")
        renamed = base.with_overrides(name="b", notes="second run")

        assert renamed.fingerprint() == base.fingerprint()

    def test_model_order_is_significant(self):
        a = SolverConfig(models=("x", "y"))
        b = SolverConfig(models=("y", "x"))

        assert a.fingerprint() != b.fingerprint()


class TestValidation:
    @pytest.mark.parametrize(
        "kwargs",
        [
            {"consensus_on": "vibes"},
            {"consensus_threshold": 0.0},
            {"consensus_threshold": 1.5},
            {"samples_per_model": 0},
            {"max_repair_iterations": -1},
            {"max_primary_models": 0},
        ],
    )
    def test_invalid_values_are_rejected(self, kwargs):
        with pytest.raises(ValueError):
            SolverConfig(**kwargs)

    def test_is_immutable(self):
        config = SolverConfig()
        with pytest.raises(Exception):
            config.max_repair_iterations = 9  # type: ignore[misc]


class TestFromEnv:
    def test_reads_historical_env_flags(self, monkeypatch):
        monkeypatch.setenv("MAX_REPAIR_ITERATIONS", "7")
        monkeypatch.setenv("ENABLE_COLLABORATIVE_IMPROVEMENT", "true")
        monkeypatch.setenv("SOLVER_MODELS", "a:7b, b:7b")

        config = SolverConfig.from_env()

        assert config.max_repair_iterations == 7
        assert config.enable_collaborative_improvement is True
        assert config.models == ("a:7b", "b:7b")

    def test_explicit_overrides_win(self, monkeypatch):
        monkeypatch.setenv("MAX_REPAIR_ITERATIONS", "7")

        assert SolverConfig.from_env(max_repair_iterations=1).max_repair_iterations == 1

    def test_malformed_int_falls_back_to_default(self, monkeypatch):
        monkeypatch.setenv("MAX_REPAIR_ITERATIONS", "not-a-number")

        assert SolverConfig.from_env().max_repair_iterations == 2

    def test_defaults_are_safe(self, monkeypatch):
        for var in ("MAX_REPAIR_ITERATIONS", "ENABLE_COLLABORATIVE_IMPROVEMENT",
                    "SOLVER_MODELS", "SUBMIT_SOLUTIONS", "REFERENCE_MODEL"):
            monkeypatch.delenv(var, raising=False)

        config = SolverConfig.from_env()

        assert config.submit_solutions is False
        assert config.require_oracle is True
        assert config.reference_model is None


def _attempt(outcome: Outcome, model: str = "m") -> AttemptRecord:
    return AttemptRecord(
        model=model, problem_id="2024_day01_part1", config_fingerprint="abc",
        outcome=outcome,
    )


class TestMetrics:
    def test_unverified_is_not_counted_as_solved(self):
        """The distinction the pre-oracle pipeline collapsed."""
        results = [
            ProblemResult("p1", 2024, 1, 1, "abc", outcome=Outcome.SOLVED),
            ProblemResult("p2", 2024, 2, 1, "abc", outcome=Outcome.UNVERIFIED),
            ProblemResult("p3", 2024, 3, 1, "abc", outcome=Outcome.WRONG),
        ]
        experiment = ExperimentResult("c", "abc", {}, results)

        assert experiment.solved == 1
        assert experiment.solve_rate == pytest.approx(1 / 3)
        assert experiment.claimed_minus_verified == 2

    def test_attempts_to_solve_finds_the_first_success(self):
        result = ProblemResult(
            "p1", 2024, 1, 1, "abc", outcome=Outcome.SOLVED,
            attempts=[
                _attempt(Outcome.WRONG, "a"),
                _attempt(Outcome.WRONG, "b"),
                _attempt(Outcome.SOLVED, "c"),
            ],
        )

        assert result.attempts_to_solve == 3
        assert result.first_try is False

    def test_first_try_rate_is_over_solved_problems(self):
        solved_first = ProblemResult(
            "p1", 2024, 1, 1, "abc", outcome=Outcome.SOLVED,
            attempts=[_attempt(Outcome.SOLVED)],
        )
        solved_late = ProblemResult(
            "p2", 2024, 2, 1, "abc", outcome=Outcome.SOLVED,
            attempts=[_attempt(Outcome.WRONG), _attempt(Outcome.SOLVED)],
        )
        never = ProblemResult("p3", 2024, 3, 1, "abc", outcome=Outcome.NO_CANDIDATE)
        experiment = ExperimentResult("c", "abc", {}, [solved_first, solved_late, never])

        assert experiment.first_try_rate == pytest.approx(0.5)

    def test_unsolved_problem_has_no_attempts_to_solve(self):
        result = ProblemResult(
            "p1", 2024, 1, 1, "abc", outcome=Outcome.WRONG,
            attempts=[_attempt(Outcome.WRONG)],
        )

        assert result.attempts_to_solve is None
        assert result.first_try is False

    def test_empty_experiment_does_not_divide_by_zero(self):
        experiment = ExperimentResult("c", "abc", {}, [])

        assert experiment.solve_rate == 0.0
        assert experiment.first_try_rate == 0.0
        assert experiment.mean_attempts_to_solve is None

    def test_replay_material_is_excluded_by_default(self):
        attempt = _attempt(Outcome.SOLVED)
        attempt.prompt = "a very long prompt"
        attempt.code = "def solve(): ..."

        assert "prompt" not in attempt.to_dict()
        assert "prompt" in attempt.to_dict(include_replay=True)

    def test_save_round_trips(self, tmp_path):
        import json

        experiment = ExperimentResult(
            "c", "abc", SolverConfig().to_dict(),
            [ProblemResult("p1", 2024, 1, 1, "abc", outcome=Outcome.SOLVED)],
        )
        path = experiment.save(tmp_path / "run.json")

        data = json.loads(path.read_text())
        assert data["summary"]["solved"] == 1
        assert data["results"][0]["outcome"] == "solved"
