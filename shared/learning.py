"""Learning system for strategy optimization and feedback."""

import dataclasses
import json
import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Optional, Set, Any
from pathlib import Path

from .database import LearningDatabase
from .strategies import Strategy, ProblemCategory, SOLUTION_STRATEGIES, get_strategies_for_problem

logger = logging.getLogger(__name__)

@dataclass
class StrategyResult:
    """Records the effectiveness of a strategy."""
    strategy_name: str
    problem_characteristics: Dict[str, Any]
    execution_time: float
    memory_usage: float
    was_successful: bool

@dataclass
class StrategyResultForProblem:
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
    """Learns and optimizes strategy selection."""
    
    def __init__(self, learning_dir: Path, workspace_dir: Path):
        """Initialize the strategy optimizer.
        
        Args:
            learning_dir: Directory for storing learning data
            workspace_dir: Directory for storing database
        """
        self.learning_dir = learning_dir
        self.learning_dir.mkdir(parents=True, exist_ok=True)
        self.results_file = learning_dir / "strategy_results.json"
        self.results: List[StrategyResult] = []
        self._load_results()
        
        self.workspace_dir = workspace_dir
        self.db = LearningDatabase(workspace_dir)
        self.problem_results: List[StrategyResultForProblem] = []

    def _load_results(self) -> None:
        """Load strategy results from storage."""
        if self.results_file.exists():
            with open(self.results_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                self.results = [StrategyResult(**r) for r in data]
                
    def _save_results(self) -> None:
        """Save strategy results to storage."""
        with open(self.results_file, "w", encoding="utf-8") as f:
            json.dump([dataclasses.asdict(r) for r in self.results], f, indent=2)
            
    def record_result(self, result: StrategyResult) -> None:
        """Record the result of using a strategy.
        
        Args:
            result: The strategy execution result
        """
        self.results.append(result)
        self._save_results()

    def record_problem_result(self, result: StrategyResultForProblem) -> None:
        """Record a new strategy result."""
        self.problem_results.append(result)
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

    def get_strategy_effectiveness(
        self, characteristics: Dict[str, Any], strategy_names: List[str]
    ) -> Dict[str, float]:
        """Get effectiveness scores for strategies.
        
        Args:
            characteristics: Problem characteristics
            strategy_names: List of strategy names to get scores for
            
        Returns:
            Dict mapping strategy names to effectiveness scores
        """
        # For now just return equal weights
        # TODO: Implement actual learning based on results
        return {name: 1.0 for name in strategy_names}

    def analyze_failures(self) -> Dict[str, List[str]]:
        """Analyze common failure patterns and their relationships to strategies."""
        failure_patterns: Dict[str, List[str]] = {}
        
        # Group failures by strategy combinations
        for result in self.problem_results:
            if not result.success:
                strategy_key = ','.join(sorted(result.strategies_used))
                if strategy_key not in failure_patterns:
                    failure_patterns[strategy_key] = []
                failure_patterns[strategy_key].extend(result.failure_points)
        
        # Deduplicate and sort failure points
        return {k: sorted(set(v)) for k, v in failure_patterns.items()}

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

    def update_strategy_weights(self) -> None:
        """Update strategy weights based on their effectiveness."""
        effectiveness = self.get_strategy_effectiveness({}, list(SOLUTION_STRATEGIES.keys()))
        
        # Calculate new weights based on success rate and performance
        new_weights = {}
        for strategy, metrics in effectiveness.items():
            # Combine metrics into a single weight
            # Higher success rate and lower resource usage = higher weight
            weight = (
                metrics * 0.6 +  # Prioritize success
                0.2 +  # Lower time is better
                0.2  # Lower memory is better
            )
            new_weights[strategy] = {
                'weight': weight,
                'success_rate': metrics,
                'avg_execution_time': 0.0,
                'avg_memory_usage': 0.0
            }
        
        # Update database
        if new_weights:
            self.db.update_strategy_weights(new_weights)
