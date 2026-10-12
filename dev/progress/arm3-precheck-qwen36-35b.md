# Arm 3 pre-check: `qwen3.6:35b-a3b` alone on the standing targets — **registered, not yet run**

The entry criterion from `ensemble-precheck-negative.md`: *measure each member individually on the
targets first; only run an ensemble if one solves something the others reliably miss.* This file
registers the run and its prediction before any result exists. Results replace the last section.

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
| 2024 d15 p2 | 0/3 (2 of 16 over all arms) | 0/3 |
| 2025 d9 p1 | 3/3 | 0/3 |
| 2025 d9 p2 | 0/3 (0 of 10 over all arms) | 0/3 |

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

Not yet run.
