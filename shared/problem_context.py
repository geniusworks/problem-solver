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

import re
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Optional, Tuple

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


def supplement(
    year: int, day: int, part: int, part_one_code: Optional[str] = None
) -> str:
    """Prompt text for what the solver has besides the statement.

    `part_one_code` is the program that solved Part One in this same trial. The
    recorded one is used only when the caller has none, which happens outside
    the experiment harness.
    """
    sections = []
    preview = input_preview(year, day)
    if preview:
        sections.append(preview)
    if int(part) == 2:
        code = part_one_code or part_one_solution(year, day)
        if code:
            sections.append(
                "Your Part One solution, which produced the accepted Part One "
                "answer on this input:\n```python\n" + code + "\n```"
            )
    return "\n\n".join(sections)



def answer_direction(candidate: Optional[str], accepted: Optional[str]) -> Optional[str]:
    """'too high' / 'too low' for a wrong integer answer, as the site reports.

    None when either value is not an integer or they are equal. Callers pass
    the returned words on, never the accepted answer.
    """
    try:
        got, want = int(str(candidate).strip()), int(str(accepted).strip())
    except (TypeError, ValueError):
        return None
    if got == want:
        return None
    return "too high" if got > want else "too low"


_ERROR_WORDS = re.compile(r"\b(error|exception|traceback)\b", re.IGNORECASE)


def looks_like_error_output(output: Optional[str]) -> bool:
    """Whether a program's whole output is an error report, not an answer.

    Generated code often catches its own exception, prints a message and then a
    placeholder such as 0. That is a crash the program hid, not a wrong answer.
    """
    return bool(output) and bool(_ERROR_WORDS.search(output))


def _emphasised_result(article) -> Optional[str]:
    """The last emphasised code span in an article: the worked example's result."""
    spans = [e.get_text().strip() for e in article.select("code > em, em > code")]
    return spans[-1] if spans else None


def _run_on_example(code: str, example_input: str, timeout: int = 20) -> Optional[str]:
    """Last line a program prints when `input.txt` holds `example_input`."""
    with tempfile.TemporaryDirectory() as workdir:
        Path(workdir, "input.txt").write_text(example_input, encoding="utf-8")
        Path(workdir, "solution.py").write_text(code, encoding="utf-8")
        try:
            done = subprocess.run(
                [sys.executable, "-I", "solution.py"], cwd=workdir,
                capture_output=True, text=True, timeout=timeout,
            )
        except (subprocess.TimeoutExpired, OSError):
            return None
    lines = done.stdout.strip().splitlines()
    return lines[-1].strip() if lines else None


def part_two_example(
    year: int, day: int, part_one_code: Optional[str]
) -> Optional[Tuple[str, str]]:
    """(example input, expected Part Two result) from the page, or None.

    A Part Two usually reuses Part One's example and states a new result for
    it. The pairing is offered only when it can be checked the way a solver
    would check it: the Part One program must reproduce Part One's stated
    result on that example, and the Part Two result must be an integer.
    Against verified solutions this pairing was right in 11 of 13 cases
    (dev/progress/part2-prompt-omits-part1.md), so it is feedback, never a veto.
    """
    if not part_one_code:
        return None
    html_path = get_problem_dir(year, day) / config.HTML_FILE
    if not html_path.exists():
        return None
    soup = BeautifulSoup(html_path.read_text(encoding="utf-8"), "html.parser")
    articles = soup.find_all("article", class_="day-desc")
    if len(articles) < 2:
        return None
    pre = articles[0].find("pre")
    block = pre.find("code") if pre else None
    if block is None:
        return None
    example_input = block.get_text()
    part_one_result = _emphasised_result(articles[0])
    part_two_result = _emphasised_result(articles[1])
    if not part_one_result or not part_two_result:
        return None
    if not re.fullmatch(r"-?\d+", part_two_result):
        return None
    if _run_on_example(part_one_code, example_input) != part_one_result:
        return None
    return example_input, part_two_result
