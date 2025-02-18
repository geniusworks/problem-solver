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
            conn.execute(
                """
                INSERT INTO strategy_results (
                    problem_id, timestamp, strategies_used, success,
                    execution_time, memory_usage, attempts,
                    failure_points, generation_time, code_size
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    problem_id,
                    datetime.now().isoformat(),
                    str(strategies),
                    success,
                    metrics.get("execution_time"),
                    metrics.get("memory_usage"),
                    metrics.get("attempts", 1),
                    str(metrics.get("failure_points", [])),
                    metrics.get("generation_time"),
                    metrics.get("code_size"),
                ),
            )
            conn.commit()
    
    def get_successful_strategies(self, problem_type: str) -> List[Tuple[str, float]]:
        """Get strategies that have worked well for similar problems.
        
        Returns:
            List of (strategy_name, success_rate) tuples.
        """
        with self.connect() as conn:
            return conn.execute(
                """
                SELECT strategy_name, success_rate 
                FROM strategy_weights
                WHERE problem_types LIKE ?
                AND success_rate > 0.5
                ORDER BY success_rate DESC
                """,
                (f"%{problem_type}%",),
            ).fetchall()
    
    def update_model_performance(
        self,
        model_name: str,
        problem_type: str,
        role: str,
        metrics: Dict[str, float]
    ) -> None:
        """Update performance metrics for a model."""
        with self.connect() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO model_performance (
                    model_name, problem_type, role,
                    success_rate, avg_quality_score,
                    avg_response_time, cost_per_token,
                    last_updated
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    model_name,
                    problem_type,
                    role,
                    metrics["success_rate"],
                    metrics.get("quality_score"),
                    metrics.get("response_time"),
                    metrics.get("cost_per_token"),
                    datetime.now().isoformat(),
                ),
            )
            conn.commit()

    def get_top_models(self, problem_type: str, role: str, min_success_rate: float = 0.5) -> List[Tuple[str, float]]:
        """Get top performing models for a given problem type and role.
        
        Args:
            problem_type: Type of problem (e.g. 'string', 'math', etc.)
            role: Role the model plays (e.g. 'solver', 'reviewer', etc.)
            min_success_rate: Minimum success rate to consider
            
        Returns:
            List of (model_name, success_rate) tuples sorted by success rate.
        """
        with self.connect() as conn:
            return conn.execute(
                """
                SELECT model_name, success_rate 
                FROM model_performance
                WHERE problem_type = ? 
                AND role = ?
                AND success_rate >= ?
                ORDER BY success_rate DESC
                """,
                (problem_type, role, min_success_rate),
            ).fetchall()
