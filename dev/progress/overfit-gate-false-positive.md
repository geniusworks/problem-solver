# The overfit gate rejected a correct, general solution (2024 d13 p1)

**The gate refused a solution that was right.** During the `qwen3.8:27b` frontier scan the solver
produced code for 2024 d13 p1 that executed against the **full input** and printed **37680 — the
correct accepted answer** — and the overfit gate rejected it:

```
Refusing to record solution ... due to overfit heuristics: Solution code contains a long line
from example 1 input as a literal: 'Button A: X+94, Y+34'
```

Recorded as `CHEAT` (`Outcome.OVERFIT`), kept out of the ledger. This is the first non-zero overfit
count in the M2 Max series, and it was **the gate's mistake, not the model's**.

## Why it was a false positive

Code that hardcodes *example* data cannot produce the correct answer for the *real* input. The
answer matched, so the algorithm was general; the example literal was decoration.

`_check_example_literal_reuse` tested `if line in solution_code` against **raw source**. It never
asked *where* the literal appeared — docstring, comment, or executable code all counted the same.

Demonstrated directly against a hand-written, unambiguously general solution (Cramer's rule, reads
`input.txt`, hardcodes nothing) whose only example reference is in its docstring:

```
general algorithm, example ONLY in docstring:
  is_suspicious: True
   - Solution code contains a long line from example 1 input as a literal: 'Button A: X+94, Y+34'
```

**This model is unusually exposed to it.** `qwen3.8:27b` writes its reasoning into comments and
docstrings — the behaviour documented in `m2max-qwen38-27b-d4-7.md`, where it debugged itself in
comments on d6 p2 and got a free self-correction. The same habit that helps it solve hard problems
made it trip a gate that reads prose as if it were code.

## The fix: strip prose, then apply the identical checks

`_strip_comments_and_docstrings()` removes comments (via `tokenize`) and docstrings (via AST — a
bare string as the first statement of a module, class, or function), then the existing example
checks run unchanged on what remains. **The bar is not lowered.** A literal that survives stripping
is one the program can branch on; one that does not, cannot affect what the program computes.

If the source will not tokenize or parse, the original is returned unchanged, so malformed code is
still checked against raw source rather than slipping through.

## Verified both directions

Loosening a correctness gate is only safe if the real cheats still trip it, so both were tested:

| case | before | after | wanted |
|------|--------|-------|--------|
| `tests/fixtures/overfit/2024_day03_part2.py` (real pre-oracle cheat) | flagged | **flagged** | flagged |
| `tests/fixtures/overfit/2024_day05_part2.py` (real pre-oracle cheat) | flagged | **flagged** | flagged |
| general algorithm, example in **docstring** | flagged | **clean** | clean |
| general algorithm, example in **`#` comments** | flagged | **clean** | clean |
| example literal in **real control flow** (`if 'Button A…' in data: return 480`) | flagged | **flagged** | flagged |
| unparseable source | flagged | **still checked** | not silently passed |

Four regression tests in `tests/unit/test_overfit_detection.py` pin all of it.

## Aftermath

Re-running d13 p1 produced a **different draw with no embedded example**, which passed cleanly and
is now recorded: **ledger 22 correct, 0 wrong.** So the problem was always within reach; the gate
had rejected one particular phrasing of a correct answer.

The original offending source is **lost** — the scan did not use `--include-replay`, and the replay
generated fresh code. The false positive was therefore proved by reconstruction (a hand-written
general solution with a docstring example) rather than by inspecting the original. That is weaker
evidence about *that specific draw*: what is certain is that the heuristic flags correct general
code, and that d13 p1's answer was right.

**Operational note:** run frontier scans with `--include-replay` when a gate rejection is plausible.
The source of a refused solution is exactly the artifact needed to audit the refusal, and it is the
one thing not kept.

## Direction of the error matters

This is the *safe* direction — nothing false entered the ledger, and every recorded solution stays
trustworthy. The cost is under-crediting, which shows up as an artificially low solve rate and, in a
capability comparison, as a model looking weaker than it is. Worth fixing, worth fixing carefully,
and not worth fixing by loosening the bar.
