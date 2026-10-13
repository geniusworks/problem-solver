# Every Part 2 was posed without Part 1's text — and on d19 p2 that decides the outcome

**Headline: the prompt for a Part 2 contains only the "Part Two" article. The Part 1 statement —
the rules, the input format, the worked example input — is not in it.** On 2024 d19 p2 this
accounts for every result: of 80 first drafts, the 16 correct ones are exactly the correct subset
of the 26 that guessed the input's first line is comma-separated; none of the 54 that did not
guess it is correct. Found 2026-10-13 from the saved drafts of `m5pro-d19p2-power.md`. **Fixed
the same day** behind a config switch (below); the A/B that measures the difference is registered
and not yet run.

## The mechanism

`shared/aoc.py::fetch_problem_text` selects one `<article class="day-desc">` per part:

```python
if part == 2 and len(articles) > 1:
    article = articles[1]      # the "Part Two" article only
else:
    article = articles[0]
```

The comment calls this solving each part "atomically", and `dev/docs/architecture.md` describes
it as a feature. For Part 1 it is correct. For Part 2 it removes the problem: an AoC Part Two is
written as an amendment to Part One and rarely restates the setup.

Checked on the latest saved Part 2 prompt for 2024 d4, d6, d13, d15, d16, d19 and d24: each
begins `--- Part Two ---` and none contains the `--- Day N ---` article.

## What the model was shown on d19 p2

The Part Two text says designs "can be made" from towels in a number of ways and asks for the
total. It does not say that the input's first line is a comma-separated list of towel patterns,
that a blank line follows, or that designs come one per line. The model's own analysis step
starts by trying to work out which puzzle this is ("This is **Day 7, Part 2** … wait, let me
reconsider"), and one draft solved a different, invented problem with a `target: n1, n2` format.

Re-running the 80 saved first drafts from both arms reproduces the recorded outcomes (16 correct,
60 printing `0`, 4 other):

| draft handles a comma-separated first line | correct | not correct |
|---|---|---|
| yes (26) | **16** | 10 |
| no (54) | **0** | 54 |

The counting algorithm is the same dynamic programme in nearly every draft, right or wrong. What
varies is the guess about a format the prompt never gave. The 20% draft rate on this problem is
mostly the rate at which the model reconstructs the input format, from the Part Two example or
from having seen the puzzle before.

## What this does and does not change

**Unchanged as measurements.** Every comparison in the record posed the same prompt to both
arms, so k1-vs-k3, repair, temperature, model-vs-model and machine-vs-machine deltas are valid
measurements of the pipeline as built. The ledger is unaffected: a solution counts only if it
produced the accepted answer.

**Changed in meaning — needs a caveat wherever it is quoted:**

- **The Part 1/Part 2 cliff** (2024 d8–15; 2025 83% vs 55%; 2024 d16–25 8/10 vs 1/9). Reported as
  a property of the problems and the model. Some of it, possibly much of it, is that Part 2 was
  asked without its problem statement. How much is unmeasured.
- **The walls.** 2024 d16 p2 gave `682` in 13 of 13 first drafts, described in
  `m5pro-passk-2024-d16-25.md` as "a shared misreading of the problem". The Part Two text does
  not restate the maze's move and turn costs, so the misreading may be a missing reading. 2025
  d9 p2 (0/22) and the eight 0/4 problems of the d16–25 band have the same exposure. None of
  these is established as a capability wall until it is re-run with the full statement.
- **"Sometimes" problems and sampling.** On d19 p2, what sampling rescues is a format guess, not
  a hard algorithmic step. The independence result stands; the thing being drawn is different
  from what the write-ups assumed. The earlier bands may or may not be the same.
- **Contamination.** A Part 2 solved without its statement was solved partly from recall of the
  puzzle. That is direct evidence for the contamination caveat in `RESULTS.md`, and it means
  Part 2 solve rates on a genuinely unseen year (AoC 2026) would be lower than these for a reason
  that has nothing to do with capability.

## The fix: show the model what a solver on the site has

`SolverConfig.problem_context`, default `"aoc"`; `"legacy"` is the old behaviour. Assembled in
`shared/problem_context.py` from the per-problem cache.

| step | a person on the site has | the model is now shown |
|---|---|---|
| Part One | the Part One statement; the puzzle input | the statement (as before); the first 12 lines of the input, clipped, with its size |
| Part Two | Part One's statement, "Your puzzle answer was N", the Part Two statement; the input; their working Part One program | all of those, in page order; the recorded Part One program from the ledger |
| after a wrong answer | "not the right answer", often "too high" / "too low" | "not accepted" (as before). **Not** the direction |

Limits of the equivalence:

- **No "too high / too low".** Computing it needs the accepted answer inside the feedback
  builder, and `test_never_leaks_the_expected_answer` forbids that by design. Left as it was.
- **The Part One program is the ledger's**, which may have been written by a different model
  than the one now solving Part Two. It is offered only when the Part One answer is known.
- **A Part Two is attempted even when this model has not solved Part One.** The site would not
  show it. The statement and accepted Part One answer are still shown, from the cache.
- **Part Two examples are not paired.** A Part Two usually reuses Part One's example input with a
  new expected result. The model now reads both in the statement, but the harness still builds
  executable test cases from the Part Two article alone (none on d19 p2), so example-based
  feedback for Part Twos is as thin as before. Pairing them by heuristic risks a wrong expected
  value, which is worse than none.
- **The Part Two answer is never included.** Only the two statement articles and the Part One
  answer are read; `tests/unit/test_problem_context.py` asserts it.

Checked on real prompts for 2024 d19 p2, 2024 d16 p2 and 2025 d9 p2: Part One statement and
answer present, Part Two answer absent, implementation prompt 14–23k characters against 8–18k.

**Fingerprints.** Both new fields are left out of the hash at their legacy values, so the runs on
record keep their fingerprints and can be reproduced:

| settings | k1 reference | k3 reference |
|---|---|---|
| `problem_context=legacy,analysis_temperature=model_default` | `62ee65d6b521` | `d0e67ebf4cee` |
| defaults (`aoc`, `configured`) | `907898143ff0` | `12412ed652a4` |

**Every result before 2026-10-13 is a legacy-context result.** New runs are not comparable with
them unless the legacy settings are passed.

## The A/B (registered 2026-10-13, not yet run)

2024 d19 p2, `samples_per_model=1`, 20 trials, `analysis_temperature=model_default` in both arms
so that only the context differs:

- **legacy:** the 6/20 on record (`62ee65d6b521`).
- **aoc:** fingerprint `5d259bb8f103`.
- **Prediction:** at least 14 of 20. The failure was a format guess; with the format stated and a
  working parser in the Part One program, the remaining misses should be algorithmic. Below 10
  would mean the diagnosis here is incomplete.
- Then the walls, same design, 3 trials each: 2024 d16 p2 (0/7) and 2025 d9 p2 (0/22).
  No prediction for d9 p2; for d16 p2, at least 1 of 3.

## Second gap, same session: the analysis call ignored the configured temperature

Each draft is two model calls. The second (implementation) and every repair are sent the
configured temperature. The first (analysis) is `self.generate(prompt)` with no temperature, so
it runs at the model's own default — the same omission that was fixed for repair on 2026-08-22
(`token-accounting-fix.md`, Bug 2), in the one call that fix did not touch.

- The reference model's default is **1.0** (`ollama show qwen3.8:27b`), so every "temperature
  0.7" run had its analysis at 1.0 and its code at 0.7.
- `temperature-diversity-negative.md` therefore varied the implementation call only (0.7 → 1.0
  with analysis at 1.0 in both arms), after the August correction had already narrowed it once.
- Defaults differ by model (`gemma4:31b` and `muse-glimmer:30b` 1.0; `ornith-1.5:35b` declares
  none), so a cross-model comparison holds the code temperature fixed and not the analysis one.

**Fixed 2026-10-13:** `SolverConfig.analysis_temperature`, default `"configured"`;
`"model_default"` is the old behaviour and keeps the old fingerprints. Its effect is unmeasured.
