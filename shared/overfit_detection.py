"""Heuristics for detecting obviously overfit solution code before recording.

This module is intentionally conservative and AoC-agnostic. It focuses on
catching clearly suspicious patterns such as:

- Direct reuse of full example inputs (or long lines from them) as literals
  in the solution code.
- Equality checks against long string literals that look like entire inputs.
- Trivial constant-output stubs that never read the canonical input file.

Solutions flagged here are treated as *suspicious* and are not recorded as
validated canonical solutions, even if they happen to pass current tests.
"""

from __future__ import annotations

import ast
import json
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import List

from shared import config

logger = logging.getLogger(__name__)

# Thresholds to avoid obvious false positives on short tokens like "mul(".
_MIN_EXAMPLE_LITERAL_LENGTH = 20
_MIN_EXAMPLE_LINE_LENGTH = 16
_MIN_EQ_STRING_LENGTH = 20


@dataclass
class OverfitAnalysisResult:
    """Result of running overfit detection heuristics on a solution."""

    is_suspicious: bool
    reasons: List[str]


def analyze_overfit_risk(
    year: int,
    day: int,
    part: int,
    solution_code: str,
) -> OverfitAnalysisResult:
    """Analyze solution code for signs of obvious overfitting.

    This function performs cheap static checks only. It does *not* execute code
    and does not depend on any particular problem statement. It relies on the
    repository's cached example inputs when available.
    """

    reasons: List[str] = []

    # Heuristic 1: direct reuse of example input literals.
    reasons.extend(_check_example_literal_reuse(year, day, solution_code))

    # AST-based heuristics (constant-output stubs, equality to long literals).
    tree = None
    try:
        tree = ast.parse(solution_code)
    except SyntaxError as exc:  # pragma: no cover - defensive
        logger.debug("Overfit detection: failed to parse solution code: %s", exc)

    if tree is not None:
        reasons.extend(_check_constant_output_stub(solution_code, tree))
        reasons.extend(_check_input_equality(tree))

    return OverfitAnalysisResult(is_suspicious=bool(reasons), reasons=reasons)


def _load_example_inputs(year: int, day: int) -> List[str]:
    """Load cached example input strings for a given problem if available."""

    base_dir = config.BASE_DIR
    examples_dir = (
        base_dir
        / "years"
        / str(year)
        / f"day{day:02d}"
        / config.EXAMPLES_DIR
    )

    if not examples_dir.exists() or not examples_dir.is_dir():
        return []

    inputs: List[str] = []
    # rglob so both the legacy flat layout and per-part subdirectories are picked up.
    for path in sorted(examples_dir.rglob("example_*.json")):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):  # pragma: no cover - defensive
            continue
        raw = data.get("input")
        if isinstance(raw, str) and raw:
            inputs.append(raw)
    return inputs


def _strip_comments_and_docstrings(source: str) -> str:
    """Return `source` with comments and docstrings removed.

    Used before the example-literal checks so that prose quoting an example
    cannot be mistaken for code branching on one. Deliberately conservative: if
    the source will not tokenize or parse, the original is returned unchanged so
    the caller still runs its checks against *something* rather than silently
    letting a suspicious solution through.
    """
    import io
    import tokenize

    # 1. Comments, via tokenize (keeps string literals intact).
    try:
        out: List[str] = []
        prev_end = (1, 0)
        for tok in tokenize.generate_tokens(io.StringIO(source).readline):
            if tok.type == tokenize.COMMENT:
                continue
            srow, scol = tok.start
            if srow > prev_end[0]:
                out.append("\n" * (srow - prev_end[0]))
                prev_end = (srow, 0)
            if scol > prev_end[1]:
                out.append(" " * (scol - prev_end[1]))
            out.append(tok.string)
            prev_end = tok.end
        stripped = "".join(out)
    except (tokenize.TokenError, IndentationError, SyntaxError):
        stripped = source

    # 2. Docstrings, via AST -- blank out the string constant of any
    #    module/class/function whose first statement is a bare string.
    try:
        tree = ast.parse(stripped)
    except SyntaxError:
        return stripped

    spans: List[tuple] = []
    for node in ast.walk(tree):
        if not isinstance(
            node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)
        ):
            continue
        body = getattr(node, "body", None)
        if not body:
            continue
        first = body[0]
        if (
            isinstance(first, ast.Expr)
            and isinstance(first.value, ast.Constant)
            and isinstance(first.value.value, str)
            and first.lineno is not None
            and first.end_lineno is not None
        ):
            spans.append((first.lineno, first.end_lineno))

    if not spans:
        return stripped

    lines = stripped.splitlines()
    for start, end in spans:
        for i in range(start - 1, min(end, len(lines))):
            lines[i] = ""
    return "\n".join(lines)


def _check_example_literal_reuse(
    year: int,
    day: int,
    solution_code: str,
) -> List[str]:
    """Detect direct reuse of example inputs as literals in the solution.

    This targets patterns like assigning an entire example block to a string
    and branching on it. We intentionally ignore very short lines to avoid
    flagging legitimate token-level comparisons.
    """

    reasons: List[str] = []
    inputs = _load_example_inputs(year, day)
    if not inputs:
        return reasons

    # Only *executable* code can overfit. Comments and docstrings cannot change
    # what a program computes, so a model that quotes the example while
    # explaining itself is not cheating -- and some models do this constantly
    # (qwen3.8:27b writes its reasoning into comments; see
    # dev/progress/m2max-qwen38-27b-d4-7.md). Checking raw source rejected a
    # verifiably correct, fully general 2024 d13 p1 solution whose only sin was
    # an example in its docstring (dev/progress/overfit-gate-false-positive.md).
    # Strip prose first, then apply exactly the same checks as before: a literal
    # that survives stripping is one the program can actually branch on.
    solution_code = _strip_comments_and_docstrings(solution_code)

    for idx, input_text in enumerate(inputs, start=1):
        if not isinstance(input_text, str):
            continue

        # Full example block as a literal (e.g., triple-quoted string).
        if len(input_text) >= _MIN_EXAMPLE_LITERAL_LENGTH and input_text in solution_code:
            reasons.append(
                f"Solution code contains the entire text of example {idx} input as a literal."
            )
            continue

        # Long individual lines from the example reused verbatim.
        for line in input_text.splitlines():
            line = line.rstrip("\n\r")
            if len(line) < _MIN_EXAMPLE_LINE_LENGTH:
                continue
            if line in solution_code:
                snippet = line[:40] + ("..." if len(line) > 40 else "")
                reasons.append(
                    "Solution code contains a long line from example "
                    f"{idx} input as a literal: '{snippet}'"
                )
                break

    return reasons


def _check_constant_output_stub(solution_code: str, tree: ast.AST) -> List[str]:
    """Detect trivial constant-output stubs that never read input.txt.

    This focuses on patterns like:

        def solve() -> int:
            return 123456

    with no reference to the canonical input file. Legitimate AoC solutions
    are expected (by prompt and by convention) to read from 'input.txt'.
    """

    reasons: List[str] = []

    # Quick textual check: if the code never mentions input.txt at all, it is
    # more likely to be a stub that ignores the problem input.
    mentions_input_file = "input.txt" in solution_code

    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and node.name == "solve":
            returns = [n for n in ast.walk(node) if isinstance(n, ast.Return)]
            if not returns:
                continue

            all_constant_returns = True
            for ret in returns:
                value = getattr(ret, "value", None)
                if value is None:
                    continue
                if not isinstance(value, ast.Constant):
                    all_constant_returns = False
                    break

            if all_constant_returns and not mentions_input_file:
                reasons.append(
                    "Function solve() only returns constant literal values and the code "
                    "never references 'input.txt'; this looks like a constant-output stub."
                )

    return reasons


def _check_input_equality(tree: ast.AST) -> List[str]:
    """Detect equality checks against long string literals.

    This targets patterns where the code branches on entire inputs, e.g.:

        if data.strip() == "<full example input>":
            ...

    Short string comparisons (tokens, small prefixes) are ignored.
    """

    reasons: List[str] = []

    class _Visitor(ast.NodeVisitor):
        def visit_If(self, node: ast.If) -> None:  # type: ignore[override]
            test = node.test
            if isinstance(test, ast.Compare):
                for comp in test.comparators:
                    if (
                        isinstance(comp, ast.Constant)
                        and isinstance(comp.value, str)
                        and len(comp.value) >= _MIN_EQ_STRING_LENGTH
                    ):
                        snippet = comp.value[:40] + (
                            "..." if len(comp.value) > 40 else ""
                        )
                        reasons.append(
                            "If-statement compares a value directly to a long string "
                            f"literal: '{snippet}'"
                        )
            self.generic_visit(node)

    _Visitor().visit(tree)
    return reasons
