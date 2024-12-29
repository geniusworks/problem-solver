"""Dynamic role assignment and optimization for LLM ensemble."""

from enum import Enum
from dataclasses import dataclass
from typing import Dict, List, Optional, Set
import numpy as np
from datetime import datetime, timedelta


class ModelRole(Enum):
    """Possible roles for models in the ensemble."""

    PRIMARY = "primary"  # First attempt at solution
    REVIEWER = "reviewer"  # Reviews and improves solutions
    VALIDATOR = "validator"  # Validates correctness
    OPTIMIZER = "optimizer"  # Optimizes for performance
    BACKUP = "backup"  # Available but not preferred


@dataclass
class RolePerformance:
    """Performance metrics for a model in a specific role."""

    role: ModelRole
    success_rate: float
    avg_quality_score: float
    first_attempt_success: float
    improvement_impact: float  # How much it improves others' solutions
    validation_accuracy: float  # How often its validations are correct
    last_updated: datetime


@dataclass
class ModelProfile:
    """Complete profile of a model's capabilities and performance."""

    model_name: str
    roles: Dict[ModelRole, RolePerformance]
    strengths: Set[str]  # e.g., "math", "string_manipulation"
    weaknesses: Set[str]
    avg_response_time: float
    cost_per_token: float
    win_probability: Dict[str, float]  # Problem type -> win probability


class RoleOptimizer:
    """Optimizes role assignments based on performance history."""

    def __init__(
        self, performance_window: timedelta = timedelta(days=7), min_samples: int = 10
    ):
        self.performance_window = performance_window
        self.min_samples = min_samples
        self.profiles: Dict[str, ModelProfile] = {}

    def update_profile(
        self,
        model_name: str,
        problem_type: str,
        role: ModelRole,
        success: bool,
        quality_score: float,
        was_first_attempt: bool,
        improvement_made: Optional[float] = None,
        validation_correct: Optional[bool] = None,
    ) -> None:
        """Update a model's performance profile."""
        if model_name not in self.profiles:
            self.profiles[model_name] = ModelProfile(
                model_name=model_name,
                roles={
                    r: RolePerformance(
                        role=r,
                        success_rate=1.0,
                        avg_quality_score=0.0,
                        first_attempt_success=1.0,
                        improvement_impact=0.0,
                        validation_accuracy=1.0,
                        last_updated=datetime.now(),
                    )
                    for r in ModelRole
                },
                strengths=set(),
                weaknesses=set(),
                avg_response_time=0.0,
                cost_per_token=0.0,
                win_probability={},
            )

        profile = self.profiles[model_name]
        role_perf = profile.roles[role]

        # Update role-specific metrics
        role_perf.success_rate = self._update_moving_average(
            role_perf.success_rate, float(success), 0.1
        )
        role_perf.avg_quality_score = self._update_moving_average(
            role_perf.avg_quality_score, quality_score, 0.1
        )

        if was_first_attempt:
            role_perf.first_attempt_success = self._update_moving_average(
                role_perf.first_attempt_success, float(success), 0.1
            )

        if improvement_made is not None:
            role_perf.improvement_impact = self._update_moving_average(
                role_perf.improvement_impact, improvement_made, 0.1
            )

        if validation_correct is not None:
            role_perf.validation_accuracy = self._update_moving_average(
                role_perf.validation_accuracy, float(validation_correct), 0.1
            )

        role_perf.last_updated = datetime.now()

        # Update win probability
        if was_first_attempt:
            if problem_type not in profile.win_probability:
                profile.win_probability[problem_type] = 0.5

            profile.win_probability[problem_type] = self._update_moving_average(
                profile.win_probability[problem_type],
                float(success and quality_score > 0.8),  # High quality success
                0.1,
            )

    def _update_moving_average(
        self, current: float, new_value: float, weight: float
    ) -> float:
        """Update moving average with new value."""
        return current * (1 - weight) + new_value * weight

    def get_optimal_roles(
        self, problem_type: str, available_models: List[str]
    ) -> Dict[str, List[ModelRole]]:
        """Determine optimal roles for available models."""
        if not available_models:
            return {}

        # Calculate role scores for each model
        role_scores: Dict[str, Dict[ModelRole, float]] = {}
        for model_name in available_models:
            if model_name not in self.profiles:
                continue

            profile = self.profiles[model_name]
            scores = {}

            for role, perf in profile.roles.items():
                if (datetime.now() - perf.last_updated) > self.performance_window:
                    continue

                # Base score on role-specific metrics
                base_score = {
                    ModelRole.PRIMARY: perf.first_attempt_success * 0.7
                    + perf.avg_quality_score * 0.3,
                    ModelRole.REVIEWER: perf.improvement_impact * 0.8
                    + perf.success_rate * 0.2,
                    ModelRole.VALIDATOR: perf.validation_accuracy * 0.9
                    + perf.success_rate * 0.1,
                    ModelRole.OPTIMIZER: perf.improvement_impact * 0.6
                    + perf.avg_quality_score * 0.4,
                    ModelRole.BACKUP: perf.success_rate,
                }[role]

                # Adjust score based on problem-specific win probability
                win_prob = profile.win_probability.get(problem_type, 0.5)
                scores[role] = base_score * (0.7 + 0.3 * win_prob)

            role_scores[model_name] = scores

        # Assign roles based on scores
        assignments: Dict[str, List[ModelRole]] = {
            model: [] for model in available_models
        }
        assigned_roles: Set[ModelRole] = set()

        # First, assign primary role to best candidate
        primary_scores = {
            model: scores.get(ModelRole.PRIMARY, 0)
            for model, scores in role_scores.items()
        }
        if primary_scores:
            best_primary = max(primary_scores.items(), key=lambda x: x[1])
            if best_primary[1] > 0.7:  # Minimum threshold for primary
                assignments[best_primary[0]].append(ModelRole.PRIMARY)
                assigned_roles.add(ModelRole.PRIMARY)

        # Assign other roles based on scores and availability
        remaining_roles = [r for r in ModelRole if r not in assigned_roles]
        for role in remaining_roles:
            role_candidates = {
                model: scores.get(role, 0)
                for model, scores in role_scores.items()
                if len(assignments[model]) < 2  # Limit roles per model
            }
            if role_candidates:
                best_candidate = max(role_candidates.items(), key=lambda x: x[1])
                if best_candidate[1] > 0.5:  # Minimum threshold for other roles
                    assignments[best_candidate[0]].append(role)

        return assignments

    def get_win_probability(self, model_name: str, problem_type: str) -> float:
        """Get the probability of a model succeeding on first attempt."""
        if model_name not in self.profiles:
            return 0.5
        return self.profiles[model_name].win_probability.get(problem_type, 0.5)


class AdaptiveEnsemble:
    """Ensemble that adapts its composition based on performance history."""

    def __init__(self, optimizer: RoleOptimizer):
        self.optimizer = optimizer
        self.current_roles: Dict[str, List[ModelRole]] = {}

    async def solve_problem(self, problem_type: str, available_models: List[str]):
        """Solve a problem using optimal role assignments."""
        # Get optimal roles based on historical performance
        self.current_roles = self.optimizer.get_optimal_roles(
            problem_type, available_models
        )

        # Execute solution strategy based on roles
        primary_model = next(
            (
                model
                for model, roles in self.current_roles.items()
                if ModelRole.PRIMARY in roles
            ),
            None,
        )

        if not primary_model:
            # Fall back to highest win probability if no clear primary
            win_probs = {
                model: self.optimizer.get_win_probability(model, problem_type)
                for model in available_models
            }
            primary_model = max(win_probs.items(), key=lambda x: x[1])[0]

        # TODO: Implement actual problem solving logic here

        return self.current_roles
