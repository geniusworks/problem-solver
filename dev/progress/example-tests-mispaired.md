# The example tests are paired with the wrong input on about half the problems

**Headline: on 25 of the 47 verified solutions that get an example test, the verified program
fails that test.** The parser attaches the statement's worked result to the nearest preceding
code block, which is often an illustration of the example (a grid drawing, a marked-up copy)
and not the example input. A failed example does not block acceptance when the full-input
answer matches the oracle, so recorded solves are sound. It does go into every repair prompt as
"Example 1: expected 'X', got 'Y'", so repairs are steered by a test that a correct program
would also fail. Found 2026-10-13 in the walls run (`part2-prompt-omits-part1.md`); **not
fixed.**

## How it was found

Every failed attempt at 2025 d9 in `m5pro-aoc-walls-k1` was told `expected '50', got '0'` (Part
One) or `expected '24', got '0'` (Part Two). The statement's example input is a list of
coordinates. The parser yields six blocks for Part One; the result `50` is attached to the fifth,
a drawing of the tile floor in `.` and `#`. The verified Part One program prints `50` on the
coordinate list and `0` on the drawing.

## Audit

Each verified solution in `years/*/day*/` was run on every example the harness would test it
with (`OrchestratedSolver.build_test_cases`: examples that carry an expected output), under the
legacy parse.

| verified solutions | 57 |
|---|---|
| no paired example | 10 |
| every paired example reproduced | 22 |
| at least one paired example not reproduced | **25** |

Not reproduced (reproduced/paired): 2024 d5 p1 (0/1), d6 p1 (0/1), d6 p2 (0/2), d8 p1 (0/1), d8
p2 (0/1), d9 p1 (0/1), d11 p1 (0/1), d12 p1 (1/2), d12 p2 (2/3), d13 p1 (0/1), d14 p1 (0/1), d15
p1 (0/1), d15 p2 (0/1), d16 p1 (1/2), d16 p2 (0/1), d18 p1 (0/1), d22 p1 (0/1), d23 p1 (0/1),
d25 p1 (0/1); 2025 d6 p1 (0/1), d6 p2 (0/1), d8 p1 (0/1), d9 p1 (0/1), d10 p1 (0/2), d11 p2
(0/1).

The 25 are an upper bound on mis-pairings. Some statements give an example under different
parameters from the real input (2024 d14's smaller room, d18's smaller grid), where a correct
program fails a correctly paired example; those were not separated out. Unsolved problems have
no verified program and could not be audited.

## What it affects

- **Repair, in every run on record.** A draft that is wrong on the full input is sent back with
  the bogus example failure. Repair's low yield (1 of 52 in `m5pro-d19p2-power.md`) was measured
  with this in place on any problem in the list above. d19 p2 itself has no paired example, so
  that figure is not affected.
- **2025 d9 p2 is not yet a clean wall.** 0 of 2 reached under the site's conditions, but both
  attempts and all four repairs carried `expected '24', got '0'`.
- **The arm-3 entry cells.** 2024 d15 p1, d15 p2 and 2025 d9 p1 are all in the list, so the
  queued reference re-baseline would be measured with it too.
- **Not affected:** which programs count as solved. The oracle decides, on the full input.
- **Not used here:** the Part 2 pairing added in `part2-prompt-omits-part1.md` only runs when the
  parser found no paired example, so a wrong parser pairing takes precedence over it.

## Next

Fix the pairing before the reference re-baseline, and measure the fix with the audit above (25
of 47 not reproduced now). The audit script is the test: a pairing rule is better if more
verified programs reproduce their paired examples, and the residue should be the
different-parameter cases only.
