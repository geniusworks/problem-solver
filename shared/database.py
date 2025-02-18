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
        
        # Initialize if needed
        if not self.db_path.exists():
            logger.info("Database not found. Initializing at %s", self.db_path)
            schema_path = Path(__file__).parent / 'schema.sql'
            init_db(str(self.db_path), schema_path=str(schema_path))
    
    @contextmanager
    def connect(self) -> Generator[sqlite3.Connection, None, None]:
        """Get a database connection with automatic cleanup."""
        conn = sqlite3.connect(self.db_path)
        try:
            yield conn
        finally:
            conn.close()
    
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
