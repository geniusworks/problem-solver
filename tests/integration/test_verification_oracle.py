"""The correctness oracle must reject solutions that were previously accepted.

Before the oracle existed, acceptance meant "ran without crashing and printed
something", so hardcoded stubs and wrong algorithms were recorded as validated
solutions. These tests pin that behaviour shut using the real failures the old
pipeline produced, kept under solutions/rejected/ and tests/fixtures/overfit/.

Fixtures must live in COMMITTED directories. They used to be read out of
`years/`, which is both gitignored and the directory the solver writes its
canonical solution into -- so solving a problem destroyed its own regression
fixture. That is not hypothetical: on 2026-08-16 `qwen3-coder:30b` solved
2024 d5 p2 for the first time, overwrote `years/2024/day05/2024_day05_part2.py`,
and permanently destroyed the hardcoded stub that had been this file's second
OVERFIT_CASE (see solutions/README.md for what it did). Never point a fixture at
a path the solver can write.
"""

from pathlib import Path

import pytest

from shared.ground_truth import extract_answers_from_html, get_known_answer
from shared.overfit_detection import analyze_overfit_risk
from shared.verification import Verdict, verify_solution_code

REPO_ROOT = Path(__file__).resolve().parent.parent.parent

# Solutions the pre-oracle pipeline accepted that produce the wrong answer.
WRONG_ANSWER_CASES = [
    (2024, 2, 2, "solutions/rejected/2024_day02_part2.py", "86", "476"),
    (2024, 4, 1, "solutions/rejected/2024_day04_part1.py", "2344", "2401"),
]

# Solutions that hardcode example data instead of implementing the algorithm.
# The 2024 d5 p2 case is absent because its fixture no longer exists -- see the
# module docstring. It is not reconstructed here: a hand-written stand-in would
# be a fabricated artifact, not the real failure the old pipeline produced.
OVERFIT_CASES = [
    (2024, 3, 2, "tests/fixtures/overfit/2024_day03_part2.py"),
]

VERIFIED_CASES = [
    (2024, 1, 1, "solutions/2024_day01_part1.py"),
    (2024, 1, 2, "solutions/2024_day01_part2.py"),
    (2024, 2, 1, "solutions/2024_day02_part1.py"),
    (2024, 3, 1, "solutions/2024_day03_part1.py"),
]


def _read(relative: str) -> str:
    path = REPO_ROOT / relative
    if not path.exists():
        pytest.skip(f"fixture not available: {relative}")
    return path.read_text(encoding="utf-8")


def _require_ground_truth(year: int, day: int, part: int) -> None:
    if get_known_answer(year, day, part) is None:
        pytest.skip(f"no ground truth cached for {year} day {day} part {part}")


@pytest.mark.parametrize("year,day,part,relative,produced,expected", WRONG_ANSWER_CASES)
def test_wrong_answers_are_rejected(year, day, part, relative, produced, expected):
    """A solution that runs cleanly but computes the wrong answer must not pass."""
    _require_ground_truth(year, day, part)
    result = verify_solution_code(_read(relative), year, day, part)

    assert result.verdict is Verdict.WRONG, (
        f"{relative} produced {result.actual!r}; the oracle must reject it"
    )
    assert result.actual == produced
    assert result.expected == expected


@pytest.mark.parametrize("year,day,part,relative", OVERFIT_CASES)
def test_hardcoded_stubs_are_rejected(year, day, part, relative):
    """Stubs that branch on example literals must be caught before recording."""
    code = _read(relative)

    analysis = analyze_overfit_risk(year, day, part, code)
    oracle = verify_solution_code(code, year, day, part)

    # Either gate is sufficient; both firing is fine. What must never happen is
    # a stub passing cleanly.
    assert analysis.is_suspicious or oracle.verdict is Verdict.WRONG, (
        f"{relative} passed both the overfit heuristics and the oracle"
    )
    assert oracle.verdict is not Verdict.CORRECT


@pytest.mark.parametrize("year,day,part,relative", VERIFIED_CASES)
def test_known_good_solutions_still_pass(year, day, part, relative):
    """The oracle must not reject the solutions that are genuinely correct."""
    _require_ground_truth(year, day, part)
    result = verify_solution_code(_read(relative), year, day, part)

    assert result.verdict is Verdict.CORRECT, (
        f"{relative} produced {result.actual!r}, expected {result.expected!r}"
    )


def test_missing_ground_truth_reports_unverified():
    """No oracle means UNVERIFIED, which must never be treated as CORRECT."""
    code = "def solve():\n    return 1\n\nif __name__ == '__main__':\n    print(solve())\n"
    # Day 25 of a year we have not cached has no stored answer.
    result = verify_solution_code(code, 2024, 25, 1)

    assert result.verdict is not Verdict.CORRECT


class TestExampleComparison:
    """Example runs must compare output to expected, not merely avoid crashing."""

    @staticmethod
    def _load_example(day: int, part: int, index: int = 1):
        import json

        path = (
            REPO_ROOT / "years" / "2024" / f"day{day:02d}"
            / "examples" / f"part{part}" / f"example_{index}.json"
        )
        if not path.exists():
            pytest.skip(f"cached example not available: {path}")
        data = json.loads(path.read_text(encoding="utf-8"))
        if not (data.get("expected_output") or "").strip():
            pytest.skip("cached example has no expected output")
        return data

    async def test_matching_example_passes(self):
        from shared.execution import SolutionExecutor, TestCase

        data = self._load_example(1, 1)
        executor = SolutionExecutor(REPO_ROOT)
        cases = [TestCase(input_data=data["input"], expected_output=data["expected_output"])]

        results, _, answer = await executor.test_solution(
            _read("solutions/2024_day01_part1.py"), 2024, 1, 1, cases, "test"
        )

        assert [r.error for r in results] == [None]
        assert answer == get_known_answer(2024, 1, 1)

    async def test_mismatched_example_is_caught(self):
        """The regression that mattered: a wrong expected output must fail."""
        from shared.execution import SolutionExecutor, TestCase

        data = self._load_example(1, 1)
        executor = SolutionExecutor(REPO_ROOT)
        cases = [TestCase(input_data=data["input"], expected_output="999")]

        results, _, answer = await executor.test_solution(
            _read("solutions/2024_day01_part1.py"), 2024, 1, 1, cases, "test"
        )

        assert results and results[0].error is not None
        assert "999" in results[0].error
        assert answer is None

    async def test_force_full_input_survives_a_bad_example(self):
        """A mis-parsed example must not hide a correct answer when truth is known."""
        from shared.execution import SolutionExecutor, TestCase

        data = self._load_example(1, 1)
        executor = SolutionExecutor(REPO_ROOT)
        cases = [TestCase(input_data=data["input"], expected_output="999")]

        _, _, answer = await executor.test_solution(
            _read("solutions/2024_day01_part1.py"), 2024, 1, 1, cases,
            "test", force_full_input=True,
        )

        assert answer == get_known_answer(2024, 1, 1)

    async def test_real_input_is_not_clobbered_by_example_runs(self):
        """Example inputs must never be written over the real puzzle input."""
        from shared.execution import SolutionExecutor, TestCase

        input_path = REPO_ROOT / "years" / "2024" / "day01" / "input.txt"
        if not input_path.exists():
            pytest.skip("real input not available")
        before = input_path.read_bytes()

        executor = SolutionExecutor(REPO_ROOT)
        cases = [TestCase(input_data="9 9\n9 9\n", expected_output="0")]
        await executor.test_solution(
            _read("solutions/2024_day01_part1.py"), 2024, 1, 1, cases, "test"
        )

        assert input_path.read_bytes() == before


def test_answer_extraction_from_html():
    """Ground truth is scraped from a plain <p>, not the day-success element."""
    html = """
    <article class="day-desc"><h2>--- Day 1 ---</h2></article>
    <p>Your puzzle answer was <code>2970687</code>.</p>
    <article class="day-desc"><h2>--- Part Two ---</h2></article>
    <p>Your puzzle answer was <code>23963899</code>.</p>
    <p class="day-success">Both parts of this puzzle are complete!</p>
    """
    assert extract_answers_from_html(html) == {1: "2970687", 2: "23963899"}


def test_answer_extraction_handles_unsolved_page():
    html = "<article class='day-desc'><h2>--- Day 7 ---</h2></article>"
    assert extract_answers_from_html(html) == {}
