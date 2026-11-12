"""Judging and choosing candidates: run each against the oracle, and pick among those accepted.

Moved out of shared/solver.py unchanged (2026-11-12); BaseSolver gets these methods from
CandidateMixin, and shared.solver re-exports CandidateVerdict.
"""

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from shared import problem_context
from shared.execution import SolutionExecutor, TestCase
from shared.experiment import Outcome, SolverConfig
from shared.solving.feedback import FeedbackMixin

# The solver's logger, so log records keep the name they had before the move.
logger = logging.getLogger("shared.solver")


@dataclass
class CandidateVerdict:
    """Judgement on one generated candidate, from _verify_candidate."""

    accepted: bool
    outcome: Outcome
    answer: Optional[str] = None
    feedback: Optional[str] = None
    example_results: List[Any] = field(default_factory=list)
    # The worked examples' verdict, recorded beside the oracle's: how many of the
    # examples with a known result this candidate passed. 0 of 0 means the
    # problem had no usable example; validation failing first counts 0 passed.
    examples_passed: int = 0
    examples_total: int = 0


class CandidateMixin(FeedbackMixin):
    """Verification and selection, as BaseSolver uses them."""

    config: SolverConfig
    debug: bool
    solution_executor: SolutionExecutor

    def _select_candidate(
        self,
        validated: List[Tuple[str, str, Optional[str]]],
        quality_scores: Dict[str, float],
        known_answer: Optional[str],
    ) -> Tuple[str, str]:
        """Choose one candidate from those that passed verification.

        With a ground-truth oracle every validated candidate already produced
        the accepted answer, so code quality just breaks the tie. Without one
        (the submission-phase case), group candidates by their executed answer
        and prefer the plurality -- answer-based consensus. On the samp3 A/B data
        this picked the correct answer for 10 of 11 solved problem-trials; the
        one miss was two wrong candidates agreeing, which is the technique's
        inherent failure mode, so a quorum of min_consensus_models is required
        before consensus overrides quality.
        """
        def best_by_quality(items: List[Tuple[str, str, Optional[str]]]) -> Tuple[str, str]:
            ranked = sorted(
                items, key=lambda it: quality_scores.get(it[0], 0.0), reverse=True
            )
            return ranked[0][0], ranked[0][1]

        if known_answer is not None:
            return best_by_quality(validated)

        from collections import Counter
        counts = Counter(
            (ans or "").strip() for _, _, ans in validated if ans and ans.strip()
        )
        if counts:
            top_answer, top_n = counts.most_common(1)[0]
            if top_n >= self.config.min_consensus_models:
                agreeing = [
                    it for it in validated if (it[2] or "").strip() == top_answer
                ]
                logger.info(
                    "answer-based consensus selected %r (%d of %d candidates agree)",
                    top_answer, top_n, len(validated),
                )
                return best_by_quality(agreeing)

        # No answer reached quorum: fall back to the highest-quality candidate.
        return best_by_quality(validated)

    @staticmethod
    def build_test_cases(parsed_problem: Any) -> List[TestCase]:
        """Examples usable as an oracle: those with a known expected output."""
        cases: List[TestCase] = []
        for example in getattr(parsed_problem, "examples", []) or []:
            input_data = getattr(example, "input_data", None)
            expected_output = getattr(example, "expected_output", None)
            if input_data is None or expected_output in (None, ""):
                continue
            cases.append(
                TestCase(
                    input_data=str(input_data),
                    expected_output=str(expected_output),
                    description=getattr(example, "description", None),
                )
            )
        return cases

    async def _verify_candidate(
        self,
        model_name: str,
        solution: str,
        year: int,
        day: int,
        part: int,
        test_cases: List[TestCase],
        known_answer: Optional[str],
    ) -> "CandidateVerdict":
        """Run one candidate and judge it against the best available oracle.

        Oracle hierarchy: the accepted AoC answer wins when known, because the
        parser can mis-pair an expected output with the wrong <pre> block and a
        bad example must never veto a correct answer. Without ground truth,
        every example must pass -- they are the only oracle available.
        """
        example_results, full_result, full_answer = (
            await self.solution_executor.test_solution(
                solution_code=solution,
                year=year,
                day=day,
                part=part,
                test_cases=test_cases,
                model_name=model_name,
                debug=self.debug,
                force_full_input=known_answer is not None,
            )
        )

        examples_total = len(test_cases)
        examples_passed = (
            sum(1 for r in example_results if r.error is None)
            if len(example_results) == examples_total else 0
        )

        def _reject(outcome: Outcome) -> "CandidateVerdict":
            return CandidateVerdict(
                accepted=False,
                outcome=outcome,
                answer=full_answer,
                feedback=self._build_execution_feedback(
                    model_name, test_cases, example_results, full_result, full_answer,
                    direction=(
                        problem_context.answer_direction(full_answer, known_answer)
                        if self.config.problem_context == "aoc" else None
                    ),
                ),
                example_results=example_results,
                examples_passed=examples_passed,
                examples_total=examples_total,
            )

        examples_failed = bool(example_results) and any(
            r.error is not None for r in example_results
        )
        if examples_failed and known_answer is None:
            return _reject(Outcome.WRONG)
        if not full_result or full_result.error is not None:
            return _reject(Outcome.ERROR)
        if not full_answer:
            return _reject(Outcome.NO_CANDIDATE)

        if known_answer is not None:
            if full_answer.strip() != known_answer.strip():
                logger.info(
                    "%s rejected: produced %r, accepted answer is %r",
                    model_name, full_answer.strip(), known_answer.strip(),
                )
                # Code that caught its own exception and printed a message
                # crashed; it did not compute a wrong answer.
                if problem_context.looks_like_error_output(full_answer):
                    return _reject(Outcome.ERROR)
                return _reject(Outcome.WRONG)
            outcome = Outcome.SOLVED
        else:
            # Examples all passed, but nothing confirms the full-input answer.
            outcome = Outcome.UNVERIFIED

        return CandidateVerdict(
            accepted=True,
            outcome=outcome,
            answer=full_answer,
            feedback=None,
            example_results=example_results,
            examples_passed=examples_passed,
            examples_total=examples_total,
        )
