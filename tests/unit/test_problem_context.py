"""A Part Two must be posed the way the puzzle page poses it.

Every run before 2026-10-13 gave the model the "Part Two" article alone: no
rules, no input format. On 2024 d19 p2 a draft was correct only if it guessed
the format (dev/progress/part2-prompt-omits-part1.md). These tests pin what the
model is shown, and that it is never shown the answer to the part it is solving.
"""

import pytest

from shared import problem_context
from shared.experiment import SolverConfig

PAGE = """<html><body><main>
<article class="day-desc"><h2>--- Day 19: Linen Layout ---</h2>
<p>The first line lists the available towel patterns, separated by commas.</p>
<p>How many designs are possible?</p></article>
<p>Your puzzle answer was <code>304</code>.</p>
<article class="day-desc"><h2 id="part2">--- Part Two ---</h2>
<p>Add up the number of different ways you could make each design.</p></article>
<p>Your puzzle answer was <code>705756472327497</code>.</p>
</main></body></html>"""

PART_TWO_TEXT = "--- Part Two ---\nAdd up the number of different ways you could make each design."


@pytest.fixture
def problem_dir(tmp_path, monkeypatch):
    (tmp_path / "problem.html").write_text(PAGE, encoding="utf-8")
    monkeypatch.setattr(problem_context, "get_problem_dir", lambda year, day: tmp_path)
    answers = {1: "304", 2: "705756472327497"}
    monkeypatch.setattr(
        problem_context, "get_known_answer", lambda year, day, part: answers.get(part)
    )
    return tmp_path


class TestPageDescription:
    def test_part_two_reads_under_part_one_and_its_accepted_answer(self, problem_dir):
        text = problem_context.page_description(2024, 19, 2, PART_TWO_TEXT)
        assert "separated by commas" in text
        assert "Your puzzle answer was 304." in text
        assert text.index("Linen Layout") < text.index("304") < text.index("Part Two")

    def test_part_two_answer_is_never_shown(self, problem_dir):
        text = problem_context.page_description(2024, 19, 2, PART_TWO_TEXT)
        assert "705756472327497" not in text
        assert "705756472327497" not in problem_context.supplement(2024, 19, 2)

    def test_part_one_is_its_own_article(self, problem_dir):
        assert problem_context.page_description(2024, 19, 1, "part one text") == "part one text"

    def test_unsolved_part_one_has_no_answer_line(self, problem_dir, monkeypatch):
        monkeypatch.setattr(problem_context, "get_known_answer", lambda y, d, p: None)
        text = problem_context.page_description(2024, 19, 2, PART_TWO_TEXT)
        assert "separated by commas" in text
        assert "Your puzzle answer was" not in text

    def test_no_cached_page_leaves_the_text_alone(self, tmp_path, monkeypatch):
        monkeypatch.setattr(problem_context, "get_problem_dir", lambda y, d: tmp_path)
        assert problem_context.page_description(2024, 19, 2, PART_TWO_TEXT) == PART_TWO_TEXT


class TestSupplement:
    def test_input_preview_shows_shape_and_clips(self, problem_dir):
        long_line = "ab, " * 200
        lines = [long_line, ""] + [f"design{i}" for i in range(40)]
        (problem_dir / "input.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
        preview = problem_context.input_preview(2024, 19)
        assert "42 lines" in preview
        assert f"[line is {len(long_line)} characters]" in preview
        assert "design9" in preview
        assert "design10" not in preview  # past the preview window

    def test_part_two_gets_the_recorded_part_one_program(self, problem_dir):
        (problem_dir / "2024_day19_part1.py").write_text("def solve():\n    return 304\n")
        assert "def solve()" in problem_context.supplement(2024, 19, 2)
        assert "def solve()" not in problem_context.supplement(2024, 19, 1)

    def test_no_program_without_an_accepted_part_one_answer(self, problem_dir, monkeypatch):
        (problem_dir / "2024_day19_part1.py").write_text("def solve():\n    return 1\n")
        monkeypatch.setattr(problem_context, "get_known_answer", lambda y, d, p: None)
        assert problem_context.part_one_solution(2024, 19) is None


class TestFingerprintsKeepTheirMeaning:
    """Runs on record hashed a config that had neither field."""

    LEGACY = dict(problem_context="legacy", analysis_temperature="model_default")
    REFERENCE = dict(
        models=("qwen3.8:27b",), temperature=0.7, enable_thinking=False,
        enable_fallback_models=False,
    )

    def test_legacy_settings_reproduce_the_recorded_fingerprints(self):
        k1 = SolverConfig(samples_per_model=1, **self.REFERENCE, **self.LEGACY)
        k3 = SolverConfig(samples_per_model=3, **self.REFERENCE, **self.LEGACY)
        assert k1.fingerprint() == "62ee65d6b521"
        assert k3.fingerprint() == "d0e67ebf4cee"

    def test_each_new_default_is_a_different_experiment(self):
        legacy = SolverConfig(**self.REFERENCE, **self.LEGACY)
        prints = {
            legacy.fingerprint(),
            legacy.with_overrides(problem_context="aoc").fingerprint(),
            legacy.with_overrides(analysis_temperature="configured").fingerprint(),
            SolverConfig(**self.REFERENCE).fingerprint(),
        }
        assert len(prints) == 4

    def test_unknown_values_are_rejected(self):
        with pytest.raises(ValueError):
            SolverConfig(problem_context="everything")
        with pytest.raises(ValueError):
            SolverConfig(analysis_temperature="hot")


class TestErrorShapedOutput:
    def test_a_caught_exception_is_not_an_answer(self):
        assert problem_context.looks_like_error_output("An error occurred: boom\n0")
        assert problem_context.looks_like_error_output("Traceback (most recent call last)")

    def test_answers_are_left_alone(self):
        assert not problem_context.looks_like_error_output("705756472327497")
        assert not problem_context.looks_like_error_output("co,de,ka,ta")
        assert not problem_context.looks_like_error_output("")


class TestPartTwoExample:
    """Part Two reuses Part One's worked example with a new stated result."""

    PAGE = """<article class="day-desc"><h2>--- Day 1: Sums ---</h2>
<pre><code>1
2
3
</code></pre><p>The total is <code><em>6</em></code>.</p></article>
<article class="day-desc"><h2 id="part2">--- Part Two ---</h2>
<p>Now multiply. The product is <code><em>6</em></code>... no, <code><em>12</em></code>.</p></article>"""

    ADDS = "print(sum(int(x) for x in open('input.txt').read().split()))\n"

    @pytest.fixture
    def page(self, tmp_path, monkeypatch):
        (tmp_path / "problem.html").write_text(self.PAGE, encoding="utf-8")
        monkeypatch.setattr(problem_context, "get_problem_dir", lambda y, d: tmp_path)
        return tmp_path

    def test_paired_when_the_part_one_program_reproduces_the_example(self, page):
        assert problem_context.part_two_example(2024, 1, self.ADDS) == ("1\n2\n3\n", "12")

    def test_not_paired_when_the_program_disagrees_with_the_example(self, page):
        assert problem_context.part_two_example(2024, 1, "print(0)\n") is None

    def test_not_paired_without_a_part_one_program(self, page):
        assert problem_context.part_two_example(2024, 1, None) is None

    def test_not_paired_when_the_stated_result_is_not_a_number(self, page):
        (page / "problem.html").write_text(
            self.PAGE.replace("<em>12</em>", "<em>co,de</em>"), encoding="utf-8"
        )
        assert problem_context.part_two_example(2024, 1, self.ADDS) is None

    def test_supplement_prefers_this_trials_own_program(self, page, monkeypatch):
        monkeypatch.setattr(problem_context, "get_known_answer", lambda y, d, p: "6")
        (page / "2024_day01_part1.py").write_text("# someone else's\n")
        text = problem_context.supplement(2024, 1, 2, part_one_code="# mine\n")
        assert "# mine" in text and "someone else" not in text
