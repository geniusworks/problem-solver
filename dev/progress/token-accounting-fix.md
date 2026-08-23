# Token accounting was stale across repair attempts — and repair ignored the configured temperature

Two bugs in one function, both in `OllamaProvider.improve_solution` (the repair path). Step 1 of the
endgame sequence: **no cost claim is honest until this lands**, and arm 2 of the project's thesis is
an economic claim measured in tokens.

## Bug 1: repair attempts reported the previous generation's tokens

`improve_solution` called `self.generate(prompt)` and returned the extracted code **without touching
`last_token_usage`**. The attribute therefore still held whatever `generate_solution()` had recorded,
and `_record_attempt` copied that stale value onto every repair attempt.

The symptom that exposed it — three attempts on 2024 d1 p2 reporting identical counts while
returning **different answers**:

```
attempts:  ans='0'        ans='0'        ans='87471881'
tokens:    (4283, 876)    (4283, 876)    (4283, 876)
```

Different generations cannot have identical token counts
(`dev/progress/ollama-0.32.14-runtime-check.md`).

**Impact:** every `input_tokens`/`output_tokens` figure on a repair attempt in every result JSON to
date is wrong — a duplicate of the initial generation's count rather than the repair's own. Since
repair only runs on failure, **the understatement is concentrated in exactly the expensive,
repair-heavy runs** a cost comparison cares most about. Wall-clock was never affected and remains
trustworthy.

**Fix:** record `self._tokens(response)` into `last_token_usage` before returning.

## Bug 2 (found while fixing Bug 1): repair ran at the model's default temperature

The same call was `self.generate(prompt)` — **no `temperature` argument**. `generate()` only sends a
temperature when one is passed, so every repair generation used Ollama's model default while every
initial generation used the configured value.

### This partially confounds the temperature experiment

`temperature-diversity-negative.md` set `temperature=1.0` and found no benefit. But at k3 with
`max_repair_iterations=2`, a *failing* problem produces up to **9 generations: 3 initial + up to 6
repair**. Only the 3 initial draws received the manipulation. **Roughly two-thirds of the
generations in that experiment ran at the model default, not at 1.0.**

The comparison itself stays valid — repair ran at the default in *both* arms, so the treatment
difference is real. But the treatment was **much weaker than intended**: it reached about a third of
the generations on precisely the problems it was aimed at. The honest restatement:

> **Raising the temperature of the *initial draws only*, from 0.7 to 1.0, produced no benefit.** A
> full-pipeline temperature manipulation has not been tested.

That does not resurrect temperature as a promising lever — it still added variance without
information, which the five-null rule predicts will fail — but the null is weaker evidence than the
doc claimed, and the doc now says so.

## Tests

`tests/unit/test_token_accounting.py`, three cases, all failing before the fix:

- repair records its own tokens, not the stale prior value;
- consecutive repairs report *different* counts (the exact observed symptom);
- repair honours the configured temperature.

## What this unblocks

**Step 3 of the endgame — the economic A/B** (arm 2 of the thesis: many cheap draws vs one expensive
pass at matched cost). Cost per verified solution can now be computed from the artifacts without
systematically under-counting repair.

**Caveat for any historical cost analysis:** result JSONs written *before* this fix carry inflated-
by-duplication repair token counts. Wall-clock is unaffected; token totals from earlier runs should
be treated as lower bounds on repair cost, not measurements.
