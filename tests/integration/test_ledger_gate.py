"""The ledger records a solution only when it produces the accepted answer.

`record_solution` is the last gate before `solutions/README.md`, the record that
"68 verified, 0 wrong" is counted from. These tests drive it against a synthetic
problem in a temp tree, so the real ledger, `solutions/` and `years/` are never
touched.
"""

import json

import pytest

from shared import config, ledger

YEAR, DAY, PART = 2099, 1, 1
ACCEPTED = "6000"

SUMS_INPUT = """def solve():
    with open('input.txt') as f:
        return sum(int(line) for line in f if line.strip())

if __name__ == '__main__':
    print(solve())
"""
MULTIPLIES_INPUT = SUMS_INPUT.replace("sum(int(line) for line in f if line.strip())",
                                      "len([line for line in f if line.strip()]) * 10")
CRASHES = """def solve():
    with open('input.txt') as f:
        raise ValueError('bad parse')

if __name__ == '__main__':
    print(solve())
"""
CONSTANT_STUB = """def solve():
    return 6000

if __name__ == '__main__':
    print(solve())
"""
BARE_PRINT_STUB = "print(6000)\n"

LEDGER_TEMPLATE = (
    "# Advent of Code Solutions Log\n\n"
    "| Year | Day | Part | Answer | LLM Model(s) | Recorded (UTC) | Solution File |\n"
    "|------|-----|------|--------|--------------|----------------|---------------|\n"
    f"{ledger.VERIFIED_ROWS_MARKER}\n\n"
    "## Rejected\n\n"
    "| Year | Day | Part | Reason |\n"
    "|------|-----|------|--------|\n"
)


@pytest.fixture
def tree(tmp_path, monkeypatch):
    """A repo root in tmp_path with one problem whose accepted answer is 6000."""
    monkeypatch.setattr(config, "BASE_DIR", tmp_path)
    # The ledger locates solutions/ from its own file; point that at the temp root.
    (tmp_path / "shared").mkdir()
    monkeypatch.setattr(ledger, "__file__", str(tmp_path / "shared" / "ledger.py"))

    problem_dir = tmp_path / "years" / str(YEAR) / f"day{DAY:02d}"
    problem_dir.mkdir(parents=True)
    (problem_dir / config.INPUT_FILE).write_text("1000\n2000\n3000\n")
    (problem_dir / config.ANSWERS_FILE).write_text(json.dumps({str(PART): ACCEPTED}))

    (tmp_path / "solutions").mkdir()
    ledger_file = tmp_path / "solutions" / "README.md"
    ledger_file.write_text(LEDGER_TEMPLATE)
    return tmp_path


def _verified_rows(root):
    text = (root / "solutions" / "README.md").read_text()
    verified = text.split(ledger.VERIFIED_ROWS_MARKER, 1)[0]
    return [line for line in verified.splitlines() if line.startswith(f"|{YEAR}|")]


def test_correct_solution_is_recorded_with_the_accepted_answer(tree):
    ledger.record_solution(YEAR, DAY, PART, "model-a", SUMS_INPUT)

    rows = _verified_rows(tree)
    assert len(rows) == 1
    cells = rows[0].strip("|").split("|")
    assert cells[:5] == [str(YEAR), str(DAY), str(PART), ACCEPTED, "model-a"]
    assert (tree / "solutions" / f"{YEAR}_day{DAY:02d}_part{PART}.py").read_text() == SUMS_INPUT


@pytest.mark.parametrize("code", [MULTIPLIES_INPUT, CRASHES, CONSTANT_STUB, BARE_PRINT_STUB],
                         ids=["wrong-answer", "crash", "constant-stub", "bare-print"])
def test_failing_solutions_are_refused(tree, code):
    ledger.record_solution(YEAR, DAY, PART, "model-a", code)

    assert _verified_rows(tree) == []
    assert not (tree / "solutions" / f"{YEAR}_day{DAY:02d}_part{PART}.py").exists()


def test_a_second_solution_does_not_add_a_row(tree):
    ledger.record_solution(YEAR, DAY, PART, "model-a", SUMS_INPUT)
    ledger.record_solution(YEAR, DAY, PART, "model-b", SUMS_INPUT)

    assert len(_verified_rows(tree)) == 1


def test_new_rows_land_above_the_rejected_table(tree):
    ledger.record_solution(YEAR, DAY, PART, "model-a", SUMS_INPUT)

    text = (tree / "solutions" / "README.md").read_text()
    assert text.index(f"|{YEAR}|{DAY}|{PART}|") < text.index(ledger.VERIFIED_ROWS_MARKER)


def test_a_rejected_entry_does_not_block_a_correct_one(tree):
    ledger_file = tree / "solutions" / "README.md"
    ledger_file.write_text(ledger_file.read_text() + f"| {YEAR} | {DAY} | {PART} | wrong answer |\n")

    ledger.record_solution(YEAR, DAY, PART, "model-a", SUMS_INPUT)

    assert len(_verified_rows(tree)) == 1


def test_without_an_accepted_answer_the_row_is_marked_unverified(tree):
    """A live, unsolved problem has no cached answer. The ledger records the
    solution but says so, and `dev/verify_solutions.py` counts it as unverified,
    not correct."""
    (tree / "years" / str(YEAR) / f"day{DAY:02d}" / config.ANSWERS_FILE).unlink()

    ledger.record_solution(YEAR, DAY, PART, "model-a", SUMS_INPUT)

    rows = _verified_rows(tree)
    assert len(rows) == 1
    assert rows[0].strip("|").split("|")[3] == "unverified"
