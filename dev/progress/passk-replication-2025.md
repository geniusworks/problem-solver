# Out-of-sample replication: sampling works on a second year, and a harder one

**The central claim replicates.** On AoC 2025 — a year the project had never measured, whose
frontier has a demonstrably *less favourable* shape than 2024's — the two "sometimes" problems went
from **25–33% at k=1 to 100% at k=3**, while the wall stayed walled and the control stayed reliable.

The prediction was registered before the run, on problems selected by an independent classification.

- **Config:** `models=qwen3.8:27b, temperature=0.7, samples_per_model=3, enable_thinking=false`
  (fingerprint `bb22870d2a6d` — **byte-identical to the 2024 k3 arm**, so the two years compare
  directly), 3 trials, 2025 d9 + d11 (both parts each: the two "sometimes" problems plus a wall and
  a control).
- **Cost:** 18,268 s (5h). **0 wrong / 0 unverified / 0 overfit.**
- **Run:** `dev/experiments/20260819T112247Z_k3-2025_bb22870d2a6d.json` (gitignored).
- **Baseline:** `band-2025-classification.md` (and the 2025 scan draw), same fingerprint pool.

## Result — all four cells as predicted

| problem | pass@1 | **pass@3** | predicted | role |
|---------|--------|-----------|-----------|------|
| **d9 p1** | 1/4 (25%) | **3/3 (100%)** | ~58% | *sometimes* → rescued |
| d9 p2 | 0/4 | **0/3** | ~0% | wall → held (now **0/7** overall) |
| d11 p1 | 3/3 (100%) | **3/3 (100%)** | 100% | control → held |
| **d11 p2** | 1/3 (33%) | **3/3 (100%)** | ~70% | *sometimes* → rescued |

Overall **9/12 (75%)** — coincidentally the same headline as the 2024 arm.

## Why this is stronger than a repeat of 2024

**2025 was the unfavourable venue, and it was flagged as such in advance.**
`band-2025-classification.md` recorded, before this run, that 2025's frontier is **bimodal** —
4 reliable / 2 sometimes / 4 walls — against 2024's 5-of-8 near-misses, and warned that the 2024
band "may have been unusually favourable" to sampling. It was. The effect replicated anyway.

**The three-way structure is what makes it interpretable.** A rate improvement alone could be noise
or drift. Here sampling **rescued** exactly the problems that were uncertain, did **nothing** for the
problem that never solves, and was **unnecessary** for the problem that always solves. Walls and
controls are what turn a number into a mechanism.

| | pass@1 | pass@3 |
|---|---|---|
| 2024 band (5 problems) | 42% | 75% |
| **2025 band (2 problems + wall + control)** | **25–33%** | **100%** |

## Statistical note (added 2026-08-22)

Recomputed from the artifacts: the 2024 aggregate alone (10/24 vs 9/12) is **marginal** — one-sided
Fisher exact p ≈ 0.061. This replication (2/8 vs 6/6 on the "sometimes" problems) is p ≈ 0.009, and
the combined evidence (Fisher's method) is **p ≈ 0.005**. The honest statement: **neither year alone
is decisive; together they are** — which is precisely what a replication is for.

## Limits — unchanged, and they matter

- **Two "sometimes" problems, three trials each.** This is a **replication attempt that succeeded**,
  not a second independent confirmation at scale. A null result here would have been under-powered
  rather than decisive, and the successful result inherits the same width of uncertainty.
- Same caveat as 2024: these arms run with the repair loop at its default (`max_repair_iterations=2`),
  so they measure *k samples + repair*, not textbook pass@k over independent draws
  (`passk-ab-d13-d15.md`, correction section).
- One model, one temperature.

## The other half: a class of failure that sampling cannot touch

**2025 d9 p2 is now 0/7** — every configuration, k=1 and k=3, four hours of compute in this run
alone (one attempt ran 4,221 s, the longest problem-trial recorded). It was originally paired with
**2024 d15 p2** as a second member of this class — **that was wrong**: d15 p2 has solved 2 of 16
times (~12%), so the class currently has **one confirmed member**
(`CORRECTION-d15p2-is-not-a-wall.md`). The remainder of this section read:
as a second confirmed member of a class that more draws simply do not reach.

Two years, two such problems. This is not an anomaly to be explained away — it is a **standing
boundary on the sampling claim**, and the reason the next lever is *diversity* (temperature, prompt
variants, model mixing) rather than larger k. Both problems are now named, reproducible benchmarks
for anything claiming to decorrelate draws.

## What this changes

The project's central claim can now be stated with out-of-sample support: **on problems a strong
model solves only sometimes, drawing several candidates and letting an exact verifier choose lifts
the solve rate substantially — measured on two independent years, including one whose frontier shape
worked against it.** What remains open is the complementary question: what to do about the problems
where it doesn't work.

## Reproduce

```
venv/bin/python experiment.py --problems 2025:9,2025:11 --trials 3 \
  --config "name=k3-2025,models=qwen3.8:27b,temperature=0.7,samples_per_model=3,enable_thinking=false"
```
