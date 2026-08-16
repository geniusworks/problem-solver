"""Learning-database write paths that were previously broken.

Each of these methods either did not exist or targeted columns that were not on
the table it queried, so any call raised at runtime. They were unreachable from
the default solve loop, which is why nothing surfaced them.
"""

import json

import pytest

from learning.database import LearningDatabase
from learning.optimizer import StrategyResultForProblem


@pytest.fixture
def db(tmp_path):
    return LearningDatabase(tmp_path)


def test_record_strategy_result_writes_to_strategy_results(db):
    """Previously queried model_performance.problem_id, a column that isn't there."""
    db.record_strategy_result(
        "2024_day01_part1",
        ["brute_force", "parsing"],
        True,
        {
            "execution_time": 1.5,
            "memory_usage": 100,
            "attempts": 2,
            "failure_points": ["timeout"],
        },
    )

    with db.connect() as conn:
        row = conn.execute(
            "SELECT problem_id, strategies_used, success, execution_time, attempts, "
            "failure_points FROM strategy_results"
        ).fetchone()

    assert row[0] == "2024_day01_part1"
    assert json.loads(row[1]) == ["brute_force", "parsing"]
    assert row[2] == 1
    assert row[3] == pytest.approx(1.5)
    assert row[4] == 2
    assert json.loads(row[5]) == ["timeout"]


def test_add_problem_result_round_trips(db):
    """StrategyOptimizer.record_problem_result called this missing method."""
    result = StrategyResultForProblem(
        problem_id="2024_day02_part1",
        strategies_used=["simulation"],
        success=False,
        execution_time=2.0,
        memory_usage=50.0,
        attempts=3,
        failure_points=["wrong answer"],
    )

    db.add_problem_result(result)

    with db.connect() as conn:
        row = conn.execute(
            "SELECT problem_id, success, attempts FROM strategy_results"
        ).fetchone()

    assert row == ("2024_day02_part1", 0, 3)


def test_record_improvement_writes_history(db):
    """BaseSolver's collaborative branch called this missing method."""
    db.record_improvement("2024_day03_part1", "gemma3", "collaborative", 0.42, iteration=1)

    with db.connect() as conn:
        row = conn.execute(
            "SELECT problem_id, iteration, model_name, improvement_type, impact_score "
            "FROM improvement_history"
        ).fetchone()

    assert row == ("2024_day03_part1", 1, "gemma3", "collaborative", pytest.approx(0.42))


class TestRunningSuccessRate:
    """success_rate was overwritten with each attempt's boolean, not accumulated."""

    def test_rate_accumulates_across_attempts(self, db):
        for success in [True, True, True, False, True]:
            db.update_model_performance("m1", {"quality_score": 6.0}, success=success)

        with db.connect() as conn:
            attempts, successes, rate = conn.execute(
                "SELECT attempts, successes, success_rate FROM model_performance "
                "WHERE model_name = 'm1'"
            ).fetchone()

        assert (attempts, successes) == (5, 4)
        assert rate == pytest.approx(0.8)

    def test_one_failure_does_not_erase_a_strong_record(self, db):
        """Previously a single failure zeroed the rate and dropped the model."""
        for _ in range(9):
            db.update_model_performance("m2", {"quality_score": 5.0}, success=True)
        db.update_model_performance("m2", {"quality_score": 5.0}, success=False)

        with db.connect() as conn:
            rate = conn.execute(
                "SELECT success_rate FROM model_performance WHERE model_name = 'm2'"
            ).fetchone()[0]

        assert rate == pytest.approx(0.9)
        assert rate >= 0.5, "model must survive the default min_success_rate filter"

    def test_avg_quality_is_a_running_mean(self, db):
        """avg_quality_score was set on INSERT and never updated again."""
        for quality in [2.0, 4.0, 6.0]:
            db.update_model_performance("m3", {"quality_score": quality}, success=True)

        with db.connect() as conn:
            avg, latest = conn.execute(
                "SELECT avg_quality_score, quality_score FROM model_performance "
                "WHERE model_name = 'm3'"
            ).fetchone()

        assert avg == pytest.approx(4.0)
        assert latest == pytest.approx(6.0)

    def test_fresh_database_has_no_model_performance_rows(self, db):
        """A measurement store starts empty -- init_db must not fabricate priors.

        It used to seed model_performance with an invented 0.5 success rate for a
        model that was never run (and whose name wasn't even a valid Ollama tag).
        Cold start is _get_top_models' fallback-to-installed-models, not fake data.
        """
        with db.connect() as conn:
            rows = conn.execute(
                "SELECT attempts, successes FROM model_performance"
            ).fetchall()

        assert rows == []

    def test_first_real_observation_replaces_the_prior(self, db):
        """Legacy rows (pre-migration or hand-seeded) hold a prior rate with zero
        counters; the first measured attempt must replace it outright."""
        model, role = "legacy-model:7b", "primary"
        with db.connect() as conn:
            conn.execute(
                "INSERT INTO model_performance (model_name, problem_type, role, "
                "success_rate, response_time, cost, quality_score, avg_quality_score) "
                "VALUES (?, 'general', ?, 0.5, 10.0, 0.0, 5.0, 5.0)",
                (model, role),
            )
            conn.commit()

        db.update_model_performance(model, {"quality_score": 5.0}, success=False, role=role)

        with db.connect() as conn:
            attempts, successes, rate = conn.execute(
                "SELECT attempts, successes, success_rate FROM model_performance "
                "WHERE model_name = ? AND role = ?",
                (model, role),
            ).fetchone()

        assert (attempts, successes) == (1, 0)
        assert rate == pytest.approx(0.0)


def test_optimizer_shares_the_learning_dir_database(tmp_path):
    """One database only: the optimizer must read the file the solver writes.

    It previously located its DB from workspace_dir, creating a second,
    always-empty ./solver.db -- so strategy effectiveness was computed over
    zero rows while the real performance data sat in learning/solver.db.
    """
    from learning.optimizer import StrategyOptimizer

    learning_dir = tmp_path / "learning"
    workspace_dir = tmp_path  # deliberately different from learning_dir

    optimizer = StrategyOptimizer(learning_dir, workspace_dir)

    assert optimizer.db.db_path == learning_dir / "solver.db"
    assert not (workspace_dir / "solver.db").exists(), (
        "constructing the optimizer must not create a second root database"
    )


def test_count_strategy_attempts_is_scoped_per_problem(db):
    db.record_strategy_result("2024_day01_part1", ["a"], True, {})
    db.record_strategy_result("2024_day01_part1", ["b"], False, {})
    db.record_strategy_result("2024_day05_part2", ["c"], True, {})

    assert db.count_strategy_attempts("2024_day01_part1") == 2
    assert db.count_strategy_attempts("2024_day05_part2") == 1
    assert db.count_strategy_attempts("2024_day09_part1") == 0
