# The parallel3 arm: 7/12 (58%) — separating sampling from repair

**The middle row of `RESULTS.md`'s three-row pass@k table, now with an audit trail.** It was
published as "58%" with no `dev/progress/` write-up behind it; this is that write-up, recomputed
from the run artifact rather than inferred.

**7 of 12 = 58.3%.**

- **Config:** `models=qwen3.8:27b, temperature=0.7, samples_per_model=3, max_repair_iterations=0,
  enable_thinking=false` (fingerprint `4589b39ed1e5`), 3 trials, 2024 d13 + d15 (both parts).
- **Cost:** 21,210 s, 699,763 tokens. **0 wrong / 0 unverified / 0 overfit.**
- **Artifact:** `dev/experiments/20260818T082725Z_parallel3_4589b39ed1e5.json` (gitignored).

## Result

| problem | k/3 | outcomes |
|---------|-----|----------|
| 2024 d13 p1 | 3/3 | solved, solved, solved |
| 2024 d13 p2 | **1/3** | solved, no_candidate, no_candidate |
| 2024 d15 p1 | 3/3 | solved, solved, solved |
| 2024 d15 p2 | **0/3** | no_candidate, no_candidate, no_candidate |
| **total** | **7/12 (58.3%)** | |

## What it is for

This arm is the middle term that makes the pass@k decomposition possible. All three configurations
share the same band, model and temperature, and differ only in sampling and repair:

| configuration | samples | repair | solved | fingerprint |
|---|---|---|---|---|
| k1 — one attempt, with repair | 1 | 2 | **10/24 (42%)** | `5b33a3519b5d` |
| **parallel3 — three blind draws** | **3** | **0** | **7/12 (58%)** | **`4589b39ed1e5`** |
| k3 — three attempts, each with repair | 3 | 2 | **9/12 (75%)** | `bb22870d2a6d` |

Without this arm, 42% → 75% is a single lever of unknown composition. With it, sampling alone and
repair alone each contribute, and **the combination exceeds either** — the superadditivity claim in
`RESULTS.md` rests on this row.

The per-problem cells carry the same story. **d13 p2** solves 1/3 on blind draws and 3/3 with repair
added: sampling finds a good draw occasionally, repair converts more of them. **d15 p2** is 0/3 here
and 0/3 with repair — the configuration-independent failure discussed in
`temperature-diversity-negative.md` and `CORRECTION-d15p2-is-not-a-wall.md` (it is a ~12% problem
overall, not a wall).

## Note for anyone re-running this

`dev/analyze_passk.py` does **not** cover this arm — it globs `*_k1_*`, `*band-classify*`, `*_k3_*`
and `*_k5_*` only. It has been extended with a `parallel3` glob so the decomposition can be
reproduced from one command.

Also, outcomes in the result JSON are **lowercase** (`"solved"`, `"no_candidate"`); a filter written
against `"SOLVED"` silently returns 0/12.

## Reproduce

```
venv/bin/python experiment.py --problems 2024:13,2024:15 --trials 3 \
  --config "name=parallel3,models=qwen3.8:27b,temperature=0.7,samples_per_model=3,max_repair_iterations=0,enable_thinking=false"
```
