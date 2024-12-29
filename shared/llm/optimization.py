"""Cost-aware optimization and resource management."""

from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional, Set, Tuple
import numpy as np
import logging
from pathlib import Path
import json


class ResourceMetric(Enum):
    """Types of resource metrics to track."""

    COST = "cost"
    TIME = "time"
    ENERGY = "energy"
    MEMORY = "memory"


@dataclass
class ResourceUsage:
    """Resource usage metrics for a model."""

    cost_per_token: float
    avg_tokens_per_request: float
    avg_response_time: float
    energy_estimate: float  # Relative energy usage (1.0 = baseline)
    memory_required: int  # MB of RAM required


@dataclass
class ProblemComplexity:
    """Complexity metrics for a problem."""

    estimated_tokens: int
    time_constraint: Optional[float]  # seconds
    memory_constraint: Optional[int]  # MB
    required_techniques: Set[str]
    similar_problems: List[str]


class CostOptimizer:
    """Optimizes model selection based on cost and performance."""

    def __init__(
        self,
        budget_per_problem: float = 0.1,  # Default 10 cents per problem
        max_response_time: float = 30.0,
    ):  # Default 30 seconds max
        self.budget_per_problem = budget_per_problem
        self.max_response_time = max_response_time
        self.logger = logging.getLogger(__name__)

        # Load cached performance data if available
        self.cache_file = Path("model_performance_cache.json")
        self.performance_cache = self._load_cache()

    def _load_cache(self) -> Dict:
        """Load cached performance data."""
        if self.cache_file.exists():
            try:
                with open(self.cache_file) as f:
                    return json.load(f)
            except:
                return {}
        return {}

    def _save_cache(self):
        """Save performance data to cache."""
        with open(self.cache_file, "w") as f:
            json.dump(self.performance_cache, f)

    def calculate_roi(
        self,
        success_rate: float,
        quality_score: float,
        resource_usage: ResourceUsage,
        problem_complexity: ProblemComplexity,
    ) -> float:
        """Calculate ROI score for a model."""
        # Estimate cost
        estimated_cost = (
            resource_usage.cost_per_token * problem_complexity.estimated_tokens
        )

        # Estimate time
        estimated_time = resource_usage.avg_response_time * (
            problem_complexity.estimated_tokens / resource_usage.avg_tokens_per_request
        )

        # Calculate base ROI
        performance_score = success_rate * 0.7 + quality_score * 0.3

        # Penalize if exceeds constraints
        if (
            problem_complexity.time_constraint
            and estimated_time > problem_complexity.time_constraint
        ):
            performance_score *= 0.5

        if (
            problem_complexity.memory_constraint
            and resource_usage.memory_required > problem_complexity.memory_constraint
        ):
            performance_score *= 0.5

        # Calculate ROI (higher is better)
        roi = performance_score / (estimated_cost + 0.01)  # Avoid division by zero

        # Adjust ROI based on energy usage for local models
        if resource_usage.cost_per_token == 0:  # Local model
            roi /= resource_usage.energy_estimate

        return roi


class ResourceManager:
    """Manages resource allocation and tracking."""

    def __init__(self):
        self.usage_history: Dict[str, List[ResourceUsage]] = {}
        self.current_usage: Dict[str, ResourceUsage] = {}

    def update_usage(self, model: str, tokens: int, response_time: float, cost: float):
        """Update resource usage metrics."""
        if model not in self.usage_history:
            self.usage_history[model] = []

        usage = ResourceUsage(
            cost_per_token=cost / tokens if tokens > 0 else 0,
            avg_tokens_per_request=tokens,
            avg_response_time=response_time,
            energy_estimate=1.0,  # Default estimate
            memory_required=0,  # To be implemented
        )

        self.usage_history[model].append(usage)
        self.current_usage[model] = usage

    def get_optimal_allocation(
        self,
        available_budget: float,
        models: List[str],
        problem_complexity: ProblemComplexity,
    ) -> Dict[str, float]:
        """Get optimal budget allocation for models."""
        allocations = {}
        remaining_budget = available_budget

        # Sort models by ROI
        model_roi = [
            (model, self._calculate_model_roi(model, problem_complexity))
            for model in models
        ]
        model_roi.sort(key=lambda x: x[1], reverse=True)

        # Allocate budget proportionally to ROI
        total_roi = sum(roi for _, roi in model_roi)
        for model, roi in model_roi:
            if total_roi > 0:
                allocation = (roi / total_roi) * available_budget
            else:
                allocation = available_budget / len(models)

            allocations[model] = min(allocation, remaining_budget)
            remaining_budget -= allocations[model]

        return allocations

    def _calculate_model_roi(
        self, model: str, problem_complexity: ProblemComplexity
    ) -> float:
        """Calculate ROI for a model based on historical performance."""
        if model not in self.usage_history:
            return 0.0

        recent_usage = self.usage_history[model][-10:]  # Last 10 uses
        if not recent_usage:
            return 0.0

        avg_cost_per_token = np.mean([u.cost_per_token for u in recent_usage])
        avg_response_time = np.mean([u.avg_response_time for u in recent_usage])

        # Simple ROI calculation
        estimated_cost = avg_cost_per_token * problem_complexity.estimated_tokens
        if estimated_cost == 0:  # Local model
            return 1.0 / avg_response_time  # Prioritize faster local models
        else:
            return 1.0 / (estimated_cost * avg_response_time)


class EnsembleOptimizer:
    """Optimizes ensemble composition based on cost and performance."""

    def __init__(
        self, cost_optimizer: CostOptimizer, resource_manager: ResourceManager
    ):
        self.cost_optimizer = cost_optimizer
        self.resource_manager = resource_manager
        self.logger = logging.getLogger(__name__)

    async def optimize_ensemble(
        self,
        available_models: List[str],
        problem_complexity: ProblemComplexity,
        budget: float,
    ) -> List[str]:
        """Create optimal ensemble based on constraints."""
        # Get ROI scores for all models
        model_scores: List[Tuple[str, float]] = []
        for model in available_models:
            usage = self.resource_manager.current_usage.get(model)
            if not usage:
                continue

            # Get cached performance metrics
            perf = self.cost_optimizer.performance_cache.get(model, {})
            success_rate = perf.get("success_rate", 0.5)
            quality_score = perf.get("quality_score", 0.5)

            roi = self.cost_optimizer.calculate_roi(
                success_rate=success_rate,
                quality_score=quality_score,
                resource_usage=usage,
                problem_complexity=problem_complexity,
            )

            model_scores.append((model, roi))

        # Sort by ROI
        model_scores.sort(key=lambda x: x[1], reverse=True)

        # Select optimal ensemble
        selected_models = []
        remaining_budget = budget

        # Always include at least one local model if available
        local_model = next(
            (
                model
                for model, _ in model_scores
                if self.resource_manager.current_usage[model].cost_per_token == 0
            ),
            None,
        )
        if local_model:
            selected_models.append(local_model)

        # Add highest ROI models until we hit budget or size limit
        for model, roi in model_scores:
            if model in selected_models:
                continue

            usage = self.resource_manager.current_usage[model]
            estimated_cost = usage.cost_per_token * problem_complexity.estimated_tokens

            if estimated_cost <= remaining_budget:
                selected_models.append(model)
                remaining_budget -= estimated_cost

                if len(selected_models) >= 3:  # Maximum ensemble size
                    break

        return selected_models
