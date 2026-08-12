"""Problem path primitives -- the repo's lowest layer.

These compute where a problem's files live; they import nothing but config, so
every other layer (verification, ground truth, the AoC fetcher, the ledger) can
depend on them without creating a cycle. They used to live in shared/utils.py,
which the ledger also lived in, so verification/ground_truth importing
get_problem_dir from there closed a utils -> verification -> ground_truth ->
utils loop. Splitting the leaf out breaks that loop.
"""

from datetime import datetime
from pathlib import Path
from typing import Tuple

from shared import config


def get_aoc_day_count(year: int) -> int:
    """Return the number of Advent of Code days for a given year."""
    return 25 if year < 2025 else 12


def get_problem_year_day() -> Tuple[int, int]:
    """Get the current Advent of Code year and day.

    If we're in December, use the current year and day. Otherwise, default to
    the most recent December.
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


def get_input_path(year: int, day: int) -> Path:
    """Get the path to the input file for the given year and day."""
    return get_problem_dir(year, day) / config.INPUT_FILE
