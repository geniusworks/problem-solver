# gemma4:12b samples=3 on 2024 d4–7 — the deciding test (resolved: a tie, with a twist)

The bake-off (`model-bakeoff-gemma4-vs-9b.md`) left one question open: at **samples=3**, does
`gemma4:12b` clear the 9b's recorded **5/8** on the hard days — ideally cracking d5 p2 / d6 p2, which
no 16 GB model has? This run answers it. Config: `models=gemma4:12b, samples_per_model=3,
temperature=0.7, enable_thinking=false`, 2024 d4–7, 1 trial. Run 2026-08-14, wall **15,160 s (~4.2 h)**.

Verified from the run JSON that **only `gemma4:12b` produced candidates on every problem** (no
fallback fired despite the default), so this is a clean single-model number.

## Result: 5/8, clean — a tie with the 9b, not a win

```
problem        gemma4 samp3   answer
2024 d4 p1     OK             2401
2024 d4 p2     OK             1822
2024 d5 p1     OK             5747
2024 d5 p2     none           (expected 5502)
2024 d6 p1     OK             5331
2024 d6 p2     none           (expected 1812)
2024 d7 p1     OK             5702958180383
2024 d7 p2     none           (expected 92612386119138)
```

**5/8 (62%), 0 wrong / 0 unverified / 0 overfit.** No new ledger entries (all five were already
recorded); `verify_solutions` stays **12/12**.

The deciding test resolves cleanly: **gemma4 samp3 did *not* beat the 9b's 5/8, and did *not* crack
d5 p2 / d6 p2.** gemma4 is a *co-leader* on 16 GB, not the decisive new baseline the bake-off
speculated it might be. Its real edge is per-draw efficiency (it already hit 5/8 at *samples=1*),
not a higher ceiling — the ceiling on this set is the same 5/8 for both models.

## Two findings that matter more than the headline count

**1. A single-sample "win" can be noise.** gemma4 at samp1 solved d7 p2 (a hard Part 2) on one lucky
draw; at samp3 it *missed* d7 p2 but *gained* d6 p1 — same 5/8, different set. So more samples was not
monotonically better here: d7 p2 sits so close to gemma4's probabilistic frontier that a single solve
is largely luck. This is a caution against reading any one Part-2 solve as robust capability, and a
concrete reminder of why single runs are noise.

**2. The two 5/8 models miss *different* Part 2s — a direct ensemble opportunity.** Lining up the
two samples=3 leaders:

```
common (both):   d4 p1, d5 p1, d6 p1, d7 p1
gemma4 only:     d4 p2          <- gemma4 cracks this Part 2, the 9b misses it
9b only:         d7 p2          <- the 9b cracks this Part 2, gemma4 misses it
neither:         d5 p2, d6 p2
```

Their errors *appeared* decorrelated on the hard Part 2s, so the *union* looked like **6/8** — one
more than either alone — a cheap M1 test of the "diverse portfolios decorrelate error" arm of the
orchestration thesis (README, "Does orchestrated voting scale?").

> **TESTED — it did not hold (`ensemble-samp3-d4-7.md`).** The combined `gemma4:12b|qwen3.5:9b` samp3
> run got **5/8, not 6/8**, at ~2.2× wall. Both models participated fully, but neither solved d7 p2
> that run: the 9b's d7 p2 "crack" was itself a low-probability draw (like gemma4's d7 p2 at samp1 —
> finding 1 above), not a robust competency, so the ensemble had nothing stable to pool. Diversity
> pays only when members' distinct solves are *reproducible*; the lever for a marginal problem like
> d7 p2 is more samples or a stronger model, not a second same-tier model.

## What stays unchanged

d5 p2 and d6 p2 remain uncracked by *every* 16 GB model/config tried — the efficiency-bound ceiling
holds. Those still need a stronger model (the m2max-32 / 30B+ runs) or a genuine reasoning step.

## Reproduce

```
venv/bin/python experiment.py --problems 2024:4-7 --trials 1 \
  --config "name=gemma4-samp3,models=gemma4:12b,temperature=0.7,samples_per_model=3,enable_thinking=false"

# the ensemble follow-up this finding motivated (models list is PIPE-separated, not comma):
venv/bin/python experiment.py --problems 2024:4-7 --trials 1 \
  --config "name=ensemble-samp3,models=gemma4:12b|qwen3.5:9b,temperature=0.7,samples_per_model=3,enable_thinking=false"
```
