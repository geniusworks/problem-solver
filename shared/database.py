"""Database module for storing learning and strategy data."""

import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any
import json


class LearningDatabase:
    """Database for storing and retrieving learning data."""

    def __init__(self, workspace_dir: Path):
        """Initialize the database."""
        self.db_path = workspace_dir / "learning" / "solver.db"
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self) -> None:
        """Initialize database tables."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS strategy_results (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    problem_id TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    strategies_used TEXT NOT NULL,
                    success INTEGER NOT NULL,
                    execution_time REAL,
                    memory_usage REAL,
                    attempts INTEGER,
                    failure_points TEXT,
                    generation_time REAL,
                    code_size INTEGER
                )
            """)

            conn.execute("""
                CREATE TABLE IF NOT EXISTS strategy_weights (
                    strategy TEXT PRIMARY KEY,
                    weight REAL NOT NULL,
                    success_rate REAL,
                    avg_execution_time REAL,
                    avg_memory_usage REAL,
                    last_updated TEXT NOT NULL
                )
            """)

            conn.execute("""
                CREATE TABLE IF NOT EXISTS problem_characteristics (
                    problem_id TEXT PRIMARY KEY,
                    characteristics TEXT NOT NULL,
                    successful_strategies TEXT,
                    avg_solution_time REAL,
                    attempts INTEGER,
                    last_updated TEXT NOT NULL
                )
            """)

    def store_result(self, 
                    problem_id: str,
                    strategies_used: List[str],
                    success: bool,
                    execution_metrics: Dict[str, float],
                    attempts: int,
                    failure_points: List[str]) -> None:
        """Store a strategy result."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                INSERT INTO strategy_results (
                    problem_id, timestamp, strategies_used, success,
                    execution_time, memory_usage, attempts, failure_points,
                    generation_time, code_size
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    problem_id,
                    datetime.now().isoformat(),
                    json.dumps(strategies_used),
                    1 if success else 0,
                    execution_metrics.get('execution_time', 0.0),
                    execution_metrics.get('memory_usage', 0.0),
                    attempts,
                    json.dumps(failure_points),
                    execution_metrics.get('generation_time', 0.0),
                    execution_metrics.get('code_size', 0)
                )
            )

    def update_strategy_weights(self, weights: Dict[str, Dict[str, float]]) -> None:
        """Update strategy weights."""
        with sqlite3.connect(self.db_path) as conn:
            for strategy, metrics in weights.items():
                conn.execute(
                    """
                    INSERT OR REPLACE INTO strategy_weights (
                        strategy, weight, success_rate, avg_execution_time,
                        avg_memory_usage, last_updated
                    ) VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        strategy,
                        metrics['weight'],
                        metrics.get('success_rate', 0.0),
                        metrics.get('avg_execution_time', 0.0),
                        metrics.get('avg_memory_usage', 0.0),
                        datetime.now().isoformat()
                    )
                )

    def store_problem_characteristics(self,
                                   problem_id: str,
                                   characteristics: Dict[str, float],
                                   successful_strategies: Optional[List[str]] = None) -> None:
        """Store problem characteristics and successful strategies."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO problem_characteristics (
                    problem_id, characteristics, successful_strategies,
                    avg_solution_time, attempts, last_updated
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    problem_id,
                    json.dumps(characteristics),
                    json.dumps(successful_strategies) if successful_strategies else None,
                    0.0,  # Will be updated with actual metrics
                    1,    # Initial attempt
                    datetime.now().isoformat()
                )
            )

    def get_strategy_weights(self) -> Dict[str, Dict[str, float]]:
        """Get current strategy weights and metrics."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                "SELECT strategy, weight, success_rate, avg_execution_time, avg_memory_usage FROM strategy_weights"
            )
            return {
                row[0]: {
                    'weight': row[1],
                    'success_rate': row[2],
                    'avg_execution_time': row[3],
                    'avg_memory_usage': row[4]
                }
                for row in cursor.fetchall()
            }

    def get_similar_problems(self, characteristics: Dict[str, float], limit: int = 5) -> List[Dict[str, Any]]:
        """Find similar problems based on characteristics."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                "SELECT problem_id, characteristics, successful_strategies FROM problem_characteristics"
            )
            
            # Calculate similarity scores
            similar_problems = []
            for row in cursor.fetchall():
                problem_chars = json.loads(row[1])
                similarity = self._calculate_similarity(characteristics, problem_chars)
                similar_problems.append({
                    'problem_id': row[0],
                    'characteristics': problem_chars,
                    'successful_strategies': json.loads(row[2]) if row[2] else None,
                    'similarity': similarity
                })
            
            # Return top N similar problems
            similar_problems.sort(key=lambda x: x['similarity'], reverse=True)
            return similar_problems[:limit]

    def _calculate_similarity(self, chars1: Dict[str, float], chars2: Dict[str, float]) -> float:
        """Calculate similarity score between two sets of characteristics."""
        # Simple Euclidean distance for now
        score = 0.0
        for key in set(chars1.keys()) & set(chars2.keys()):
            score += (chars1[key] - chars2[key]) ** 2
        return 1.0 / (1.0 + score ** 0.5)  # Convert distance to similarity
