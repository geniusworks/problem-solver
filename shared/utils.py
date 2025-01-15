"""Utility functions for Advent of Code solutions."""

import json
import logging
import time
import os
import asyncio
from datetime import datetime
from pathlib import Path
from typing import Tuple, Dict, Any

import aiohttp
import requests
from bs4 import BeautifulSoup
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from shared import config
from shared.config import ValidationError, SessionError, InputError

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


def setup_logging():
    """Configure logging for the application."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )


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
                return False, "Session cookie is invalid or expired. Please update PROBLEM_SITE_SESSION in your .env file with a valid session cookie from adventofcode.com"
            else:
                return False, f"Unexpected error validating session cookie: HTTP {response.status}"


def get_session_cookie() -> str:
    """Get the session cookie from environment variables. If invalid, prompt for a new one."""
    session = config.PROBLEM_SITE_SESSION
    if not session:
        print("\nPROBLEM_SITE_SESSION environment variable not set.")
        return _prompt_for_session()
    
    return session

async def get_session_cookie_async() -> str:
    """Async version of get_session_cookie that validates the session."""
    session = get_session_cookie()
    
    # Validate the session cookie
    is_valid, error_message = await validate_session_cookie(session)
    if not is_valid:
        print(f"\n{error_message}")
        return _prompt_for_session()
        
    return session

def _prompt_for_session() -> str:
    """Prompt the user for a new session cookie and update .env file."""
    print("\nTo get your session cookie:")
    print("1. Go to adventofcode.com and log in")
    print("2. Open browser developer tools (F12)")
    print("3. Go to Application/Storage > Cookies")
    print("4. Find and copy the 'session' cookie value")
    
    while True:
        session = input("\nEnter your session cookie (or 'q' to quit): ").strip()
        if session.lower() == 'q':
            raise SessionError("Session cookie required to continue")
            
        is_valid, error_message = asyncio.run(validate_session_cookie(session))
        if is_valid:
            # Update .env file
            env_path = Path(__file__).parent.parent / '.env'
            if env_path.exists():
                from dotenv import set_key
                set_key(str(env_path), 'PROBLEM_SITE_SESSION', session)
                os.environ['PROBLEM_SITE_SESSION'] = session
                print("\nSession cookie validated and saved to .env file")
            return session
        else:
            print(f"\nInvalid session cookie: {error_message}")
            print("Please try again")


async def make_request(url: str, timeout: int = 30) -> str:
    """Make a request to Advent of Code with appropriate headers and delay."""
    logger = logging.getLogger(__name__)
    session_cookie = await get_session_cookie_async()
    logger.info("Making request to %s", url)
    logger.info("Using session cookie: %s...", session_cookie[:10])

    # Add session cookie
    async with aiohttp.ClientSession() as session:
        headers = {
            "Cookie": f"session={session_cookie}",
            "User-Agent": "github.com/your-username/aoc-solver v1.0",
        }
        async with session.get(url, headers=headers, timeout=timeout) as response:
            response.raise_for_status()
            return await response.text()


async def fetch_problem_text(year: int, day: int) -> str:
    """Fetch the problem text from Advent of Code website."""
    url = f"{config.AOC_BASE_URL}/{year}/day/{day}"
    response = await make_request(url)

    # Parse with html.parser
    soup = BeautifulSoup(response, "html.parser")

    # Find all problem description articles
    articles = soup.find_all("article", class_="day-desc")
    if not articles:
        logger = logging.getLogger(__name__)
        logger.error("No articles found in HTML")
        return ""

    # Extract text from each article
    texts = []
    for article in articles:
        # Get the title
        title = article.find("h2")
        if title:
            texts.append(title.get_text().strip())
            texts.append("")  # Add blank line after title

        # Process each element in the article
        for elem in article.children:
            if elem.name == "p":
                # Handle paragraphs
                text = ""
                for child in elem.children:
                    if isinstance(child, str):
                        text += child
                    elif child.name == "code":
                        text += f"`{child.get_text()}`"
                    elif child.name == "em":
                        text += f"*{child.get_text()}*"
                    elif child.name == "span":
                        if child.get("title"):
                            text += f"{child.get_text()} ({child['title']})"
                        else:
                            text += child.get_text()
                    else:
                        text += child.get_text()
                texts.append(text.strip())
                texts.append("")  # Add blank line after paragraph
            elif elem.name == "pre":
                # Handle code blocks
                code = elem.find("code")
                if code:
                    texts.append("Example:")
                    # Clean up the code text
                    code_lines = []
                    for line in code.get_text().strip().split("\n"):
                        # Remove any emphasized text markers but keep the text
                        line = line.replace("(increased)", "")
                        line = line.replace("(decreased)", "")
                        line = line.replace("(N/A - no previous measurement)", "")
                        # Clean up whitespace but preserve indentation
                        line = line.strip()
                        code_lines.append(line)
                    texts.append("\n".join(code_lines))
                    texts.append("")  # Add blank line after code block

    # Join all text with proper spacing
    return "\n".join(texts).strip()


def save_to_file(filename: str, content: str, problem_dir: Path) -> None:
    """Save content to a file in the problem directory."""
    filepath = problem_dir / filename
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(content)
    logger = logging.getLogger(__name__)
    logger.info(f"Saved content to {filename}")


def ensure_problem_files(year: int, day: int) -> Dict[str, Path]:
    """
    Ensure all problem-related files exist and return their paths.
    """
    # Create problem directory if it doesn't exist
    problem_dir = create_problem_dir(year, day)

    # Fetch problem text and example
    problem_text = asyncio.run(fetch_problem_text(year, day))
    save_to_file(config.PROBLEM_FILE, problem_text, problem_dir)

    # Extract example from problem text
    example = parse_example_from_html(problem_text)
    save_to_file(config.EXAMPLE_FILE, example, problem_dir)

    # Fetch input data
    input_data = fetch_input_data(year, day)
    save_to_file(config.INPUT_FILE, input_data, problem_dir)

    return {
        "problem": problem_dir / config.PROBLEM_FILE,
        "example": problem_dir / config.EXAMPLE_FILE,
        "input": problem_dir / config.INPUT_FILE,
    }


def parse_example_from_html(problem_text: str) -> str:
    """Extract example data from problem text."""
    # Look for the example section
    if "Example:" not in problem_text:
        return ""

    # Get everything after "Example:"
    example_section = problem_text.split("Example:")[1]

    # Get the first block of numbers
    lines = example_section.strip().split("\n")
    example_lines = []
    for line in lines:
        # Skip empty lines and lines with explanatory text
        if not line.strip() or any(
            x in line.lower() for x in ["increased", "decreased", "n/a"]
        ):
            continue
        # Clean up any remaining text and keep only numbers
        numbers = "".join(c for c in line if c.isdigit() or c.isspace())
        if numbers.strip():
            example_lines.append(numbers.strip())

    return "\n".join(example_lines)


def fetch_input_data(year: int, day: int) -> str:
    """Fetch the input data from Advent of Code website."""
    # First get the problem page to find the input link
    problem_url = f"{config.AOC_BASE_URL}/{year}/day/{day}"
    response = asyncio.run(make_request(problem_url))
    soup = BeautifulSoup(response, "html.parser")

    # Find the puzzle input link
    input_link = soup.find("a", string="get your puzzle input")
    if not input_link:
        raise ValidationError("Could not find puzzle input link")

    # Get the input data
    input_url = f"{config.AOC_BASE_URL}/{year}/day/{day}/input"
    response = asyncio.run(make_request(input_url))
    return response.strip()


def parse_problem_html(html: str) -> Tuple[str, str]:
    """Parse problem HTML to extract problem text and example."""
    soup = BeautifulSoup(html, "html.parser")

    # Extract problem text
    article = soup.find("article")
    if not article:
        raise InputError("Could not find problem description in HTML")
    problem_text = article.get_text().strip()

    # Extract example
    code = soup.find("pre")
    example = code.text.strip() if code else ""

    return problem_text, example


def log_attempt(
    year: int, day: int, part: int, solution: Any, result: str, feedback: str = ""
) -> None:
    """
    Log a solution attempt.

    Args:
        year: Problem year
        day: Problem day
        part: Problem part (1 or 2)
        solution: The attempted solution
        result: 'accepted' or 'rejected'
        feedback: Any feedback received about the attempt
    """
    problem_dir = get_problem_dir(year, day)
    log_file = problem_dir / config.ATTEMPTS_LOG

    timestamp = datetime.now().isoformat()
    entry = {
        "timestamp": timestamp,
        "part": part,
        "solution": str(solution),
        "result": result,
        "feedback": feedback,
    }

    with open(log_file, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")
    logger = logging.getLogger(__name__)
    logger.info(f"Logged {result} attempt for Year {year} Day {day} Part {part}")


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
        session = get_session_cookie()
        
        # Create directory if it doesn't exist
        input_dir = Path(f"{year}/day{day:02d}")
        input_dir.mkdir(parents=True, exist_ok=True)

        # Download input if it doesn't exist
        input_file = input_dir / "input.txt"
        if not input_file.exists():
            url = f"https://adventofcode.com/{year}/day/{day}/input"
            response = requests.get(
                url,
                cookies={"session": session},
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
