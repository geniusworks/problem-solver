"""Utility functions for Advent of Code solutions."""

import json
import logging
import time
import requests
import os
import asyncio
import re
from datetime import datetime
from pathlib import Path
from shared.errors import SessionError
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
from shared.parser import parse_problem_text
from shared.overfit_detection import analyze_overfit_risk

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


def get_aoc_day_count(year: int) -> int:
    """Return the number of Advent of Code days for a given year."""
    return 25 if year < 2025 else 12


def get_problem_year_day() -> Tuple[int, int]:
    """
    Get the current Advent of Code year and day.
    If we're in December, use the current year and day.
    Otherwise, default to the most recent December.
    """
    now = datetime.now()

    if now.month == 12:
        year = now.year
        day = min(now.day, get_aoc_day_count(year))
    else:
        year = now.year - 1
        day = get_aoc_day_count(year)
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
    
    # Validate the session cookie synchronously
    url = "https://adventofcode.com/2024/day/1"
    response = requests.get(
        url,
        cookies={"session": session_cookie},
        headers={"User-Agent": config.USER_AGENT},
        timeout=30,
    )
    
    if response.status_code == 400:
        raise SessionError("Authentication failed: Your session token appears to be invalid or expired. Please update AOC_SESSION in your .env file with a valid session cookie from adventofcode.com")
    
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
            if response.status == 400:
                raise SessionError("Authentication failed: Your session token appears to be invalid or expired. Please update AOC_SESSION in your .env file with a valid session cookie from adventofcode.com")
            response.raise_for_status()
            text = await response.text()
            logger.debug("Response text length: %d characters", len(text))
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
    answers: List[str] = []

    # AoC renders accepted answers as a plain <p> (no class) directly after each
    # article: "Your puzzle answer was <code>2970687</code>." They appear in part
    # order, so the first is Part 1 and the second is Part 2.
    for elem in soup.find_all("p"):
        text = elem.get_text().strip()
        if "Your puzzle answer was" not in text:
            continue
        code = elem.find("code")
        if code is not None:
            answers.append(code.get_text().strip())
            continue
        match = re.search(r"Your puzzle answer was\s+([^.\s]+)", text)
        if match:
            answers.append(match.group(1).strip())

    if answers:
        part1_answer = answers[0]
    if len(answers) > 1:
        part2_answer = answers[1]

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

    # Mirror any accepted answers into the ground-truth store so the solver has a
    # correctness oracle for the full input. Imported locally to avoid a cycle:
    # shared.ground_truth depends on get_problem_dir from this module.
    from shared.ground_truth import save_known_answers

    known = {}
    if meta.part1_answer:
        known[1] = meta.part1_answer
    if meta.part2_answer:
        known[2] = meta.part2_answer
    if known:
        save_known_answers(year, day, known)

async def fetch_problem_text(year: int, day: int, part: int = 1) -> Tuple[str, Any, Optional[str]]:
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
    problem_dir = create_problem_dir(year, day)
    cache_file = problem_dir / "problem.html"
    if cache_file.exists():
        logger.debug("Using cached problem text from %s", cache_file)
        with open(cache_file, "r", encoding="utf-8") as f:
            html = f.read()

        # Parse HTML and extract examples
        soup = BeautifulSoup(html, "html.parser")
        state, part1_answer, part2_answer = await _get_problem_state(soup)

        # Extract examples from HTML before converting to text
        examples = []
        for article in soup.find_all("article", class_="day-desc"):
            pre_blocks = article.find_all("pre")
            for pre in pre_blocks:
                code = pre.find("code")
                if code:
                    examples.append(code.get_text())

        # Select the appropriate article HTML for the requested part so that
        # each part is solved atomically. This avoids including Part Two
        # instructions when solving Part One and vice versa.
        # Return HTML (not just text) so parse_problem_text can use HTML parsing.
        problem_text: str
        articles = soup.find_all("article", class_="day-desc") if soup else []
        if articles:
            if part == 2 and len(articles) > 1:
                article = articles[1]
            else:
                article = articles[0]
            # Return the article's outer HTML so the parser can use HTML-aware extraction
            problem_text = str(article)
        else:
            # Fallback to full page HTML if structure is unexpected
            problem_text = html

        # Return appropriate data based on part
        if part == 2:
            return problem_text, soup, part2_answer
        return problem_text, soup, part1_answer
    else:
        logger.info(f"Fetching fresh problem text for year {year} day {day} part {part}")
        url = f"{config.AOC_BASE_URL}/{year}/day/{day}"
        response = await make_request(url)
        html = response
        
        # Get current state and answers
        soup = BeautifulSoup(html, "html.parser")
        state, part1_answer, part2_answer = await _get_problem_state(soup)
        
        # Extract examples from HTML before saving
        examples = []
        for article in soup.find_all("article", class_="day-desc"):
            pre_blocks = article.find_all("pre")
            for pre in pre_blocks:
                code = pre.find("code")
                if code:
                    examples.append(code.get_text())

        # Select the appropriate article HTML for the requested part so that
        # each part is solved atomically. This avoids including Part Two
        # instructions when solving Part One and vice versa.
        # Return HTML (not just text) so parse_problem_text can use HTML parsing.
        problem_text: str
        articles = soup.find_all("article", class_="day-desc") if soup else []
        if articles:
            if part == 2 and len(articles) > 1:
                article = articles[1]
            else:
                article = articles[0]
            # Return the article's outer HTML so the parser can use HTML-aware extraction
            problem_text = str(article)
        else:
            # Fallback to full page HTML if structure is unexpected
            problem_text = html

        # Save to cache
        meta = CacheMetadata(
            state=state,
            timestamp=datetime.now().isoformat(),
            part1_answer=part1_answer,
            part2_answer=part2_answer,
        )
        await _save_cache(year, day, html, meta)

        # Save examples separately
        if examples:
            examples_path = cache_file.with_suffix(".examples.txt")
            with open(examples_path, "w", encoding="utf-8") as f:
                f.write("\n---\n".join(examples))
    
        # Return appropriate data based on part
        if part == 2:
            return problem_text, soup, part2_answer
        return problem_text, soup, part1_answer

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
    cache_file = problem_dir / "problem.html"

    # Fetch problem text and examples
    html_text, soup, _ = await fetch_problem_text(year, day)
    problem_text = _extract_problem_text(soup)
    save_to_file(config.PROBLEM_FILE, problem_text, problem_dir)

    # Extract and save examples per part. The per-part article HTML is used rather
    # than the whole-page plain text: the HTML path can infer expected outputs from
    # <em> prose, and each part has its own expected answers for the same input.
    examples_file = cache_file.with_suffix(".examples.txt")
    article_count = len(soup.find_all("article", class_="day-desc")) if soup else 0

    # Note: examples_file is deliberately not passed here. Supplying it routes the
    # parser down the stored-plain-text path, which loses the expected outputs the
    # HTML path infers from <em> prose.
    part_one_examples: List[Any] = []
    for part in range(1, max(article_count, 1) + 1):
        part_html, _, _ = await fetch_problem_text(year, day, part)
        parsed_part = parse_problem_text(part_html)
        save_examples(parsed_part.examples, problem_dir, part=part)
        if part == 1:
            part_one_examples = parsed_part.examples

    # Preserve the legacy flat layout for part 1 so existing consumers keep working,
    # and keep writing problem.examples.txt for its own side effect.
    parsed_problem = parse_problem_text(problem_text, examples_file)
    save_examples(part_one_examples or parsed_problem.examples, problem_dir)

    # Fetch input data using the same soup object. Puzzle input never changes, so a
    # cached copy is reused rather than re-downloaded -- this keeps the pipeline
    # usable offline and when the AoC session cookie has expired.
    input_path = problem_dir / config.INPUT_FILE
    if input_path.exists() and input_path.stat().st_size > 0:
        logger.debug("Reusing cached input for %d day %02d", year, day)
    else:
        input_data = await fetch_input_data(year, day, soup)
        save_to_file(config.INPUT_FILE, input_data, problem_dir)

    return {
        "problem": problem_dir / config.PROBLEM_FILE,
        "examples": problem_dir / config.EXAMPLES_DIR,
        "input": problem_dir / config.INPUT_FILE,
    }


# parse_problem_text is re-exported from shared.parser at the top of this module.
# A second definition used to live here and silently shadowed that import; it only
# delegated to the same function, so it has been removed.


def save_examples(examples: List[Any], problem_dir: Path, part: Optional[int] = None) -> None:
    """Save examples to individual files in the examples directory.

    Examples are part-specific -- 2024 day 1 uses the same input for both parts but
    expects 11 for part 1 and 31 for part 2 -- so each part is written to its own
    ``examples/part<N>/`` subdirectory. Passing ``part=None`` writes to the legacy
    flat layout.
    """
    examples_dir = problem_dir / config.EXAMPLES_DIR
    if part is not None:
        examples_dir = examples_dir / f"part{part}"
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
    logger.info(f"Saved {filename}")


def get_input_path(year: int, day: int) -> Path:
    """Get the path to the input file for the given year and day."""
    return get_problem_dir(year, day) / config.INPUT_FILE


async def ensure_input_file(workspace_dir: Path, year: int, day: int) -> Path:
    """Ensure input file exists, downloading if necessary."""
    day_dir = workspace_dir / "years" / str(year) / f"day{day:02d}"
    day_dir.mkdir(parents=True, exist_ok=True)
    
    # Use simple input.txt name for consistency
    input_file = day_dir / "input.txt"
    
    if not input_file.exists():
        logger = logging.getLogger(__name__)
        logger.info(f"Downloading input for Year {year} Day {day}")
        url = f"{config.AOC_BASE_URL}/{year}/day/{day}/input"
        response = await make_request(url)

        # Save input
        input_file.write_text(response, encoding="utf-8")
        logger.info(f"Saved input to {input_file}")

    return input_file


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
            logging.info(f"Attempting to download input from: {url}")
            try:
                response = requests.get(
                    url,
                    cookies={"session": session_cookie},
                    headers={"User-Agent": config.USER_AGENT},
                    timeout=30,
                )
                logging.info(f"Response status: {response.status_code}")
                logging.info(f"Response headers: {response.headers}")
                if response.status_code == 400:
                    raise SessionError("Authentication failed: Your session token appears to be invalid or expired. Please update AOC_SESSION in your .env file with a valid session cookie from adventofcode.com")
                response.raise_for_status()
            except requests.exceptions.RequestException as e:
                logging.error(f"Request failed: {str(e)}")
                if "404" in str(e):
                    raise InputError(f"Input for year {year} day {day} is not available yet")
                raise SessionError(f"Failed to download input: {str(e)}")
            input_file.write_text(response.text, encoding="utf-8")

        return input_file.read_text(encoding="utf-8")
        
    except requests.exceptions.RequestException as e:
        if "404" in str(e):
            raise InputError(f"Input for year {year} day {day} is not available yet")
        if "400" in str(e):
            raise SessionError("Authentication failed: Your session token appears to be invalid or expired. Please update AOC_SESSION in your .env file with a valid session cookie from adventofcode.com")
        raise SessionError(f"Failed to download input: {str(e)}")


def _extract_problem_text(soup: BeautifulSoup) -> str:
    """Extract problem text from BeautifulSoup object."""
    article = soup.find("article", class_="day-desc")
    if article:
        return article.get_text()
    return ""


def ensure_problem_directory_structure(workspace_dir: Path, year: int, day: int) -> Dict[str, Path]:
    """Ensure the standard directory structure exists for a problem.
    
    Creates:
    years/
      YYYY/
        dayXX/
          attempts/      # JSON records of all solution attempts
          examples/      # Example inputs and outputs with metadata.json
          input.txt     # Full problem input
          problem.txt   # Problem description in text format
          problem.html  # Problem description in HTML format
          problem_meta.json  # Problem metadata
    
    Note: The actual Python files for attempts are stored in the tmp/ directory
    at the root of the workspace.
    
    Args:
        workspace_dir: Root workspace directory
        year: Problem year
        day: Problem day
        
    Returns:
        Dictionary containing paths to each directory
    """
    day_dir = workspace_dir / "years" / str(year) / f"day{day:02d}"
    attempts_dir = day_dir / "attempts"
    examples_dir = day_dir / "examples"
    
    # Create all directories
    for directory in [attempts_dir, examples_dir]:
        directory.mkdir(parents=True, exist_ok=True)
        
    return {
        "day": day_dir,
        "attempts": attempts_dir,
        "examples": examples_dir
    }

import subprocess
from datetime import datetime, timezone
import re

def get_github_username() -> str:
    """Attempt to get the user's GitHub username through various methods."""
    try:
        # First try GitHub CLI
        result = subprocess.run(
            ["gh", "auth", "status"],
            capture_output=True,
            text=True
        )
        if result.returncode == 0:
            # Extract username from gh output
            match = re.search(r"Logged in to github.com as (\w+)", result.stdout)
            if match:
                return match.group(1)
    except FileNotFoundError:
        pass  # gh CLI not installed
        
    try:
        # Try getting GitHub email
        email = subprocess.check_output(
            ["git", "config", "user.email"],
            text=True
        ).strip()
        
        # If it's a GitHub email, extract username
        match = re.match(r"(.+)@users.noreply.github.com", email)
        if match:
            return match.group(1)
    except subprocess.CalledProcessError:
        pass
        
    try:
        # Fall back to git user.name
        return subprocess.check_output(
            ["git", "config", "user.name"],
            text=True
        ).strip()
    except subprocess.CalledProcessError:
        return "unknown"

def get_repository_state() -> Tuple[str, bool]:
    """Get the current repository state including uncommitted changes.
    
    Returns:
        Tuple of (commit_hash, has_local_changes)
    """
    try:
        # Get current commit hash
        commit_hash = subprocess.check_output(
            ["git", "rev-parse", "HEAD"],
            text=True
        ).strip()
        
        # Check for uncommitted changes
        status = subprocess.check_output(
            ["git", "status", "--porcelain"],
            text=True
        )
        has_local_changes = bool(status.strip())
        
        return commit_hash, has_local_changes
    except subprocess.CalledProcessError:
        return "unknown", False

def save_solution_file(year: int, day: int, part: int, model_name: str, solution_code: str) -> str:
    """Save a successful solution to both the year directory and solutions directory.
    
    Args:
        year: Problem year
        day: Problem day
        part: Problem part
        model_name: Name of the model that generated the solution (ignored for filename)
        solution_code: The solution code to save
        
    Returns:
        Path to the solution file in the solutions directory (relative to repo root)
    """
    # Use a canonical solution filename independent of model name so that paths are
    # stable across re-runs and different model choices.
    solution_filename = f"{year}_day{day:02d}_part{part}.py"

    # Save to year directory
    year_dir = get_problem_dir(year, day)
    year_path = year_dir / solution_filename
    year_path.write_text(solution_code)
    
    # Save to solutions directory
    root_dir = Path(__file__).parent.parent
    solutions_dir = root_dir / "solutions"
    solutions_dir.mkdir(exist_ok=True)
    solution_path = solutions_dir / solution_filename
    solution_path.write_text(solution_code)
    
    return f"solutions/{solution_filename}"

# Anchor in solutions/README.md marking the end of the verified-solutions table.
# New rows are inserted immediately above it so they never land in the rejected
# table that follows.
VERIFIED_ROWS_MARKER = "<!-- end verified rows -->"


def record_solution(year: int, day: int, part: int, model_name: str, solution_code: str) -> None:
    """Record a successful solution in solutions/README.md.
    
    This function is called automatically by the solver when a solution is validated.
    It should never be called manually. The solutions/README.md file is maintained
    automatically as a historical record of validated solutions.
    
    Args:
        year: Problem year
        day: Problem day
        part: Problem part (1 or 2)
        model_name: Name of the model that generated the solution
        solution_code: The solution code to save
        
    Note:
        This function will only record a solution once per year/day/part combination.
        It is safe to call multiple times as it will ignore duplicate entries.
    """
    solutions_file = Path(__file__).parent.parent / "solutions" / "README.md"
    solutions_file.parent.mkdir(parents=True, exist_ok=True)

    # Ensure file exists with a minimal header
    table_header = (
        "| Year | Day | Part | Answer | LLM Model(s) | Recorded (UTC) | Solution File |\n"
        "|------|-----|------|--------|--------------|----------------|---------------|\n"
    )
    if not solutions_file.exists():
        initial = "# Advent of Code Solutions Log\n\n" + table_header
        solutions_file.write_text(initial)

    # Read existing content
    content = solutions_file.read_text()

    # Ensure the table header is present (handle both "|Year" and "| Year")
    header_added = False
    if not re.search(r"(?m)^\s*\|\s*Year\s*\|\s*Day\s*\|\s*Part\s*\|", content):
        # Insert header after title line if present; otherwise prepend
        insert_at = content.find("\n") + 1 if content.startswith("# Advent of Code Solutions Log") else 0
        content = content[:insert_at] + ("\n" if insert_at and not content[insert_at-1] == "\n" else "") + table_header + content[insert_at:]
        header_added = True

    # Check if this year/day/part already has a solution. Only the verified table
    # counts: the ledger also lists rejected solutions below the marker, and a
    # rejected entry must not block a later correct one from being recorded.
    verified_section = content.split(VERIFIED_ROWS_MARKER, 1)[0]
    pattern = rf"(?m)^\s*\|\s*{year}\s*\|\s*{day}\s*\|\s*{part}\s*\|"
    if re.search(pattern, verified_section):
        if header_added:
            # Persist the header fix even when not adding a new row
            solutions_file.write_text(content)
        return  # Already recorded

    # Run automatic overfit detection before recording anything. If the
    # heuristics flag this solution as suspicious, log and return early so it
    # is never treated as a validated canonical solution.
    analysis = analyze_overfit_risk(year, day, part, solution_code)
    if analysis.is_suspicious:
        logger.warning(
            "Refusing to record solution for year %d day %02d part %d due to "
            "overfit heuristics: %s",
            year,
            day,
            part,
            "; ".join(analysis.reasons),
        )
        if header_added:
            solutions_file.write_text(content)
        return

    # Ground-truth gate: if we know the accepted answer for this problem, the code
    # must actually produce it. Without this the ledger records anything that runs,
    # which is how hardcoded stubs were previously logged as validated solutions.
    from shared.verification import Verdict, verify_solution_code

    result = verify_solution_code(solution_code, year, day, part)
    if result.verdict is Verdict.WRONG:
        logger.warning(
            "Refusing to record solution for year %d day %02d part %d: produced %r, "
            "accepted answer is %r",
            year, day, part, result.actual, result.expected,
        )
        if header_added:
            solutions_file.write_text(content)
        return
    if result.verdict is Verdict.ERROR:
        logger.warning(
            "Refusing to record solution for year %d day %02d part %d: failed to run (%s)",
            year, day, part, (result.error or "").splitlines()[0][:200],
        )
        if header_added:
            solutions_file.write_text(content)
        return

    # Save solution file and get path
    solution_path = save_solution_file(year, day, part, model_name, solution_code)

    # Format current time in UTC
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

    # Record the accepted answer when we know it, so the ledger itself carries the
    # oracle rather than only a claim that something was validated.
    from shared.ground_truth import get_known_answer

    answer = get_known_answer(year, day, part) or "unverified"

    new_entry = (
        f"|{year}|{day}|{part}|{answer}|{model_name}|{timestamp}|{solution_path}|\n"
    )

    # Insert into the verified table rather than appending at end-of-file: the
    # ledger has a second table of rejected solutions below it.
    if VERIFIED_ROWS_MARKER in content:
        content = content.replace(VERIFIED_ROWS_MARKER, new_entry + VERIFIED_ROWS_MARKER, 1)
    else:
        if not content.endswith("\n"):
            content += "\n"
        content += new_entry

    # Write updated content
    solutions_file.write_text(content)

    logger.info("Recorded validated solution for year %d day %d part %d", year, day, part)
