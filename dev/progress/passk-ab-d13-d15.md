# The pass@k A/B: sampling nearly doubles the solve rate at a strong model's frontier

**pass@1 = 42% → pass@3 = 75%.** The project's central open thesis — *does sampling + voting still
add correctness at a strong model's own frontier?* — now has a direct, controlled answer on the
model that had outgrown every earlier problem set. **It does.**

And one problem says the opposite, loudly, which is the more useful half of the result.

- **Model:** `qwen3.8:27b`, `temperature=0.7`, `enable_thinking=false`, ollama 0.32.14, `m2max-32`.
- **Problems:** 2024 d13 p1/p2, d15 p1/p2 — the frontier band, selected *before* this experiment by
  an independent 3-trial classification (`m2max-qwen38-frontier-scan-d8-15.md`), on the criterion
  that the model solves them *sometimes*.
- **Arms:** k1 (`samples_per_model=1`, fp `5b33a3519b5d`), k3 (`=3`, fp `bb22870d2a6d`), 3 trials each.
- **k1 is pooled** with the band-classification run — identical fingerprint — for **24 samp1 draws**.
- **k5 was deliberately not run** (maintainer scope decision). This is a two-point comparison, not a
  dose-response curve; saturation at higher k is untested.

## Result

| problem | pass@1 (24 pooled draws) | pass@3 measured | pass@3 predicted | delta |
|---------|--------------------------|-----------------|------------------|-------|
| d13 p1 | 5/6 = **83%** | **3/3 = 100%** | 100% | — |
| **d13 p2** | 1/6 = **17%** | **3/3 = 100%** | 42% (unbiased 50%) | **+58** |
| d15 p1 | 2/6 = **33%** | **3/3 = 100%** | 70% (unbiased 80%) | **+30** |
| **d15 p2** | 2/6 = **33%** | **0/3 = 0%** | 70% (unbiased 80%) | **−70** |
| **overall** | **10/24 = 42%** | **9/12 = 75%** | 71% | +4 |

Predictions are `1-(1-p)^k` from the pooled pass@1 rate, **registered in writing before the k3 arm
ran**, so the comparison is not retrofitted.

## The two halves

### Where it works, it works better than theory: d13 p2

A problem solved by **1 of 6** single draws was solved by **3 of 3** k3 trials. This is the thesis'
mechanism in its purest form: the correct solution is *in* the model's distribution but is not the
modal output, and a cheap exact verifier collapses several draws to the one that is right.

It is also the problem this project twice called an insight wall — it needs the `+10000000000000`
reformulation solved algebraically rather than by brute force. Both times that call was wrong.
**Sampling reaches insight problems, not just fiddly ones.** The tidy story we were drifting toward
("voting buys execution reliability, not ideas") does not survive its own data.

### Where it fails, it fails completely: d15 p2

33% per draw, 70% predicted at k=3, and **0 of 3** — nine samples, no solve. If draws were
independent at p=0.33, that outcome has probability ~0.03.

The reading: **sampling multiplies draws, not diversity.** d15 p2 is the most execution-bound
problem in the band (3,337–3,677 s per k3 trial), and the model appears to produce *the same
too-slow approach* every time. Where failure is systematic rather than stochastic, extra draws
re-roll the same die.

This is a real boundary on arm 1 of the thesis, found by the experiment built to test it, and it
points somewhere specific: **the lever for correlated failure is diversity — temperature, prompt
variants, or different models — not larger k.**

## Correction: these are "k samples + repair", not pure pass@k

Registered 2026-08-17, on reading `shared/solver.py:532-605` while designing the follow-up.

**Both arms ran with `max_repair_iterations=2`** (the default; neither `--config` set it). So the
loop is: generate k candidates, verify, and if none is accepted, feed execution feedback back and
regenerate *each* failing candidate, up to twice. The arms are therefore:

- "k1" = **1 sample + up to 2 feedback-guided repairs** (up to 3 generations)
- "k3" = **3 samples + up to 2 repair rounds on each** (up to 9 generations)

Two consequences, and neither overturns the result:

1. **The comparison stays valid** — repair is identical in both arms, so the delta is attributable
   to sample count.
2. **But the labels overstate precision.** This is not textbook pass@k over independent draws. The
   `1-(1-p)^k` curve assumes independent samples with no feedback; our k1 baseline of 42% *already
   contains* whatever repair contributes, which if anything makes the k3 gain **conservative** —
   the baseline is inflated relative to a true single-shot pass@1. It also means k3 cost up to 9
   generations, not 3, so the cost side of the comparison is worse than the label suggests.

The honest statement of the headline: **going from 1 sample to 3 samples, with repair held constant
at 2, lifts the solve rate from 42% to 75% on this band.** Whether the gain comes from *sampling*
or from *sampling interacting with repair* is exactly what the follow-up experiment separates
(`topology`: 3 blind draws vs 1 draw refined twice, both capped at 3 generations).

## Honest limits

- **n = 3 trials per problem.** Every per-problem cell has a wide interval; 3/3 and 0/3 are strong
  directional signals, not precise rates.
- **The overall +4% versus theory is noise**, and it averages a +58 and a −70. The aggregate is the
  least informative number in the table.
- **k5 not run**, so there is no dose-response curve and no saturation point.
- **One model, one temperature, four problems, one year of AoC.** The effect is measured where the
  band was found; it is not established as general.
- `p` itself is estimated from 6 draws per problem. Pooling moved two estimates materially
  (d13 p1 67→83%, d13 p2 33→17%), which is a reminder that even these baselines are provisional.

## What it changes

- **README's central open thesis is no longer open** in its k1-vs-k3 form: the decisive test ran, on
  a strong model, at its own frontier, and sampling nearly doubled the solve rate.
- **A new, sharper question replaces it:** *when does sampling fail?* d15 p2 says correlated draws
  are the failure mode, which makes **draw diversity** the next orchestration lever to measure —
  and that is a strategy question, not a compute question.

## Reproduce

```
venv/bin/python experiment.py --problems 2024:13,2024:15 --trials 3 --include-replay \
  --config "name=k1,models=qwen3.8:27b,temperature=0.7,samples_per_model=1,enable_thinking=false" \
  --config "name=k3,models=qwen3.8:27b,temperature=0.7,samples_per_model=3,enable_thinking=false"
```
