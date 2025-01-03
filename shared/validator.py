"""Solution validation and submission module."""

import os
import logging
from datetime import datetime, timedelta
from typing import Optional, Tuple
import aiohttp
from bs4 import BeautifulSoup

from .utils import get_session_cookie
from shared.config import ValidationError

logger = logging.getLogger(__name__)


class SubmissionError(ValidationError):
    """Solution submission error."""


async def submit_solution(
    year: int, day: int, part: int, answer: str
) -> Tuple[bool, str]:
    """Submit a solution for validation.

    Args:
        year: Puzzle year
        day: Puzzle day
        part: Puzzle part (1 or 2)
        answer: Solution to submit

    Returns:
        Tuple of (success, message)

    Raises:
        SubmissionError: If there's an error submitting the solution
    """
    # Check if submission is enabled
    if not os.getenv("SUBMIT_SOLUTIONS", "false").lower() == "true":
        return False, "Solution submission is disabled in .env"

    url = f"https://adventofcode.com/{year}/day/{day}/answer"
    data = {"level": str(part), "answer": answer}

    try:
        session_cookie = get_session_cookie()
        cookies = {"session": session_cookie}

        async with aiohttp.ClientSession(cookies=cookies) as session:
            async with session.post(url, data=data) as response:
                if response.status != 200:
                    raise SubmissionError(
                        f"Failed to submit solution: {response.status}"
                    )

                html = await response.text()
                soup = BeautifulSoup(html, "html.parser")
                message = soup.article.text.strip()

                if "That's the right answer" in message:
                    return True, "Correct answer!"
                elif "You gave an answer too recently" in message:
                    wait_time = message.split("You have ")[1].split(" left to wait.")[0]
                    return False, f"Rate limited. Wait {wait_time} before trying again."
                elif "That's not the right answer" in message:
                    return False, "Incorrect answer"
                elif "You don't seem to be solving the right level" in message:
                    return False, "Wrong level or already solved"
                else:
                    return False, f"Unknown response: {message}"

    except Exception as e:
        raise SubmissionError(f"Error submitting solution: {str(e)}")
