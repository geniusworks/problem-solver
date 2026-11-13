#!/usr/bin/env python
"""The AoC 2026 nightly run: fetch, trials, submission step, Part 2, summary.

Run unattended by launchd at 02:00 Pacific, five hours after each puzzle's release
(scripts/com.problem-solver.nightly.plist). As registered in
dev/progress/aoc2026-registration.md, "The nightly run":

  1. Refuses to start unless a named account is active (AOC_ACCOUNT) and generated code
     runs without network (execution.deny_network / DENY_NETWORK).
  2. One request checks the session; the run stops, loudly, if it has expired.
  3. Fetches the day's page and input once. If either is unavailable it stops and
     reports; it never polls. The page is audited for hidden text.
  4. For every event day up to tonight's, in order, does whatever is still owed: Part 1
     trials (config/nightly.yaml), the submission step, and once a model's Part 1 is
     accepted, the recorded answers scored, the page refreshed for Part 2, Part 2's
     trials (the held-out test's arms) and its submission step. Every step is idempotent:
     a run restarted the same night picks up where the last one stopped, at the trial.
  5. Writes a log and a one-page summary for the morning.

Usage:
    AOC_ACCOUNT=experiment venv/bin/python nightly.py            # tonight's puzzle
    AOC_ACCOUNT=experiment venv/bin/python nightly.py --day 3    # catch up to day 3
    AOC_ACCOUNT=experiment venv/bin/python nightly.py --year 2025 --from-day 9 --day 9
                                                                 # one past day (end-to-end test)
"""

import argparse
import asyncio
import logging
import os
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Awaitable, Callable, Dict, List, Optional
from zoneinfo import ZoneInfo

import yaml

REPO_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(REPO_ROOT))

from experiment import parse_config  # noqa: E402
from shared import config as settings  # noqa: E402
from shared.experiment import ExperimentResult, Outcome, SolverConfig  # noqa: E402
from shared.experiment.rescore import rescore  # noqa: E402
from shared.experiment.runner import problem_id  # noqa: E402
from shared.ground_truth import get_known_answer, part_has_puzzle  # noqa: E402
from shared.page_audit import audit_page, needs_review  # noqa: E402
from shared.paths import account_dir, get_aoc_day_count, get_problem_dir  # noqa: E402
from shared.sandbox import network_denied  # noqa: E402
from shared.verification import Verdict, verify_solution_code  # noqa: E402
from submission.policy import SubmissionState  # noqa: E402
from submission.replies import ReplyKind  # noqa: E402
from submission.step import StepReport, state_path, submit_part  # noqa: E402

logger = logging.getLogger("nightly")

PLAN_FILE = REPO_ROOT / "config" / "nightly.yaml"
RELEASE_ZONE = ZoneInfo("America/New_York")


@dataclass
class Plan:
    year: int
    trials: Dict[int, int]
    configs: Dict[int, List[SolverConfig]]

    @classmethod
    def load(cls, path: Path = PLAN_FILE) -> "Plan":
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        return cls(
            year=int(data["year"]),
            trials={part: int(data[f"part{part}"]["trials"]) for part in (1, 2)},
            configs={part: [parse_config(spec) for spec in data[f"part{part}"]["configs"]]
                     for part in (1, 2)},
        )


def puzzle_day(year: int, now: Optional[datetime] = None) -> Optional[int]:
    """The latest day of `year`'s event released by `now` (puzzles open at midnight in
    New York), or None outside the event."""
    local = (now or datetime.now(timezone.utc)).astimezone(RELEASE_ZONE)
    if local.year != year or local.month != 12:
        return None
    return min(local.day, get_aoc_day_count(year))


@dataclass
class Tools:
    """Everything the run does outside this module; tests replace them."""

    check_session: Callable[[int], Awaitable[None]]
    ensure_problem_files: Callable[[int, int], Awaitable[Any]]
    refresh_problem_page: Callable[[int, int], Awaitable[Any]]
    run_experiment: Callable[..., Awaitable[ExperimentResult]]
    submit_part: Callable[..., Awaitable[StepReport]] = submit_part

    @classmethod
    def real(cls) -> "Tools":
        from shared.aoc import check_session, ensure_problem_files, refresh_problem_page
        from shared.experiment.runner import run_experiment
        return cls(check_session, ensure_problem_files, refresh_problem_page, run_experiment)


@dataclass
class Night:
    """What the run did, for the log and the morning summary."""

    started: datetime
    lines: List[str] = field(default_factory=list)
    stopped: Optional[str] = None
    flagged_days: List[int] = field(default_factory=list)

    def note(self, text: str) -> None:
        logger.info(text)
        self.lines.append(text)

    def stop(self, reason: str) -> None:
        logger.error(reason)
        self.stopped = reason

    def summary(self, year: int) -> str:
        head = f"# AoC {year} nightly run, {self.started.astimezone(RELEASE_ZONE):%Y-%m-%d %H:%M %Z}\n"
        status = f"\n**Stopped:** {self.stopped}\n" if self.stopped else "\n**Completed.**\n"
        flagged = (f"\nDays reported apart for hidden page text: {', '.join(map(str, self.flagged_days))}\n"
                   if self.flagged_days else "")
        return head + status + flagged + "\n" + "\n".join(f"- {line}" for line in self.lines) + "\n"


def night_dir(year: int) -> Path:
    return account_dir() / "nightly" / str(year)


def results_dir(year: int, day: int, part: int) -> Path:
    return account_dir() / "experiments" / problem_id(year, day, part)


def trial_file(year: int, day: int, part: int, cfg: SolverConfig, trial: int) -> Path:
    return results_dir(year, day, part) / f"{cfg.name}_{cfg.fingerprint()}_t{trial}.json"


def finished(path: Path) -> Optional[ExperimentResult]:
    """The saved trial at `path` if it ran to the end; a partial one is run again."""
    if not path.exists():
        return None
    result = ExperimentResult.load(path)
    return result if result.finished_at else None


def recorded(year: int, day: int, part: int) -> List[Path]:
    folder = results_dir(year, day, part)
    return sorted(folder.glob("*.json")) if folder.exists() else []


async def run_trials(year: int, day: int, part: int, plan: Plan, tools: Tools, night: Night) -> None:
    """The plan's trials for one part, one trial at a time across its configs."""
    ran = 0
    for trial in range(plan.trials[part]):
        for cfg in plan.configs[part]:
            path = trial_file(year, day, part, cfg, trial)
            if finished(path) is not None:
                continue
            result = await tools.run_experiment(
                [(year, day, part)], cfg, account_dir(), trials=1,
                save_to=path, include_replay=True,
            )
            for problem in result.results:
                problem.trial = trial
            result.save(path, include_replay=True)
            ran += 1
    if ran:
        night.note(f"{problem_id(year, day, part)}: ran {ran} trial(s)")


def accepted_by_step(year: int, day: int, part: int) -> bool:
    """Whether the submission step's own post was accepted (not a hand-solved part)."""
    state = SubmissionState.load(state_path())
    part_state = state.parts.get(problem_id(year, day, part))
    return part_state is not None and any(
        s["reply"] == ReplyKind.ACCEPTED.value for s in part_state.submissions)


def score_recorded(year: int, day: int, part: int, night: Night) -> List[ExperimentResult]:
    accepted = get_known_answer(year, day, part)
    experiments = []
    for path in recorded(year, day, part):
        experiment = ExperimentResult.load(path)
        if accepted is not None and rescore(experiment, year, day, part, accepted):
            experiment.save(path, include_replay=True)
        experiments.append(experiment)
    if accepted is not None:
        solved = sum(1 for e in experiments for r in e.results if r.outcome is Outcome.SOLVED)
        night.note(f"{problem_id(year, day, part)}: accepted {accepted}; "
                   f"{solved} of {sum(len(e.results) for e in experiments)} trial(s) solved it")
    return experiments


def install_part_one_program(year: int, day: int, experiments: List[ExperimentResult],
                             night: Night) -> bool:
    """Write a model's verified Part 1 program where the context arm reads it.

    The solve loop may already have saved a program there that it could not verify (no
    answer was known during the trials). If no recorded program reproduces the accepted
    answer, that file is removed, so the context arm is never shown an unverified program.
    """
    from shared.ledger import save_solution_file

    for experiment in experiments:
        for result in experiment.results:
            for attempt in result.attempts:
                if attempt.outcome is not Outcome.SOLVED or not attempt.code:
                    continue
                if verify_solution_code(attempt.code, year, day, 1).verdict is Verdict.CORRECT:
                    save_solution_file(year, day, 1, attempt.model, attempt.code)
                    return True
    (get_problem_dir(year, day) / f"{problem_id(year, day, 1)}.py").unlink(missing_ok=True)
    night.note(f"{problem_id(year, day, 1)}: no recorded program reproduces the accepted "
               f"answer, so the context arm has no Part 1 program")
    return False


async def submit(year: int, day: int, part: int, tools: Tools, night: Night) -> StepReport:
    experiments = [ExperimentResult.load(path) for path in recorded(year, day, part)]
    report = await tools.submit_part(year, day, part, experiments)
    night.note(report.line())
    if report.outcome == "halted":
        night.stop(f"submission halted: {report.detail}")
    return report


async def advance_day(year: int, day: int, plan: Plan, tools: Tools, night: Night) -> None:
    """Do whatever is still owed for one day of the event."""
    # Part 1
    if get_known_answer(year, day, 1) is None:
        await run_trials(year, day, 1, plan, tools, night)
        await submit(year, day, 1, tools, night)
        if night.stopped or get_known_answer(year, day, 1) is None:
            return
    part_one = score_recorded(year, day, 1, night)
    if not accepted_by_step(year, day, 1):
        night.note(f"{problem_id(year, day, 1)}: accepted outside the submission step; "
                   f"its Part 2 is not run by the nightly (reported apart)")
        return

    # Part 2, visible once Part 1 is accepted
    page = get_problem_dir(year, day) / settings.HTML_FILE
    if "--- Part Two ---" not in page.read_text(encoding="utf-8"):
        try:
            await tools.refresh_problem_page(year, day)
            await tools.ensure_problem_files(year, day)
        except Exception as error:
            night.stop(f"day {day}: refreshing the page for Part 2 failed ({error}); not retried")
            return
        if "--- Part Two ---" not in page.read_text(encoding="utf-8"):
            night.stop(f"day {day}: Part 1 is accepted but the refreshed page shows no Part 2")
            return
        audit(year, day, night)
    if not part_has_puzzle(year, day, 2):
        night.note(f"{problem_id(year, day, 2)}: the last day's Part 2 is not a puzzle")
        return
    if get_known_answer(year, day, 2) is None:
        install_part_one_program(year, day, part_one, night)
        await run_trials(year, day, 2, plan, tools, night)
        await submit(year, day, 2, tools, night)
    score_recorded(year, day, 2, night)


def audit(year: int, day: int, night: Night) -> None:
    findings = audit_page((get_problem_dir(year, day) / settings.HTML_FILE).read_text(encoding="utf-8"))
    if needs_review(findings):
        night.flagged_days.append(day)
        for finding in findings:
            night.note(f"day {day} page: {finding.line()}")


async def run_night(year: int, last_day: int, plan: Plan, tools: Tools,
                    now: Optional[datetime] = None, first_day: int = 1) -> Night:
    night = Night(started=now or datetime.now(timezone.utc))
    if not settings.account_name():
        night.stop("AOC_ACCOUNT is not set: the nightly runs only as the experiment account")
        return night
    if not network_denied():
        night.stop("generated code would run with network access: set execution.deny_network")
        return night
    try:
        await tools.check_session(year)
    except Exception as error:
        night.stop(f"session check failed: {error}")
        return night
    night.note("session checked")
    for day in range(first_day, last_day + 1):
        try:
            await tools.ensure_problem_files(year, day)
        except Exception as error:
            night.stop(f"day {day}: page or input unavailable ({error}); not retried")
            return night
        if day not in night.flagged_days:
            audit(year, day, night)
        await advance_day(year, day, plan, tools, night)
        if night.stopped:
            break
    return night


def clear_halt() -> str:
    """Lift a submission halt once the maintainer has looked at it. A post whose reply was
    never read stays on record as an unknown reply: never posted again, and counted wrong."""
    path = state_path()
    state = SubmissionState.load(path)
    reason = state.halted
    for part in state.parts.values():
        for entry in part.submissions:
            if entry["reply"] == "pending":
                entry["reply"] = ReplyKind.UNKNOWN.value
    state.halted = None
    state.save(path)
    return f"cleared: {reason}" if reason else "no halt was set"


class _Lock:
    """One nightly run per account at a time."""

    def __init__(self, path: Path):
        self.path = path

    def __enter__(self) -> "_Lock":
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if self.path.exists():
            pid = int(self.path.read_text().strip() or 0)
            try:
                os.kill(pid, 0)
            except (OSError, ValueError):
                pass
            else:
                raise SystemExit(f"another nightly run (pid {pid}) holds {self.path}")
        self.path.write_text(str(os.getpid()))
        return self

    def __exit__(self, *exc: Any) -> None:
        self.path.unlink(missing_ok=True)


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--plan", type=Path, default=PLAN_FILE)
    parser.add_argument("--day", type=int, help="Last day to work on (default: tonight's)")
    parser.add_argument("--year", type=int,
                        help="Event year (default: the plan's; the end-to-end test uses 2024 and 2025)")
    parser.add_argument("--from-day", type=int, default=1,
                        help="First day to work on (default 1; the end-to-end test runs one day)")
    parser.add_argument("--refresh-page", type=int, metavar="DAY",
                        help="Fetch DAY's page once (after solving a part by hand) and exit")
    parser.add_argument("--clear-halt", action="store_true",
                        help="Clear a submission halt after reviewing it, and exit")
    args = parser.parse_args(argv)

    plan = Plan.load(args.plan)
    if args.year:
        plan.year = args.year
    if args.clear_halt:
        print(clear_halt())
        return 0
    if args.refresh_page:
        from shared.aoc import refresh_problem_page
        asyncio.run(refresh_problem_page(plan.year, args.refresh_page))
        print(f"day {args.refresh_page}: page refreshed; accepted answers "
              f"{[get_known_answer(plan.year, args.refresh_page, p) for p in (1, 2)]}")
        return 0
    started = datetime.now(timezone.utc)
    last_day = args.day or puzzle_day(plan.year, started)
    if last_day is None:
        print(f"No AoC {plan.year} puzzle is open tonight.")
        return 0

    folder = night_dir(plan.year)
    folder.mkdir(parents=True, exist_ok=True)
    stamp = f"{started.astimezone(RELEASE_ZONE):%Y-%m-%d}"
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s",
        handlers=[logging.FileHandler(folder / f"{stamp}.log"), logging.StreamHandler()],
    )
    with _Lock(folder / ".lock"):
        night = asyncio.run(run_night(plan.year, last_day, plan, Tools.real(), started,
                                      first_day=args.from_day))
    summary = folder / f"{stamp}-summary.md"
    summary.write_text(night.summary(plan.year), encoding="utf-8")
    print(f"summary: {summary}")
    return 1 if night.stopped else 0


if __name__ == "__main__":
    sys.exit(main())
