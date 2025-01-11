"""Learning system for strategy optimization and feedback."""

import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Optional, Set
from pathlib import Path

from .database import LearningDatabase

logger = logging.getLogger(__name__)

@dataclass
class StrategyResult:
    """Records the effectiveness of strategies for a specific problem."""
    problem_id: str  # Format: "year/day/part"
    strategies_used: List[str]
    success: bool
    execution_time: float
    memory_usage: float
    attempts: int
    failure_points: List[str]
    timestamp: datetime = datetime.now()


class StrategyOptimizer:
    """Analyzes and optimizes strategy effectiveness."""

    def __init__(self, workspace_dir: Path):
        self.workspace_dir = workspace_dir
        self.db = LearningDatabase(workspace_dir)
        self.results: List[StrategyResult] = []

    def record_result(self, result: StrategyResult) -> None:
        """Record a new strategy result."""
        self.results.append(result)
        self.db.store_result(
            result.problem_id,
            result.strategies_used,
            result.success,
            {
                'execution_time': result.execution_time,
                'memory_usage': result.memory_usage
            },
            result.attempts,
            result.failure_points
        )
        self.update_strategy_weights()

    def analyze_failures(self) -> Dict[str, List[str]]:
        """Analyze common failure patterns and their relationships to strategies."""
        failure_patterns: Dict[str, List[str]] = {}
        
        # Group failures by strategy combinations
        for result in self.results:
            if not result.success:
                strategy_key = ','.join(sorted(result.strategies_used))
                if strategy_key not in failure_patterns:
                    failure_patterns[strategy_key] = []
                failure_patterns[strategy_key].extend(result.failure_points)
        
        # Deduplicate and sort failure points
        return {k: sorted(set(v)) for k, v in failure_patterns.items()}

    def get_strategy_effectiveness(self) -> Dict[str, Dict[str, float]]:
        """Calculate effectiveness metrics for each strategy."""
        return self.db.get_strategy_weights()

    def update_strategy_weights(self) -> None:
        """Update strategy weights based on their effectiveness."""
        effectiveness = self.get_strategy_effectiveness()
        
        # Calculate new weights based on success rate and performance
        new_weights = {}
        for strategy, metrics in effectiveness.items():
            # Combine metrics into a single weight
            # Higher success rate and lower resource usage = higher weight
            weight = (
                metrics['success_rate'] * 0.6 +  # Prioritize success
                (1 / (metrics['avg_execution_time'] + 1)) * 0.2 +  # Lower time is better
                (1 / (metrics['avg_memory_usage'] + 1)) * 0.2  # Lower memory is better
            )
            new_weights[strategy] = {
                'weight': weight,
                'success_rate': metrics['success_rate'],
                'avg_execution_time': metrics['avg_execution_time'],
                'avg_memory_usage': metrics['avg_memory_usage']
            }
        
        # Update database
        if new_weights:
            self.db.update_strategy_weights(new_weights)

    def get_recommended_strategies(self, problem_characteristics: Dict[str, float]) -> List[str]:
        """Get weighted strategy recommendations for a problem."""
        # First, check for similar problems
        similar_problems = self.db.get_similar_problems(problem_characteristics)
        
        # Get successful strategies from similar problems
        strategy_scores: Dict[str, float] = {}
        for problem in similar_problems:
            if problem['successful_strategies']:
                similarity = problem['similarity']
                for strategy in problem['successful_strategies']:
                    if strategy not in strategy_scores:
                        strategy_scores[strategy] = 0.0
                    strategy_scores[strategy] += similarity
        
        # Combine with general strategy weights
        weights = self.db.get_strategy_weights()
        for strategy, metrics in weights.items():
            if strategy not in strategy_scores:
                strategy_scores[strategy] = 0.0
            strategy_scores[strategy] += metrics['weight'] * 0.5  # Balance with similarity scores
        
        # Sort and return top strategies
        sorted_strategies = sorted(
            strategy_scores.items(),
            key=lambda x: x[1],
            reverse=True
        )
        return [s[0] for s in sorted_strategies]
