"""Performance tracking and model optimization."""

import json
import time
from dataclasses import dataclass, asdict
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Set
import sqlite3
import logging


class ModelCategory(Enum):
    """Categories of models based on their characteristics."""

    LOCAL_FAST = "local_fast"  # Quick, less accurate (e.g., Llama-7b)
    LOCAL_BALANCED = "local_balanced"  # Good balance (e.g., CodeLlama-13b)
    LOCAL_QUALITY = "local_quality"  # High quality (e.g., Llama-70b)
    CLOUD_BASIC = "cloud_basic"  # Basic cloud (e.g., GPT-3.5)
    CLOUD_PREMIUM = "cloud_premium"  # Premium (e.g., Claude-2)


@dataclass
class ModelPerformanceMetrics:
    """Performance metrics for a model."""

    model_name: str
    category: ModelCategory
    avg_latency: float
    success_rate: float
    correct_solutions: int
    total_attempts: int
    avg_confidence: float
    last_used: datetime
    specialties: Set[str]  # e.g., "math", "string_manipulation", etc.

    def to_dict(self):
        data = asdict(self)
        data["specialties"] = list(self.specialties)
        data["last_used"] = self.last_used.isoformat()
        return data


class PerformanceTracker:
    """Tracks and analyzes model performance."""

    def __init__(self, db_path: Path):
        self.db_path = db_path
        self.logger = logging.getLogger(__name__)
        self._init_db()

    def _init_db(self):
        """Initialize SQLite database."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS model_performance (
                    timestamp TEXT,
                    model_name TEXT,
                    category TEXT,
                    problem_type TEXT,
                    latency REAL,
                    success BOOLEAN,
                    confidence REAL,
                    solution_correct BOOLEAN,
                    execution_time REAL
                )
            """
            )

            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS model_specialties (
                    model_name TEXT,
                    specialty TEXT,
                    success_rate REAL,
                    UNIQUE(model_name, specialty)
                )
            """
            )

    def record_attempt(
        self,
        model_name: str,
        category: ModelCategory,
        problem_type: str,
        latency: float,
        success: bool,
        confidence: float,
        solution_correct: bool,
        execution_time: float,
    ):
        """Record a solution attempt."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                INSERT INTO model_performance VALUES
                (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    datetime.now().isoformat(),
                    model_name,
                    category.value,
                    problem_type,
                    latency,
                    success,
                    confidence,
                    solution_correct,
                    execution_time,
                ),
            )

        # Update specialties
        if success and solution_correct:
            self._update_specialty(model_name, problem_type)

    def _update_specialty(self, model_name: str, problem_type: str):
        """Update model's specialty success rate."""
        with sqlite3.connect(self.db_path) as conn:
            # Get current success rate
            cur = conn.execute(
                """
                SELECT success_rate FROM model_specialties
                WHERE model_name = ? AND specialty = ?
                """,
                (model_name, problem_type),
            )
            result = cur.fetchone()

            if result:
                # Update existing rate (weighted average)
                current_rate = result[0]
                new_rate = (current_rate * 9 + 1) / 10
                conn.execute(
                    """
                    UPDATE model_specialties
                    SET success_rate = ?
                    WHERE model_name = ? AND specialty = ?
                    """,
                    (new_rate, model_name, problem_type),
                )
            else:
                # Insert new specialty
                conn.execute(
                    """
                    INSERT INTO model_specialties VALUES (?, ?, ?)
                    """,
                    (model_name, problem_type, 1.0),
                )

    def get_model_metrics(self, model_name: str) -> Optional[ModelPerformanceMetrics]:
        """Get performance metrics for a model."""
        with sqlite3.connect(self.db_path) as conn:
            # Get general performance metrics
            cur = conn.execute(
                """
                SELECT 
                    category,
                    AVG(latency) as avg_latency,
                    AVG(CASE WHEN success THEN 1 ELSE 0 END) as success_rate,
                    SUM(CASE WHEN solution_correct THEN 1 ELSE 0 END) as correct_solutions,
                    COUNT(*) as total_attempts,
                    AVG(confidence) as avg_confidence,
                    MAX(timestamp) as last_used
                FROM model_performance
                WHERE model_name = ?
                GROUP BY model_name
                """,
                (model_name,),
            )
            result = cur.fetchone()

            if not result:
                return None

            # Get specialties
            cur = conn.execute(
                """
                SELECT specialty
                FROM model_specialties
                WHERE model_name = ? AND success_rate >= 0.8
                """,
                (model_name,),
            )
            specialties = {row[0] for row in cur.fetchall()}

            return ModelPerformanceMetrics(
                model_name=model_name,
                category=ModelCategory(result[0]),
                avg_latency=result[1],
                success_rate=result[2],
                correct_solutions=result[3],
                total_attempts=result[4],
                avg_confidence=result[5],
                last_used=datetime.fromisoformat(result[6]),
                specialties=specialties,
            )

    def suggest_models(
        self, problem_type: str, max_latency: Optional[float] = None
    ) -> List[str]:
        """Suggest best models for a problem type."""
        query = """
            SELECT 
                m.model_name,
                AVG(m.latency) as avg_latency,
                AVG(CASE WHEN m.success THEN 1 ELSE 0 END) as success_rate,
                COALESCE(s.success_rate, 0) as specialty_rate
            FROM model_performance m
            LEFT JOIN model_specialties s 
                ON m.model_name = s.model_name 
                AND s.specialty = ?
            GROUP BY m.model_name
            HAVING 1=1
        """

        params = [problem_type]
        if max_latency is not None:
            query += " AND avg_latency <= ?"
            params.append(max_latency)

        query += " ORDER BY specialty_rate DESC, success_rate DESC LIMIT 3"

        with sqlite3.connect(self.db_path) as conn:
            cur = conn.execute(query, params)
            return [row[0] for row in cur.fetchall()]

    def export_metrics(self, export_path: Path):
        """Export performance metrics to JSON."""
        with sqlite3.connect(self.db_path) as conn:
            # Get all model names
            cur = conn.execute("SELECT DISTINCT model_name FROM model_performance")
            model_names = [row[0] for row in cur.fetchall()]

            # Get metrics for each model
            metrics = {}
            for model_name in model_names:
                model_metrics = self.get_model_metrics(model_name)
                if model_metrics:
                    metrics[model_name] = model_metrics.to_dict()

        with open(export_path, "w") as f:
            json.dump(metrics, f, indent=2)


class ModelSelector:
    """Selects optimal models based on performance history."""

    def __init__(self, tracker: PerformanceTracker):
        self.tracker = tracker
        self.logger = logging.getLogger(__name__)

    def select_ensemble(
        self, problem_type: str, max_latency: Optional[float] = None
    ) -> List[str]:
        """Select an optimal ensemble for a problem type."""
        # Get model suggestions
        candidates = self.tracker.suggest_models(problem_type, max_latency)

        if not candidates:
            self.logger.warning(f"No suitable models found for {problem_type}")
            return []

        # Ensure diversity in model categories
        selected = []
        categories_used = set()

        for model_name in candidates:
            metrics = self.tracker.get_model_metrics(model_name)
            if metrics and metrics.category not in categories_used:
                selected.append(model_name)
                categories_used.add(metrics.category)

                if len(selected) >= 3:  # Maintain optimal size
                    break

        return selected
