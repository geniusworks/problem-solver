"""Module for intelligent model selection based on performance metrics."""

import json
import logging
import os
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Optional, Set, Tuple
from shared.config import RESOURCES_CONFIG
from .models import ModelRole, RolePerformance

logger = logging.getLogger(__name__)


@dataclass
class ModelPerformanceMetrics:
    """Performance metrics for a model."""
    role_metrics: Dict[ModelRole, RolePerformance]
    avg_response_time: float
    avg_code_quality: float
    success_rate: float
    total_attempts: int
    successful_attempts: int
    last_success: Optional[datetime]
    cost_per_success: float


@dataclass
class AttemptResult:
    """Result of a single model attempt."""
    model_name: str
    role: ModelRole
    response_time: float
    code_quality: float
    was_successful: bool
    cost: float


@dataclass
class ConsensusResult:
    """Result of a consensus check."""
    has_consensus: bool
    agreed_solution: Optional[str]
    agreeing_models: List[str]
    pending_models: List[str]


class ModelSelector:
    """Intelligent model selection based on performance history."""

    def __init__(
        self, 
        metrics_file: str = "model_metrics.json", 
        consensus_timeout: int = 60,
        models_per_role: int = 3  # Number of leading models to track per role
    ):
        """Initialize the model selector.

        Args:
            metrics_file: Path to the metrics storage file.
            consensus_timeout: Seconds to wait for additional votes after consensus.
            models_per_role: Number of leading models to maintain per role.
        """
        self.metrics_file = metrics_file
        self.metrics: Dict[str, ModelPerformanceMetrics] = {}
        self.cloud_timeout = RESOURCES_CONFIG.get("consensus", {}).get("timeout_seconds", 300)
        self.min_code_quality = float(os.getenv("MIN_CODE_QUALITY", "7.0"))
        self.consensus_timeout = consensus_timeout
        self.models_per_role = models_per_role
        self.leading_models: Dict[ModelRole, List[str]] = {
            role: [] for role in ModelRole
        }
        self._load_metrics()
        self._update_leading_models()

    def _load_metrics(self) -> None:
        """Load metrics from storage."""
        if not os.path.exists(self.metrics_file):
            return

        try:
            with open(self.metrics_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                for model_name, metrics in data.items():
                    role_metrics = {}
                    for role_name, role_data in metrics.get("role_metrics", {}).items():
                        role = ModelRole(role_name)
                        role_metrics[role] = RolePerformance(
                            success_rate=role_data["success_rate"],
                            avg_latency=role_data["avg_latency"],
                            last_used=datetime.fromisoformat(role_data["last_used"]) if role_data.get("last_used") else None,
                            problems_attempted=role_data["problems_attempted"],
                            problems_solved=role_data["problems_solved"]
                        )

                    self.metrics[model_name] = ModelPerformanceMetrics(
                        role_metrics=role_metrics,
                        avg_response_time=metrics["avg_response_time"],
                        avg_code_quality=metrics["avg_code_quality"],
                        success_rate=metrics["success_rate"],
                        total_attempts=metrics["total_attempts"],
                        successful_attempts=metrics["successful_attempts"],
                        last_success=(
                            datetime.fromisoformat(metrics["last_success"])
                            if metrics.get("last_success")
                            else None
                        ),
                        cost_per_success=metrics["cost_per_success"],
                    )
        except Exception as e:
            logger.error("Failed to load metrics: %s", str(e))

    def _save_metrics(self) -> None:
        """Save metrics to storage."""
        try:
            data = {
                model_name: {
                    "role_metrics": {
                        role.value: {
                            "success_rate": perf.success_rate,
                            "avg_latency": perf.avg_latency,
                            "last_used": perf.last_used.isoformat() if perf.last_used else None,
                            "problems_attempted": perf.problems_attempted,
                            "problems_solved": perf.problems_solved
                        }
                        for role, perf in metrics.role_metrics.items()
                    },
                    "avg_response_time": metrics.avg_response_time,
                    "avg_code_quality": metrics.avg_code_quality,
                    "success_rate": metrics.success_rate,
                    "total_attempts": metrics.total_attempts,
                    "successful_attempts": metrics.successful_attempts,
                    "last_success": metrics.last_success.isoformat()
                    if metrics.last_success
                    else None,
                    "cost_per_success": metrics.cost_per_success,
                }
                for model_name, metrics in self.metrics.items()
            }
            with open(self.metrics_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.error("Failed to save metrics: %s", str(e))

    def _update_leading_models(self) -> None:
        """Update the list of leading models for each role based on performance."""
        for role in ModelRole:
            # Sort models by role-specific performance
            sorted_models = sorted(
                [(name, metrics) for name, metrics in self.metrics.items()],
                key=lambda x: (
                    x[1].role_metrics.get(role, RolePerformance()).success_rate,
                    -x[1].role_metrics.get(role, RolePerformance()).avg_latency
                ),
                reverse=True
            )
            
            # Update leading models for this role
            self.leading_models[role] = [
                name for name, _ in sorted_models[:self.models_per_role]
            ]

    def record_attempt(self, result: AttemptResult) -> None:
        """Record the result of a model attempt and update rankings."""
        if result.model_name not in self.metrics:
            self.metrics[result.model_name] = ModelPerformanceMetrics(
                role_metrics={role: RolePerformance() for role in ModelRole},
                avg_response_time=result.response_time,
                avg_code_quality=result.code_quality,
                success_rate=1.0 if result.was_successful else 0.0,
                total_attempts=1,
                successful_attempts=1 if result.was_successful else 0,
                last_success=datetime.now() if result.was_successful else None,
                cost_per_success=result.cost if result.was_successful else 0.0,
            )
        else:
            metrics = self.metrics[result.model_name]
            # Update role-specific metrics
            role_perf = metrics.role_metrics.get(result.role, RolePerformance())
            role_perf.problems_attempted += 1
            if result.was_successful:
                role_perf.problems_solved += 1
            role_perf.success_rate = role_perf.problems_solved / role_perf.problems_attempted
            role_perf.avg_latency = (
                (role_perf.avg_latency * (role_perf.problems_attempted - 1) + result.response_time)
                / role_perf.problems_attempted
            )
            role_perf.last_used = datetime.now()
            metrics.role_metrics[result.role] = role_perf

            # Update overall metrics
            metrics.total_attempts += 1
            if result.was_successful:
                metrics.successful_attempts += 1
                metrics.last_success = datetime.now()
            metrics.success_rate = metrics.successful_attempts / metrics.total_attempts
            metrics.avg_response_time = (
                (metrics.avg_response_time * (metrics.total_attempts - 1) + result.response_time)
                / metrics.total_attempts
            )
            metrics.avg_code_quality = (
                (metrics.avg_code_quality * (metrics.total_attempts - 1) + result.code_quality)
                / metrics.total_attempts
            )
            if result.was_successful:
                metrics.cost_per_success = (
                    (metrics.cost_per_success * (metrics.successful_attempts - 1) + result.cost)
                    / metrics.successful_attempts
                )

        self._update_leading_models()
        self._save_metrics()

    def get_models_for_role(self, role: ModelRole, count: Optional[int] = None) -> List[str]:
        """Get the top performing models for a specific role.
        
        Args:
            role: The role to get models for
            count: Number of models to return, defaults to models_per_role
            
        Returns:
            List of model names, ordered by performance
        """
        count = count or self.models_per_role
        return self.leading_models[role][:count]

    def select_models(
        self, available_models: Set[str], is_cloud: Dict[str, bool], max_models: int = 3
    ) -> List[str]:
        """Select the best models based on performance history.

        Args:
            available_models: Set of available model names.
            is_cloud: Dictionary mapping model names to whether they are cloud models.
            max_models: Maximum number of models to select.

        Returns:
            List of selected model names.
        """
        # First, try local models with good performance
        local_models = {m for m in available_models if not is_cloud[m]}
        cloud_models = {m for m in available_models if is_cloud[m]}

        selected = []

        # Sort local models by success rate and code quality
        local_candidates = sorted(
            [m for m in local_models if m in self.metrics],
            key=lambda m: (
                self.metrics[m].success_rate,
                self.metrics[m].avg_code_quality,
                -self.metrics[m].avg_response_time,
            ),
            reverse=True,
        )

        # Add untried local models at the start
        untried_local = [m for m in local_models if m not in self.metrics]
        selected.extend(untried_local)

        # Add best performing local models
        selected.extend(local_candidates)

        # If we still need more models and have cloud models available
        if len(selected) < max_models and cloud_models:
            # Sort cloud models by success rate and cost
            cloud_candidates = sorted(
                [m for m in cloud_models if m in self.metrics],
                key=lambda m: (
                    self.metrics[m].success_rate,
                    -self.metrics[m].cost_per_success,
                    self.metrics[m].avg_code_quality,
                ),
                reverse=True,
            )

            # Add untried cloud models at the end
            untried_cloud = [m for m in cloud_models if m not in self.metrics]
            selected.extend(cloud_candidates)
            selected.extend(untried_cloud)

        return selected[:max_models]

    def should_switch_to_cloud(
        self, current_duration: float, current_quality: float
    ) -> bool:
        """Determine if we should switch to cloud models.

        Args:
            current_duration: How long we've been trying with local models.
            current_quality: Current code quality score.

        Returns:
            True if we should switch to cloud models.
        """
        return (
            current_duration > self.cloud_timeout
            or current_quality < self.min_code_quality
        )

    def check_consensus(
        self,
        solutions: Dict[str, str],
        pending_models: Set[str],
        consensus_start: Optional[datetime] = None,
    ) -> ConsensusResult:
        """Check for consensus among model solutions.

        Args:
            solutions: Dictionary mapping model names to their solutions.
            pending_models: Set of models still working on solutions.
            consensus_start: When the first consensus was reached (for timeout).

        Returns:
            ConsensusResult indicating consensus status and details.
        """
        # Group solutions by their values
        solution_groups: Dict[str, List[str]] = {}
        for model, solution in solutions.items():
            if solution in solution_groups:
                solution_groups[solution].append(model)
            else:
                solution_groups[solution] = [model]

        # Find the largest group of agreeing models
        if not solution_groups:
            return ConsensusResult(
                has_consensus=False,
                agreed_solution=None,
                agreeing_models=[],
                pending_models=list(pending_models),
            )

        best_solution, agreeing_models = max(
            solution_groups.items(), key=lambda x: len(x[1])
        )

        # Check if we have at least 2 models agreeing
        if len(agreeing_models) >= 2:
            # If this is our first consensus, all models are still in play
            if not consensus_start:
                return ConsensusResult(
                    has_consensus=True,
                    agreed_solution=best_solution,
                    agreeing_models=agreeing_models,
                    pending_models=list(pending_models),
                )

            # If we've been waiting for consensus for too long, proceed with
            # agreeing models only
            time_waiting = (datetime.now() - consensus_start).total_seconds()
            if time_waiting > self.consensus_timeout:
                return ConsensusResult(
                    has_consensus=True,
                    agreed_solution=best_solution,
                    agreeing_models=agreeing_models,
                    pending_models=[],  # Drop pending models
                )

        # No consensus yet
        return ConsensusResult(
            has_consensus=False,
            agreed_solution=None,
            agreeing_models=[],
            pending_models=list(pending_models),
        )

    def reactivate_models_after_failure(
        self,
        current_models: Set[str],
        available_models: Set[str],
        is_cloud: Dict[str, bool],
        max_additional: int = 1,
    ) -> List[str]:
        """Select additional models to try after a submission failure.

        Args:
            current_models: Models currently in use.
            available_models: All available models.
            is_cloud: Dictionary mapping model names to whether they are cloud models.
            max_additional: Maximum number of additional models to select.

        Returns:
            List of additional models to try.
        """
        # Get models we aren't currently using
        unused_models = available_models - current_models

        # Select best unused models
        candidates = self.select_models(
            unused_models, is_cloud, max_models=max_additional
        )

        return candidates
