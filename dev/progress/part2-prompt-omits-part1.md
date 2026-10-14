# Every Part 2 was posed without Part 1's text — and on d19 p2 that decides the outcome

**Headline: the prompt for a Part 2 contains only the "Part Two" article. The Part 1 statement —
the rules, the input format, the worked example input — is not in it.** On 2024 d19 p2 this
accounts for every result: of 80 first drafts, the 16 correct ones are exactly the correct subset
of the 26 that guessed the input's first line is comma-separated; none of the 54 that did not
guess it is correct. Found 2026-10-13 from the saved drafts of `m5pro-d19p2-power.md`. **Fixed
the same day** behind a config switch (below). **A/B run 2026-10-13: 6/20 under the old prompt,
19/19 under the site's conditions** (Fisher exact p = 2.6e-6); the result is below.

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
| reaching Part Two | shown only once Part One is accepted | **attempted only in a trial that solved Part One**; otherwise recorded `not_reached` and left out of every denominator |
| Part Two | Part One's statement, "Your puzzle answer was N", the Part Two statement; the input; their working Part One program | all of those, in page order; **the program that solved Part One in this same trial** |
| the worked example | Part One's example with the result Part Two states for it | the same, as a runnable example, when the Part One program reproduces Part One's stated result on it |
| after a wrong answer | "not the right answer", and for a number "too high" / "too low" | "not accepted", and for an integer "too high" / "too low" |

Details and limits:

- **"Too high / too low"** is computed by the caller and only those words are passed on; the
  feedback builder still never receives the accepted answer
  (`test_never_leaks_the_expected_answer` is unchanged). The site's growing wait between wrong
  submissions is not simulated.
- **A requested Part Two brings its Part One.** `--problems 2024:19.2` runs 19.1 first in every
  trial. A Part Two solve rate is now "solved, of the trials that reached it"; `per_problem`
  reports `trials` and `scored` separately.
- **The example pairing is a heuristic with a guard.** Checked offline against verified
  solutions: where the Part One program reproduces Part One's example result, the paired Part Two
  expectation was right in **11 of 13** cases. The misses are 2024 d2 and d3 (d3's Part Two
  brings its own example). It is added only when an accepted Part Two answer is on file, so a
  wrong pairing can mislead repair feedback but cannot reject a correct answer.
- **Outside the experiment harness** (`solve.py`) there is no "this trial"; the recorded Part One
  program from the ledger is used.
- **The Part Two answer is never included.** Only the two statement articles and the Part One
  answer are read; `tests/unit/test_problem_context.py` asserts it.
- **An unseen year cannot reach Part Two.** Reaching it needs an accepted Part One answer, which
  for a new puzzle exists only after a submission, and submission is deliberately unwired. Under
  these conditions AoC 2026 measures Part Ones only until that is decided (PLAN.md §4b).

Two scoring labels changed with it. Neither alters what the model sees or what counts as solved:

- **`harness_error`**: an exception out of the solve path, or while testing a candidate, is the
  project's code failing. It was scored like a model failure (`strategy-keyerror-d8.md`). It is
  now its own outcome, in no denominator, with its own count in the summary.
- **A printed error is an `error`.** Code that catches its own exception and prints a message
  then `0` was scored `wrong`. Its output is now recognised and, under `aoc` context, shown back
  to the model as its program's output.

Checked on real prompts for 2024 d19 p2, 2024 d16 p2 and 2025 d9 p2: Part One statement and
answer present, Part Two answer absent, implementation prompt 14–23k characters against 8–18k.

**Plumbing check** (2024 d1, 3 trials, reference model, defaults; not a measurement): Part One
3/3 and Part Two 3/3, each Part Two posed after its trial's Part One. The prompt sent for Part Two
held Part One's statement, its accepted answer, the trial's Part One program and the input
preview, and not the Part Two answer. A first attempt at this check scored 0/3 on Part Two with
three `harness_error`s — an undefined name in the new preparation step, since fixed and covered
by a test — which is the new label doing its job. The example pairing was not exercised: d1's
Part Two carries its own example.

**Fingerprints.** Both new fields are left out of the hash at their legacy values, so the runs on
record keep their fingerprints and can be reproduced:

| settings | k1 reference | k3 reference |
|---|---|---|
| `problem_context=legacy,analysis_temperature=model_default` | `62ee65d6b521` | `d0e67ebf4cee` |
| defaults (`aoc`, `configured`) | `907898143ff0` | `12412ed652a4` |

**Every result before 2026-10-13 is a legacy-context result.** New runs are not comparable with
them unless the legacy settings are passed.

## The A/B (registered 2026-10-13 under the final conditions; d19 run the same day)

2024 d19, `samples_per_model=1`, 20 trials, `analysis_temperature=model_default` in both arms so
that the context is the only difference:

- **legacy:** Part Two posed cold, 6/20 on record (`62ee65d6b521`).
- **aoc:** Part One then Part Two in each trial, fingerprint `5d259bb8f103`.
- **Prediction:** Part Two is reached in at least 18 of 20 trials (Part One is 10/10 on record),
  and solved in at least 80% of the trials that reach it. Below 50% would mean the diagnosis here
  is incomplete.
- Then the walls, same design, 3 trials each: 2024 d16 (Part Two 0/7 cold) and 2025 d9 (0/22
  cold). No prediction for 2025 d9 p2; for 2024 d16 p2, at least 1 of the trials that reach it.

- Then the reference on the arm-3 entry cells (2024 d15, 2025 d9; `samples_per_model=3`, 3
  trials) under the full new defaults, fingerprint `12412ed652a4`. A re-baseline, not a test: its
  legacy row is 6/12 (d15 p1 3/3, d15 p2 1/3, d9 p1 2/3, d9 p2 0/3). No prediction.

### Result, 2024 d19: 6/20 → 19/19

`m5pro-aoc-d19-k1-n20`, fingerprint `5d259bb8f103`, 20 trials, 6,650 s
(`dev/experiments/20261014T001948Z_m5pro-aoc-d19-k1-n20_5d259bb8f103.json`).

| | legacy (`62ee65d6b521`) | aoc (`5d259bb8f103`) |
|---|---|---|
| Part Two solved / reached | 6/20 | **19/19** |
| solved by the first draft | 5/20 | 19/19 |
| repair records | 18 | 0 |
| Part Two wall-clock per trial | 169 s | 91 s |
| Part One, same trial | not run | 19/20, 246 s per trial |

- **Both predictions held:** Part Two was reached in 19 of 20 trials (predicted at least 18) and
  solved in 19 of the 19 that reached it (predicted at least 80%). Fisher exact, 19/19 against
  6/20: p = 2.6e-6.
- **d19 p2 is not a "sometimes" problem.** With the statement in the prompt the reference solves
  it on the first draft every time. Its 20% first-draft rate under the old prompt measured how
  often a draft guessed the input format.
- **Consequence for arm 1 on this machine:** d19 p2 was the one informative problem in the
  k1-vs-k3 runs of `m5pro-d19p2-power.md` and `m5pro-passk-2024-d16-25.md`. Those runs still
  show that drafts are independent (49% predicted, 50% measured), but what sampling rescued there
  was a format guess. The M5 Pro has no "sometimes" band on record under the site's conditions;
  one has to be found again before k1-vs-k3 is re-run here.
- **The one trial that did not reach Part Two** was stopped by the hardcoding gate, not by a
  wrong answer. Its Part One program read `input.txt` and printed the accepted answer, 304, but
  also carried the worked example's input as a fallback for a missing file, and the gate rejects
  any program that contains an example input verbatim. Recorded as `overfit` for Part One and
  `not_reached` for Part Two. The gate is conservative by design; this is its cost, 1 in 20 here.
- **Not exercised:** no draft failed, so the too-high/too-low hint and the repair path under the
  new context are still untested on a live run.

### Result, the walls: 2024 d16 p2 0/7 → 3/3; 2025 d9 p2 still 0

`m5pro-aoc-walls-k1`, fingerprint `5d259bb8f103`, 3 trials, 4,078 s
(`dev/experiments/20261014T013038Z_m5pro-aoc-walls-k1_5d259bb8f103.json`).

| | legacy | aoc |
|---|---|---|
| 2024 d16 Part One | — | 3/3 |
| 2024 d16 Part Two | 0/7 (`682` in 13 of 13 first drafts) | **3/3**, each a first draft |
| 2025 d9 Part One | — | 2/3 |
| 2025 d9 Part Two | 0/22 | 0/2 reached (1 not reached) |

- **Prediction held:** 2024 d16 p2 was predicted solved in at least 1 trial that reached it; it
  was solved in all 3. The shared wrong answer `682` was a missing reading, not a misreading:
  the Part Two text does not restate the move and turn costs.
- **2024 d16 p2 is not a wall** and drops out of the arm-3 entry cells.
- **2025 d9 p2 stays unsolved, but not cleanly.** One trial timed out on the full input in the
  draft and both repairs. The other answered `4623431865` (too high), repeated it, then
  `23426835` (too low). All six attempts were also told `expected '24', got '0'` on an example
  test that is paired with the wrong input (`example-tests-mispaired.md`).
- **First live use of the too-high/too-low hint:** five wrong numeric answers got it (three on
  d9 p1, two on d9 p2). None of the repairs that followed was accepted.
- **A repair that returns different code with the same answer** is recorded as `wrong`, not
  `no_candidate` (d9 p1 trial 0: `4781096936` three times).

The reference re-baseline is still queued, and should wait for the example-pairing fix.

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
