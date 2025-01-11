"""Solution validation and submission module."""

import os
import re
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict
import aiohttp
from bs4 import BeautifulSoup

from .utils import get_session_cookie
from shared.config import ValidationError, SessionError
from .submission import SubmissionManager, SubmissionResult

logger = logging.getLogger(__name__)


class SubmissionError(ValidationError):
    """Solution submission error."""


class SolutionValidator:
    """Handles solution validation and submission workflow."""

    def __init__(self):
        """Initialize the solution validator."""
        self.submission_manager = SubmissionManager()
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
                hint = "Answer was too high. Review your solution for:"
                hint += "\n- Off-by-one errors in loop bounds"
                hint += "\n- Double-counting in aggregations"
                hint += "\n- Integer division rounding"
            elif "too low" in message.lower():
                hint = "Answer was too low. Review your solution for:"
                hint += "\n- Missing edge cases"
                hint += "\n- Incomplete iterations"
                hint += "\n- Early termination conditions"
            else:
                hint = "Incorrect answer. Review your solution for:"
                hint += "\n- Logic errors in the core algorithm"
                hint += "\n- Input parsing assumptions"
                hint += "\n- Edge cases in the problem description"
                
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
        # Check if submission is enabled
        if not os.getenv("SUBMIT_SOLUTIONS", "false").lower() == "true":
            return SubmissionResult(
                was_correct=False,
                cooldown_seconds=None,
                error_message="Solution submission is disabled in .env"
            )

        # Problem identifier
        problem_id = f"{year}_day{day}_part{part}"

        # Check rate limiting
        can_submit, wait_time = self.submission_manager.can_submit(problem_id)
        if not can_submit:
            return SubmissionResult(
                was_correct=False,
                cooldown_seconds=int(wait_time.total_seconds()),
                error_message=f"Rate limited. Wait {wait_time} before trying again."
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
                    self.submission_manager.record_submission(problem_id, result)
                    
                    return result

        except aiohttp.ClientError as e:
            raise SubmissionError(f"Network error submitting solution: {str(e)}")
        except Exception as e:
            raise SubmissionError(f"Error submitting solution: {str(e)}")
