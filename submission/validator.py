"""Solution validation and submission module."""

import re
import logging
from typing import Optional
from pathlib import Path

import aiohttp
from bs4 import BeautifulSoup

from shared.utils import get_session_cookie, fetch_problem_text
from shared.errors import ValidationError, SessionError, SubmissionError
from shared.config import SUBMIT_SOLUTIONS
from .manager import SubmissionManager, SubmissionResult

logger = logging.getLogger(__name__)


class SolutionValidator:
    """Handles solution validation and submission workflow."""

    def __init__(self, workspace_dir: Optional[Path] = None):
        """Initialize the solution validator.

        Args:
            workspace_dir: Repository root used for submission history. Defaults to
                the directory containing this package.
        """
        if workspace_dir is None:
            workspace_dir = Path(__file__).resolve().parent.parent
        self.submission_manager = SubmissionManager(workspace_dir)
        self.logger = logging.getLogger(__name__)

    def _parse_wait_time(self, message: str) -> int:
        """Parse wait time from error message.
        
        Example messages:
        - "You have 30s left to wait"
        - "You have 5m 30s left to wait"
        """
        minutes = 0
        seconds = 0
        
        # Try to match "Xm Ys" format
        match = re.search(r"(\d+)m\s+(\d+)s", message)
        if match:
            minutes = int(match.group(1))
            seconds = int(match.group(2))
        else:
            # Try to match "Xs" format
            match = re.search(r"(\d+)s", message)
            if match:
                seconds = int(match.group(1))
                
        return minutes * 60 + seconds

    async def _parse_submission_response(self, html: str) -> SubmissionResult:
        """Parse the submission response HTML."""
        soup = BeautifulSoup(html, "html.parser")
        message = soup.article.text.strip() if soup.article else ""
        
        if "That's the right answer" in message:
            return SubmissionResult(
                was_correct=True,
                cooldown_seconds=None,
                error_message=None
            )
            
        if "You gave an answer too recently" in message:
            cooldown = self._parse_wait_time(message)
            return SubmissionResult(
                was_correct=False,
                cooldown_seconds=cooldown,
                error_message=f"Rate limited. Wait {cooldown} seconds before trying again."
            )
            
        if "That's not the right answer" in message:
            # Extract additional info if available
            if "too high" in message.lower():
                hint = "Answer was too high. Solution generation should:"
                hint += "\n- Verify loop boundary conditions and iteration limits"
                hint += "\n- Check for duplicate counting in aggregations"
                hint += "\n- Validate numeric operation precision and rounding"
                hint += "\n- Review array/sequence access indices"
            elif "too low" in message.lower():
                hint = "Answer was too low. Solution generation should:"
                hint += "\n- Ensure all valid cases are processed"
                hint += "\n- Verify early termination conditions"
                hint += "\n- Check for missing elements in collections"
                hint += "\n- Validate input parsing completeness"
            else:
                hint = "Incorrect answer. Solution generation should:"
                hint += "\n- Verify core algorithm implementation matches problem requirements"
                hint += "\n- Validate assumptions about input format and constraints"
                hint += "\n- Check handling of special cases and edge conditions"
                hint += "\n- Review mathematical operations and their order"
                
            return SubmissionResult(
                was_correct=False,
                cooldown_seconds=60,  # Default cooldown for wrong answers
                error_message=f"{hint}"
            )
            
        if "You don't seem to be solving the right level" in message:
            return SubmissionResult(
                was_correct=False,
                cooldown_seconds=None,
                error_message="Wrong level or already solved"
            )
            
        return SubmissionResult(
            was_correct=False,
            cooldown_seconds=None,
            error_message=f"Unknown response: {message}"
        )

    async def get_previous_answer(self, year: int, day: int, part: int) -> Optional[str]:
        """Get previously successful answer if problem was already solved.
        
        Args:
            year: Problem year
            day: Problem day
            part: Problem part (1 or 2)
            
        Returns:
            Previously successful answer if found, None otherwise
        """
        # Reuse the problem text fetch to check for previous answers
        _, _, previous_answer = await fetch_problem_text(year, day, part)
        return previous_answer

    async def submit_and_validate(
        self,
        year: int,
        day: int,
        part: int,
        answer: str,
    ) -> SubmissionResult:
        """Submit a solution and validate the response.
        
        Args:
            year: Problem year
            day: Problem day
            part: Problem part (1 or 2)
            answer: Solution to submit
            
        Returns:
            SubmissionResult with validation status and details
            
        Raises:
            SubmissionError: If there's an error submitting the solution
            SessionError: If there's an issue with the session
        """
        # First check if we have a previous answer
        previous_answer = await self.get_previous_answer(year, day, part)
        if previous_answer is not None:
            # Compare with our generated answer
            if answer == previous_answer:
                return SubmissionResult(
                    was_correct=True,
                    cooldown_seconds=None,
                    error_message="Matches previously successful answer"
                )
            else:
                return SubmissionResult(
                    was_correct=False,
                    cooldown_seconds=None,
                    error_message=f"Does not match previously successful answer: {previous_answer}"
                )

        # Check if solution submission is enabled
        if not SUBMIT_SOLUTIONS:
            return SubmissionResult(
                was_correct=False,
                cooldown_seconds=None,
                error_message="Solution submission is disabled. Set SUBMIT_SOLUTIONS=true in .env to enable."
            )

        # Check rate limiting. can_submit returns the remaining wait in seconds.
        can_submit, wait_seconds = self.submission_manager.can_submit(year, day, part)
        if not can_submit:
            return SubmissionResult(
                was_correct=False,
                cooldown_seconds=wait_seconds,
                error_message=f"Rate limited. Wait {wait_seconds}s before trying again."
            )

        # Submit solution
        url = f"https://adventofcode.com/{year}/day/{day}/answer"
        data = {"level": str(part), "answer": answer}

        try:
            session_cookie = get_session_cookie()
            cookies = {"session": session_cookie}

            async with aiohttp.ClientSession(cookies=cookies) as session:
                async with session.post(url, data=data) as response:
                    if response.status != 200:
                        if response.status in (302, 401):
                            raise SessionError("Session is invalid or expired")
                        raise SubmissionError(
                            f"Failed to submit solution: HTTP {response.status}"
                        )

                    html = await response.text()
                    result = await self._parse_submission_response(html)
                    
                    # Record the submission attempt for rate limiting
                    self.submission_manager.record_submission(year, day, part, result)
                    
                    return result

        except aiohttp.ClientError as e:
            raise SubmissionError(f"Network error submitting solution: {str(e)}")
        except Exception as e:
            raise SubmissionError(f"Error submitting solution: {str(e)}")

async def validate_solution(year: int, day: int, part: int, answer: str) -> None:
    """Validate a solution before submission.
    
    Args:
        year: Problem year
        day: Problem day
        part: Problem part (1 or 2)
        answer: Solution to validate
        
    Raises:
        ValidationError: If the solution is invalid
        SubmissionError: If solution submission is disabled
    """
    # Check if solution submission is enabled
    if not SUBMIT_SOLUTIONS:
        raise SubmissionError(
            "Solution submission is disabled. Set SUBMIT_SOLUTIONS=true in .env to enable."
        )

    validator = SolutionValidator()
    result = await validator.submit_and_validate(year, day, part, answer)
    if not result.was_correct:
        raise ValidationError(result.error_message)
