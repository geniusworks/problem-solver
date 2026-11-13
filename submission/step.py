"""The submission step: after a night's trials, post the best candidates within the budget.

It runs after the trials and is separate from them: the solve loop never sees AoC's
replies, and "too high" or "too low" only rules candidates out here. Usage:

    AOC_ACCOUNT=experiment venv/bin/python -m submission.step 2026 1 1 accounts/experiment/experiments/*.json

With SUBMIT_SOLUTIONS unset or false it reports what it would post and posts nothing.
"""

import argparse
import asyncio
import logging
import sys
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Awaitable, Callable, List, Optional, Sequence, Tuple

from shared import config
from shared.experiment.results import ExperimentResult
from shared.experiment.runner import problem_id
from shared.ground_truth import get_known_answer, save_known_answers
from shared.paths import account_dir
from submission.policy import (Budget, SubmissionState, decide, halt_on_unanswered_posts,
                               rank_candidates, record_pending, record_reply, utcnow)
from submission.replies import ReplyKind, parse_reply

logger = logging.getLogger(__name__)

Poster = Callable[[int, int, int, str], Awaitable[str]]


def state_path() -> Path:
    return account_dir() / "submissions.json"


@dataclass
class StepReport:
    problem: str
    # accepted | already_accepted | budget_spent | night_cap | no_candidates | waiting |
    # halted | disabled
    outcome: str
    posted: List[Tuple[str, str]] = field(default_factory=list)
    would_post: Optional[str] = None
    detail: str = ""

    def line(self) -> str:
        posted = ", ".join(f"{a} -> {k}" for a, k in self.posted) or "nothing posted"
        extra = f"; would post {self.would_post}" if self.would_post else ""
        detail = f" ({self.detail})" if self.detail else ""
        return f"{self.problem}: {self.outcome}{detail}; {posted}{extra}"


async def submit_part(
    year: int, day: int, part: int, experiments: Sequence[ExperimentResult], *,
    post: Optional[Poster] = None,
    enabled: Optional[bool] = None,
    budget: Optional[Budget] = None,
    now: Callable[[], datetime] = utcnow,
    sleep: Callable[[float], Awaitable[Any]] = asyncio.sleep,
) -> StepReport:
    """Post candidates for one part until one is accepted or a limit is reached."""
    if not config.account_name():
        raise ValueError("The submission step runs only for a named account: set AOC_ACCOUNT")
    if post is None:
        from submission.client import post_answer
        post = post_answer
    enabled = config.SUBMIT_SOLUTIONS if enabled is None else enabled
    budget = budget or Budget.from_config()
    problem = problem_id(year, day, part)
    path = state_path()
    state = SubmissionState.load(path)
    halt_on_unanswered_posts(state)
    report = StepReport(problem, "")

    # An answer the account's page already shows is final; nothing is posted for it.
    known = get_known_answer(year, day, part)
    if known is not None and state.part(problem).accepted is None:
        state.part(problem).accepted = known
        state.save(path)
        report.outcome = "already_accepted"
        return report

    candidates = rank_candidates(experiments, problem)
    while True:
        decision = decide(state, problem, candidates, budget, now())
        if decision.reason == "accepted" and get_known_answer(year, day, part) is None:
            # Accepted before a crash kept it from the answer cache.
            save_known_answers(year, day, {part: str(state.part(problem).accepted)})
        if decision.answer is None:
            report.outcome = decision.reason
            report.detail = state.halted or ""
            break
        if decision.wait_until is not None:
            seconds = (decision.wait_until - now()).total_seconds()
            if seconds > budget.longest_wait_seconds:
                report.outcome = "waiting"
                report.detail = f"AoC's wait runs to {decision.wait_until.isoformat()}"
                break
            await sleep(max(seconds, 0))
            continue
        if not enabled:
            report.outcome = "disabled"
            report.would_post = decision.answer
            break

        record_pending(state, problem, decision.answer, now())
        state.save(path)
        try:
            html = await post(year, day, part, decision.answer)
        except Exception as error:
            # Whether the post reached AoC is unknown, so the pending entry stays and halts.
            state.halted = f"posting {decision.answer!r} for {problem} failed: {error}"
            state.save(path)
            report.outcome = "halted"
            report.detail = state.halted
            break
        reply = parse_reply(html)
        record_reply(state, problem, decision.answer, reply.kind, reply.wait_seconds, budget, now())
        state.save(path)
        report.posted.append((decision.answer, reply.kind.value))
        logger.info("%s: posted %s, AoC replied %s", problem, decision.answer, reply.kind.value)

        if reply.kind is ReplyKind.ACCEPTED:
            save_known_answers(year, day, {part: decision.answer})
            report.outcome = "accepted"
            break
    return report


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("year", type=int)
    parser.add_argument("day", type=int)
    parser.add_argument("part", type=int, choices=(1, 2))
    parser.add_argument("results", type=Path, nargs="+", help="Result files of the trials")
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    experiments = [ExperimentResult.load(path) for path in args.results]
    report = asyncio.run(submit_part(args.year, args.day, args.part, experiments))
    print(report.line())
    return 0 if report.outcome != "halted" else 2


if __name__ == "__main__":
    sys.exit(main())
