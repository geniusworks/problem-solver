"""What a human solver has in front of them at each step, beyond one article.

`fetch_problem_text` hands the parser a single `<article class="day-desc">`.
That is the whole problem for Part One. A Part Two article is written as an
amendment: it rarely restates the rules or the input format, and a solver only
ever reads it underneath Part One's statement, their accepted Part One answer,
and with their working Part One program and the puzzle input to hand. Posing it
alone measured recall of the puzzle, not the ability to solve it
(dev/progress/part2-prompt-omits-part1.md).

Everything here is read from the per-problem cache. Nothing in this module may
ever return the answer to the part being solved.
"""

from typing import Optional

from bs4 import BeautifulSoup

from shared import config
from shared.ground_truth import get_known_answer
from shared.paths import get_problem_dir

# Enough of the input to see its shape without paying for all of it.
INPUT_PREVIEW_LINES = 12
INPUT_PREVIEW_WIDTH = 160


def part_one_statement(year: int, day: int) -> Optional[str]:
    """Text of the Part One article from the cached page, or None."""
    html_path = get_problem_dir(year, day) / config.HTML_FILE
    if not html_path.exists():
        return None
    soup = BeautifulSoup(html_path.read_text(encoding="utf-8"), "html.parser")
    articles = soup.find_all("article", class_="day-desc")
    if not articles:
        return None
    return articles[0].get_text()


def page_description(year: int, day: int, part: int, part_text: str) -> str:
    """The statement as the puzzle page shows it when `part` is being solved.

    Part One is its own article. Part Two is Part One's article, the line
    confirming the accepted Part One answer, then the Part Two article.
    """
    if int(part) != 2:
        return part_text
    part_one = part_one_statement(year, day)
    if not part_one:
        return part_text
    pieces = [part_one.strip()]
    answer = get_known_answer(year, day, 1)
    if answer is not None:
        pieces.append(f"Your puzzle answer was {answer}.")
    pieces.append(part_text.strip())
    return "\n\n".join(pieces)


def input_preview(year: int, day: int) -> Optional[str]:
    """The first lines of the puzzle input, clipped, with its overall size."""
    input_path = get_problem_dir(year, day) / config.INPUT_FILE
    if not input_path.exists():
        return None
    text = input_path.read_text(encoding="utf-8", errors="replace")
    if not text.strip():
        return None
    lines = text.splitlines()
    shown = []
    for line in lines[:INPUT_PREVIEW_LINES]:
        if len(line) > INPUT_PREVIEW_WIDTH:
            line = f"{line[:INPUT_PREVIEW_WIDTH]}... [line is {len(line)} characters]"
        shown.append(line)
    header = (
        f"Your puzzle input (input.txt) has {len(lines)} lines and {len(text)} "
        f"characters. Its first {len(shown)} lines:"
    )
    return header + "\n" + "\n".join(shown)


def part_one_solution(year: int, day: int) -> Optional[str]:
    """The recorded, oracle-verified Part One program, or None.

    Only offered alongside a known Part One answer: the file is written by the
    ledger when a solution produces the accepted answer, and a solver cannot
    reach Part Two any other way.
    """
    if get_known_answer(year, day, 1) is None:
        return None
    path = get_problem_dir(year, day) / f"{year}_day{day:02d}_part1.py"
    if not path.exists():
        return None
    code = path.read_text(encoding="utf-8").strip()
    return code or None


def supplement(year: int, day: int, part: int) -> str:
    """Prompt text for what the solver has besides the statement."""
    sections = []
    preview = input_preview(year, day)
    if preview:
        sections.append(preview)
    if int(part) == 2:
        code = part_one_solution(year, day)
        if code:
            sections.append(
                "Your Part One solution, which produced the accepted Part One "
                "answer on this input:\n```python\n" + code + "\n```"
            )
    return "\n\n".join(sections)

