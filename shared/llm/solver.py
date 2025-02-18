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
from dataclasses import dataclass, field
from typing import List, Dict, Optional
from datetime import datetime
import time
from pathlib import Path

# Local application imports
from shared.quality.analyzer import CodeQualityAnalyzer, QualityMetrics, StyleMetrics
from .roles import ModelRole, RoleOptimizer, AdaptiveEnsemble
from .optimization import (
    CostOptimizer,
    ResourceManager,
    EnsembleOptimizer,
    ProblemComplexity,
)
from .performance_tracker import PerformanceTracker, ModelCategory

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


@dataclass
class AttemptHistory:
    """Tracks solution generation attempts."""
    failed_solutions: List[str] = field(default_factory=list)
    error_patterns: Dict[str, int] = field(default_factory=dict)
    models_tried: Dict[str, int] = field(default_factory=dict)
    total_attempts: int = 0
    start_time: datetime = field(default_factory=datetime.now)


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

    MAX_TOTAL_ATTEMPTS = 50  # Up to 50 total attempts
    MAX_MODEL_ATTEMPTS = 10  # Up to 10 attempts per model
    SOLUTION_TIMEOUT = 3600  # 1 hour timeout
    
    def __init__(
        self, 
        budget_per_problem: float = 0.1, 
        max_response_time: float = 30.0,
        performance_db: Optional[Path] = None
    ):
        self.logger = logging.getLogger(__name__)
        self.quality_analyzer = CodeQualityAnalyzer()
        self.attempt_history = AttemptHistory()

        # Initialize performance tracking
        self.performance_tracker = PerformanceTracker(
            performance_db or (Path(__file__).parent.parent.parent / 'learning' / 'solver.db')
        )
        
        # Initialize optimizers with performance data
        self.cost_optimizer = CostOptimizer(
            budget_per_problem=budget_per_problem,
            max_response_time=max_response_time
        )
        self.resource_manager = ResourceManager()
        self.ensemble_optimizer = EnsembleOptimizer(
            self.cost_optimizer, 
            self.resource_manager,
            self.performance_tracker
        )
        self.role_optimizer = RoleOptimizer(self.performance_tracker)

    def _should_continue_attempts(self, model_name: str) -> bool:
        """Check if we should continue making attempts with current model."""
        # Check total attempts limit
        if self.attempt_history.total_attempts >= self.MAX_TOTAL_ATTEMPTS:
            self.logger.warning("Reached maximum total attempts")
            return False

        # Get model's success rate and adjust attempts limit
        metrics = self.performance_tracker.get_model_metrics(model_name)
        if metrics:
            # Allow more attempts for models with higher success rates
            model_max_attempts = int(
                self.MAX_MODEL_ATTEMPTS * (1 + metrics.success_rate)
            )
            model_attempts = self.attempt_history.models_tried.get(model_name, 0)
            if model_attempts >= model_max_attempts:
                self.logger.warning(
                    f"Reached maximum attempts ({model_max_attempts}) for model {model_name}"
                )
                return False

        # Check timeout
        elapsed = (datetime.now() - self.attempt_history.start_time).total_seconds()
        if elapsed > self.SOLUTION_TIMEOUT:
            self.logger.warning("Solution generation timeout reached")
            return False

        return True

    def _record_attempt(
        self, 
        model_name: str, 
        solution: str, 
        success: bool, 
        error_message: Optional[str] = None,
        execution_time: float = 0.0,
        confidence: float = 0.0
    ):
        """Record a solution attempt and update performance metrics."""
        if not success:
            self.attempt_history.failed_solutions.append(solution)
            if error_message:
                self.attempt_history.error_patterns[error_message] = (
                    self.attempt_history.error_patterns.get(error_message, 0) + 1
                )
        
        self.attempt_history.models_tried[model_name] = (
            self.attempt_history.models_tried.get(model_name, 0) + 1
        )
        self.attempt_history.total_attempts += 1

        # Update performance metrics
        self.performance_tracker.record_attempt(
            model_name=model_name,
            category=ModelCategory.LOCAL_FAST,  # This should come from model registry
            problem_type="code_generation",
            latency=execution_time,
            success=success,
            confidence=confidence,
            solution_correct=success,
            execution_time=execution_time
        )

    def _create_history_prompt(self) -> str:
        """Create a prompt section from attempt history."""
        prompt = "\nPrevious Attempt Analysis:\n"
        
        # Add common error patterns with solutions
        if self.attempt_history.error_patterns:
            prompt += "\nCommon Error Patterns:\n"
            for error, count in self.attempt_history.error_patterns.items():
                prompt += f"- {error} (occurred {count} times)\n"
                # Add learned solutions from performance tracker
                solutions = self.performance_tracker.get_error_solutions(error)
                if solutions:
                    prompt += "  Suggested fixes:\n"
                    for solution in solutions:
                        prompt += f"  * {solution}\n"
        
        return prompt

    async def solve(
        self, problem_type: str, problem_text: str, available_models: List[str]
    ) -> Solution:
        """Generate a solution using the optimized model ensemble."""
        self.logger.info(
            f"Solving {problem_type} problem with {len(available_models)} available models"
        )
        
        # Reset attempt history
        self.attempt_history = AttemptHistory()
        
        # Estimate problem complexity
        complexity = self._estimate_complexity(problem_text)

        # Get optimal model tiers based on performance history
        model_tiers = self.ensemble_optimizer.get_model_tiers(
            available_models=available_models,
            problem_complexity=complexity,
            budget=self.cost_optimizer.budget_per_problem,
        )

        solution = None
        used_models = set()

        # Try each tier of models
        for tier, models in enumerate(model_tiers):
            self.logger.info(f"Trying model tier {tier + 1}")
            
            # Sort models by success rate within tier
            models_with_metrics = []
            for model in models:
                metrics = self.performance_tracker.get_model_metrics(model)
                success_rate = metrics.success_rate if metrics else 0.0
                models_with_metrics.append((model, success_rate))
            
            # Try models in order of success rate
            for model, _ in sorted(
                models_with_metrics, 
                key=lambda x: x[1], 
                reverse=True
            ):
                if model in used_models:
                    continue
                    
                used_models.add(model)
                
                while self._should_continue_attempts(model):
                    # Add history to prompt
                    enhanced_prompt = problem_text + self._create_history_prompt()
                    
                    # Generate solution
                    start_time = time.time()
                    solution = await self._generate_solution(
                        model, enhanced_prompt, problem_type
                    )
                    execution_time = time.time() - start_time
                    
                    # Record attempt
                    self._record_attempt(
                        model_name=model,
                        solution=solution.code if solution else "",
                        success=bool(solution and solution.success),
                        error_message=solution.error_message if solution else None,
                        execution_time=execution_time,
                        confidence=solution.confidence if solution else 0.0
                    )
                    
                    if solution and solution.success:
                        return solution

        # If we've exhausted all models
        if not solution or not solution.success:
            self.logger.warning("All models exhausted without success")
            
            # Get best performing models for this problem type
            suggested_models = self.performance_tracker.suggest_models(
                problem_type, max_latency=None
            )
            if suggested_models:
                self.logger.info(
                    "Consider prioritizing these models in the future: %s",
                    ", ".join(suggested_models)
                )

        return solution

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

    async def _generate_solution(
        self, model: str, prompt: str, problem_type: str
    ) -> Solution:
        """Generate a solution using a specific model and role."""
        return Solution(
            code="",
            confidence=0.0,
            quality_metrics=QualityMetrics(),
            execution_time=0.0,
            success=True,
            model_name=model,
            role=ModelRole.PRIMARY,
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
