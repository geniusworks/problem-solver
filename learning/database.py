"""Database management for the learning system."""

import json
import logging
import sqlite3
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Generator, List, Optional, Tuple

from .init_db import init_db

logger = logging.getLogger(__name__)

class LearningDatabase:
    """Manages database connections and operations for the learning system."""
    
    def __init__(self, db_dir: Optional[Path] = None) -> None:
        """Initialize the database manager.
        
        Args:
            db_dir: Directory containing the database. If None, uses the learning directory.
        """
        if db_dir is None:
            db_dir = Path(__file__).parent
        
        self.db_path = db_dir / "solver.db"
        
        # Create parent directory if needed
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Initialize if needed
        if not self.db_path.exists():
            logger.info("Database not found. Initializing at %s", self.db_path)
            schema_path = Path(__file__).parent / 'schema.sql'
            init_db(str(db_dir), db_path="solver.db", schema_path=str(schema_path))
        
        # Ensure schema migrations are applied (e.g., newly added columns)
        try:
            self._ensure_schema()
        except Exception as e:
            logger.warning("Schema check/update failed: %s", e)
    
    @contextmanager
    def connect(self) -> Generator[sqlite3.Connection, None, None]:
        """Get a database connection with automatic cleanup."""
        conn = sqlite3.connect(self.db_path)
        try:
            yield conn
        finally:
            conn.close()

    # Columns added after the original schema shipped, with their DDL.
    _MIGRATIONS = {
        "avg_quality_score": "REAL NOT NULL DEFAULT 0.0",
        # attempts/successes make success_rate a real running rate. Without them
        # success_rate was overwritten with 1.0/0.0 on every update, so it meant
        # "did the most recent attempt succeed" and a model that had succeeded
        # nine times was excluded from ranking after a single failure.
        "attempts": "INTEGER NOT NULL DEFAULT 0",
        "successes": "INTEGER NOT NULL DEFAULT 0",
    }

    def _ensure_schema(self) -> None:
        """Apply lightweight schema migrations if needed."""
        with self.connect() as conn:
            cursor = conn.cursor()
            cursor.execute("PRAGMA table_info(model_performance)")
            cols = {row[1] for row in cursor.fetchall()}

            added = False
            for column, ddl in self._MIGRATIONS.items():
                if column not in cols:
                    cursor.execute(
                        f"ALTER TABLE model_performance ADD COLUMN {column} {ddl}"
                    )
                    added = True

            if added:
                conn.commit()

            # Pre-migration rows keep attempts = successes = 0 on purpose.
            #
            # Their stored success_rate was a last-attempt boolean (or a synthetic
            # cold-start value from seed_model_performance), not a measured rate,
            # so backfilling counters from it would fabricate history -- a seeded
            # 0.5 would round into a perfect 1/1 record. Leaving the counters at
            # zero keeps success_rate as a prior estimate that the first real
            # observation replaces outright.
    
    def record_strategy_result(
        self,
        problem_id: str,
        strategies: List[str],
        success: bool,
        metrics: Dict[str, Any]
    ) -> None:
        """Record the result of applying strategies to a problem.

        Writes to strategy_results. The previous implementation targeted
        model_performance using problem_id/attempts/successes/last_attempt columns,
        none of which exist on that table, so any call raised OperationalError.
        """
        with self.connect() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO strategy_results
                    (problem_id, timestamp, strategies_used, success,
                     execution_time, memory_usage, attempts, failure_points,
                     generation_time, code_size)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    problem_id,
                    datetime.now().isoformat(),
                    json.dumps(list(strategies)),
                    bool(success),
                    metrics.get("execution_time"),
                    metrics.get("memory_usage"),
                    metrics.get("attempts"),
                    json.dumps(metrics.get("failure_points", [])),
                    metrics.get("generation_time"),
                    metrics.get("code_size"),
                ),
            )
            conn.commit()

    def record_improvement(
        self,
        problem_id: str,
        model_name: str,
        improvement_type: str,
        impact_score: float,
        iteration: int = 0,
    ) -> None:
        """Record a collaborative-improvement round in improvement_history.

        Called by BaseSolver's collaborative-improvement branch, which previously
        referenced this method although it did not exist.
        """
        with self.connect() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO improvement_history
                    (problem_id, iteration, model_name, improvement_type,
                     impact_score, timestamp)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    problem_id,
                    iteration,
                    model_name,
                    improvement_type,
                    impact_score,
                    datetime.now().isoformat(),
                ),
            )
            conn.commit()

    def count_strategy_attempts(self, problem_id: str) -> int:
        """Number of recorded strategy results for a problem."""
        with self.connect() as conn:
            cursor = conn.execute(
                "SELECT COUNT(*) FROM strategy_results WHERE problem_id = ?",
                (problem_id,),
            )
            row = cursor.fetchone()
            return int(row[0]) if row else 0

    def add_problem_result(self, result: Any) -> None:
        """Record a StrategyResultForProblem.

        Called by StrategyOptimizer.record_problem_result, which previously
        referenced this method although it did not exist.
        """
        timestamp = getattr(result, "timestamp", None) or datetime.now()
        if isinstance(timestamp, datetime):
            timestamp = timestamp.isoformat()

        with self.connect() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO strategy_results
                    (problem_id, timestamp, strategies_used, success,
                     execution_time, memory_usage, attempts, failure_points)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    result.problem_id,
                    timestamp,
                    json.dumps(list(result.strategies_used)),
                    bool(result.success),
                    result.execution_time,
                    result.memory_usage,
                    result.attempts,
                    json.dumps(list(result.failure_points or [])),
                ),
            )
            conn.commit()

    def update_model_performance(
        self,
        model_name: str,
        metrics: Dict[str, float],
        success: bool,
        problem_type: str = 'general',
        role: str = 'primary'
    ) -> None:
        """Update performance metrics for a model.
        
        Args:
            model_name: Name of the model
            metrics: Dictionary of metric names to values
            success: Whether the model succeeded at its task
            problem_type: Type of problem being solved
            role: Role of the model (primary, reviewer, etc.)
        """
        with self.connect() as conn:
            cursor = conn.cursor()
            
            # Check if model exists for this problem type and role
            cursor.execute(
                """SELECT model_name 
                   FROM model_performance 
                   WHERE model_name = ? AND problem_type = ? AND role = ?""",
                (model_name, problem_type, role)
            )
            exists = cursor.fetchone() is not None
            
            quality = float(metrics.get('quality_score', 0.0))

            if exists:
                # Accumulate counters and derive the rate from them, rather than
                # overwriting success_rate with this attempt's boolean. Also keep
                # avg_quality_score as a true running mean; it was previously set
                # only on INSERT and never updated.
                cursor.execute(
                    """UPDATE model_performance
                       SET attempts = attempts + 1,
                           successes = successes + ?,
                           success_rate = CAST(successes + ? AS REAL) / (attempts + 1),
                           avg_quality_score =
                               ((avg_quality_score * attempts) + ?) / (attempts + 1),
                           response_time = ?,
                           cost = ?,
                           quality_score = ?
                       WHERE model_name = ? AND problem_type = ? AND role = ?""",
                    (
                        int(success),
                        int(success),
                        quality,
                        metrics.get('response_time', 0.0),
                        metrics.get('cost', 0.0),
                        quality,
                        model_name,
                        problem_type,
                        role
                    )
                )
            else:
                # Insert new record
                cursor.execute(
                    """INSERT INTO model_performance
                       (model_name, problem_type, role, success_rate,
                        response_time, cost, quality_score, avg_quality_score,
                        attempts, successes)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        model_name,
                        problem_type,
                        role,
                        1.0 if success else 0.0,
                        metrics.get('response_time', 0.0),
                        metrics.get('cost', 0.0),
                        quality,
                        quality,  # Initial avg same as current
                        1,
                        int(success),
                    )
                )

            conn.commit()

    def store_result(
        self,
        problem_id: str,
        strategies: List[str],
        success: bool,
        metrics: Dict[str, float],
        attempts: int,
        failure_points: List[str]
    ) -> None:
        """Store a problem-solving attempt result."""
        with self.connect() as conn:
            cursor = conn.cursor()

            # Serialize failure points to a string
            failure_points_str = ",".join(failure_points)

            # Insert the result into the problem_results table
            cursor.execute(
                """
                INSERT INTO problem_results (
                    problem_id, strategies, success, execution_time, memory_usage, attempts, failure_points
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    problem_id,
                    ','.join(strategies),
                    success,
                    metrics.get('execution_time', 0.0),
                    metrics.get('memory_usage', 0.0),
                    attempts,
                    failure_points_str,
                ),
            )
            conn.commit()

    def get_similar_problems(self, problem_characteristics: Dict[str, float]) -> List[Dict[str, Any]]:
        """Get similar problems from the database based on characteristics."""
        # TODO: Implement similarity calculation and retrieval logic
        return []  # Placeholder implementation

    def get_strategy_weights(self) -> Dict[str, Dict[str, Any]]:
        """Get strategy weights from the database."""
        # TODO: Implement strategy weight retrieval logic
        return {}

    def update_strategy_weights(self, new_weights: Dict[str, Dict[str, Any]]) -> None:
        """Update strategy weights in the database."""
        # TODO: Implement strategy weight update logic
        pass

    def get_top_models(self, problem_type: str, role: str, limit: int = 3, min_success_rate: float = 0.5) -> List[str]:
        """Get top performing models for a specific problem type and role.
        
        Args:
            problem_type: Type of problem (e.g., 'general', 'math', etc.)
            role: Role of the model (e.g., 'primary', 'reviewer')
            limit: Maximum number of models to return
            min_success_rate: Minimum success rate required
            
        Returns:
            List of model names
        """
        with self.connect() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT model_name, success_rate
                FROM model_performance
                WHERE problem_type = ? AND role = ? AND success_rate >= ?
                ORDER BY success_rate DESC
                LIMIT ?
                """,
                (problem_type, role, min_success_rate, limit)
            )
            results = cursor.fetchall()
            return [row[0] for row in results] if results else []
