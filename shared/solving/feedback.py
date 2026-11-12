"""What a failed candidate's repair is told: the execution feedback and its targeted guidance.

Moved out of shared/solver.py unchanged (2026-11-12); BaseSolver gets _build_execution_feedback
from FeedbackMixin (through CandidateMixin), and shared.solver re-exports _is_timeout_error.
"""

from typing import Any, List, Optional

from shared import problem_context
from shared.execution import TestCase
from shared.experiment import SolverConfig


def _wrong_answer_guidance(produced: str) -> List[str]:
    """Repair guidance for code that runs cleanly and computes the wrong thing.

    This is the dominant real failure mode: across the two hardest recorded
    problems, 80 of 132 attempts were wrong answers and none was a timeout
    (dev/progress/CORRECTION-d15p2-is-not-a-wall.md). The default message says
    only that the answer was not accepted, which invites a cosmetic edit and
    another wrong answer.

    NOTE: deliberately echoes only what the model ITSELF produced. The expected
    full-input answer is not available to this function and must never be --
    handing the model the target would make the overfit gate the only thing
    standing between us and a hardcoded "solution", and would invalidate the
    measurement.
    """
    return [
        f"Your code ran successfully and produced: {produced}",
        "That value is INCORRECT. The code has no crash and no timeout -- the logic "
        "computes the wrong thing.",
        "Do NOT make a cosmetic edit and resubmit. A wrong answer that runs cleanly "
        "usually means a misread requirement, not a typo.",
        "Re-read the problem statement and check specifically: are you answering the "
        "exact question asked (count vs sum vs index, 0- vs 1-based)? Have you handled "
        "the boundary and wrap-around cases? Does your reading of the rules match the "
        "worked example step by step, including any case the example does not cover?",
        "If the worked example passes but the real input does not, the difference is a "
        "case the example never exercises -- name that case explicitly before coding.",
    ]


def _is_timeout_error(error: str) -> bool:
    """True if an execution error is a timeout rather than a crash.

    Both execution paths phrase it the same way ("... timed out after N
    seconds", shared/execution.py), so a substring check is sufficient and
    avoids coupling to an exception type that does not survive the subprocess
    boundary.
    """
    return "timed out" in str(error).lower()


def _efficiency_guidance(examples_passed: bool) -> List[str]:
    """Repair guidance for a solution that is too slow rather than wrong.

    The default feedback for a timeout says only that the run errored, which
    leaves the model free to resubmit the same approach -- and it does: 2024
    d15 p2 and 2025 d9 p2 resisted 11 and 10 configurations respectively, and
    raising temperature did not help (dev/progress/temperature-diversity-
    negative.md). The diagnosis there was that extra draws re-roll the same
    die; this tells the model *which* die to stop rolling.
    """
    lines = [
        "DIAGNOSIS: this is a PERFORMANCE failure, not a correctness failure. "
        "The code did not crash and did not return a wrong answer -- it did not "
        "finish in time on the real input.",
    ]
    if examples_passed:
        lines.append(
            "Your approach is CORRECT on the small example but does not scale: "
            "the real input is far larger."
        )
    lines.extend([
        "Do NOT resubmit the same algorithm with minor edits -- it will time out again.",
        "Find an asymptotically faster approach. Consider: memoising or caching repeated "
        "sub-computations; replacing a scan over all candidates with a direct "
        "computation; using a dict/set instead of repeated list scans; deriving the "
        "answer mathematically instead of simulating every step; or pruning branches "
        "that cannot affect the result.",
        "State the time complexity of your previous attempt and of your new one, and "
        "make sure the new one is strictly better.",
    ])
    return lines


class FeedbackMixin:
    """The execution-feedback builder BaseSolver uses for every repair prompt."""

    config: SolverConfig

    def _build_execution_feedback(
        self,
        model_name: str,
        exec_test_cases: List[TestCase],
        example_results: List[Any],
        full_result: Optional[Any],
        full_answer: Optional[str],
        direction: Optional[str] = None,
    ) -> str:
        lines: List[str] = []
        lines.append(f"Execution feedback for model {model_name}.")
        if exec_test_cases:
            lines.append("Example test results:")
            max_examples = 3
            for idx, (test_case, result) in enumerate(
                zip(exec_test_cases, example_results), start=1
            ):
                if idx > max_examples:
                    break
                expected = str(getattr(test_case, "expected_output", "")).strip()
                if getattr(result, "error", None):
                    lines.append(
                        f"- Example {idx}: ERROR: {getattr(result, 'error', '')}"
                    )
                else:
                    actual = str(getattr(result, "output", "")).strip()
                    lines.append(
                        f"- Example {idx}: expected '{expected}', got '{actual}'"
                    )
        else:
            if example_results and any(getattr(r, "error", None) for r in example_results):
                lines.append("Execution failed on examples with no structured test cases.")
        if full_result is not None:
            full_error = getattr(full_result, "error", None)
            if full_error:
                lines.append(f"Full input run ERROR: {full_error}")
                if self.config.targeted_feedback and _is_timeout_error(full_error):
                    lines.extend(_efficiency_guidance(bool(exec_test_cases and not any(
                        getattr(r, "error", None) for r in example_results
                    ))))
            elif not full_answer:
                lines.append("Full input run completed but produced an empty answer.")
            else:
                lines.append("Full input run completed but the answer is still not accepted.")
                if self.config.problem_context == "aoc":
                    if problem_context.looks_like_error_output(full_answer):
                        # The program's own output, which its author would see.
                        lines.append(
                            "Your program printed an error message instead of "
                            f"an answer: {full_answer.strip()[:400]}"
                        )
                    elif direction:
                        # What the site says about a wrong number, and no more.
                        lines.append(f"Your answer {full_answer.strip()} is {direction}.")
                if self.config.targeted_feedback:
                    lines.extend(_wrong_answer_guidance(full_answer))
        return "\n".join(lines)
