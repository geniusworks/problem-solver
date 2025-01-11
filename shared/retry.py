"""Retry management for solution submissions."""

import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

from .submission import SubmissionResult

logger = logging.getLogger(__name__)


@dataclass
class RetryState:
    """State information for solution retries."""

    attempted_solutions: List[str]
    last_value: Optional[int]  # For numeric solutions
    upper_bound: Optional[int]  # Based on "too high" feedback
    lower_bound: Optional[int]  # Based on "too low" feedback
    retry_count: int
    last_attempt: datetime
    cooldown_until: Optional[datetime]

    @property
    def has_bounds(self) -> bool:
        """Check if we have any bounds information."""
        return self.upper_bound is not None or self.lower_bound is not None

    @property
    def is_numeric(self) -> bool:
        """Check if the solution appears to be numeric based on attempts."""
        return any(s.isdigit() for s in self.attempted_solutions)


class RetryManager:
    """Manages solution retry attempts with intelligent feedback handling."""

    def __init__(self, max_retries: int = 5, base_cooldown: int = 60):
        """Initialize the retry manager.

        Args:
            max_retries: Maximum number of retry attempts per problem
            base_cooldown: Base cooldown period in seconds
        """
        self.max_retries = max_retries
        self.base_cooldown = base_cooldown
        self.states: Dict[str, RetryState] = {}
        self.logger = logging.getLogger(__name__)

    def _get_state(self, problem_id: str) -> RetryState:
        """Get or create retry state for a problem."""
        if problem_id not in self.states:
            self.states[problem_id] = RetryState(
                attempted_solutions=[],
                last_value=None,
                upper_bound=None,
                lower_bound=None,
                retry_count=0,
                last_attempt=datetime.min,
                cooldown_until=None,
            )
        return self.states[problem_id]

    def can_retry(self, problem_id: str) -> Tuple[bool, Optional[timedelta]]:
        """Check if we can retry a solution for a problem.

        Args:
            problem_id: Unique identifier for the problem

        Returns:
            Tuple of (can_retry, time_remaining)
        """
        state = self._get_state(problem_id)

        # Check retry count
        if state.retry_count >= self.max_retries:
            return False, None

        # Check cooldown
        now = datetime.now()
        if state.cooldown_until and now < state.cooldown_until:
            return False, state.cooldown_until - now

        return True, None

    def record_attempt(
        self, problem_id: str, solution: str, result: SubmissionResult
    ) -> None:
        """Record a solution attempt and update state based on feedback.

        Args:
            problem_id: Unique identifier for the problem
            solution: The attempted solution
            result: Result of the submission attempt
        """
        state = self._get_state(problem_id)
        state.attempted_solutions.append(solution)
        state.retry_count += 1
        state.last_attempt = datetime.now()

        # Set cooldown
        if result.cooldown_seconds:
            state.cooldown_until = datetime.now() + timedelta(
                seconds=result.cooldown_seconds
            )

        # Update bounds for numeric solutions
        if solution.isdigit():
            value = int(solution)
            state.last_value = value

            if result.error_message:
                if "too high" in result.error_message.lower():
                    if (
                        state.upper_bound is None
                        or value < state.upper_bound
                    ):
                        state.upper_bound = value
                elif "too low" in result.error_message.lower():
                    if (
                        state.lower_bound is None
                        or value > state.lower_bound
                    ):
                        state.lower_bound = value

    def get_retry_hints(self, problem_id: str) -> Dict[str, str]:
        """Get hints for the next retry attempt.

        Args:
            problem_id: Unique identifier for the problem

        Returns:
            Dictionary of hint types and their values
        """
        state = self._get_state(problem_id)
        hints = {}

        if state.is_numeric:
            if state.upper_bound is not None:
                hints["upper_bound"] = str(state.upper_bound)
            if state.lower_bound is not None:
                hints["lower_bound"] = str(state.lower_bound)

        if state.attempted_solutions:
            hints["attempted"] = ", ".join(state.attempted_solutions)

        return hints

    def get_next_numeric_guess(self, problem_id: str) -> Optional[int]:
        """Get the next numeric guess based on bounds.

        Args:
            problem_id: Unique identifier for the problem

        Returns:
            Next numeric guess to try, or None if not applicable
        """
        state = self._get_state(problem_id)

        if not state.is_numeric or not state.has_bounds:
            return None

        if state.upper_bound is not None and state.lower_bound is not None:
            # Binary search between bounds
            return (state.upper_bound + state.lower_bound) // 2
        elif state.upper_bound is not None:
            # Try halfway between last value and upper bound
            last = state.last_value or 0
            return (last + state.upper_bound) // 2
        elif state.lower_bound is not None:
            # Try doubling the difference from lower bound
            last = state.last_value or state.lower_bound
            return last + (last - state.lower_bound)

        return None

    def reset(self, problem_id: str) -> None:
        """Reset retry state for a problem.

        Args:
            problem_id: Unique identifier for the problem
        """
        if problem_id in self.states:
            del self.states[problem_id]
