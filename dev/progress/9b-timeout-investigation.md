# Timeout is not the lever: the 9b's hard Part 2s are a real capability limit

Follow-up to the 9b-confirmation finding, testing whether the dominant failure — 9 execution timeouts
among the 14 no_candidates — was *correct-but-slow* (a bigger timeout recovers it) or *genuinely too
slow*. Re-ran the three timeout-bound Part 2s (2024 d4 p2, d5 p2, d6 p2) with the 9b at samples=3 and
a **300 s** execution timeout (5× the 60 s default), `--include-replay`.

## Verdict: 0/3, even at 300 s

```
problem   outcome        what changed at 300s
d4 p2     no_candidate   still times out (2 of 5 attempts) -- genuinely too slow
d5 p2     no_candidate   no longer times out; now COMPLETES but is WRONG (6 wrong) -- wrong algorithm
d6 p2     no_candidate   still times out (2 of 3) -- genuinely too slow
```

A 5× timeout recovered nothing. So the timeouts were never a harness/config problem:

- **d4 p2, d6 p2** run past 300 s — the 9b writes brute-force that is too slow in pure Python for the
  full input regardless of the limit.
- **d5 p2** was never really timeout-bound; with more time its code runs and produces the wrong
  answer. It's a reasoning error wearing a timeout costume at 60 s.

## What the code shows (d6 p2)

The captured d6 p2 candidate has the **right shape** — `simulate_with_obstacle`, `check_obstruction`,
a `visited` set for loop detection, a nested loop over candidate obstacle positions. The 9b *knows*
the intended approach. But its implementations are either too slow (the naive "place an obstacle at
every one of ~17k cells and re-simulate" is minutes of pure-Python work) or subtly buggy (the one
that finished was wrong). The efficient version — only test cells on the guard's original path — is
the reasoning step it doesn't reach.

## Conclusion — harness levers for the hard problems are exhausted

The cheap knobs are spent: extraction is robust, self-consistency handles variance, thinking-off
fixed the reasoning model, and now a 5× timeout changes nothing. **The remaining hard Part 2s (d4–6
p2) are a genuine algorithmic-capability limit of qwen3.5:9b** — right idea, wrong/too-slow code —
and at least d6 p2 is Python-speed-bound even with the correct brute force, so it needs a *smarter*
algorithm, not more time.

The levers that could still move these, in rough order of expected value:

1. **A stronger model** (bigger machine / remote endpoint) — the direct fix; the 9b has found its
   ceiling on the middle-day Part 2s.
2. **Algorithm-efficiency prompting** — an A/B nudging the model toward optimized approaches ("the
   full input is large; avoid brute force that re-simulates from scratch"). Cheap to try, but if the
   model can't *find* the optimization, prompting won't conjure it — low-confidence.
3. Accept the current state as the platform's demonstrated result on this hardware: **11 verified
   solutions, 5/8 of the hard d4–7 days, oracle-clean throughout.**

Minor harness note: timed-out attempts don't store their code even under `--include-replay` (the
timeout path skips replay capture) — a small gap worth closing if timeout diagnostics recur.

## Reproduce

```
venv/bin/python experiment.py --problems 2024:4.2,2024:5.2,2024:6.2 --trials 1 --include-replay \
  --config "name=9b-t300,models=qwen3.5:9b,temperature=0.7,samples_per_model=3,enable_thinking=false,execution_timeout=300"
```
