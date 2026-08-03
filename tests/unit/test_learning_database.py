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


def test_count_strategy_attempts_is_scoped_per_problem(db):
    db.record_strategy_result("2024_day01_part1", ["a"], True, {})
    db.record_strategy_result("2024_day01_part1", ["b"], False, {})
    db.record_strategy_result("2024_day05_part2", ["c"], True, {})

    assert db.count_strategy_attempts("2024_day01_part1") == 2
    assert db.count_strategy_attempts("2024_day05_part2") == 1
    assert db.count_strategy_attempts("2024_day09_part1") == 0
