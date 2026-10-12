# Instrument fix: an event's last day may have one puzzle — its "Part Two" was scored as a miss

**The harness attempted a problem that does not exist and recorded a `no_candidate` for it.** The
last day of an AoC event can have a single puzzle; the page still carries a "Part Two" article, but
that part is finished with a button, not an answer. Two scans were affected by one phantom problem
each. The reported solve counts were right — both docs excluded the part by hand — but one of them
explained the exclusion wrongly.

| scan | harness printed | real | the phantom |
|---|---|---|---|
| 2025 d1–12 (`generality-2025-scan.md`) | 16/24 | 16/23 | 2025 d12 p2 |
| 2024 d16–25 (`m5pro-scan-2024-d16-25.md`) | 9/20 | 9/19 | 2024 d25 p2 |

In both runs the record is the same: outcome `no_candidate`, model `solver`, **0 tokens**. No model
was ever asked anything.

## The claim this corrects

`generality-2025-scan.md`, the checkpoint and `PLAN.md` §4b described **2025 d12 p2** as *"the
genuinely unseen problem"* — the one problem the account had not solved, a Milestone F scenario in
miniature, and the first real target for the submission path. **None of that was true.** 2025 ran
for 12 days, day 12 is its last, and its Part Two has no puzzle. There was nothing to solve, nothing
to submit, and no evidence about how the harness treats an unseen problem. The page says so itself:
*"Both parts of this puzzle are complete"* with a single accepted answer on it.

The related claim in `PLAN.md` §4b — that problems with no cached answer score as `UNVERIFIED` and
stay out of the totals, "demonstrated on 2025 d12 p2" — loses its demonstration. The code path
exists (`Outcome.UNVERIFIED`, and `ExperimentResult` counts it apart from solved), but no run has
exercised it on a real unseen problem. It is untested until AoC 2026.

## Detection

Which day is last varies by year (25 in 2024, 12 in 2025) and is the site maintainer's choice, so
the day number is never assumed. The page is read instead:

- A part with no puzzle has a form posting `level=2` with a **hidden** `answer` field — a
  finish button — both before the day is complete and after.
- A real Part 2 has a **text** `answer` field while unsolved, and no form once solved.

Across every cached page (2024 d1–25, 2025 d1–12) this flags exactly 2024 d25 p2 and 2025 d12 p2.
The before-completion form is taken from how the after-completion form is built on those two pages
and has not been observed directly; the first live last day will confirm or correct it.

## The fix

- `shared/ground_truth.py`: `html_part_has_puzzle` / `part_has_puzzle`. An uncached page is assumed
  to be a puzzle — absence of evidence is no reason to drop a problem.
- `experiment.py`: such parts are removed from the problem set before the run and named in the
  output, so the banner count and every denominator are right.
- `shared/experiment/runner.py`: the run loop skips them too, and discards an attempt if the page
  was only fetched during that attempt and turns out to have no puzzle.
- 7 tests. Suite: 217 passed.

Result JSONs written before this still contain the phantom row; recompute denominators without it.
The band classification on 2024 d16–25 was already running when this landed, and its problem list
never included d25 p2.

## Not fixed here

The wider gap stays open: a solver-side failure still lands in the same bucket as "the model could
not do it" (`PLAN.md` §4, the `HARNESS_ERROR` item). This fix removes one way of getting there.
