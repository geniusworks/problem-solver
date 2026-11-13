"""Scoring recorded answers once an accepted answer exists.

A trial of an unseen puzzle records its answers as UNVERIFIED: nothing can check them
yet. When an answer is accepted (by the submission step, or by the maintainer solving the
part on the same account), every recorded answer for that part, from any trial or model,
is scored against it exactly as it would have been scored live: an attempt's output compared
whole with the accepted answer (shared/solving/candidates.py), a trial's final answer by its
last printed line (shared/verification.py; an unverified record keeps the whole output), and a
match checked for hardcoding when the attempt's code was recorded (--include-replay).
"""

import argparse
import sys
from pathlib import Path
from typing import List, Optional

from shared.experiment.results import ExperimentResult, Outcome
from shared.experiment.runner import problem_id
from shared.ground_truth import get_known_answer
from shared.verification import answer_line, overfit_reasons_for_source


def _verdict(answer: Optional[str], code: Optional[str], year: int, day: int, part: int,
             accepted: str, last_line: bool) -> Outcome:
    printed = answer_line(answer) if last_line else (answer or "").strip()
    if printed != accepted:
        return Outcome.WRONG
    if code and overfit_reasons_for_source(code, year, day, part, accepted):
        return Outcome.OVERFIT
    return Outcome.SOLVED


def rescore(experiment: ExperimentResult, year: int, day: int, part: int, accepted: str) -> int:
    """Score the UNVERIFIED records of one part against `accepted`; returns how many changed."""
    accepted = accepted.strip()
    target = problem_id(year, day, part)
    changed = 0
    for result in experiment.results:
        if result.problem_id != target:
            continue
        for attempt in result.attempts:
            if attempt.outcome is Outcome.UNVERIFIED:
                attempt.outcome = _verdict(attempt.answer, attempt.code, year, day, part, accepted,
                                           last_line=False)
                attempt.expected = accepted
                changed += 1
        if result.outcome is Outcome.UNVERIFIED:
            winner = next((a for a in result.attempts
                           if answer_line(a.answer) == answer_line(result.answer)), None)
            result.outcome = _verdict(result.answer, winner.code if winner else None,
                                      year, day, part, accepted, last_line=True)
            result.expected = accepted
            if result.outcome is Outcome.SOLVED and winner is not None:
                result.winning_model = winner.model
            changed += 1
    return changed


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="Score a part's recorded answers against the active account's accepted answer")
    parser.add_argument("year", type=int)
    parser.add_argument("day", type=int)
    parser.add_argument("part", type=int, choices=(1, 2))
    parser.add_argument("results", type=Path, nargs="+")
    args = parser.parse_args(argv)
    accepted = get_known_answer(args.year, args.day, args.part)
    if accepted is None:
        print(f"no accepted answer is cached for {problem_id(args.year, args.day, args.part)}")
        return 1
    for path in args.results:
        experiment = ExperimentResult.load(path)
        changed = rescore(experiment, args.year, args.day, args.part, accepted)
        if changed:
            experiment.save(path, include_replay=True)
        print(f"{path}: {changed} record(s) scored")
    return 0


if __name__ == "__main__":
    sys.exit(main())
