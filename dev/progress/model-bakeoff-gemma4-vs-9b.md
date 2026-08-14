# Model bake-off: gemma4:12b vs qwen3.5:9b (2024 d4–7)

Prompted by the community/aggregator consensus that **Gemma 4 12B** is the top coding-specific model
that fits 16 GB. Head-to-head on the hard days, only the model swapped: samples=1, temperature 0.7,
thinking off, `--include-replay` off. Run 2026-08-14.

(Two other candidates were dropped first: a Q6 quant of qwen3.5 — no such tag exists, it's a
Q4-only community import; and `deepseek-r1:14b` — reasoning-native, ignores `think=false`, slow, and
its inline `<think>` format doesn't fit our pipeline. Both removed.)

## Result: gemma4 wins, and is faster

```
model (d4-7, samples=1)   solved   which                                   wall
gemma4:12b                5/8      d4p1, d4p2, d5p1, d7p1, d7p2             6206 s
qwen3.5:9b                2/8      d4p2, d7p1                               10643 s
```

New verified solution: **d4 p2** (1822, X-MAS pattern count); `verify_solutions` now **12/12**. Zero
wrong/overfit.

The load-bearing comparison isn't the raw 5-vs-2 — it's that **gemma4 at samples=1 matched the 9b's
best result (5/8 at samples=3)**, solving the hard Part 2 (d7 p2) on a single draw, in ~40% less wall
clock. Matching a 3-sample result with 1 sample is a strong signal gemma4 is more capable per draw
(and cheaper).

## Honest caveats

- **samples=1 is noisy, and the 9b drew low.** Its 2/8 here is well under its known 5/8 at samples=3
  — a single draw missed d4p1, d5p1, d6p1. So this single run *overstates* the raw gap. The robust
  claim is the matched-at-fewer-samples one above, not "gemma4 is 2.5× the 9b."
- The two have slightly different strengths on one draw: gemma4 got d4p1/d5p1; the 9b's samp3 got
  d6p1 (gemma4 missed it here). A samples=3 gemma4 run is needed to compare like-for-like.
- gemma4 writes verbose prose around its code (the extractor handles it), and — unexpectedly — it was
  *faster* end-to-end than the 9b here, because the 9b spent time on many failed/timeout attempts.

## Conclusion

**gemma4:12b is the new leading candidate** — it matched the 9b's best at a third of the samples and
less wall clock, and it is the community's flagged coding-specific pick for 16 GB. The definitive
test is **gemma4 at samples=3 on d4–7 vs the 9b's recorded 5/8**: if it clears 5/8 — especially any
of d5 p2 / d6 p2, which neither model has cracked — it is decisively the new baseline. Until that
confirms, treat gemma4 as *promising and probably better*, not proven-best.

## Reproduce

```
venv/bin/python experiment.py --problems 2024:4-7 --trials 1 \
  --config "name=qwen35-9b,models=qwen3.5:9b,temperature=0.7,samples_per_model=1,enable_thinking=false" \
  --config "name=gemma4-12b,models=gemma4:12b,temperature=0.7,samples_per_model=1,enable_thinking=false"
```
