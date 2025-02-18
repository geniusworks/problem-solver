"""Database management for the learning system."""

import logging
import sqlite3
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Generator, List, Optional, Tuple

logger = logging.getLogger(__name__)

SCHEMA_SQL = """
-- Strategy results for each solution attempt
CREATE TABLE IF NOT EXISTS strategy_results (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    problem_id TEXT NOT NULL,  -- Format: YYYY_dayDD_partN
    timestamp TEXT NOT NULL,   -- ISO format
    strategies_used TEXT NOT NULL,  -- JSON array of strategy names
    success BOOLEAN NOT NULL,
    execution_time REAL,       -- In seconds
    memory_usage INTEGER,      -- In bytes
    attempts INTEGER,          -- Number of attempts before success/giving up
    failure_points TEXT,       -- JSON array of failure descriptions
    generation_time REAL,      -- Time to generate solution
    code_size INTEGER,         -- Size of solution in bytes
    UNIQUE(problem_id, timestamp)
);

-- Strategy weights and effectiveness
CREATE TABLE IF NOT EXISTS strategy_weights (
    strategy_name TEXT PRIMARY KEY,
    success_rate REAL NOT NULL,      -- 0.0 to 1.0
    avg_execution_time REAL,         -- In seconds
    avg_memory_usage INTEGER,        -- In bytes
    avg_attempts INTEGER,            -- Average attempts when this strategy is used
    total_uses INTEGER NOT NULL,     -- Total times this strategy was used
    last_updated TEXT NOT NULL,      -- ISO timestamp
    problem_types TEXT               -- JSON array of problem types this works well for
);

-- Problem characteristics and patterns
CREATE TABLE IF NOT EXISTS problem_characteristics (
    problem_id TEXT PRIMARY KEY,     -- Format: YYYY_dayDD_partN
    characteristics TEXT NOT NULL,    -- JSON object of problem features
    successful_strategies TEXT,       -- JSON array of strategies that worked
    solution_metrics TEXT,           -- JSON object with solution metrics
    attempt_history TEXT,            -- JSON array of attempt summaries
    last_updated TEXT NOT NULL       -- ISO timestamp
);

-- Model performance tracking
CREATE TABLE IF NOT EXISTS model_performance (
    model_name TEXT NOT NULL,
    problem_type TEXT NOT NULL,
    role TEXT NOT NULL,
    success_rate REAL NOT NULL,
    avg_quality_score REAL NOT NULL,
    avg_response_time REAL NOT NULL,
    cost_per_token REAL NOT NULL,
    last_updated TEXT NOT NULL,
    PRIMARY KEY (model_name, problem_type, role)
);

-- Improvement history
CREATE TABLE IF NOT EXISTS improvement_history (
    problem_id TEXT NOT NULL,
    iteration INTEGER NOT NULL,
    model_name TEXT NOT NULL,
    improvement_type TEXT NOT NULL,
    impact_score REAL NOT NULL,
    timestamp TEXT NOT NULL,
    PRIMARY KEY (problem_id, iteration)
);

-- Create indexes for common queries
CREATE INDEX IF NOT EXISTS idx_strategy_results_problem 
ON strategy_results(problem_id);

CREATE INDEX IF NOT EXISTS idx_problem_characteristics_type
ON problem_characteristics(problem_type);

CREATE INDEX IF NOT EXISTS idx_model_performance_role
ON model_performance(role);

CREATE INDEX IF NOT EXISTS idx_model_performance_type
ON model_performance(problem_type);

CREATE INDEX IF NOT EXISTS idx_improvement_history_model
ON improvement_history(model_name);
"""


class LearningDatabase:
    """Manages database connections and operations for the learning system."""
    
    def __init__(self, workspace_dir: Optional[Path] = None) -> None:
        """Initialize the database manager.
        
        Args:
            workspace_dir: Directory containing the database. If None, uses current directory.
        """
        if workspace_dir is None:
            workspace_dir = Path.cwd()
        
        self.db_dir = workspace_dir / "learning"
        self.db_dir.mkdir(parents=True, exist_ok=True)
        self.db_path = Path(__file__).parent.parent / 'learning' / 'solver.db'
        
        # Initialize if needed
        if not self.db_path.exists():
            logger.info("Database not found. Initializing at %s", self.db_path)
            self._init_db()
    
    def _init_db(self) -> None:
        """Initialize the database with the schema."""
        with self.connect() as conn:
            conn.executescript(SCHEMA_SQL)
            conn.commit()
    
    @contextmanager
    def connect(self) -> Generator[sqlite3.Connection, None, None]:
        """Get a database connection with automatic cleanup."""
        conn = sqlite3.connect(self.db_path)
        try:
            yield conn
        finally:
            conn.close()
    
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
            # Store strategy result
            conn.execute(
                """
                INSERT INTO strategy_results (
                    problem_id, timestamp, strategies_used, success,
                    execution_time, memory_usage, attempts,
                    failure_points
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    problem_id,
                    datetime.now().isoformat(),
                    str(strategies),
                    success,
                    metrics.get("execution_time"),
                    metrics.get("memory_usage"),
                    attempts,
                    str(failure_points),
                ),
            )
            
            # Update strategy weights
            for strategy in strategies:
                self._update_strategy_weight(conn, strategy, success, metrics)
            
            conn.commit()
    
    def _update_strategy_weight(
        self,
        conn: sqlite3.Connection,
        strategy: str,
        success: bool,
        metrics: Dict[str, float]
    ) -> None:
        """Update weights for a strategy based on results."""
        # Get current stats
        cur = conn.execute(
            "SELECT * FROM strategy_weights WHERE strategy_name = ?",
            (strategy,)
        )
        row = cur.fetchone()
        
        if row:
            # Update existing stats
            total_uses = row[5] + 1
            success_rate = (row[1] * row[5] + (1 if success else 0)) / total_uses
            avg_exec_time = (row[2] * row[5] + metrics.get("execution_time", 0)) / total_uses
            avg_memory = (row[3] * row[5] + metrics.get("memory_usage", 0)) / total_uses
            
            conn.execute(
                """
                UPDATE strategy_weights
                SET success_rate = ?,
                    avg_execution_time = ?,
                    avg_memory_usage = ?,
                    total_uses = ?,
                    last_updated = ?
                WHERE strategy_name = ?
                """,
                (
                    success_rate,
                    avg_exec_time,
                    avg_memory,
                    total_uses,
                    datetime.now().isoformat(),
                    strategy,
                ),
            )
        else:
            # Insert new strategy
            conn.execute(
                """
                INSERT INTO strategy_weights (
                    strategy_name, success_rate, avg_execution_time,
                    avg_memory_usage, total_uses, last_updated
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    strategy,
                    1.0 if success else 0.0,
                    metrics.get("execution_time", 0),
                    metrics.get("memory_usage", 0),
                    1,
                    datetime.now().isoformat(),
                ),
            )
    
    def get_strategy_weights(self) -> Dict[str, Dict[str, float]]:
        """Get current weights and metrics for all strategies."""
        with self.connect() as conn:
            cur = conn.execute("SELECT * FROM strategy_weights")
            return {
                row[0]: {
                    "weight": row[1],  # success_rate
                    "avg_execution_time": row[2],
                    "avg_memory_usage": row[3],
                    "avg_attempts": row[4],
                    "total_uses": row[5]
                }
                for row in cur.fetchall()
            }
    
    def get_similar_problems(
        self, characteristics: Dict[str, float]
    ) -> List[Dict[str, Any]]:
        """Find problems with similar characteristics."""
        with self.connect() as conn:
            # For now, just return successful problems
            # TODO: Implement actual similarity scoring
            cur = conn.execute(
                """
                SELECT problem_id, characteristics, successful_strategies
                FROM problem_characteristics
                WHERE successful_strategies IS NOT NULL
                """
            )
            return [
                {
                    "problem_id": row[0],
                    "characteristics": row[1],
                    "successful_strategies": row[2],
                    "similarity": 0.5  # Placeholder similarity score
                }
                for row in cur.fetchall()
            ]

    def update_model_performance(
        self,
        model_name: str,
        problem_type: str,
        role: str,
        success: bool,
        quality_score: float,
        response_time: float,
        cost: float
    ) -> None:
        """Update performance metrics for a model.
        
        Args:
            model_name: Name of the model
            problem_type: Type of problem being solved
            role: Role of the model (primary, reviewer, etc.)
            success: Whether the attempt was successful
            quality_score: Code quality metric (0.0 to 10.0)
            response_time: Time taken to generate response
            cost: Cost per token in USD
        """
        with self.connect() as conn:
            cursor = conn.cursor()
            
            # Get existing metrics
            cursor.execute(
                """
                SELECT success_rate, avg_quality_score, avg_response_time, cost_per_token
                FROM model_performance
                WHERE model_name = ? AND problem_type = ? AND role = ?
                """,
                (model_name, problem_type, role)
            )
            row = cursor.fetchone()
            
            if row:
                # Update existing metrics with exponential moving average
                alpha = 0.1  # Weight for new values
                old_success_rate, old_quality, old_response_time, old_cost = row
                new_success_rate = old_success_rate * (1 - alpha) + float(success) * alpha
                new_quality = old_quality * (1 - alpha) + quality_score * alpha
                new_response_time = old_response_time * (1 - alpha) + response_time * alpha
                new_cost = old_cost * (1 - alpha) + cost * alpha
                
                cursor.execute(
                    """
                    UPDATE model_performance
                    SET success_rate = ?,
                        avg_quality_score = ?,
                        avg_response_time = ?,
                        cost_per_token = ?,
                        last_updated = datetime('now')
                    WHERE model_name = ? AND problem_type = ? AND role = ?
                    """,
                    (new_success_rate, new_quality, new_response_time, new_cost,
                     model_name, problem_type, role)
                )
            else:
                # Insert new record
                cursor.execute(
                    """
                    INSERT INTO model_performance (
                        model_name, problem_type, role,
                        success_rate, avg_quality_score,
                        avg_response_time, cost_per_token,
                        last_updated
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, datetime('now'))
                    """,
                    (model_name, problem_type, role,
                     float(success), quality_score,
                     response_time, cost)
                )

    def get_top_models(
        self, problem_type: str, role: str, limit: int = 3
    ) -> List[str]:
        """Get the top performing models for a specific problem type and role.
        
        Args:
            problem_type: Type of problem
            role: Role of the model
            limit: Maximum number of models to return
            
        Returns:
            List of model names sorted by performance
        """
        with self.connect() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT model_name
                FROM model_performance
                WHERE problem_type = ? AND role = ?
                ORDER BY 
                    success_rate * 0.4 +  -- Weight success rate highest
                    (1.0 - avg_response_time / MAX(avg_response_time) OVER ()) * 0.3 +  -- Faster is better
                    (avg_quality_score / 10.0) * 0.2 +  -- Quality matters
                    (1.0 - cost_per_token / NULLIF(MAX(cost_per_token) OVER (), 0)) * 0.1  -- Lower cost preferred
                    DESC
                LIMIT ?
                """,
                (problem_type, role, limit)
            )
            return [row[0] for row in cursor.fetchall()]

    def record_improvement(
        self,
        problem_id: str,
        model_name: str,
        improvement_type: str,
        impact_score: float
    ) -> None:
        """Record a model's improvement of a solution.
        
        Args:
            problem_id: ID of the problem (YYYY_dayDD_partN)
            model_name: Name of the model making the improvement
            improvement_type: Type of improvement made
            impact_score: Impact of the improvement (0.0 to 1.0)
        """
        with self.connect() as conn:
            cursor = conn.cursor()
            
            # Get the latest iteration number for this problem
            cursor.execute(
                """
                SELECT MAX(iteration)
                FROM improvement_history
                WHERE problem_id = ?
                """,
                (problem_id,)
            )
            max_iteration = cursor.fetchone()[0] or 0
            
            # Record the improvement
            cursor.execute(
                """
                INSERT INTO improvement_history (
                    problem_id, iteration, model_name,
                    improvement_type, impact_score, timestamp
                ) VALUES (?, ?, ?, ?, ?, datetime('now'))
                """,
                (problem_id, max_iteration + 1, model_name,
                 improvement_type, impact_score)
            )
