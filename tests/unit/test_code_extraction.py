"""Code extraction is the last gate before a candidate exists.

The old extractor accepted only ```python fences with a crude line-heuristic
fallback that broke on module-level class/for/import. Anything else -- ```py,
a bare ```, ~~~, or unfenced code in a reasoning model's thinking text --
produced no candidate at all, which the baseline measured as the dominant
failure mode. These tests pin the robust, AST-validated behaviour.
"""

import ast

import pytest

from shared.llm.local import OllamaProvider


@pytest.fixture
def extract():
    provider = OllamaProvider(model="m")
    return provider._extract_code


SOLVE = "def solve(data):\n    return len(data)\n"


def _runs(code: str) -> bool:
    ast.parse(code)  # raises if not valid Python
    return True


class TestFenceVariants:
    def test_python_fence(self, extract):
        out = extract(f"Here:\n```python\n{SOLVE}```\n")
        assert out and "def solve" in out and _runs(out)

    def test_py_fence(self, extract):
        out = extract(f"```py\n{SOLVE}```")
        assert out and "def solve" in out

    def test_capitalised_python_fence(self, extract):
        out = extract(f"```Python\n{SOLVE}```")
        assert out and "def solve" in out

    def test_bare_triple_backtick_fence(self, extract):
        out = extract(f"```\n{SOLVE}```")
        assert out and "def solve" in out

    def test_tilde_fence(self, extract):
        out = extract(f"~~~\n{SOLVE}~~~")
        assert out and "def solve" in out


class TestUnfenced:
    def test_pure_code_no_fence(self, extract):
        out = extract(SOLVE)
        assert out and "def solve" in out

    def test_prose_then_unfenced_code(self, extract):
        text = (
            "Sure, here's my approach. I iterate over the lines and count.\n\n"
            f"{SOLVE}\n"
            "That should do it!"
        )
        out = extract(text)
        assert out and "def solve" in out and _runs(out)
        # The trailing prose must not be included -- it would break execution.
        assert "That should do it" not in out

    def test_module_level_constructs_survive(self, extract):
        """The old line-heuristic broke on a top-level import/for/if-main."""
        code = (
            "import sys\n"
            "from collections import Counter\n"
            "\n"
            "def solve(data):\n"
            "    c = Counter(data.split())\n"
            "    return c.most_common(1)[0][0]\n"
            "\n"
            'if __name__ == "__main__":\n'
            "    print(solve(sys.stdin.read()))\n"
        )
        out = extract(f"```python\n{code}```")
        assert out and "import sys" in out and "if __name__" in out and _runs(out)


class TestPreferSolve:
    def test_prefers_the_block_that_defines_solve(self, extract):
        text = (
            "First a helper snippet:\n"
            "```python\n"
            "x = 1 + 1\n"
            "```\n"
            "And the solution:\n"
            "```python\n"
            f"{SOLVE}```\n"
        )
        out = extract(text)
        assert out and "def solve" in out

    def test_reasoning_thinking_text_with_code(self, extract):
        """Reasoning models put the answer in thinking; it's prose + code."""
        thinking = (
            "Let me think. The input is space-separated numbers.\n"
            "I'll parse and sum them.\n\n"
            "```python\n"
            f"{SOLVE}```\n"
            "Yeah, that works."
        )
        out = extract(thinking)
        assert out and "def solve" in out


class TestNoCode:
    def test_pure_prose_returns_none(self, extract):
        assert extract("I'm not sure how to solve this problem, sorry.") is None

    def test_empty_returns_none(self, extract):
        assert extract("") is None
        assert extract("   \n  ") is None
