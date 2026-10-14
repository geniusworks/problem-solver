"""Audit the example tests against verified solutions.

For every solution in years/ that prints the accepted answer, run it on each example the harness
would test it with and count how many it reproduces. A verified program that
fails its example test means the test is wrong (or the statement's example
uses different parameters from the real input).

    PYTHONPATH=. venv/bin/python dev/audit_example_pairing.py [--legacy]
"""

import asyncio
import glob
import re
import sys

from shared import problem_context
from shared.aoc import fetch_problem_text
from shared.ground_truth import get_known_answer
from shared.parser import parse_problem_text


def main() -> None:
    legacy = "--legacy" in sys.argv
    reproduced, failed, untested, skipped = [], [], [], []
    for path in sorted(glob.glob("years/*/day*/*_day*_part[12].py")):
        year, day, part = map(int, re.search(r"(\d{4})_day(\d+)_part(\d)\.py", path).groups())
        name = f"{year} d{day} p{part}"
        with open(path, encoding="utf-8") as handle:
            code = handle.read()
        with open(f"years/{year}/day{day:02d}/input.txt", encoding="utf-8") as handle:
            puzzle_input = handle.read()
        accepted = get_known_answer(year, day, part)
        if accepted is None or problem_context._run_on_example(
            code, puzzle_input, timeout=120
        ) != str(accepted).strip():
            skipped.append(name)
            continue
        text, _, _ = asyncio.run(fetch_problem_text(year, day, part))
        if legacy:
            cases = [
                (e.input_data, str(e.expected_output).strip())
                for e in parse_problem_text(text).examples
                if e.input_data is not None and e.expected_output
            ]
        else:
            cases = problem_context.statement_examples(year, day, part) or []
        if not cases:
            untested.append(name)
            continue
        hits = sum(
            problem_context._run_on_example(code, given) == expected
            for given, expected in cases
        )
        (reproduced if hits == len(cases) else failed).append(f"{name} ({hits}/{len(cases)})")
    print(f"verified solutions: {len(reproduced) + len(failed) + len(untested)}")
    print(f"every example test reproduced: {len(reproduced)}")
    print(f"an example test not reproduced: {len(failed)}  {', '.join(failed)}")
    print(f"no example test: {len(untested)}  {', '.join(untested)}")
    print(f"not counted, program does not print the accepted answer: {', '.join(skipped) or 'none'}")


if __name__ == "__main__":
    main()
