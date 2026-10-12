"""Ground-truth answer store.

Advent of Code renders the accepted answer for every part the user has already
solved directly into the puzzle page:

    <p>Your puzzle answer was <code>2970687</code>.</p>

That makes any previously-solved day a *labelled* benchmark problem: we can score
a generated solution against the real answer without submitting anything. This
module persists those answers next to the cached problem HTML so the solver has a
correctness oracle for the full input, not just for the worked examples.

Days the user has not solved simply have no entry, and callers must treat a
missing answer as "unknown" rather than "wrong" -- see ``get_known_answer``.
"""

import json
import logging
from pathlib import Path
from typing import Dict, Optional

from bs4 import BeautifulSoup

from shared import config
from shared.paths import get_problem_dir

logger = logging.getLogger(__name__)


def _answers_path(year: int, day: int) -> Path:
    return get_problem_dir(year, day) / config.ANSWERS_FILE


def load_known_answers(year: int, day: int) -> Dict[int, str]:
    """Return the stored ground-truth answers for a day, keyed by part number."""
    path = _answers_path(year, day)
    if not path.exists():
        return {}

    try:
        with open(path, "r", encoding="utf-8") as f:
            raw = json.load(f)
    except (json.JSONDecodeError, OSError) as e:
        logger.warning("Could not read ground truth at %s: %s", path, e)
        return {}

    answers: Dict[int, str] = {}
    for key, value in raw.items():
        if value in (None, ""):
            continue
        try:
            answers[int(key)] = str(value)
        except (TypeError, ValueError):
            logger.warning("Ignoring malformed ground-truth key %r in %s", key, path)
    return answers


def save_known_answers(year: int, day: int, answers: Dict[int, str]) -> None:
    """Persist ground-truth answers, merging with anything already stored.

    Existing entries win: an answer accepted by AoC is final, so a later scrape
    returning nothing (for example a logged-out fetch) must not erase it.
    """
    merged = load_known_answers(year, day)
    for part, answer in answers.items():
        if answer in (None, ""):
            continue
        merged[int(part)] = str(answer)

    if not merged:
        return

    path = _answers_path(year, day)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump({str(k): v for k, v in sorted(merged.items())}, f, indent=2)
        f.write("\n")


def get_known_answer(year: int, day: int, part: int) -> Optional[str]:
    """Return the accepted answer for a part, or None if it is not known.

    None means "we have no oracle for this problem", never "the answer is wrong".
    """
    return load_known_answers(year, day).get(int(part))


def extract_answers_from_html(html: str) -> Dict[int, str]:
    """Pull accepted answers out of a cached AoC puzzle page.

    The answers appear in part order, so the first is Part 1 and the second is
    Part 2.
    """
    soup = BeautifulSoup(html, "html.parser")
    found = []

    for elem in soup.find_all("p"):
        text = elem.get_text().strip()
        if "Your puzzle answer was" not in text:
            continue
        code = elem.find("code")
        if code is not None:
            found.append(code.get_text().strip())

    return {part: answer for part, answer in enumerate(found[:2], start=1) if answer}


def backfill_from_cached_html(year: int, day: int) -> Dict[int, str]:
    """Recover ground truth from an already-downloaded problem page."""
    html_path = get_problem_dir(year, day) / config.HTML_FILE
    if not html_path.exists():
        return {}

    with open(html_path, "r", encoding="utf-8") as f:
        answers = extract_answers_from_html(f.read())

    if answers:
        save_known_answers(year, day, answers)
    return answers


def html_part_has_puzzle(html: str, part: int) -> bool:
    """Whether `part` of a cached AoC page is a puzzle with an answer to find.

    The last day of an event may have only one puzzle. Its page still carries a
    "Part Two" article, but that part is finished with a button rather than an
    answer: the form posts ``level=2`` with a *hidden* ``answer`` field, both
    before the day is complete and after ("... Again"). A real Part 2 either
    shows a text ``answer`` field or, once solved, no form at all. Which days
    are like this varies by year, so it is read from the page, never assumed
    from the day number.
    """
    if int(part) != 2:
        return True

    soup = BeautifulSoup(html, "html.parser")
    for form in soup.find_all("form"):
        level = form.find("input", attrs={"name": "level"})
        answer = form.find("input", attrs={"name": "answer"})
        if level is None or answer is None:
            continue
        if level.get("value") == "2" and answer.get("type") == "hidden":
            return False
    return True


def part_has_puzzle(year: int, day: int, part: int) -> bool:
    """Whether a part exists as a puzzle, judged from the cached page.

    Returns True when the page is not cached: absence of evidence is not a
    reason to drop a problem from a run.
    """
    html_path = get_problem_dir(year, day) / config.HTML_FILE
    if not html_path.exists():
        return True

    with open(html_path, "r", encoding="utf-8") as f:
        return html_part_has_puzzle(f.read(), part)
