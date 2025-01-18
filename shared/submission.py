"""Module for managing solution submissions and rate limiting."""

import json
import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Optional, List, Tuple, Any

from .learning import StrategyResult, StrategyOptimizer, Strategy, ProblemCategory, SOLUTION_STRATEGIES, get_strategies_for_problem

logger = logging.getLogger(__name__)


@dataclass
class SubmissionResult:
    """Result of a solution submission."""
    was_correct: bool
    cooldown_seconds: Optional[int]
    error_message: Optional[str]
    execution_metrics: Optional[Dict[str, float]] = None
    strategies_used: Optional[List[str]] = None


class SubmissionManager:
    """Manages solution submissions, rate limiting, and learning."""

    def __init__(self, workspace_dir: Path):
        """Initialize the submission manager.

        Args:
            workspace_dir: Path to the workspace directory
        """
        self.workspace_dir = workspace_dir
        self.history_file = workspace_dir / "submission_history.json"
        self.last_submission: Dict[str, datetime] = {}
        self.cooldown_periods: Dict[str, timedelta] = {}
        self.strategy_optimizer = StrategyOptimizer(
            workspace_dir / "learning",
            workspace_dir
        )
        self._load_history()

    def _load_history(self) -> None:
        """Load submission history from storage."""
        try:
            if self.history_file.exists():
                with open(self.history_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.last_submission = {
                        k: datetime.fromisoformat(v)
                        for k, v in data.get("last_submission", {}).items()
                    }
                    self.cooldown_periods = {
                        k: timedelta(seconds=v)
                        for k, v in data.get("cooldown_periods", {}).items()
                    }
        except Exception as e:
            logger.error("Failed to load submission history: %s", str(e))

    def _save_history(self) -> None:
        """Save submission history to storage."""
        try:
            self.history_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.history_file, "w", encoding="utf-8") as f:
                json.dump(
                    {
                        "last_submission": {
                            k: v.isoformat()
                            for k, v in self.last_submission.items()
                        },
                        "cooldown_periods": {
                            k: v.total_seconds()
                            for k, v in self.cooldown_periods.items()
                        },
                    },
                    f,
                    indent=2,
                )
        except Exception as e:
            logger.error("Failed to save submission history: %s", str(e))

    def record_submission(
        self,
        year: int,
        day: int,
        part: int,
        result: SubmissionResult,
        execution_metrics: Optional[Dict[str, float]] = None,
        strategies_used: Optional[List[str]] = None
    ) -> None:
        """Record a submission attempt and update learning system."""
        problem_key = f"{year}/{day}/{part}"
        
        # Update submission history
        self.last_submission[problem_key] = datetime.now()
        if result.cooldown_seconds:
            self.cooldown_periods[problem_key] = timedelta(seconds=result.cooldown_seconds)
        self._save_history()

        # Record strategy result if metrics available
        if execution_metrics and strategies_used:
            strategy_result = StrategyResult(
                problem_id=problem_key,
                strategies_used=strategies_used,
                success=result.was_correct,
                execution_time=execution_metrics.get('execution_time', 0.0),
                memory_usage=execution_metrics.get('memory_usage', 0.0),
                attempts=self._get_attempt_count(problem_key),
                failure_points=[result.error_message] if result.error_message else []
            )
            self.strategy_optimizer.record_result(strategy_result)

    def get_recommended_strategies(
        self, problem_text: str, characteristics: Dict[str, Any]
    ) -> Tuple[List[Strategy], Dict[str, float]]:
        """Get recommended strategies based on problem characteristics.
        
        Args:
            problem_text: The problem description text
            characteristics: Problem characteristics from analysis
            
        Returns:
            Tuple of (list of strategies, dict of strategy effectiveness scores)
        """
        # Get strategy names from problem text
        strategy_names = get_strategies_for_problem(problem_text)
        
        # Look up the actual Strategy objects
        strategies = []
        for category in ProblemCategory:
            if category in SOLUTION_STRATEGIES:
                for strategy in SOLUTION_STRATEGIES[category]:
                    if strategy.name in strategy_names:
                        strategies.append(strategy)
        
        # Get effectiveness scores from optimizer
        effectiveness = self.strategy_optimizer.get_strategy_effectiveness(
            characteristics, [s.name for s in strategies]
        )
        
        return strategies, effectiveness

    def _get_attempt_count(self, problem_key: str) -> int:
        """Get the number of submission attempts for a problem."""
        return sum(1 for result in self.strategy_optimizer.results 
                  if result.problem_id == problem_key)

    def can_submit(self, year: int, day: int, part: int) -> Tuple[bool, Optional[int]]:
        """Check if we can submit a solution now."""
        problem_key = f"{year}/{day}/{part}"
        
        if problem_key not in self.last_submission:
            return True, None
            
        last_time = self.last_submission[problem_key]
        cooldown = self.cooldown_periods.get(problem_key, timedelta(seconds=0))
        
        if datetime.now() - last_time < cooldown:
            wait_seconds = int((cooldown - (datetime.now() - last_time)).total_seconds())
            return False, wait_seconds
            
        return True, None

    async def submit_solution(
        self, year: int, day: int, part: int, answer: str
    ) -> Tuple[bool, str]:
        """Submit a solution to Advent of Code.

        Args:
            year: Problem year
            day: Problem day
            part: Problem part
            answer: Solution answer

        Returns:
            Tuple of (success, message)
        """
        # TODO: Implement actual submission to AoC
        # For now, just simulate submission
        logging.info(f"Would submit answer '{answer}' for {year} day {day} part {part}")
        return True, "Submission successful (simulated)"
