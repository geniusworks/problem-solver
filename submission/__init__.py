"""AoC answer submission -- real, tested-in-isolation, and deliberately UNWIRED.

Nothing in the solve loop calls into this package. It is the genuine
Advent-of-Code submitter (posts to /answer, parses the response, respects the
cooldown) plus the rate-limit/history bookkeeping it needs, kept for the
solver phase (Milestone F) per "platform now, solver later". It is isolated
here rather than left threaded through the solver so that "not in the solve
loop yet" is visible in the layout, not just a comment.

To wire it, a caller would gate on config.SUBMIT_SOLUTIONS and hold a fresh
AOC_SESSION; see submit_and_validate / validate_solution.
"""

from .manager import SubmissionManager, SubmissionResult
from .validator import SolutionValidator, validate_solution

__all__ = [
    "SubmissionManager",
    "SubmissionResult",
    "SolutionValidator",
    "validate_solution",
]
