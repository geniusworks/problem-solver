#!/usr/bin/env python
"""Audit every recorded solution against ground truth.

Usage:
    venv/bin/python dev/verify_solutions.py [--dir solutions]

Exits non-zero if any recorded solution is wrong or errors, so this can be used
as a regression gate.
"""

import argparse
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from shared.verification import Verdict, verify_solution_file  # noqa: E402

SYMBOLS = {
    Verdict.CORRECT: "OK  ",
    Verdict.WRONG: "WRONG",
    Verdict.ERROR: "ERROR",
    Verdict.UNVERIFIED: "?   ",
}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dir", default="solutions", help="directory of solution files")
    parser.add_argument("--timeout", type=int, default=60)
    args = parser.parse_args()

    target = (REPO_ROOT / args.dir).resolve()
    paths = sorted(p for p in target.glob("*.py") if not p.name.startswith("_"))

    if not paths:
        print(f"No solution files found in {target}")
        return 0

    results = [verify_solution_file(p, timeout=args.timeout) for p in paths]

    print(f"{'':5}  {'problem':22} {'expected':>14} {'actual':>14}")
    print("-" * 60)
    for r in results:
        problem = f"{r.year} day{r.day:02d} part{r.part}"
        expected = r.expected if r.expected is not None else "-"
        actual = r.actual if r.actual is not None else "-"
        print(f"{SYMBOLS[r.verdict]}  {problem:22} {expected:>14} {actual:>14}")
        if r.error:
            print(f"       {r.error.splitlines()[0][:100]}")

    counts = {v: sum(1 for r in results if r.verdict is v) for v in Verdict}
    print("-" * 60)
    print(
        f"{counts[Verdict.CORRECT]} correct, {counts[Verdict.WRONG]} wrong, "
        f"{counts[Verdict.ERROR]} error, {counts[Verdict.UNVERIFIED]} unverified "
        f"({len(results)} total)"
    )

    bad = counts[Verdict.WRONG] + counts[Verdict.ERROR] + counts[Verdict.UNVERIFIED]
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
