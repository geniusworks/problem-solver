"""
Problem solver using optimized model ensemble.

This module implements an adaptive problem-solving system that uses multiple
language models in an optimized ensemble. It dynamically selects and combines
models based on their performance characteristics, cost constraints, and
specific problem requirements.

Classes:
    Solution: Represents a generated solution with associated metadata
    AdaptiveSolver: Main solver class that orchestrates the solution generation process

Typical usage example:
    solver = AdaptiveSolver(budget_per_problem=0.1)
    solution = solver.solve("advent_of_code", problem_text, ["gpt-4", "claude-3"])
"""

# Standard library imports
import logging
from dataclasses import dataclass
from typing import List

# Local application imports
from shared.quality.analyzer import CodeQualityAnalyzer, QualityMetrics, StyleMetrics
from .roles import ModelRole, RoleOptimizer, AdaptiveEnsemble
from .optimization import (
    CostOptimizer,
    ResourceManager,
    EnsembleOptimizer,
    ProblemComplexity,
)

# Third-party imports


@dataclass
class Solution:
    """
    A generated solution with associated metadata.

    Attributes:
        code: The actual solution code
        confidence: Confidence score (0-1) in the solution's correctness
        quality_metrics: Code quality metrics from static analysis
        execution_time: Time taken to generate the solution in seconds
        success: Whether the solution was successful
        model_name: Name of the model that generated this solution
        role: Role of the model in the ensemble
    """

    code: str
    confidence: float
    quality_metrics: QualityMetrics = QualityMetrics()
    execution_time: float = 0.0
    success: bool = True
    model_name: str = ""
    role: ModelRole = ModelRole.PRIMARY


class AdaptiveSolver:
    """
    Adaptive problem solver using optimized model ensemble.

    This class manages the solution generation process by:
    1. Analyzing problem complexity
    2. Selecting appropriate models based on constraints
    3. Generating solutions using selected models
    4. Validating and improving solutions
    5. Tracking performance metrics

    Attributes:
        budget_per_problem: Maximum cost allowed per problem in USD
        max_response_time: Maximum time to wait for model response in seconds
        quality_analyzer: Static code analysis tool
        cost_optimizer: Manages cost constraints
        resource_manager: Manages compute resources
        ensemble_optimizer: Optimizes model ensemble selection
        role_optimizer: Manages model roles
        ensemble: Group of models working together
    """

    def __init__(
        self, budget_per_problem: float = 0.1, max_response_time: float = 30.0
    ):
        self.logger = logging.getLogger(__name__)
        self.quality_analyzer = CodeQualityAnalyzer()

        # Initialize optimizers
        self.cost_optimizer = CostOptimizer(
            budget_per_problem=budget_per_problem, max_response_time=max_response_time
        )
        self.resource_manager = ResourceManager()
        self.ensemble_optimizer = EnsembleOptimizer(
            self.cost_optimizer, self.resource_manager
        )
        self.role_optimizer = RoleOptimizer()

        self.ensemble = AdaptiveEnsemble(self.role_optimizer)

    def solve(
        self, problem_type: str, problem_text: str, available_models: List[str]
    ) -> Solution:
        """Generate a solution using the optimized model ensemble."""
        self.logger.info(
            f"Solving {problem_type} problem with {len(available_models)} available models"
        )
        # Estimate problem complexity
        complexity = self._estimate_complexity(problem_text)

        # Get optimal ensemble
        selected_models = self.ensemble_optimizer.optimize_ensemble(
            available_models=available_models,
            problem_complexity=complexity,
            budget=self.cost_optimizer.budget_per_problem,
        )

        if not selected_models:
            self.logger.error("No suitable models available")
            return None

        # Get role assignments
        roles = self.role_optimizer.get_optimal_roles(
            problem_type=problem_type, available_models=selected_models
        )

        # Try primary solution
        primary_model = next(
            (
                model
                for model, model_roles in roles.items()
                if ModelRole.PRIMARY in model_roles
            ),
            selected_models[0],  # Fallback to first model
        )

        primary_solution = self._generate_solution()

        if not primary_solution or not primary_solution.success:
            self.logger.warning(f"Primary solution failed: {primary_model}")
            # Try backup model if available
            backup_model = next(
                (
                    model
                    for model, model_roles in roles.items()
                    if ModelRole.BACKUP in model_roles
                ),
                None,
            )
            if backup_model:
                primary_solution = self._generate_solution()

        if not primary_solution:
            return None

        # Get reviewers
        reviewers = [
            model
            for model, model_roles in roles.items()
            if ModelRole.REVIEWER in model_roles
        ]

        # Review and improve solution
        current_solution = primary_solution
        for reviewer in reviewers:
            improved_solution = self._review_solution()

            if (
                improved_solution
                and improved_solution.quality_metrics.style_metrics.style_violations
                < current_solution.quality_metrics.style_metrics.style_violations
            ):
                current_solution = improved_solution

        # Validate solution quality
        quality_analyzer = CodeQualityAnalyzer()
        quality_metrics = quality_analyzer.analyze(current_solution.code)

        if quality_metrics.style_metrics.style_violations > 5:
            self.logger.warning("Solution has too many style violations")
            return None

        # Update performance metrics
        self._update_metrics(current_solution, problem_type)

        return current_solution

    def _estimate_complexity(self, problem_text: str) -> ProblemComplexity:
        """Estimate problem complexity metrics."""
        # Simple estimation based on text length and keywords
        tokens = len(problem_text.split())
        techniques = set()

        # Detect required techniques from keywords
        if "dynamic programming" in problem_text.lower():
            techniques.add("dynamic_programming")
        if "graph" in problem_text.lower():
            techniques.add("graph_theory")
        if "tree" in problem_text.lower():
            techniques.add("tree_traversal")
        # Add more technique detection as needed

        return ProblemComplexity(
            estimated_tokens=tokens * 2,  # Rough estimate for solution size
            time_constraint=None,  # No specific constraint
            memory_constraint=None,  # No specific constraint
            required_techniques=techniques,
            similar_problems=[],  # To be implemented
        )

    def _generate_solution(self, **kwargs) -> Solution:
        """Generate a solution using a specific model and role."""
        return Solution(
            code="",
            confidence=0.0,
            quality_metrics=QualityMetrics(),
            execution_time=0.0,
            success=True,
            model_name="",
            role=ModelRole.PRIMARY,
        )

    def _review_solution(self, **kwargs) -> Solution:
        """Review and improve a solution."""
        return Solution(
            code="",
            confidence=0.0,
            quality_metrics=QualityMetrics(),
            execution_time=0.0,
            success=True,
            model_name="",
            role=ModelRole.REVIEWER,
        )

    def _update_metrics(self, solution: Solution, problem_type: str):
        """Update performance metrics for the model."""
        self.role_optimizer.update_profile(
            model_name=solution.model_name,
            problem_type=problem_type,
            role=solution.role,
            success=solution.success,
            quality_score=solution.quality_metrics.style_metrics.style_violations
            / 10.0,
            was_first_attempt=(solution.role == ModelRole.PRIMARY),
        )

        self.resource_manager.update_usage(
            model=solution.model_name,
            tokens=len(solution.code.split()),  # Simple approximation
            response_time=solution.execution_time,
            cost=(
                0.0 if "local" in solution.model_name.lower() else 0.01
            ),  # Example cost
        )
