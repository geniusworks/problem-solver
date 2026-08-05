"""The formatter must never turn valid generated code into invalid code.

Every one of these cases was destroyed by the old regex/line-based "repairs",
and each destruction was reported as the model's SyntaxError -- so the harness
corrupted correct output and then scored the model as having failed. That biases
every measurement in the direction that flatters the harness.
"""

import pytest

from shared.quality.code_formatter import format_code

APOSTROPHE = chr(39)

VALID_SOLUTIONS = {
    "f-string containing an apostrophe": (
        "def solve():\n"
        "    x = 5\n"
        f'    return f"don{APOSTROPHE}t count {{x}}"\n'
    ),
    "f-string with single-quoted subscript": (
        "def solve():\n"
        f"    d = {{{APOSTROPHE}k{APOSTROPHE}: 1}}\n"
        f'    return f"v {{d[{APOSTROPHE}k{APOSTROPHE}]}}"\n'
    ),
    "literal backslash-n inside a string": (
        'def solve():\n    return "a\\nb"\n'
    ),
    "print as the only statement in an if": (
        "def solve():\n"
        "    n = 0\n"
        "    if n > 5:\n"
        "        print('big')\n"
        "    return n\n"
    ),
    "print as the only statement in a loop": (
        "def solve():\n"
        "    for x in range(3):\n"
        "        print(x)\n"
        "    return 1\n"
    ),
    "multi-line print call": (
        'def solve():\n    print(\n        "hello"\n    )\n    return 7\n'
    ),
    "debug print before the answer": (
        'def solve():\n    print("debug")\n    return 42\n'
    ),
}


@pytest.mark.parametrize("label,source", VALID_SOLUTIONS.items(), ids=list(VALID_SOLUTIONS))
def test_valid_code_survives_formatting(label, source):
    compile(source, "<input>", "exec")  # precondition: the input really is valid

    formatted, success = format_code(source)

    assert success, f"{label}: valid code reported as a formatting failure"
    compile(formatted, "<output>", "exec")


def test_semantics_are_preserved():
    """Formatting must not change what the code computes."""
    source = (
        "def solve():\n"
        '    parts = "a\\nb".split("\\n")\n'
        "    return len(parts)\n"
    )
    formatted, success = format_code(source)
    assert success

    before, after = {}, {}
    exec(compile(source, "<a>", "exec"), before)
    exec(compile(formatted, "<b>", "exec"), after)

    assert before["solve"]() == after["solve"]() == 2


def test_malformed_code_still_reports_failure():
    """Repair is still attempted for genuinely broken output."""
    formatted, success = format_code("def solve(:\n    return 1\n")

    assert success is False


def test_formatting_failure_never_silently_corrupts():
    """Whatever comes back for valid input must itself be valid."""
    for source in VALID_SOLUTIONS.values():
        formatted, _ = format_code(source)
        compile(formatted, "<output>", "exec")
