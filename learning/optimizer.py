"""Strategy optimization and feedback system."""

import dataclasses
import json
import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Optional, Set, Any
from pathlib import Path

from shared.strategies import Strategy, ProblemCategory, SOLUTION_STRATEGIES, get_strategies_for_problem
from .database import LearningDatabase

logger = logging.getLogger(__name__)

@dataclass
class StrategyResult:
    """Records the effectiveness of a strategy."""
    strategy_name: str
    problem_characteristics: Dict[str, Any]
    execution_time: float
    success: bool
    memory_usage: Optional[float] = None

@dataclass
class StrategyResultForProblem:
    """Records the effectiveness of strategies for a specific problem."""
    problem_id: str
    strategies_used: List[str]
    success: bool
    execution_time: float
    memory_usage: float
    attempts: int
    failure_points: List[str]
    timestamp: datetime = dataclasses.field(default_factory=datetime.now)

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
        from .database import LearningDatabase  # Lazy import
        self.db = LearningDatabase(workspace_dir)
        self.problem_results: List[StrategyResultForProblem] = []

    def _load_results(self) -> None:
        """Load strategy results from storage."""
        if self.results_file.exists():
            with open(self.results_file) as f:
                data = json.load(f)
                self.results = [StrategyResult(**r) for r in data]

    def _save_results(self) -> None:
        """Save strategy results to storage."""
        with open(self.results_file, 'w') as f:
            json.dump([dataclasses.asdict(r) for r in self.results], f)

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
        self.db.add_problem_result(result)

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
        scores = {}
        for strategy in strategy_names:
            relevant_results = [
                r for r in self.results 
                if r.strategy_name == strategy
                and all(
                    r.problem_characteristics.get(k) == v 
                    for k, v in characteristics.items()
                )
            ]
            if relevant_results:
                success_rate = sum(1 for r in relevant_results if r.success) / len(relevant_results)
                avg_time = sum(r.execution_time for r in relevant_results) / len(relevant_results)
                scores[strategy] = 0.7 * success_rate + 0.3 * (1 / (1 + avg_time))
            else:
                scores[strategy] = 0.5  # Default score for untried strategies
        return scores

    def analyze_failures(self) -> Dict[str, Dict[str, int]]:
        """Analyze common failure patterns and their relationships to strategies."""
        failure_patterns = {}
        for result in self.problem_results:
            if not result.success:
                for strategy in result.strategies_used:
                    if strategy not in failure_patterns:
                        failure_patterns[strategy] = {}
                    for point in result.failure_points:
                        failure_patterns[strategy][point] = failure_patterns[strategy].get(point, 0) + 1
        return failure_patterns

    def get_recommended_strategies(
            self, problem_characteristics: Dict[str, float]
        ) -> List[tuple[str, float]]:
        """Get weighted strategy recommendations for a problem."""
        # Build a simple text hint from characteristic keys for keyword matching
        text_hint = " ".join(map(str, problem_characteristics.keys()))
        strategy_names = get_strategies_for_problem(text_hint)
        scores = self.get_strategy_effectiveness(problem_characteristics, strategy_names)
        return sorted([(name, scores[name]) for name in strategy_names], key=lambda x: x[1], reverse=True)

    def update_strategy_weights(self) -> None:
        """Update strategy weights based on their effectiveness."""
        all_characteristics = {
            k: v for r in self.results 
            for k, v in r.problem_characteristics.items()
        }
        for strategy in SOLUTION_STRATEGIES:
            scores = self.get_strategy_effectiveness(all_characteristics, [strategy.name])
            if strategy.name in scores:
                strategy.weight = scores[strategy.name]
