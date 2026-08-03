"""Run a problem set under one configuration and measure the outcome.

The runner verifies independently of the solver. solve_problem deciding a
candidate is good is a *claim*; the runner re-executes the returned code against
ground truth and records what actually happened. Keeping the two apart is what
makes a result trustworthy -- a bug in the solver's acceptance logic shows up as
a claimed/verified gap rather than as a silently inflated solve rate.
"""

import logging
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, List, Optional, Sequence, Tuple

from shared.experiment.config import SolverConfig
from shared.experiment.results import (
    AttemptRecord,
    ExperimentResult,
    Outcome,
    ProblemResult,
)
from shared.ground_truth import get_known_answer
from shared.verification import Verdict, verify_solution_code

logger = logging.getLogger(__name__)

ProblemSpec = Tuple[int, int, int]  # (year, day, part)


def problem_id(year: int, day: int, part: int) -> str:
    return f"{year}_day{day:02d}_part{part}"


def parse_problem_set(spec: str) -> List[ProblemSpec]:
    """Parse a problem-set string such as '2024:1-6' or '2024:1.1,2024:3.2'.

    Forms:
      2024:1-6      days 1..6, both parts
      2024:3        day 3, both parts
      2024:3.2      day 3 part 2 only
    """
    problems: List[ProblemSpec] = []
    for chunk in spec.split(","):
        chunk = chunk.strip()
        if not chunk:
            continue
        if ":" not in chunk:
            raise ValueError(f"Malformed problem spec {chunk!r}; expected YEAR:DAYS")
        year_text, day_text = chunk.split(":", 1)
        year = int(year_text)

        part: Optional[int] = None
        if "." in day_text:
            day_text, part_text = day_text.split(".", 1)
            part = int(part_text)

        if "-" in day_text:
            start, end = day_text.split("-", 1)
            days = range(int(start), int(end) + 1)
        else:
            days = range(int(day_text), int(day_text) + 1)

        for day in days:
            for p in ([part] if part else [1, 2]):
                problems.append((year, day, p))
    return problems


def _classify(code: Optional[str], year: int, day: int, part: int) -> Tuple[Outcome, Optional[str], Optional[str]]:
    """Independently judge what the solver returned.

    Returns (outcome, answer, expected).
    """
    expected = get_known_answer(year, day, part)

    if not code:
        return Outcome.NO_CANDIDATE, None, expected

    # solve_problem returns source on the generate paths but a bare answer on
    # the existing-solution reuse path. A bare answer is not re-runnable, so
    # score it directly against ground truth.
    if "def solve" not in code:
        answer = code.strip()
        if expected is None:
            return Outcome.UNVERIFIED, answer, None
        return (
            Outcome.SOLVED if answer == expected.strip() else Outcome.WRONG,
            answer,
            expected,
        )

    result = verify_solution_code(code, year, day, part)
    mapping = {
        Verdict.CORRECT: Outcome.SOLVED,
        Verdict.WRONG: Outcome.WRONG,
        Verdict.UNVERIFIED: Outcome.UNVERIFIED,
        Verdict.ERROR: Outcome.ERROR,
    }
    return mapping[result.verdict], result.actual, result.expected


async def run_problem(
    solver,
    year: int,
    day: int,
    part: int,
    config: SolverConfig,
    force: bool = True,
) -> ProblemResult:
    """Solve one problem and independently verify the result."""
    pid = problem_id(year, day, part)
    started = time.monotonic()
    code: Optional[str] = None
    error: Optional[str] = None

    try:
        code = await solver.solve_problem(year, day, part, force=force)
    except Exception as e:  # the harness must survive a failing problem
        error = f"{type(e).__name__}: {e}"
        logger.warning("Solver raised on %s: %s", pid, error)

    elapsed = time.monotonic() - started

    if error is not None:
        outcome, answer, expected = Outcome.ERROR, None, get_known_answer(year, day, part)
    else:
        outcome, answer, expected = _classify(code, year, day, part)

    result = ProblemResult(
        problem_id=pid,
        year=year,
        day=day,
        part=part,
        config_fingerprint=config.fingerprint(),
        outcome=outcome,
        answer=answer,
        expected=expected,
        wall_clock_seconds=elapsed,
    )
    result.attempts.append(
        AttemptRecord(
            model="solver",
            problem_id=pid,
            config_fingerprint=config.fingerprint(),
            outcome=outcome,
            answer=answer,
            expected=expected,
            error=error,
            wall_clock_seconds=elapsed,
            code=code,
        )
    )
    return result


async def run_experiment(
    problems: Sequence[ProblemSpec],
    config: SolverConfig,
    workspace_dir: Path,
    debug: bool = False,
    on_result=None,
) -> ExperimentResult:
    """Run a problem set under one configuration.

    on_result, if given, is called with each ProblemResult as it completes --
    useful for progress output on long sweeps.
    """
    from shared.solver import BaseSolver

    solver = BaseSolver(workspace_dir, debug=debug, config=config)

    experiment = ExperimentResult(
        config_name=config.name,
        config_fingerprint=config.fingerprint(),
        config=config.to_dict(),
        started_at=datetime.now(timezone.utc).isoformat(),
    )

    for year, day, part in problems:
        result = await run_problem(solver, year, day, part, config)
        experiment.results.append(result)
        if on_result is not None:
            on_result(result)

    experiment.finished_at = datetime.now(timezone.utc).isoformat()
    return experiment


def compare(experiments: Iterable[ExperimentResult]) -> str:
    """Render a side-by-side comparison table of several configurations."""
    rows = list(experiments)
    if not rows:
        return "(no experiments)"

    headers = ["config", "solved", "rate", "1st-try", "wrong", "unver", "mean-att", "wall(s)"]
    table = [headers]
    for e in rows:
        s = e.summary()
        table.append([
            f"{s['config_name']} ({s['config_fingerprint']})",
            f"{s['solved']}/{s['attempted']}",
            f"{s['solve_rate']:.0%}",
            f"{s['first_try_rate']:.0%}",
            str(s["wrong"]),
            str(s["unverified"]),
            "-" if s["mean_attempts_to_solve"] is None else f"{s['mean_attempts_to_solve']:.1f}",
            f"{s['total_wall_clock_seconds']:.0f}",
        ])

    widths = [max(len(row[i]) for row in table) for i in range(len(headers))]
    lines = []
    for index, row in enumerate(table):
        lines.append("  ".join(cell.ljust(widths[i]) for i, cell in enumerate(row)).rstrip())
        if index == 0:
            lines.append("  ".join("-" * w for w in widths))
    return "\n".join(lines)
