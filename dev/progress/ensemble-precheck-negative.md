# Arm 3 pre-check: the MoE's solve set is a strict subset — no ensemble to run

**`qwen3-coder:30b` solves nothing on these problems that `qwen3.8:27b` cannot, and fails one the
generalist handles reliably.** There is nothing for an ensemble of the pair to pool, so the planned
model-mixing A/B was **not run**: it could only have cost more and diluted.

Cost of learning this: **1h45m instead of ~9h**, because the pre-check was run first.

- **Config:** `models=qwen3-coder:30b, temperature=0.7, samples_per_model=3, enable_thinking=false`
  (fingerprint `12ff1a00c02d`), 3 trials, 2024 d15 + 2025 d9.
- **Cost:** 6,329 s. **0 wrong / 0 unverified / 0 overfit.**
- **Run:** `dev/experiments/20260822T203233Z_moe-profile-k3_12ff1a00c02d.json` (gitignored).

## Result: subset, not complement

| problem | `qwen3.8:27b` (generalist) | **`qwen3-coder:30b` (MoE)** | ensemble prospect |
|---------|---------------------------|------------------------------|-------------------|
| 2024 d15 p1 | 3/3 | **3/3** | both solve — nothing gained |
| 2024 d15 p2 | 0/3 (~12% problem) | **0/3** | both fail — nothing gained |
| 2025 d9 p1 | 3/3 | **0/3** | **MoE strictly worse** |
| 2025 d9 p2 | 0/3 (0/13 overall) | **0/3** | both fail — nothing gained |
| **total** | 6/12 | **3/12 (25%)** | |

An ensemble helps only when the second model solves what the first cannot. Here the MoE's solve set
is a **strict subset** of the generalist's, and on d9 p1 it is a proper subset — the ensemble would
inherit the generalist's answer at roughly double the generation cost, with an added chance of the
selector preferring a worse candidate.

## Why this pre-check existed, and why it paid

The M1's ensemble (`ensemble-samp3-d4-7.md`) failed for exactly this reason, discovered *after* the
run: two same-tier models whose apparently-complementary solves turned out to be sampling noise, so
there was nothing stable to pool. That lesson was applied prospectively here — **measure whether the
second model can solve the targets at all, before paying for the ensemble.**

The design that *would* have been run, had the pre-check passed, is worth recording because it fixes
a flaw in the M1's version: **ensemble-samp3 (2 models × 3 draws = 6 generations) vs single-model
samp6 (6 generations)** — equal draw count, which isolates *model diversity* from *more sampling*.
The M1 compared an ensemble against single-model samp3, confounding the two.

## What it says about arm 3 of the thesis

README arm 3 argues that **diverse portfolios decorrelate error**. It now has:

- **two failed attempts** — M1 same-tier/same-generation pair; this cross-generation pair — and
- **no successful demonstration.**

That is not a refutation. Both failures share a cause that is about the *models available*, not about
the mechanism: neither pair had **measured, reproducible, complementary** failures. The honest status
is that arm 3 remains **untested for want of a suitable pair**, and the entry criterion for any
future attempt is now explicit:

> Do not run an ensemble until each member is measured *individually* on the target problems and at
> least one solves something the others reliably miss.

## It also sharpens "generation beats size"

That finding rested on d4–7, where the MoE scored 6/8 against the generalist's 8/8 — a gap. On
genuinely hard problems the relationship is stronger than a gap: **strict domination**. The 2026
generalist does not merely outscore the newer-generation code specialist; on this set it solves a
superset of what the specialist solves, while also being the only one of the two to handle d9 p1.

## Reproduce

```
venv/bin/python experiment.py --problems 2024:15,2025:9 --trials 3 \
  --config "name=moe-profile-k3,models=qwen3-coder:30b,temperature=0.7,samples_per_model=3,enable_thinking=false"
```
