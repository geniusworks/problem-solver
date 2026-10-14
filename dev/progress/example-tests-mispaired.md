# The example tests were paired with the wrong input on about half the problems

**Headline: on 25 of the 46 verified solutions that got an example test, the verified program
failed that test.** The parser attaches the statement's worked result to the nearest preceding
code block, which is often an illustration of the example (a grid drawing, a marked-up copy)
and not the example input, and it often reads the wrong number as the result. A failed example
does not block acceptance when the full-input answer matches the oracle, so recorded solves are
sound. It did go into every repair prompt as "Example 1: expected 'X', got 'Y'", so repairs were
steered by a test that a correct program would also fail. Found 2026-10-13 in the walls run
(`part2-prompt-omits-part1.md`). **Fixed 2026-10-14: 25 of 46 failing → 3 of 46**, the three
being statements whose example uses other parameters than the real input.

## How it was found

Every failed attempt at 2025 d9 in `m5pro-aoc-walls-k1` was told `expected '50', got '0'` (Part
One) or `expected '24', got '0'` (Part Two). The statement's example input is a list of
coordinates. The parser yields six blocks for Part One; the result `50` is attached to the fifth,
a drawing of the tile floor in `.` and `#`. The verified Part One program prints `50` on the
coordinate list and `0` on the drawing.

## Audit

`PYTHONPATH=. venv/bin/python dev/audit_example_pairing.py [--legacy]` runs every solution in
`years/*/day*/` that prints the accepted answer on each example test the harness would give it.

| | parser pairing (`--legacy`) | page pairing |
|---|---|---|
| verified solutions | 55 | 55 |
| every example test reproduced | 21 | **43** |
| an example test not reproduced | **25** | **3** |
| no example test | 9 | 9 |

- **Before**, not reproduced (reproduced/paired): 2024 d5 p1 (0/1), d6 p1 (0/1), d6 p2 (0/2), d8
  p1 (0/1), d8 p2 (0/1), d9 p1 (0/1), d11 p1 (0/1), d12 p1 (1/2), d12 p2 (2/3), d13 p1 (0/1), d14
  p1 (0/1), d15 p1 (0/1), d15 p2 (0/1), d16 p1 (1/2), d16 p2 (0/1), d18 p1 (0/1), d22 p1 (0/1),
  d23 p1 (0/1), d25 p1 (0/1); 2025 d6 p1 (0/1), d6 p2 (0/1), d8 p1 (0/1), d9 p1 (0/1), d10 p1
  (0/2), d11 p2 (0/1).
- **After**, not reproduced: 2024 d14 p1, 2024 d18 p1, 2025 d8 p1. Each statement works its
  example under other parameters than the real input (a smaller room, a smaller grid, 10
  connections instead of 1,000). The pairing is right and a correct program still fails it;
  nothing in the page's markup marks these, and a solver adjusts by reading. **Open.**
- **After**, no test: 2024 d10 p2, d11 p1, d12 p2, d13 p2, d15 p2, d16 p2, d17 p1, d20 p1, d23
  p2. Five of them are deliberate (below).
- Unsolved problems have no verified program and cannot be audited.

*Correction, 2026-10-14: the first version of this write-up said 25 of 47 and "57 verified
solutions". Two of the 57 files in `years/` (2024 d2 p2, d3 p2) do not print the accepted answer
and are not ledger solutions; the audit now leaves them out. The count of failures, 25, did not
change.*

## The fix

`shared/problem_context.py::statement_examples`, used when `example_tests=page` (the default):

- **An example input is a code block that resembles the puzzle input:** it uses no character
  the input file does not (digits as a class; letters exactly when the input has ten or fewer
  distinct ones), and it is sectioned by blank lines if and only if the input is. A solver tells
  a drawing from the example the same way, by looking at the input file.
- **A block that re-shows an earlier example is not a new one:** an excerpt of its lines, or a
  block of the same line count and widths (a later state of a grid).
- **The result is the last emphasised integer** between an example input and the next one.
- **Part Two** states its result for Part One's example when it has none of its own. When Part
  One worked several examples, Part Two gets no test: its results refer back by description
  ("the larger example") and the markup does not say which. That is the cause of five of the
  nine untested cells; a missing test costs less than a false one.
- Still feedback only. The accepted answer decides what is solved.

`example_tests=parser` keeps the old pairing, and is left out of the hash, so earlier
fingerprints stand:

| settings | k1 reference | k3 reference |
|---|---|---|
| defaults (`aoc`, `configured`, `page`) | `1ac712678732` | `839b40f0bfa8` |
| `example_tests=parser` (the defaults of 2026-10-13) | `907898143ff0` | `12412ed652a4` |
| `example_tests=parser,analysis_temperature=model_default` (runs 1 and 2) | `5d259bb8f103` | — |

For the queued problems the page pairing gives: 2025 d9 p1 the coordinate list → 50; 2025 d9 p2
the same list → 24; 2024 d15 p1 the smaller example → 2028; 2024 d15 p2 no test.

## What it affected

- **Repair, in every run on record.** A draft that is wrong on the full input is sent back with
  the bogus example failure. Repair's low yield (1 of 52 in `m5pro-d19p2-power.md`) was measured
  with this in place on any problem in the list above. d19 p2 itself has no paired example, so
  that figure is not affected.
- **2025 d9 p2 is not yet a clean wall.** 0 of 2 reached under the site's conditions, but both
  attempts and all four repairs carried `expected '24', got '0'`.
- **The arm-3 entry cells.** 2024 d15 p1, d15 p2 and 2025 d9 p1 are all in the list, so the
  reference re-baseline was held until this fix.
- **Not affected:** which programs count as solved. The oracle decides, on the full input.
- **Not used here:** the Part 2 pairing added in `part2-prompt-omits-part1.md` only runs when the
  parser found no paired example, so a wrong parser pairing took precedence over it. The page pairing replaces both.

## Plumbing check

`m5pro-page-examples-plumbing`, 2024 d1, 3 trials, fingerprint `1ac712678732`: 6/6, no harness
errors. No draft failed, so the feedback path with the new tests was not exercised live; it is
covered by the unit and integration tests only.

## Not measured

Whether true example feedback raises repair yield. The audit shows the tests are now right, not
that repairs use them. The reference re-baseline and the Part 2 rescan run under the new
default and will show it on the problems that fail.
