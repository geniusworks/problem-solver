"""Overfit-gate heuristics: what must be caught, and what must not."""

from shared.overfit_detection import analyze_overfit_risk


class TestExampleLiteralsInProseAreNotOverfit:
    """Only executable code can overfit; comments and docstrings cannot.

    The example-literal check ran against raw source, so a general algorithm
    that merely quoted the example while explaining itself was rejected as
    overfit. That is not hypothetical: it refused a verifiably correct 2024
    d13 p1 solution during the qwen3.8 frontier scan (2026-08-16) -- correct
    answer on the full input, general algorithm, example in the docstring. The
    model most prone to it is the one that writes its reasoning into comments.

    The gate must stay strict about literals the program can branch on.
    """

    GENERAL_SOLUTION = '''
def solve() -> int:
    """Solve day 13.

    Example input:
    Button A: X+94, Y+34
    Button B: X+22, Y+67
    """
    import re
    total = 0
    with open("input.txt") as f:
        blocks = f.read().strip().split("\\n\\n")
    for b in blocks:
        ax, ay, bx, by, px, py = [int(x) for x in re.findall(r"\\d+", b)]
        det = ax * by - ay * bx
        if det:
            a = (px * by - py * bx) // det
            c = (ax * py - ay * px) // det
            if ax * a + bx * c == px and ay * a + by * c == py:
                total += 3 * a + c
    return total
'''

    def test_example_in_docstring_is_not_flagged(self):
        result = analyze_overfit_risk(2024, 13, 1, self.GENERAL_SOLUTION)
        assert not result.is_suspicious, result.reasons

    def test_example_in_comments_is_not_flagged(self):
        commented = (
            "def solve() -> int:\n"
            "    # Example input:\n"
            "    # Button A: X+94, Y+34\n"
            "    with open('input.txt') as f:\n"
            "        return len(f.read())\n"
        )
        assert not analyze_overfit_risk(2024, 13, 1, commented).is_suspicious

    def test_example_literal_in_control_flow_is_still_flagged(self):
        """The literal survives stripping, so the program can branch on it."""
        cheat = (
            "def solve() -> int:\n"
            "    with open('input.txt') as f:\n"
            "        data = f.read()\n"
            "    if 'Button A: X+94, Y+34' in data:\n"
            "        return 480\n"
            "    return 0\n"
        )
        result = analyze_overfit_risk(2024, 13, 1, cheat)
        assert result.is_suspicious
        assert any("Button A" in r for r in result.reasons)

    def test_unparseable_source_falls_back_to_raw_checking(self):
        """Conservative: if stripping fails, still check the original source."""
        broken = "def solve(:\n  'Button A: X+94, Y+34'\n"
        analyze_overfit_risk(2024, 13, 1, broken)  # must not raise
