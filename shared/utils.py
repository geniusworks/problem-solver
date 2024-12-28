"""Utility functions for Advent of Code solutions."""
import json
import logging
import time
from datetime import datetime
from pathlib import Path
from typing import Tuple, Dict, Any

import requests
from bs4 import BeautifulSoup

from shared import config
from shared.config import AocError, SessionError, InputError

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

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

def ensure_problem_dir(year: int, day: int) -> Path:
    """Ensure the problem directory exists and return its path."""
    problem_dir = get_problem_dir(year, day)
    problem_dir.mkdir(parents=True, exist_ok=True)
    return problem_dir

def get_session_cookie() -> str:
    """Get the Advent of Code session cookie from environment."""
    if not config.AOC_SESSION:
        raise SessionError(
            "AOC_SESSION environment variable not set. "
            "Please copy .env.template to .env and set your session cookie."
        )
    return config.AOC_SESSION

def make_request(url: str) -> requests.Response:
    """Make a request to Advent of Code with appropriate headers and delay."""
    try:
        response = requests.get(
            url,
            cookies={'session': get_session_cookie()},
            headers={'User-Agent': config.USER_AGENT}
        )
        response.raise_for_status()
        time.sleep(config.REQUEST_DELAY)  # Be nice to the server
        return response
    except requests.RequestException as e:
        raise AocError(f"Failed to fetch {url}: {str(e)}") from e

def fetch_problem_text(year: int, day: int) -> str:
    """Fetch the problem text from Advent of Code website."""
    url = f"{config.AOC_BASE_URL}/{year}/day/{day}"
    response = make_request(url)
    return response.text

def parse_problem_html(html: str) -> Tuple[str, str]:
    """Parse problem HTML to extract problem text and example."""
    soup = BeautifulSoup(html, 'html.parser')
    
    # Extract problem text
    article = soup.find('article')
    if not article:
        raise InputError("Could not find problem description in HTML")
    problem_text = article.get_text().strip()
    
    # Extract example
    code = soup.find('pre')
    example = code.text.strip() if code else ""
    
    return problem_text, example

def ensure_problem_files(year: int, day: int) -> Dict[str, Path]:
    """
    Ensure all problem-related files exist and return their paths.
    Creates problem.txt, example.txt, logic.txt, and attempts.log if they don't exist.
    """
    problem_dir = ensure_problem_dir(year, day)
    files = {
        'problem': problem_dir / config.PROBLEM_FILE,
        'example': problem_dir / config.EXAMPLE_FILE,
        'logic': problem_dir / config.LOGIC_FILE,
        'attempts': problem_dir / config.ATTEMPTS_LOG,
        'input': problem_dir / config.INPUT_FILE
    }
    
    # Create empty files if they don't exist
    for file_path in files.values():
        if not file_path.exists():
            file_path.touch()
            logger.info(f"Created file: {file_path}")
            
    return files

def log_attempt(year: int, day: int, part: int, solution: Any, result: str, feedback: str = "") -> None:
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
        'timestamp': timestamp,
        'part': part,
        'solution': str(solution),
        'result': result,
        'feedback': feedback
    }
    
    with open(log_file, 'a') as f:
        f.write(json.dumps(entry) + '\n')
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
        logger.info(f"Downloading input for Year {year} Day {day}")
        url = f"{config.AOC_BASE_URL}/{year}/day/{day}/input"
        response = make_request(url)
        
        # Save input
        input_path.write_text(response.text)
        logger.info(f"Saved input to {input_path}")
    
    return str(input_path)

def read_input(year: int, day: int) -> str:
    """Read the input file for the given year and day."""
    input_path = get_input_path(year, day)
    if not input_path.exists():
        raise InputError(f"Input file not found: {input_path}")
    return input_path.read_text().strip()
