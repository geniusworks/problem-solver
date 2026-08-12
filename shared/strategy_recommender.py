"""Strategy recommendation for a problem, backed by the learning DB.

This was extracted from `SubmissionManager.get_recommended_strategies`. It is
the only part of the old submission machinery the solve loop actually uses:
`BaseSolver` calls it to seed generation with candidate strategies and their
measured effectiveness. It has nothing to do with submitting answers to AoC --
that (unwired) code lives in the `submission` package.
"""

import logging
from pathlib import Path
from typing import Any, Dict, List, Tuple, TYPE_CHECKING

if TYPE_CHECKING:
    # Annotation-only: shared.strategies is imported lazily at the call site to
    # keep module import cheap.
    from shared.strategies import Strategy

logger = logging.getLogger(__name__)


class StrategyRecommender:
    """Recommend solution strategies for a problem from its text + characteristics."""

    def __init__(self, workspace_dir: Path) -> None:
        self.workspace_dir = workspace_dir
        self.learning_dir = workspace_dir / "learning"
        self.learning_dir.mkdir(parents=True, exist_ok=True)

    def get_recommended_strategies(
        self, problem_text: str, characteristics: Dict[str, Any]
    ) -> Tuple[List["Strategy"], Dict[str, float]]:
        """Return (matched Strategy objects, per-strategy effectiveness scores).

        Effectiveness comes from the learning DB via StrategyOptimizer; on a
        cold start it is simply empty and generation proceeds unweighted.
        """
        from shared.strategies import (  # Lazy import
            get_strategies_for_problem,
            ProblemCategory,
            SOLUTION_STRATEGIES,
        )

        strategy_names = get_strategies_for_problem(problem_text)
        strategies: List["Strategy"] = []
        for category in ProblemCategory:
            if category in SOLUTION_STRATEGIES:
                for strategy in SOLUTION_STRATEGIES[category]:
                    if strategy.name in strategy_names:
                        strategies.append(strategy)

        from learning.optimizer import StrategyOptimizer  # Lazy import
        optimizer = StrategyOptimizer(self.learning_dir, self.workspace_dir)
        effectiveness = optimizer.get_strategy_effectiveness(
            characteristics, [s.name for s in strategies]
        )

        return strategies, effectiveness
