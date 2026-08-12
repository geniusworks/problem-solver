"""The solution ledger -- where verified solutions are written down.

Records accepted solutions to `solutions/README.md` and saves the canonical
solution file, gated by the correctness oracle so nothing enters the ledger
without producing the accepted answer. This is a high layer: it imports
verification and ground_truth at the top, cleanly, because those depend only on
shared.paths -- not on this module. (When record_solution lived in
shared/utils.py alongside get_problem_dir, those top-level imports would have
closed a cycle, so they were deferred function-body imports; here they don't
need to be.)
"""

import logging
import re
from datetime import datetime, timezone
from pathlib import Path

from shared.ground_truth import get_known_answer
from shared.overfit_detection import analyze_overfit_risk
from shared.paths import get_problem_dir
from shared.verification import Verdict, verify_solution_code

logger = logging.getLogger(__name__)

# Anchor in solutions/README.md marking the end of the verified-solutions table.
# New rows are inserted immediately above it so they never land in the rejected
# table that follows.
VERIFIED_ROWS_MARKER = "<!-- end verified rows -->"


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
