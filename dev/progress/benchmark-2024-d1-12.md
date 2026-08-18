# Benchmark — 2024 d1–12, qwen2.5-coder:7b, self-consistency (samples=3)

Extends the frontier picture from d1–7 to the first 12 days of AoC 2024 with the winning config
(`samples_per_model=3`, `temperature=0.7`), all cached with oracle answers so every run is fully
verified offline. The d8–12 leg ran 2026-08-12, 1 trial, 110 min
(`dev/experiments/*_bench-samp3_a6f101eadf5f.json`, gitignored).

> **CORRECTION (2026-08-16): the d8–12 leg is 2 of *8 attempted*, not 2 of 10.**
> A harness bug crashed **2024 d8, both parts, before the model was ever called**:
> `get_strategies_for_problem` indexed `SOLUTION_STRATEGIES[category]` unguarded, and d8's text
> substring-matches the GRAPH keyword `node` via "anti**node**" — GRAPH has keywords but no
> strategies, so the lookup raised `KeyError` out of `_prepare_problem`. The unguarded line dates to
> 2025-12-06, so it was present for this run. Those two parts were counted as model failures; they
> were harness failures, and `qwen2.5-coder:7b` never got a shot at them. Fixed 2026-08-16
> (`dev/progress/strategy-keyerror-d8.md`); d8 is the only affected day in 2024 d1–15. The
> qualitative conclusions below (Part 2s are the wall; failures are capability, not variance) do not
> depend on d8, but the denominator does.

## d8–12 leg: 2/10 — see the correction above (2 of 8 *attempted*)

New verified solutions: **d10 p1** (482, hiking-trail scoring) and **d11 p1** (229043, stone
simulation) — both recorded and verified. Attempt-level (54 attempts, samples=3):
**4 solved / 29 wrong / 20 error / 1 no_candidate.** Same shape as d4–7: the model produces
candidates freely and they are mostly wrong or erroring.

## The frontier across d1–12 (all at samples=3)

| leg    | solved / total | notes |
|--------|----------------|-------|
| d1–3   | reliable on 3–4 of 6 | self-consistency A/B; 3 of 6 solved *every* trial |
| d4–7   | 1 / 8          | d6 p1 only |
| d8–12  | 2 / 10         | d10 p1, d11 p1 only |

**Seven verified solutions in the ledger** (d1 p1/p2, d2 p1, d3 p1, d6 p1, d10 p1, d11 p1) — and a
clear, consistent shape to the frontier:

- **Almost every win is a Part 1.** The one Part 2 solved is d1 p2 (the easiest). Every other Part 2
  across d1–12 failed. Part 2 raises difficulty sharply, and the 7B rarely clears it.
- **The failures are capability, not variance.** Three samples give three shots; past the easy
  problems the extra shots fail the same way (wrong reasoning or un-runnable code), exactly as the
  d4–7 leg first showed. Self-consistency converts *reachable* problems from flaky to reliable; it
  does not extend reach.
- **No regression, ever.** Across all of d1–12: zero wrong or overfit *recorded* solutions. The
  oracle + overfit gate held on every run — the platform never fooled itself, which was the whole
  point of building it first.

## Takeaway

The frontier is now well mapped: on 16 GB with `qwen2.5-coder:7b`, this platform reliably solves the
easy Part 1s of AoC 2024 and is capability-limited on Part 2s and harder days. Further coverage is a
**model** problem, not an orchestration one — which is where a stronger model (hardware-blocked here)
or the deferred submission phase against genuinely-unseen problems would come in. The measurement
job for this model is essentially complete.

## Reproduce (d8–12 leg)

```
venv/bin/python experiment.py --problems 2024:8-12 --trials 1 \
  --config "name=bench-samp3,models=qwen2.5-coder:7b,temperature=0.7,samples_per_model=3"
```
