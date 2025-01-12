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
from .models import ModelRegistry, ModelCharacteristics


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

    # Default weights for cold-start problem types
    DEFAULT_PROBLEM_TYPES = {
        "string_manipulation": {
            "LOCAL_FAST": 0.7,
            "LOCAL_BALANCED": 0.8,
            "LOCAL_QUALITY": 0.9,
            "CLOUD_BASIC": 0.85,
            "CLOUD_PREMIUM": 0.95
        },
        "math": {
            "LOCAL_FAST": 0.75,
            "LOCAL_BALANCED": 0.85,
            "LOCAL_QUALITY": 0.9,
            "CLOUD_BASIC": 0.9,
            "CLOUD_PREMIUM": 0.95
        },
        "graph_algorithms": {
            "LOCAL_FAST": 0.6,
            "LOCAL_BALANCED": 0.8,
            "LOCAL_QUALITY": 0.9,
            "CLOUD_BASIC": 0.85,
            "CLOUD_PREMIUM": 0.95
        },
        "dynamic_programming": {
            "LOCAL_FAST": 0.65,
            "LOCAL_BALANCED": 0.8,
            "LOCAL_QUALITY": 0.9,
            "CLOUD_BASIC": 0.85,
            "CLOUD_PREMIUM": 0.95
        }
    }

    def __init__(self, db_path: Path):
        self.db_path = db_path
        self.logger = logging.getLogger(__name__)
        self.model_registry = ModelRegistry()
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
                    execution_time REAL,
                    was_consensus BOOLEAN DEFAULT FALSE,
                    consensus_size INTEGER DEFAULT 1,
                    consensus_role TEXT
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
                (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
                    False,
                    1,
                    None,
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

    def record_consensus_result(
        self,
        agreeing_models: List[str],
        problem_type: str,
        success: bool,
        confidence: float,
        execution_time: float
    ):
        """Record a successful consensus result."""
        consensus_size = len(agreeing_models)
        timestamp = datetime.now().isoformat()
        
        with sqlite3.connect(self.db_path) as conn:
            for model in agreeing_models:
                conn.execute(
                    """
                    INSERT INTO model_performance (
                        timestamp, model_name, problem_type, success,
                        confidence, solution_correct, execution_time,
                        was_consensus, consensus_size, consensus_role
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        timestamp, model, problem_type, success,
                        confidence, success, execution_time,
                        True, consensus_size,
                        "PRIMARY" if model == agreeing_models[0] else "VALIDATOR"
                    ),
                )

    def get_consensus_metrics(self, model_name: str) -> Dict[str, float]:
        """Get consensus participation metrics for a model."""
        with sqlite3.connect(self.db_path) as conn:
            # Get overall consensus participation rate
            consensus_rate = conn.execute(
                """
                SELECT 
                    COUNT(CASE WHEN was_consensus THEN 1 END) * 1.0 / COUNT(*) as consensus_rate,
                    AVG(CASE WHEN was_consensus THEN consensus_size END) as avg_consensus_size,
                    COUNT(CASE WHEN was_consensus AND consensus_role = 'PRIMARY' THEN 1 END) * 1.0 / 
                        NULLIF(COUNT(CASE WHEN was_consensus THEN 1 END), 0) as primary_rate
                FROM model_performance
                WHERE model_name = ? AND success = TRUE
                """,
                (model_name,),
            ).fetchone()
            
            return {
                "consensus_participation_rate": consensus_rate[0] or 0.0,
                "avg_consensus_size": consensus_rate[1] or 0.0,
                "primary_solution_rate": consensus_rate[2] or 0.0
            }

    def get_model_metrics(self, model_name: str, problem_type: Optional[str] = None) -> Optional[ModelPerformanceMetrics]:
        """Get performance metrics for a model.
        
        Args:
            model_name: Name of the model
            problem_type: Optional problem type for cold-start handling
        """
        # First try to get historical metrics
        metrics = self._get_historical_metrics(model_name)
        
        if metrics:
            return metrics
            
        # If no history, use cold-start metrics
        return self._get_cold_start_metrics(model_name, problem_type)

    def _get_historical_metrics(self, model_name: str) -> Optional[ModelPerformanceMetrics]:
        """Get historical performance metrics from database."""
        with sqlite3.connect(self.db_path) as conn:
            basic_metrics = conn.execute(
                """
                SELECT 
                    COUNT(*) as total_attempts,
                    COUNT(CASE WHEN success THEN 1 END) * 1.0 / COUNT(*) as success_rate,
                    AVG(latency) as avg_latency,
                    AVG(confidence) as avg_confidence,
                    COUNT(CASE WHEN solution_correct THEN 1 END) as correct_solutions,
                    MAX(timestamp) as last_used
                FROM model_performance
                WHERE model_name = ?
                """,
                (model_name,),
            ).fetchone()
            
            if not basic_metrics or basic_metrics[0] == 0:
                return None

            consensus_metrics = self.get_consensus_metrics(model_name)
            specialties = self._get_specialties(model_name, conn)

            return ModelPerformanceMetrics(
                model_name=model_name,
                category=self._get_model_category(model_name),
                avg_latency=basic_metrics[2] or 0.0,
                success_rate=basic_metrics[1] * (1 + consensus_metrics["consensus_participation_rate"]),
                correct_solutions=basic_metrics[4],
                total_attempts=basic_metrics[0],
                avg_confidence=basic_metrics[3] or 0.0,
                last_used=datetime.fromisoformat(basic_metrics[5]),
                specialties=specialties
            )

    def _get_cold_start_metrics(
        self, model_name: str, problem_type: Optional[str] = None
    ) -> ModelPerformanceMetrics:
        """Get cold-start metrics based on model characteristics."""
        # Get model characteristics from registry
        chars = self.model_registry.models.get(model_name)
        if not chars:
            # Use conservative defaults if model not in registry
            return ModelPerformanceMetrics(
                model_name=model_name,
                category=ModelCategory.LOCAL_BALANCED,
                avg_latency=1.0,
                success_rate=0.5,
                correct_solutions=0,
                total_attempts=0,
                avg_confidence=0.7,
                last_used=datetime.now(),
                specialties=set()
            )

        # Calculate initial success rate
        base_success_rate = self._calculate_cold_start_success_rate(
            chars, problem_type
        )

        return ModelPerformanceMetrics(
            model_name=model_name,
            category=self._get_model_category(model_name),
            avg_latency=chars.performance.avg_latency,
            success_rate=base_success_rate,
            correct_solutions=0,
            total_attempts=0,
            avg_confidence=0.7,
            last_used=chars.last_used or datetime.now(),
            specialties=chars.strengths
        )

    def _calculate_cold_start_success_rate(
        self, chars: ModelCharacteristics, problem_type: Optional[str]
    ) -> float:
        """Calculate initial success rate for a model with no history."""
        # Start with base success rate from characteristics
        base_rate = chars.performance.success_rate

        # Adjust based on problem type if available
        if problem_type:
            problem_type = problem_type.lower()
            for known_type, weights in self.DEFAULT_PROBLEM_TYPES.items():
                if known_type in problem_type:
                    category_name = chars.category.name
                    type_weight = weights.get(category_name, 0.7)
                    base_rate *= type_weight
                    break

        # Adjust based on model strengths
        if problem_type:
            strength_bonus = 0.1 if any(
                strength in problem_type 
                for strength in chars.strengths
            ) else 0.0
            base_rate += strength_bonus

        # Adjust based on model weaknesses
        if problem_type:
            weakness_penalty = 0.1 if any(
                weakness in problem_type 
                for weakness in chars.weaknesses
            ) else 0.0
            base_rate -= weakness_penalty

        return min(max(base_rate, 0.3), 0.95)  # Keep between 30% and 95%

    def _get_specialties(self, model_name: str, conn: sqlite3.Connection) -> Set[str]:
        """Get model specialties from performance history."""
        return set(
            row[0] for row in conn.execute(
                """
                SELECT problem_type
                FROM model_performance
                WHERE model_name = ? 
                    AND success = TRUE
                GROUP BY problem_type
                HAVING COUNT(*) >= 3
                    AND COUNT(CASE WHEN success THEN 1 END) * 1.0 / COUNT(*) >= 0.7
                """,
                (model_name,),
            ).fetchall()
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
            self.logger.warning("No suitable models found for %s", problem_type)
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

        self.logger.info("Selected models for ensemble: %s", ", ".join(selected))
        return selected

    def get_model_metrics(self, model_name: str) -> Optional[ModelPerformanceMetrics]:
        """Get performance metrics for a model."""
        metrics = self.tracker.get_model_metrics(model_name)
        if metrics:
            self.logger.debug("Model %s performance metrics: %s", model_name, metrics)
        return metrics

    def validate_model(self, model_name: str) -> bool:
        """Validate a model's performance."""
        try:
            metrics = self.get_model_metrics(model_name)
            if metrics:
                # Validate performance requirements
                if metrics.success_rate < 0.8:
                    self.logger.warning(
                        "Model %s failed to meet performance requirements: %s",
                        model_name,
                        "Low success rate",
                    )
                    return False
                if metrics.avg_latency > 10:
                    self.logger.warning(
                        "Model %s failed to meet performance requirements: %s",
                        model_name,
                        "High latency",
                    )
                    return False
            return True
        except Exception as e:
            self.logger.warning(
                "Model %s failed to meet performance requirements: %s",
                model_name,
                str(e),
            )
            return False
