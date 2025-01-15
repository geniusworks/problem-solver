"""Utility functions for Advent of Code solutions."""

import json
import logging
import time
import os
import asyncio
import re
from datetime import datetime
from pathlib import Path
from typing import Tuple, Dict, Any, Optional, List
from dataclasses import dataclass
from enum import Enum, auto

import aiohttp
import requests
from bs4 import BeautifulSoup
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from shared import config
from shared.errors import ValidationError, SessionError, InputError
from shared.parser import parse_problem_text as _parse_problem_text

logger = logging.getLogger(__name__)

# Configure retry strategy
session = requests.Session()
session.headers.update(
    {
        "User-Agent": config.USER_AGENT,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "keep-alive",
        "Host": "adventofcode.com",
        "Sec-Fetch-Site": "none",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Dest": "document",
    }
)

retry_strategy = Retry(
    total=5,
    backoff_factor=2,
    status_forcelist=[429, 500, 502, 503, 504],
    allowed_methods=["GET"],
)
adapter = HTTPAdapter(max_retries=retry_strategy)
session.mount("https://", adapter)
session.mount("http://", adapter)


def setup_logging(year: Optional[int] = None, day: Optional[int] = None):
    """Configure logging for the application."""
    # Configure basic logging with stream handler only
    logging.basicConfig(
        level=os.getenv("LOG_LEVEL", "INFO"),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[logging.StreamHandler()]
    )
    
    # Set specific logger levels
    logging.getLogger("blib2to3").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.INFO)
    logging.getLogger("asyncio").setLevel(logging.INFO)


def get_problem_year_day() -> Tuple[int, int]:
    """
    Get the current Advent of Code year and day.
    If we're in December, use the current year and day.
    Otherwise, default to the most recent December.
    """
    now = datetime.now()
    year = now.year if now.month == 12 else now.year - 1
    day = min(now.day if now.month == 12 else 25, 25)
    return year, day


def get_problem_dir(year: int, day: int) -> Path:
    """Get the directory path for the given year and day."""
    return config.BASE_DIR / f"years/{year}/day{day:02d}"


def create_problem_dir(year: int, day: int) -> Path:
    """Create the problem directory if it doesn't exist."""
    problem_dir = get_problem_dir(year, day)
    problem_dir.mkdir(parents=True, exist_ok=True)
    return problem_dir


async def validate_session_cookie(session_cookie: str) -> Tuple[bool, str]:
    """Validate the session cookie by making a test request.
    
    Returns:
        Tuple of (is_valid, error_message)
    """
    url = f"{config.AOC_BASE_URL}/settings"
    
    async with aiohttp.ClientSession() as session:
        headers = {
            "Cookie": f"session={session_cookie}",
            "User-Agent": config.USER_AGENT
        }
        async with session.get(url, headers=headers) as response:
            if response.status == 200:
                return True, ""
            elif response.status == 302 or response.status == 401:
                return False, "Session cookie is invalid or expired. Please update AOC_SESSION in your .env file with a valid session cookie from adventofcode.com"
            else:
                return False, f"Unexpected error validating session cookie: HTTP {response.status}"


def get_session_cookie() -> str:
    """Get the session cookie from environment variables. If invalid, prompt for a new one."""
    session_cookie = config.AOC_SESSION
    if not session_cookie:
        print("\nAOC_SESSION environment variable not set.")
        return _prompt_for_session()
    
    return session_cookie

async def get_session_cookie_async() -> str:
    """Async version of get_session_cookie that validates the session."""
    session_cookie = get_session_cookie()
    logger = logging.getLogger(__name__)
    logger.debug("Got session cookie: %s", session_cookie[:10] if session_cookie else None)
    
    # Validate the session cookie
    is_valid, error_message = await validate_session_cookie(session_cookie)
    logger.debug("Session validation result: %s, %s", is_valid, error_message)
    if not is_valid:
        print(f"\n{error_message}")
        return _prompt_for_session()
        
    return session_cookie

def _prompt_for_session() -> str:
    """Prompt the user for a new session cookie and update .env file."""
    print("\nTo get your session cookie:")
    print("1. Go to adventofcode.com and log in")
    print("2. Open browser developer tools (F12)")
    print("3. Go to Application/Storage > Cookies")
    print("4. Find and copy the 'session' cookie value")
    
    while True:
        session_cookie = input("\nEnter your session cookie (or 'q' to quit): ").strip()
        if session_cookie.lower() == 'q':
            raise SessionError("Session cookie required to continue")
            
        is_valid, error_message = asyncio.run(validate_session_cookie(session_cookie))
        if is_valid:
            # Update .env file
            env_path = Path(__file__).parent.parent / '.env'
            if env_path.exists():
                from dotenv import set_key
                set_key(str(env_path), 'AOC_SESSION', session_cookie)
                os.environ['AOC_SESSION'] = session_cookie
                print("\nSession cookie validated and saved to .env file")
            return session_cookie
        else:
            print(f"\nInvalid session cookie: {error_message}")
            print("Please try again")


async def make_request(url: str, timeout: int = 30) -> str:
    """Make a request to Advent of Code with appropriate headers and delay."""
    logger = logging.getLogger(__name__)
    session_cookie = await get_session_cookie_async()
    logger.debug("Making request to %s", url)
    logger.debug("Session cookie length: %d", len(session_cookie) if session_cookie else 0)

    # Add session cookie
    async with aiohttp.ClientSession() as session:
        headers = {
            "Cookie": f"session={session_cookie}",
            "User-Agent": config.USER_AGENT,
        }
        logger.debug("Request headers: %s", headers)
        async with session.get(url, headers=headers, timeout=timeout) as response:
            logger.debug("Response status: %d", response.status)
            text = await response.text()
            logger.debug("Response text: %s", text[:500])  # Log first 500 chars
            logger.debug("Response text length: %d", len(text))
            return text


class ProblemState(Enum):
    """State of a problem page."""
    INITIAL = auto()  # Only part 1 visible
    PART1_SOLVED = auto()  # Part 1 solved, part 2 visible
    COMPLETE = auto()  # Both parts solved

@dataclass
class CacheMetadata:
    """Metadata for cached HTML response."""
    state: ProblemState
    timestamp: str
    part1_answer: Optional[str] = None
    part2_answer: Optional[str] = None

async def _get_problem_state(soup: BeautifulSoup) -> Tuple[ProblemState, Optional[str], Optional[str]]:
    """Determine problem state from HTML.
    
    Returns:
        Tuple of (state, part1_answer, part2_answer)
    """
    part1_answer = None
    part2_answer = None
    
    # Check for successful answers
    success_elements = soup.find_all("p", class_="day-success")
    for elem in success_elements:
        text = elem.text.strip()
        if "Your puzzle answer was" in text:
            answer = re.search(r"Your puzzle answer was ([^.]+)", text)
            if answer:
                # If part 2 exists, first success is part 1
                if part1_answer is None:
                    part1_answer = answer.group(1).strip()
                else:
                    part2_answer = answer.group(1).strip()
    
    # Determine state
    if part2_answer is not None:
        return ProblemState.COMPLETE, part1_answer, part2_answer
    elif part1_answer is not None:
        return ProblemState.PART1_SOLVED, part1_answer, None
    else:
        return ProblemState.INITIAL, None, None

async def _load_cache(year: int, day: int) -> Tuple[Optional[str], Optional[CacheMetadata]]:
    """Load cached HTML and metadata if available."""
    problem_dir = get_problem_dir(year, day)
    html_path = problem_dir / config.HTML_FILE
    meta_path = problem_dir / config.META_FILE
    
    if not (html_path.exists() and meta_path.exists()):
        return None, None
        
    try:
        with open(html_path, "r", encoding="utf-8") as f:
            html = f.read()
        with open(meta_path, "r", encoding="utf-8") as f:
            meta_dict = json.load(f)
            meta = CacheMetadata(
                state=ProblemState[meta_dict["state"]],
                timestamp=meta_dict["timestamp"],
                part1_answer=meta_dict.get("part1_answer"),
                part2_answer=meta_dict.get("part2_answer")
            )
        return html, meta
    except (IOError, json.JSONDecodeError, KeyError):
        return None, None

async def _save_cache(year: int, day: int, html: str, meta: CacheMetadata) -> None:
    """Save HTML and metadata to cache."""
    problem_dir = get_problem_dir(year, day)
    
    html_path = problem_dir / config.HTML_FILE
    meta_path = problem_dir / config.META_FILE
    
    with open(html_path, "w", encoding="utf-8") as f:
        f.write(html)
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump({
            "state": meta.state.name,
            "timestamp": meta.timestamp,
            "part1_answer": meta.part1_answer,
            "part2_answer": meta.part2_answer
        }, f, indent=2)

async def fetch_problem_text(year: int, day: int, part: int = 1) -> Tuple[str, BeautifulSoup, Optional[str]]:
    """Fetch the problem text from Advent of Code website.
    
    Returns:
        Tuple of (problem_text, soup_object, previous_answer)
        where previous_answer is None if part hasn't been solved
        
    Note:
        To be a good web citizen, we aggressively cache problem text and only
        fetch new content when absolutely necessary (i.e., after successfully
        solving a part). Multiple solution attempts for the same part will
        use cached data.
    """
    # Try to load from cache first
    cached_html, meta = await _load_cache(year, day)
    logger = logging.getLogger(__name__)
    
    if cached_html is not None and meta is not None:
        soup = BeautifulSoup(cached_html, "html.parser")
        
        # For part 1: Always use cache if we have it
        if part == 1:
            logger.debug("Using cached data for part 1")
            return cached_html, soup, meta.part1_answer
            
        # For part 2: Use cache if part 1 was solved
        if part == 2 and meta.state >= ProblemState.PART1_SOLVED:
            logger.debug("Using cached data for part 2")
            return cached_html, soup, meta.part2_answer
            
        # If we're here for part 2 but haven't solved part 1,
        # return empty since part 2 isn't available yet
        if part == 2:
            logger.debug("Part 2 not available yet - part 1 unsolved")
            return "", soup, None
    
    # No cache or invalid state - need to fetch
    # This should only happen:
    # 1. First time accessing the problem
    # 2. After successfully solving part 1 (to get part 2)
    # 3. After successfully solving part 2 (to get final state)
    logger.info(f"Fetching fresh problem text for year {year} day {day} part {part}")
    url = f"{config.AOC_BASE_URL}/{year}/day/{day}"
    response = await make_request(url)
    soup = BeautifulSoup(response, "html.parser")
    
    # Get current state and answers
    state, part1_answer, part2_answer = await _get_problem_state(soup)
    
    # Save to cache
    meta = CacheMetadata(
        state=state,
        timestamp=datetime.now().isoformat(),
        part1_answer=part1_answer,
        part2_answer=part2_answer,
    )
    await _save_cache(year, day, response, meta)
    
    # Return appropriate data based on part
    if part == 2:
        return response, soup, part2_answer
    return response, soup, part1_answer

async def fetch_input_data(year: int, day: int, soup: Optional[BeautifulSoup] = None) -> str:
    """Fetch the input data from Advent of Code website."""
    # Get the input data directly - no need to fetch problem page again
    input_url = f"{config.AOC_BASE_URL}/{year}/day/{day}/input"
    response = await make_request(input_url)
    return response.strip()


async def ensure_problem_files(year: int, day: int) -> Dict[str, Path]:
    """
    Ensure all problem-related files exist and return their paths.
    """
    # Create problem directory if it doesn't exist
    problem_dir = create_problem_dir(year, day)

    # Fetch problem text and examples
    html_text, soup, _ = await fetch_problem_text(year, day)
    problem_text = _extract_problem_text(soup)
    save_to_file(config.PROBLEM_FILE, problem_text, problem_dir)

    # Extract and save examples from problem text
    parsed_problem = parse_problem_text(problem_text)
    save_examples(parsed_problem.examples, problem_dir)

    # Fetch input data using the same soup object
    input_data = await fetch_input_data(year, day, soup)
    save_to_file(config.INPUT_FILE, input_data, problem_dir)

    return {
        "problem": problem_dir / config.PROBLEM_FILE,
        "examples": problem_dir / config.EXAMPLES_DIR,
        "input": problem_dir / config.INPUT_FILE,
    }


def parse_problem_text(problem_text: str) -> Any:
    """Parse problem text into structured data."""
    return _parse_problem_text(problem_text)


def save_examples(examples: List[Any], problem_dir: Path) -> None:
    """Save examples to individual files in the examples directory."""
    examples_dir = problem_dir / config.EXAMPLES_DIR
    examples_dir.mkdir(parents=True, exist_ok=True)
    
    # First save the metadata about all examples
    metadata = {
        "count": len(examples),
        "examples": [
            {
                "order": ex.order,
                "demonstrates": list(ex.demonstrates),
                "referenced_by": ex.referenced_by,
                "purpose": ex.purpose.name if ex.purpose else None,
                "description": ex.description
            }
            for ex in examples
        ]
    }
    
    with open(examples_dir / "metadata.json", "w") as f:
        json.dump(metadata, f, indent=2)
    
    # Then save each example's input/output
    for i, example in enumerate(examples):
        example_data = {
            "input": example.input_data,
            "expected_output": example.expected_output
        }
        with open(examples_dir / f"example_{i+1}.json", "w") as f:
            json.dump(example_data, f, indent=2)


def save_to_file(filename: str, content: str, problem_dir: Path) -> None:
    """Save content to a file in the problem directory."""
    filepath = problem_dir / filename
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(content)
    logger = logging.getLogger(__name__)
    logger.info(f"Saved content to {filename}")


def get_input_path(year: int, day: int) -> Path:
    """Get the path to the input file for the given year and day."""
    return get_problem_dir(year, day) / config.INPUT_FILE


def ensure_input_file(year: int, day: int) -> str:
    """
    Ensure the input file exists for the given year and day.
    If it doesn't exist, download it using the session cookie.
    Returns the path to the input file.
    """
    input_path = get_input_path(year, day)

    if not input_path.exists():
        logger = logging.getLogger(__name__)
        logger.info(f"Downloading input for Year {year} Day {day}")
        url = f"{config.AOC_BASE_URL}/{year}/day/{day}/input"
        response = asyncio.run(make_request(url))

        # Save input
        input_path.write_text(response, encoding="utf-8")
        logger.info(f"Saved input to {input_path}")

    return str(input_path)


def read_input(year: int, day: int) -> str:
    """Read the input file for the given year and day."""
    input_path = get_input_path(year, day)
    if not input_path.exists():
        raise InputError(f"Input file not found: {input_path}")
    return input_path.read_text(encoding="utf-8").strip()


def download_input(year: int, day: int) -> str:
    """Download input from Advent of Code website."""
    try:
        # Get and validate session cookie
        session_cookie = get_session_cookie()
        
        # Create directory if it doesn't exist
        input_dir = Path(f"{year}/day{day:02d}")
        input_dir.mkdir(parents=True, exist_ok=True)

        # Download input if it doesn't exist
        input_file = input_dir / "input.txt"
        if not input_file.exists():
            url = f"https://adventofcode.com/{year}/day/{day}/input"
            response = requests.get(
                url,
                cookies={"session": session_cookie},
                headers={"User-Agent": config.USER_AGENT},
                timeout=30,
            )
            
            if response.status_code == 404:
                raise InputError(f"Input for year {year} day {day} is not available yet")
            
            response.raise_for_status()
            input_file.write_text(response.text, encoding="utf-8")

        return input_file.read_text(encoding="utf-8")
        
    except SessionError as e:
        # Re-raise SessionError with the detailed message
        raise
    except requests.exceptions.RequestException as e:
        if "404" in str(e):
            raise InputError(f"Input for year {year} day {day} is not available yet")
        raise SessionError(f"Failed to download input: {str(e)}")


def _extract_problem_text(soup: BeautifulSoup) -> str:
    """Extract problem text from BeautifulSoup object."""
    article = soup.find("article", class_="day-desc")
    if article:
        return article.get_text()
    return ""
