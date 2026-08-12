"""Verify a solution file against known ground truth.

This is the correctness oracle for a *recorded* solution: run it against the real
puzzle input and compare its output to the accepted AoC answer. It deliberately
reports three outcomes rather than a boolean -- a solution with no known answer is
UNVERIFIED, which is not the same as CORRECT and must never be recorded as solved.
"""

import ast
import logging
import re
import subprocess
import sys
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Optional

from shared import config
from shared.ground_truth import get_known_answer
from shared.paths import get_problem_dir

SOLUTION_FILENAME_RE = re.compile(r"(\d{4})_day(\d{1,2})_part(\d)\.py$")

DEFAULT_TIMEOUT = 60

logger = logging.getLogger(__name__)


class Verdict(Enum):
    CORRECT = "correct"
    WRONG = "wrong"
    ERROR = "error"
    UNVERIFIED = "unverified"  # ran fine, but no ground truth to compare against
    # Produced the accepted answer, but by hardcoding it rather than computing
    # it. A ground-truth oracle cannot catch this on its own -- the output is
    # correct by construction -- so it must be checked separately or every
    # solve-rate measurement is gameable.
    OVERFIT = "overfit"


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
    overfit_reasons: Optional[list] = None

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

    if actual != expected.strip():
        return VerificationResult(
            year=year, day=day, part=part, path=path,
            verdict=Verdict.WRONG, actual=actual, expected=expected.strip(),
        )

    # The answer matches -- but a solution that prints the accepted answer
    # without computing it also matches, by construction. Ground truth cannot
    # distinguish the two, so check for hardcoding before calling it correct.
    # Only worth doing on an otherwise-correct answer: an overfit solution that
    # gets the wrong answer is simply wrong.
    reasons = _overfit_reasons(path, year, day, part, expected.strip())
    if reasons:
        return VerificationResult(
            year=year, day=day, part=part, path=path,
            verdict=Verdict.OVERFIT, actual=actual, expected=expected.strip(),
            overfit_reasons=reasons,
        )

    return VerificationResult(
        year=year, day=day, part=part, path=path,
        verdict=Verdict.CORRECT, actual=actual, expected=expected.strip(),
    )


# Below this many characters an answer could plausibly be an incidental
# constant in real code (a grid size, a small count), so matching it as a
# literal is not evidence of anything.
_ANSWER_LITERAL_MIN_LEN = 4


def answer_appears_as_literal(source: str, expected: str) -> bool:
    """Whether the accepted answer is written verbatim into the source.

    This is the signal that catches what the structural heuristics miss. A
    solution can read input.txt, do arithmetic on it, and still `return 2970687`
    -- that defeats "constant-output stub" detection while remaining entirely
    hardcoded. But a genuine solution *computes* its answer; it has no reason to
    contain it. Short answers are exempt because they collide with ordinary
    constants.
    """
    expected = (expected or "").strip()
    if len(expected) < _ANSWER_LITERAL_MIN_LEN:
        return False

    try:
        tree = ast.parse(source)
    except SyntaxError:
        return False

    for node in ast.walk(tree):
        if not isinstance(node, ast.Constant):
            continue
        value = node.value
        if isinstance(value, bool):
            continue
        if isinstance(value, (int, float)) and str(value) == expected:
            return True
        if isinstance(value, str) and value.strip() == expected:
            return True
    return False


def _overfit_reasons(
    path: Path, year: int, day: int, part: int, expected: Optional[str] = None
) -> list:
    """Static-analysis reasons this solution looks hardcoded, if any.

    Never raises: a detector failure must not turn a real result into an error.
    """
    reasons: list = []
    try:
        source = path.read_text(encoding="utf-8")
    except OSError as e:  # pragma: no cover - defensive
        logger.warning("Could not read %s for overfit analysis: %s", path, e)
        return reasons

    try:
        from shared.overfit_detection import analyze_overfit_risk

        analysis = analyze_overfit_risk(year, day, part, source)
        if analysis.is_suspicious:
            reasons.extend(analysis.reasons)
    except Exception as e:  # pragma: no cover - defensive
        logger.warning("Overfit analysis failed for %s: %s", path, e)

    if expected and answer_appears_as_literal(source, expected):
        reasons.append(
            f"The accepted answer {expected!r} appears verbatim as a literal in the "
            f"source; a solution that computes its answer has no reason to contain it."
        )

    return reasons
