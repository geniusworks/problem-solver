"""Utility functions for Advent of Code solutions."""
import json
import logging
import time
from datetime import datetime
from pathlib import Path
from typing import Tuple, Dict, Any

import requests
from bs4 import BeautifulSoup
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from shared import config
from shared.config import AocError, SessionError, InputError

# Configure retry strategy
session = requests.Session()
session.headers.update({
    'User-Agent': config.USER_AGENT,
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.9',
    'Accept-Encoding': 'gzip, deflate, br',
    'Connection': 'keep-alive',
    'Host': 'adventofcode.com',
    'Sec-Fetch-Site': 'none',
    'Sec-Fetch-Mode': 'navigate',
    'Sec-Fetch-Dest': 'document'
})

retry_strategy = Retry(
    total=5,
    backoff_factor=2,
    status_forcelist=[429, 500, 502, 503, 504],
    allowed_methods=["GET"]
)
adapter = HTTPAdapter(max_retries=retry_strategy)
session.mount("https://", adapter)
session.mount("http://", adapter)

def setup_logging():
    """Configure logging for the application."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
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

def get_session_cookie() -> str:
    """Get the session cookie from environment variables."""
    if not config.AOC_SESSION:
        raise SessionError("AOC_SESSION environment variable not set")
    return config.AOC_SESSION

def make_request(url: str) -> requests.Response:
    """Make a request to Advent of Code with appropriate headers and delay."""
    try:
        session_cookie = get_session_cookie()
        logger = logging.getLogger(__name__)
        logger.info(f"Making request to {url}")
        logger.info(f"Using session cookie: {session_cookie[:10]}...")
        
        # Set cookie for this request
        session.cookies.clear()  # Clear any existing cookies
        session.cookies.set('session', session_cookie, domain='adventofcode.com', path='/')
        
        # Add delay before request
        time.sleep(2)
        
        response = session.get(url)
        response.raise_for_status()
        
        # Save raw response for debugging
        with open('debug_response.html', 'w', encoding='utf-8') as f:
            f.write(response.text)
            
        return response
    except requests.exceptions.RequestException as e:
        raise AocError(f"Failed to fetch {url}: {str(e)}") from e

def fetch_problem_text(year: int, day: int) -> str:
    """Fetch the problem text from Advent of Code website."""
    url = f"{config.AOC_BASE_URL}/{year}/day/{day}"
    response = make_request(url)
    
    # Parse with html.parser
    soup = BeautifulSoup(response.text, 'html.parser')
    
    # Find all problem description articles
    articles = soup.find_all('article', class_='day-desc')
    if not articles:
        logger = logging.getLogger(__name__)
        logger.error("No articles found in HTML")
        return ""
    
    # Extract text from each article
    texts = []
    for article in articles:
        # Get the title
        title = article.find('h2')
        if title:
            texts.append(title.get_text())
        
        # Get all paragraphs
        for p in article.find_all('p'):
            # Remove code elements but keep their text
            for code in p.find_all('code'):
                code.replace_with(code.get_text())
            # Remove em elements but keep their text
            for em in p.find_all('em'):
                em.replace_with(em.get_text())
            # Remove span elements but keep their text
            for span in p.find_all('span'):
                span.replace_with(span.get_text())
            texts.append(p.get_text(strip=True))
        
        # Handle code blocks
        for pre in article.find_all('pre'):
            code = pre.find('code')
            if code:
                texts.append('\nExample:\n' + code.get_text().strip())
    
    return '\n\n'.join(texts)

def save_to_file(filename: str, content: str, problem_dir: Path) -> None:
    """Save content to a file in the problem directory."""
    filepath = problem_dir / filename
    with open(filepath, 'w', encoding='utf-8') as f:
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
    problem_text = fetch_problem_text(year, day)
    save_to_file(config.PROBLEM_FILE, problem_text, problem_dir)
    
    # Extract example from problem text
    example = parse_example_from_html(problem_text)
    save_to_file(config.EXAMPLE_FILE, example, problem_dir)
    
    # Fetch input data
    input_data = fetch_input_data(year, day)
    save_to_file(config.INPUT_FILE, input_data, problem_dir)
    
    return {
        'problem': problem_dir / config.PROBLEM_FILE,
        'example': problem_dir / config.EXAMPLE_FILE,
        'input': problem_dir / config.INPUT_FILE,
    }

def parse_example_from_html(problem_text: str) -> str:
    """Extract example data from problem text."""
    # Look for the example section
    if 'Example:' not in problem_text:
        return ""
    
    # Get everything after "Example:"
    example_section = problem_text.split('Example:')[1]
    
    # Get the first block of numbers
    lines = example_section.strip().split('\n')
    example_lines = []
    for line in lines:
        # Skip empty lines and lines with explanatory text
        if not line.strip() or any(x in line.lower() for x in ['increased', 'decreased', 'n/a']):
            continue
        # Clean up any remaining text and keep only numbers
        numbers = ''.join(c for c in line if c.isdigit() or c.isspace())
        if numbers.strip():
            example_lines.append(numbers.strip())
    
    return '\n'.join(example_lines)

def fetch_input_data(year: int, day: int) -> str:
    """Fetch the input data from Advent of Code website."""
    # First get the problem page to find the input link
    problem_url = f"{config.AOC_BASE_URL}/{year}/day/{day}"
    response = make_request(problem_url)
    soup = BeautifulSoup(response.text, 'html.parser')
    
    # Find the puzzle input link
    input_link = soup.find('a', string='get your puzzle input')
    if not input_link:
        raise AocError("Could not find puzzle input link")
    
    # Get the input data
    input_url = f"{config.AOC_BASE_URL}/{year}/day/{day}/input"
    response = make_request(input_url)
    return response.text.strip()

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
