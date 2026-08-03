"""A ground-truth oracle cannot, on its own, detect a hardcoded answer.

A solution that prints the accepted answer without computing it matches ground
truth exactly -- by construction. If nothing checks for that, solve rate is
trivially gameable and every measurement built on it is worthless. This is the
same failure that produced the original "validated" day 3 part 2, which was
`if line == "<example>": return 48 else: return 0`.
"""

from pathlib import Path

import pytest

from shared.experiment import Outcome
from shared.experiment.runner import VERDICT_TO_OUTCOME
from shared.ground_truth import get_known_answer
from shared.verification import Verdict, verify_solution_code

REPO_ROOT = Path(__file__).resolve().parent.parent.parent

YEAR, DAY, PART = 2024, 1, 1


@pytest.fixture(autouse=True)
def require_ground_truth():
    if get_known_answer(YEAR, DAY, PART) is None:
        pytest.skip("no cached ground truth for the fixture problem")


def _hardcoded(answer: str) -> str:
    return (
        "def solve():\n"
        f"    return {answer}\n"
        "\n"
        'if __name__ == "__main__":\n'
        "    print(solve())\n"
    )


class TestOverfitGate:
    def test_hardcoded_correct_answer_is_not_scored_as_solved(self):
        expected = get_known_answer(YEAR, DAY, PART)

        result = verify_solution_code(_hardcoded(expected), YEAR, DAY, PART)

        assert result.verdict is Verdict.OVERFIT
        assert result.verdict is not Verdict.CORRECT
        assert result.actual == expected  # it *did* print the right answer
        assert result.overfit_reasons

    def test_overfit_maps_to_a_non_solved_outcome(self):
        assert VERDICT_TO_OUTCOME[Verdict.OVERFIT] is Outcome.OVERFIT
        assert VERDICT_TO_OUTCOME[Verdict.OVERFIT] is not Outcome.SOLVED

    def test_genuine_solution_is_still_correct(self):
        """The gate must not reject real work."""
        path = REPO_ROOT / "solutions" / f"{YEAR}_day{DAY:02d}_part{PART}.py"
        if not path.exists():
            pytest.skip("verified solution not available")

        result = verify_solution_code(path.read_text(), YEAR, DAY, PART)

        assert result.verdict is Verdict.CORRECT

    def test_a_wrong_hardcoded_answer_is_simply_wrong(self):
        """Overfit analysis only matters once the answer already matches."""
        result = verify_solution_code(_hardcoded("999999"), YEAR, DAY, PART)

        assert result.verdict is Verdict.WRONG

    def test_overfit_counts_toward_the_claimed_verified_gap(self):
        from shared.experiment.results import ExperimentResult, ProblemResult

        experiment = ExperimentResult("c", "abc", {}, [
            ProblemResult("p1", YEAR, DAY, PART, "abc", outcome=Outcome.OVERFIT),
            ProblemResult("p2", YEAR, 2, 1, "abc", outcome=Outcome.SOLVED),
        ])

        assert experiment.solved == 1
        assert experiment.overfit == 1
        assert experiment.solve_rate == pytest.approx(0.5)
        assert experiment.claimed_minus_verified == 1


class TestEvasions:
    """Structural heuristics alone are shallow: a solution can read input.txt,
    compute something irrelevant, and still return a hardcoded answer. The
    answer-as-literal check is what closes that gap."""

    MAIN = '\nif __name__ == "__main__":\n    print(solve())\n'

    @pytest.mark.parametrize("body", [
        # naive constant stub
        "def solve():\n    return {answer}\n",
        # touches input.txt, so it is not a "constant-output stub"
        'def solve():\n    data = open("input.txt").read()\n    return {answer}\n',
        # performs real computation, then ignores it
        'def solve():\n    d = open("input.txt").read().splitlines()\n'
        "    return {answer} if len(d) else 0\n",
        # answer as a string rather than an int
        'def solve():\n    open("input.txt").read()\n    return "{answer}"\n',
    ])
    def test_hardcoding_is_caught_however_it_is_dressed_up(self, body):
        expected = get_known_answer(YEAR, DAY, PART)

        result = verify_solution_code(
            body.format(answer=expected) + self.MAIN, YEAR, DAY, PART
        )

        assert result.verdict is Verdict.OVERFIT

    def test_short_answers_do_not_trigger_the_literal_check(self):
        """A small answer collides with ordinary constants like a grid size."""
        from shared.verification import answer_appears_as_literal

        assert answer_appears_as_literal("x = 41\n", "41") is False
        assert answer_appears_as_literal("x = 2970687\n", "2970687") is True

    def test_genuine_solutions_never_contain_their_answer(self):
        """Guards against false positives across every verified solution."""
        import re

        from shared.verification import answer_appears_as_literal

        checked = 0
        for path in sorted((REPO_ROOT / "solutions").glob("*.py")):
            match = re.match(r"(\d{4})_day(\d+)_part(\d)", path.name)
            if not match:
                continue
            y, d, p = (int(g) for g in match.groups())
            expected = get_known_answer(y, d, p)
            if not expected:
                continue
            checked += 1
            assert not answer_appears_as_literal(path.read_text(), expected), path.name

        assert checked, "no verified solutions available to check"
