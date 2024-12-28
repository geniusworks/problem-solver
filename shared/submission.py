"""Module for managing solution submissions and rate limiting."""

import json
import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Dict, Optional

logger = logging.getLogger(__name__)

@dataclass
class SubmissionResult:
    """Result of a solution submission."""
    was_correct: bool
    cooldown_seconds: Optional[int]
    error_message: Optional[str]

class SubmissionManager:
    """Manages solution submissions and rate limiting."""

    def __init__(self, history_file: str = "submission_history.json"):
        """Initialize the submission manager.
        
        Args:
            history_file: Path to the submission history file.
        """
        self.history_file = history_file
        self.last_submission: Dict[str, datetime] = {}
        self.cooldown_periods: Dict[str, timedelta] = {}
        self._load_history()

    def _load_history(self) -> None:
        """Load submission history from storage."""
        try:
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
        except FileNotFoundError:
            pass
        except Exception as e:
            logger.error("Failed to load submission history: %s", str(e))

    def _save_history(self) -> None:
        """Save submission history to storage."""
        try:
            data = {
                "last_submission": {
                    k: v.isoformat()
                    for k, v in self.last_submission.items()
                },
                "cooldown_periods": {
                    k: v.total_seconds()
                    for k, v in self.cooldown_periods.items()
                }
            }
            with open(self.history_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.error("Failed to save submission history: %s", str(e))

    def can_submit(self, problem_id: str) -> tuple[bool, Optional[timedelta]]:
        """Check if we can submit a solution for a problem.
        
        Args:
            problem_id: Unique identifier for the problem (e.g., "2021_day1_part1")
            
        Returns:
            Tuple of (can_submit, time_remaining)
        """
        if problem_id not in self.last_submission:
            return True, None

        cooldown = self.cooldown_periods.get(problem_id, timedelta(seconds=0))
        time_since_last = datetime.now() - self.last_submission[problem_id]
        
        if time_since_last < cooldown:
            return False, cooldown - time_since_last
        return True, None

    def record_submission(
        self, problem_id: str, result: SubmissionResult
    ) -> None:
        """Record a submission attempt and update cooldown if necessary.
        
        Args:
            problem_id: Unique identifier for the problem
            result: Result of the submission
        """
        self.last_submission[problem_id] = datetime.now()
        
        if result.cooldown_seconds:
            self.cooldown_periods[problem_id] = timedelta(
                seconds=result.cooldown_seconds
            )
        
        self._save_history()

    def get_cooldown_period(self, problem_id: str) -> Optional[timedelta]:
        """Get the current cooldown period for a problem.
        
        Args:
            problem_id: Unique identifier for the problem
            
        Returns:
            Current cooldown period or None if not set
        """
        return self.cooldown_periods.get(problem_id)
