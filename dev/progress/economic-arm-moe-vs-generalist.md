# Arm 2 measured: cheap draws win on time, lose on tokens, and don't reach the ceiling

**At a matched wall-clock budget, a fast weak model taking many draws beats a slow strong model
taking few — per unit time. On tokens it loses by 3.35×. And it does not reach the same ceiling.**

This is thesis arm 2 — *"many cheap draws plus a verifier can beat one expensive think-harder pass at
equal or lower cost"* — argued in `README.md` since the beginning and never measured until now.

- **Arms:** `qwen3.8:27b samp3` (fp `8058f8439c6b`) vs `qwen3-coder:30b samp12` (fp `4e8381b91b3f`),
  temperature 0.7, thinking off, 1 trial, 2024 d4–7 (8 problem-parts).
- **Both arms run fresh** after the token-accounting fix, so cost figures on both are trustworthy.
- **0 wrong / 0 unverified / 0 overfit** in both.
- **Runs:** `dev/experiments/20260823T024401Z_econ-generalist-k3_8058f8439c6b.json`,
  `..._econ-moe-k12_4e8381b91b3f.json` (gitignored).

## Result

| config | solved | wall | tokens | **s / solve** | **tokens / solve** |
|--------|--------|------|--------|---------------|--------------------|
| `qwen3.8:27b` k=3 (slow, strong) | **8/8** | 11,112 s | 307,684 | 1,389 s | **38,460** |
| `qwen3-coder:30b` k=12 (fast, weak) | 7/8 | **6,234 s** | 901,111 | **891 s** | 128,730 |
| **ratio (MoE ÷ generalist)** | | | | **0.64×** | **3.35×** |

## The answer splits by which cost you actually pay

- **Wall-clock: the cheap model wins.** 891 s vs 1,389 s per verified solution — **36% cheaper** —
  and it finished the whole set in 6,234 s against 11,112 s. For local GPU inference, where the cost
  is *time*, **arm 2 is true**.
- **Tokens: the cheap model loses badly.** 128,730 vs 38,460 per solution — **3.35× worse**. Twelve
  draws burn far more tokens than three even from a smaller model. For a token-metered API, **arm 2
  is false**.
- **Ceiling: volume does not close the capability gap.** 7/8 vs 8/8.

**The sharpened claim, which is more useful than the original:** *many cheap draws beat one expensive
pass when the binding cost is time, not tokens — and only up to the cheap model's ceiling.*

## Which problem volume bought, and which it didn't

At samp3 the MoE missed **d5 p1** and **d6 p2**. At samp12 it took d5 p1 and still missed d6 p2 —
exactly as pre-registered:

- **d5 p1 — bought.** A ~25%-per-draw *parsing* failure (`invalid literal for int(): '75,47,…'`).
  Stochastic, so four times the draws found the good one.
- **d6 p2 — not bought.** 6/6 immediate `TypeError`s at samp3: a *systematic* failure. Four times
  the volume produced four times the same broken approach.

This is the pass@k finding and the five-null rule agreeing on one problem: **draws buy stochastic
failures, not systematic ones.** It also matches the d15 p2 / d9 p2 pattern, from a different angle.

## Why the ordering of the endgame mattered

This run depended on step 1 (`token-accounting-fix.md`). Before that fix, repair attempts reported
the *previous* generation's token counts. The MoE arm at samp12 is by far the more repair-heavy of
the two, so its token total — **the column the negative half of this conclusion rests on** — would
have been silently understated. Running the economics before fixing the instrument would have
produced a cleaner-looking and wrong answer.

## Limits

- **1 trial per arm.** The solve counts (8/8, 7/8) are single draws at the problem level; the *cost
  ratios* are more robust than the solve counts, being aggregates over 8 problems.
- **One problem set (2024 d4–7), chosen deliberately** because both models can score there. On the
  frontier band the MoE scores 3/12 (`ensemble-precheck-negative.md`) and any cost ratio would be
  dominated by its failures rather than measuring economics.
- **Wall-clock is machine- and load-specific.** The generalist's own 8/8 took 9,602 s in an earlier
  run and 11,112 s here — ~16% run-to-run variance on identical config, so treat the 0.64× as
  approximate.
- Two models, one hardware configuration.

## Reproduce

```
venv/bin/python experiment.py --problems 2024:4-7 --trials 1 \
  --config "name=econ-generalist-k3,models=qwen3.8:27b,temperature=0.7,samples_per_model=3,enable_thinking=false" \
  --config "name=econ-moe-k12,models=qwen3-coder:30b,temperature=0.7,samples_per_model=12,enable_thinking=false"
```
