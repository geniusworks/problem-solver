"""The one function in the project that posts to adventofcode.com."""

import aiohttp

from shared import config
from shared.aoc import get_session_cookie
from shared.errors import SessionError, SubmissionError


async def post_answer(year: int, day: int, part: int, answer: str, timeout: int = 30) -> str:
    """Post one answer as the active account and return AoC's reply page.

    Only a named account posts (config.AOC_ACCOUNT): the maintainer's account, whose
    accepted answers are the 2024-2025 oracle, never does. Redirects are not followed, so a
    logged-out post shows itself as a redirect instead of a login page.
    """
    if not config.account_name():
        raise SubmissionError("Answers are posted only from a named account: set AOC_ACCOUNT")
    url = f"{config.AOC_BASE_URL}/{year}/day/{day}/answer"
    headers = {"Cookie": f"session={get_session_cookie()}", "User-Agent": config.USER_AGENT}
    async with aiohttp.ClientSession() as http:
        async with http.post(
            url, data={"level": str(part), "answer": answer}, headers=headers,
            allow_redirects=False, timeout=aiohttp.ClientTimeout(total=timeout),
        ) as response:
            if response.status in (301, 302, 303, 400, 401):
                raise SessionError(
                    f"The answer post was refused (HTTP {response.status}): the session in "
                    f"{config.aoc_session_variable()} has probably expired"
                )
            if response.status != 200:
                raise SubmissionError(f"Answer post failed: HTTP {response.status}")
            return await response.text()
