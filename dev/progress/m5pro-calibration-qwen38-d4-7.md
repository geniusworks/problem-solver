# m5pro-64: `qwen3.8:27b` calibration on 2024 d4–7 — **23/24. The reference model reproduces.**

**Headline: 23 of 24 problem-trials solved (96%), against 16 of 16 on the M2 Max.** The one miss is
on d6 p2, the hardest problem on the set and the only one the reference runs also needed more than
one draw for. Off d6 p2 the per-attempt verify rate is the same on both machines, **90%**. The
machine is **about 2.3× faster**. Nothing here says the new runtime changed the model's behaviour;
with this n the run can rule out a gross regression and not a small one.

This run is a calibration, not an experiment. `m5pro-64` differs from `m2max-32` in hardware, Ollama
(0.32.14 → 0.34.4), Python (3.14 → 3.11.16) and macOS (26 → 27) at once, so the reference model had
to be re-measured before any new-model number from this machine could be read.

- **Config:** `models=qwen3.8:27b, temperature=0.7, samples_per_model=3, enable_thinking=false,
  enable_fallback_models=false` (fingerprint `d0e67ebf4cee`), **3 trials**, 2024 d4–7.
- **Machine:** `m5pro-64`, ollama 0.34.4. Model digest `aaee06c39dcf`, 18.2 GB loaded, 100% GPU.
- **Cost:** 13,150 s wall (3h 39m) for three trials, 74 attempts, 904,043 tokens.
- **Run:** `dev/experiments/20261012T115641Z_m5pro-calib-qwen38-samp3_d0e67ebf4cee.json` (gitignored).
- **Ledger:** unchanged. `verify_solutions` 43 correct, 0 wrong; 0 wrong/unverified/overfit in the run.

**One config difference from the reference rows:** `enable_fallback_models=false` here, `true`
there. This machine's installed models differ, so a fallback would have put a different model into
the comparison. In both reference runs every attempt came from `qwen3.8:27b` — the fallback never
fired — so the two settings behaved identically there.

## Against the M2 Max reference

The reference is two independent single trials of the same settings: the original d4–7 run
(`m2max-qwen38-27b-d4-7.md`) and the economic arm's generalist run
(`economic-arm-moe-vs-generalist.md`).

| | m2max-32 (2 × 1 trial) | m5pro-64 (3 trials) |
|---|---|---|
| problem-trials solved | 16/16 | **23/24** |
| problems solved every trial | 8/8 | 7/8 |
| attempts verified | 41/48 (85%) | 59/74 (80%) |
| attempts verified, excluding d6 p2 | 38/42 (90%) | 57/63 (90%) |
| first draw solved | 12/16 (75%) | 19/24 (79%) |
| wall per trial | 9,602 s and 11,112 s | **4,383 s** |
| tokens per trial | 287,369 and 307,684 | 301,347 |

Per problem (problem-trials solved, attempts verified):

| problem | m2max-32 | m5pro-64 |
|---|---|---|
| d4 p1 | 2/2, 6/6 | 3/3, 9/9 |
| d4 p2 | 2/2, 6/6 | 3/3, 9/9 |
| d5 p1 | 2/2, 5/6 | 3/3, 8/9 |
| d5 p2 | 2/2, 5/6 | 3/3, 5/9 |
| d6 p1 | 2/2, 6/6 | 3/3, 9/9 |
| **d6 p2** | 2/2, 3/6 | **2/3, 2/11** |
| d7 p1 | 2/2, 5/6 | 3/3, 8/9 |
| d7 p2 | 2/2, 5/6 | 3/3, 9/9 |

**The miss.** d6 p2, trial 2 of 3: three initial draws and two repairs, all wrong answers (`16105`
three times, then `0` twice), none of them a timeout or a crash. The harness labels the
problem-trial `no_candidate`; that is the problem-level rollup, and the attempt records show five
candidates.

**It is the problem where a miss was most likely.** On the M2 Max d6 p2 verified 3 of 6 draws and
was never solved on the first draw; it is one of the two problems sampling bought there. At 50% per
draw, three draws all failing has probability 1/8. Here its initial draws went 2 of 9.

## How much this can and cannot show

- **Problem level:** 23/24 against 16/16. If the two machines shared one solve rate, a split at
  least this uneven has probability 0.6 (hypergeometric, pooled 39/40). No evidence of a difference.
- **Attempt level:** 59/74 against 41/48, one-sided Fisher p ≈ 0.29. The whole gap sits on d6 p2
  (2/9 initial draws against 3/6, p ≈ 0.29 on its own); every other problem pools to 90% on both.
- **What it cannot exclude:** a modest drop on the hardest problems. d6 p2's per-draw rate here is
  lower than the reference's, on 9 and 6 draws. d5 p2 also verified 5/9 against 5/6. Neither is
  distinguishable from noise at this n, and neither is evidence of equality.

So the calibration clears the bar it was set — the reference model, on this runtime, still solves
the comparison set at the rate the record says — and new-model results from `m5pro-64` can be read
against the `m2max-32` rows. A frontier-band comparison that turns on a few percentage points should
re-run its own `qwen3.8:27b` baseline here rather than borrow the M2 Max's.

## Speed

Wall-clock per trial fell from 9,602–11,112 s to 4,383 s, **2.2–2.5×**, at the same token volume.
Output tokens per second of attempt wall-clock (which includes execution, so it understates raw
generation speed on both machines) went from 8.4–8.8 to 19.4. A single-trial d4–7 run is now about
73 minutes instead of 2h 40m–3h 05m; what took the M2 Max 121 GPU-hours would take roughly 50 here.

macOS reported no thermal or performance warning at the start or at the end of the run.
