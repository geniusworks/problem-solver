# Arm 3 pre-check: `qwen3.6:35b-a3b` matches the reference's solve set — no ensemble to run

The entry criterion from `ensemble-precheck-negative.md`: *measure each member individually on the
targets first; only run an ensemble if one solves something the others reliably miss.* The design
and prediction below were committed before the run (`6b008b2`, ten seconds ahead of launch); the
result follows them.

**Headline: 7/12 for the candidate, 6/12 for the reference on the same machine, and the two solve
the same problems.** The entry criterion is not met and the ensemble was **not run**. Unlike the
previous candidate this one is not dominated: it equals the reference's solve set in about a third
of the wall-clock.

## Design

- **Candidate:** `qwen3.6:35b-a3b` — 35.5B MoE (256 experts, 8 active), 22.6 GB Q4_K_M, never
  measured here. A one-call plumbing check confirmed it returns no thinking text with `think=false`;
  that is a check that the flag is wired, not a measurement.
- **Reference, re-run on this machine in the same invocation:** `qwen3.8:27b`, per the calibration
  doc's advice not to borrow the M2 Max baseline for a frontier comparison.
- **Config, both arms:** `temperature=0.7, samples_per_model=3, enable_thinking=false,
  enable_fallback_models=false`, default repair (2). **3 trials.**
- **Problems:** 2024 d15 p1/p2 and 2025 d9 p1/p2 — the same four as the previous pre-check.
- **Machine:** `m5pro-64`, ollama 0.34.4.

## What the record says about the reference on these problems (m2max-32)

| problem | `qwen3.8:27b` at k3 | `qwen3-coder:30b` (the previous candidate) |
|---|---|---|
| 2024 d15 p1 | 3/3 | 3/3 |
| 2024 d15 p2 | 0/3 (2 of 19 problem-trials over every recorded run) | 0/3 |
| 2025 d9 p1 | 3/3 | 0/3 |
| 2025 d9 p2 | 0/3 (0 of 13 problem-trials over every recorded run) | 0/3 |

## Prediction (registered 2026-10-12, before the run)

**The candidate fails the entry criterion, as the last one did.** Specifically:

- d15 p1: solved in at least 2 of 3 trials.
- d9 p2: 0/3. No configuration of any model has solved it.
- d15 p2: at most 1/3.
- d9 p1: no prediction. The previous MoE went 0/3 where the reference goes 3/3, and nothing
  measured says which way this one falls.

**What would justify running the ensemble:** the candidate solving d9 p2 in any trial, or d15 p2 in
at least 2 of 3 while the reference, on this machine, does not. Anything less leaves arm 3 untested
for want of a pair, with three failures at the entry condition.

**What would be evidence against the reading above:** the reference itself moving on d9 p2 or
d15 p2 here. That would be a machine or runtime effect and would send the question back to the
calibration, not forward to an ensemble.

## Result

- **Candidate run:** fingerprint `c87684c437f1`, 4,590 s (1h 16m), 69 attempts, 1,547,230 tokens.
  `dev/experiments/20261012T131643Z_m5pro-arm3-qwen36-k3_c87684c437f1.json`
- **Reference run:** fingerprint `d0e67ebf4cee` (the calibration's config), 13,236 s (3h 41m), 68
  attempts, 1,380,061 tokens. `dev/experiments/20261012T165719Z_m5pro-arm3-qwen38-k3_d0e67ebf4cee.json`
- Both: 0 wrong / 0 unverified / 0 overfit; every attempt from the named model. Ledger unchanged,
  `verify_solutions` 43 correct, 0 wrong.

| problem | `qwen3.6:35b-a3b` | `qwen3.8:27b`, same machine | initial draws verified (candidate / reference) | ensemble prospect |
|---|---|---|---|---|
| 2024 d15 p1 | **3/3** | 3/3 | 4/9 / 6/9 | both solve |
| 2024 d15 p2 | **1/3** | 1/3 | 1/9 / 0/9 | both low-rate |
| 2025 d9 p1 | **3/3** | 2/3 | 7/9 / 3/9 | both solve |
| 2025 d9 p2 | **0/3** | 0/3 | 0/9 / 0/9 | both fail |
| **total** | **7/12** | 6/12 | 12/36 / 9/36 | |

### The prediction

| registered | measured | |
|---|---|---|
| d15 p1 solved in at least 2 of 3 | 3/3 | held |
| d9 p2 0/3 | 0/3 | held |
| d15 p2 at most 1/3 | 1/3 | held |
| d9 p1: no prediction | 3/3 | — |
| fails the entry criterion | d9 p2 never solved; d15 p2 1/3, same as the reference | held |

**The reference did solve d15 p2 once here**, which the registration named as a possible sign of a
machine effect. It is not one. d15 p2 was already a low-rate "sometimes" for this model — 2 of 19
problem-trials on the M2 Max — and at that rate one or more solves in three trials has probability
about 0.28. With this run it stands at **3 of 22**. Its single solve here came from a repair, not an
initial draw.

### What is different from the last candidate

`qwen3-coder:30b` solved a strict subset (3/12, 0/3 on d9 p1). This candidate solves the **same
set** as the reference, so the reason there is no ensemble to run has changed from *dominated* to
*redundant*. Pooling two models with one solve set buys nothing either way: the best an ensemble
could have done on these trials is the candidate's own 7/12.

Three things the run was not designed to test, recorded as observations and not as findings:

- **Speed.** 4,590 s against 13,236 s on the same machine and problems, **2.9×**. Per verified
  solution: 656 s against 2,206 s, and 221k tokens against 230k. The previous MoE won on time and
  lost 3.35× on tokens (`economic-arm-moe-vs-generalist.md`); this one shows no token penalty here.
  *Correction 2026-10-12: 44–48% of both totals were draft counts copied onto repair records
  (`repair-accounting-unwired.md`). On drafts alone it is 115k against 128k per verified solution,
  so the observation holds on the sound part of the data.*
  Four problems, one run each — a reason to measure it, not a result.
- **d9 p1 per draw.** 7 of 9 initial draws against 3 of 9 (one-sided Fisher p ≈ 0.08, and the
  comparison was not registered).
- **Failure style.** Candidate: 30 errors, 26 wrong. Reference: 16 errors, 42 wrong. The MoE
  crashes where the dense model is confidently wrong, the split the first MoE showed on d4–7 (though
  not on these four problems, where it was 22 errors to 40 wrong). Four of the
  candidate's attempts hit the 60 s execution timeout (one each on d15 p1 and d15 p2, two on
  d9 p2); the reference had none.

### Where this leaves arm 3 and the wall

- **Arm 3 stays untested for want of a pair**, now after three failures at the entry condition:
  same-tier noise (M1), a dominated candidate (M2 Max), a redundant one (here).
- **2025 d9 p2 is 0 of 22 problem-trials** across three models: `qwen3.8:27b` 0/16,
  `qwen3-coder:30b` 0/3, `qwen3.6:35b-a3b` 0/3. A second current-generation model failing it the
  same way — passing nothing, mostly `expected '24', got '18'` on the worked example — is the first
  evidence that the wall is not one model's blind spot. A pair for arm 3 has to differ on exactly
  this kind of problem, and nothing measured so far does.
