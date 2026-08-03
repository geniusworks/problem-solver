"""Verify a solution file against known ground truth.

This is the correctness oracle for a *recorded* solution: run it against the real
puzzle input and compare its output to the accepted AoC answer. It deliberately
reports three outcomes rather than a boolean -- a solution with no known answer is
UNVERIFIED, which is not the same as CORRECT and must never be recorded as solved.
"""

import re
import subprocess
import sys
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Optional

from shared import config
from shared.ground_truth import get_known_answer
from shared.utils import get_problem_dir

SOLUTION_FILENAME_RE = re.compile(r"(\d{4})_day(\d{1,2})_part(\d)\.py$")

DEFAULT_TIMEOUT = 60


class Verdict(Enum):
    CORRECT = "correct"
    WRONG = "wrong"
    ERROR = "error"
    UNVERIFIED = "unverified"  # ran fine, but no ground truth to compare against


@dataclass
class VerificationResult:
    year: int
    day: int
    part: int
    path: Path
    verdict: Verdict
    actual: Optional[str] = None
    expected: Optional[str] = None
    error: Optional[str] = None

    @property
    def ok(self) -> bool:
        return self.verdict is Verdict.CORRECT


def parse_solution_filename(path: Path) -> Optional[tuple]:
    """Extract (year, day, part) from a canonical YYYY_dayDD_partP.py name."""
    match = SOLUTION_FILENAME_RE.search(path.name)
    if not match:
        return None
    year, day, part = match.groups()
    return int(year), int(day), int(part)


def run_solution_file(
    path: Path, year: int, day: int, timeout: int = DEFAULT_TIMEOUT
) -> tuple:
    """Run a solution against the real puzzle input.

    Returns (output, error). The solution is executed with its working directory
    set to the problem directory, because generated solutions open the bare
    relative path 'input.txt'.
    """
    problem_dir = get_problem_dir(year, day)
    input_path = problem_dir / config.INPUT_FILE

    if not input_path.exists():
        return None, f"missing input file: {input_path}"

    try:
        proc = subprocess.run(
            [sys.executable, str(path.resolve())],
            cwd=str(problem_dir),
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
    except subprocess.TimeoutExpired:
        return None, f"timed out after {timeout}s"

    if proc.returncode != 0:
        return None, (proc.stderr or "").strip()[-800:] or f"exit {proc.returncode}"

    return proc.stdout.strip(), None


def verify_solution_code(
    solution_code: str, year: int, day: int, part: int, timeout: int = DEFAULT_TIMEOUT
) -> VerificationResult:
    """Score generated source against ground truth without recording anything.

    The code is written to a scratch file and run with its working directory set
    to the problem directory, matching how a recorded solution is executed.
    """
    import tempfile

    with tempfile.TemporaryDirectory() as tmpdir:
        scratch = Path(tmpdir) / f"{year}_day{day:02d}_part{part}.py"
        scratch.write_text(solution_code, encoding="utf-8")
        return verify_solution_file(scratch, year, day, part, timeout=timeout)


def verify_solution_file(
    path: Path,
    year: Optional[int] = None,
    day: Optional[int] = None,
    part: Optional[int] = None,
    timeout: int = DEFAULT_TIMEOUT,
) -> VerificationResult:
    """Execute a solution file and score it against the accepted AoC answer."""
    if year is None or day is None or part is None:
        parsed = parse_solution_filename(path)
        if not parsed:
            return VerificationResult(
                year=0, day=0, part=0, path=path, verdict=Verdict.ERROR,
                error=f"cannot infer year/day/part from filename: {path.name}",
            )
        year, day, part = parsed

    output, error = run_solution_file(path, year, day, timeout=timeout)
    if error is not None:
        return VerificationResult(
            year=year, day=day, part=part, path=path,
            verdict=Verdict.ERROR, error=error,
        )

    expected = get_known_answer(year, day, part)
    if expected is None:
        return VerificationResult(
            year=year, day=day, part=part, path=path,
            verdict=Verdict.UNVERIFIED, actual=output,
        )

    # Generated solutions sometimes print a trailing narration line; compare the
    # last non-empty line, which is where the standardised template prints the
    # answer.
    lines = [line.strip() for line in (output or "").splitlines() if line.strip()]
    actual = lines[-1] if lines else ""

    verdict = Verdict.CORRECT if actual == expected.strip() else Verdict.WRONG
    return VerificationResult(
        year=year, day=day, part=part, path=path,
        verdict=verdict, actual=actual, expected=expected.strip(),
    )
