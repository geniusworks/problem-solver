# A harness crash that was being recorded as model failure (2024 d8)

**`get_strategies_for_problem` could raise `KeyError` and fail a problem before the model was ever
called.** Any problem whose text triggered `GRAPH`, `STATE_MACHINE` or `OPTIMIZATION` died in
`_prepare_problem`; the harness logged `Solver raised on <problem>` and scored it as a failure,
indistinguishable in the results from "the model could not solve it".

Found 2026-08-16 when the `qwen3.8:27b` frontier scan hit it on 2024 d8 within minutes of starting.

## The bug

`shared/strategies.py:786` indexed the strategy table directly:

```python
for category in matching_categories:
    strategies.extend(strategy.name for strategy in SOLUTION_STRATEGIES[category])
```

But `CATEGORY_KEYWORDS` (which selects the categories) and `SOLUTION_STRATEGIES` (which supplies
them) do not have the same keys. Three categories are keyword-matchable with **no strategies
defined**:

| category | triggered by |
|----------|--------------|
| `GRAPH` | `connect`, `node`, `edge`, `network`, `path` |
| `OPTIMIZATION` | `minimize`, `maximize`, `optimal`, `best`, `efficient`, `fewest_steps`, … |
| `STATE_MACHINE` | `state_machine`, `automaton`, `current_state`, … |

Scoring uses `text.count(word)` — **substring** matching, not word matching — so 2024 d8's
"anti**node**" (the word appears throughout the problem) scored as `node`, put `GRAPH` top, and
raised. `OPTIMIZATION` is the more dangerous one in principle: `best`, `minimize` and `efficient`
are ordinary AoC vocabulary.

The fix is `SOLUTION_STRATEGIES.get(category, ())`. A category with no strategies must contribute
nothing — generation then proceeds unweighted, exactly as on a cold start — never crash the solve.

## Blast radius: exactly one day in the cached set

Every cached 2024 day was re-scored against the keyword logic. Only **d8** lands a strategy-less
category in its top two:

```
d01 PARSING,SEQUENCE     d06 PARSING,GRID_TRAVERSAL   d11 PARSING,SIMULATION
d02 PARSING,SEQUENCE     d07 PARSING,COMBINATORICS    d12 PARSING,GRID_TRAVERSAL
d03 PARSING,MATH         d08 GRAPH,PARSING  <-- CRASH d13 PARSING,SEQUENCE
d04 PARSING,PATTERN_M.   d09 PARSING,SEQUENCE         d14 PARSING,MATH
d05 PARSING,SEQUENCE     d10 GRID_TRAVERSAL,PARSING   d15 PARSING,GRID_TRAVERSAL
```

So the d4–7 results (4/8, 6/8, 8/8) are unaffected — no crash-prone day in that range. The M1's
d1–7 legs are unaffected too.

## What it invalidates

**`benchmark-2024-d1-12.md`'s "d8–12 leg: 2/10" is really 2 of 8 attempted.** The unguarded line
dates to 2025-12-06, so it was live for that 2026-08-12 run: d8 p1 and d8 p2 contributed two
guaranteed failures that `qwen2.5-coder:7b` never actually attempted. Corrected in place there.

The leg's qualitative conclusions (Part 2s are the wall; the failures are capability rather than
variance) do not rest on d8 — but the denominator did, and a solve rate is a denominator claim.

## Why it survived this long

Nothing pointed at it. The harness caught the exception, logged a `WARNING`, recorded the problem as
failed, and carried on — which is correct behaviour for an unexpected solver error and exactly what
makes this class of bug invisible. The result JSON shows a failed problem with no attempts, and no
run summary distinguishes "no attempts because the solver crashed" from "no attempts because
generation produced nothing".

**Worth a follow-up:** a solver-raised exception should be a distinct outcome (`HARNESS_ERROR`),
never scored in the same bucket as a model failure. A measurement platform should not be able to
blame the model for its own crash. Logged, not fixed here.

## Regression tests

`tests/unit/test_problem_classification_and_strategies.py` gains three, all failing before the fix:

- every category in `CATEGORY_KEYWORDS`, saturated with its own keywords, must not raise;
- the literal d8 shape (`"Each antinode occurs at a point…"`) must not raise;
- `OPTIMIZATION` wording (`"best route… minimize the cost… fewest steps"`) must not raise.

## Reproduce the original crash

```
git stash && venv/bin/python -c "
from shared.strategies import get_strategies_for_problem
get_strategies_for_problem('Each antinode occurs at a point in line with two antennas')"
# KeyError: <ProblemCategory.GRAPH: 'graph'>
```
