"""Database management for the learning system."""

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

    def _ensure_schema(self) -> None:
        """Apply lightweight schema migrations if needed.
        Currently ensures 'avg_quality_score' exists on model_performance.
        """
        with self.connect() as conn:
            cursor = conn.cursor()
            # Inspect model_performance columns
            cursor.execute("PRAGMA table_info(model_performance)")
            cols = {row[1] for row in cursor.fetchall()}
            
            # Add missing avg_quality_score column if absent
            if 'avg_quality_score' not in cols:
                cursor.execute(
                    "ALTER TABLE model_performance ADD COLUMN avg_quality_score REAL NOT NULL DEFAULT 0.0"
                )
                conn.commit()
    
    def record_strategy_result(
        self,
        problem_id: str,
        strategies: List[str],
        success: bool,
        metrics: Dict[str, Any]
    ) -> None:
        """Record the result of applying strategies to a problem."""
        with self.connect() as conn:
            cursor = conn.cursor()
            
            # Check if the problem already exists
            cursor.execute("SELECT problem_id FROM model_performance WHERE problem_id = ?", (problem_id,))            
            existing_problem = cursor.fetchone()
            
            if existing_problem:
                # Update existing problem record
                cursor.execute(
                    """
                    UPDATE model_performance
                    SET attempts = attempts + 1,
                        successes = successes + ?,
                        last_attempt = ?
                    WHERE problem_id = ?
                    """,
                    (int(success), datetime.now(), problem_id)
                )
            else:
                # Insert new problem record
                cursor.execute(
                    """
                    INSERT INTO model_performance (problem_id, attempts, successes, last_attempt)
                    VALUES (?, 1, ?, ?)
                    """,
                    (problem_id, int(success), datetime.now())
                )
            
            # Commit the changes
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
            
            if exists:
                # Update existing record
                cursor.execute(
                    """UPDATE model_performance
                       SET success_rate = ?,
                           response_time = ?,
                           cost = ?,
                           quality_score = ?
                       WHERE model_name = ? AND problem_type = ? AND role = ?""",
                    (
                        1.0 if success else 0.0,
                        metrics.get('response_time', 0.0),
                        metrics.get('cost', 0.0),
                        metrics.get('quality_score', 0.0),
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
                        response_time, cost, quality_score, avg_quality_score)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        model_name,
                        problem_type,
                        role,
                        1.0 if success else 0.0,
                        metrics.get('response_time', 0.0),
                        metrics.get('cost', 0.0),
                        metrics.get('quality_score', 0.0),
                        metrics.get('quality_score', 0.0)  # Initial avg same as current
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
