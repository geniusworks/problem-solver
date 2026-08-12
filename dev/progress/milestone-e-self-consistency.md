# Milestone E A/B — self-consistency sampling (2024 d1–3, qwen2.5-coder:7b)

Run 2026-08-12, `milestone-e-self-consistency` branch. Clean isolation: two configs, both at
`temperature=0.7` with the hardened prompt, differing **only** in `samples_per_model` (1 vs 3),
3 trials each. Artifacts (gitignored): `dev/experiments/*samp1*.json`, `*samp3*.json`.

## The result — the first orchestration win with evidence

```
config                solved  rate  any / every (of 6)   wall(s)
samp1 (1 sample)      7/18    39%   4 / 0                3518
samp3 (3 samples)     11/18   61%   4 / 3                8474
```

**Solve rate 39% → 61% (+22 pts). Reliability 0 → 3 of 6 problems solved on *every* trial.**

Per-problem, the effect is exactly what the variance analysis predicted:

| problem     | samp1 (1×)              | samp3 (3×)          |
|-------------|-------------------------|---------------------|
| 2024 d1 p1  | 2/3 (flipped)           | **3/3 (100%)**      |
| 2024 d1 p2  | 1/3                     | 2/3                 |
| 2024 d2 p1  | 2/3 (flipped)           | **3/3 (100%)**      |
| 2024 d2 p2  | 0/3                     | 0/3                 |
| 2024 d3 p1  | 2/3 (flipped)           | **3/3 (100%)**      |
| 2024 d3 p2  | 0/3                     | 0/3                 |

The three flipping problems all became fully reliable: three independent draws at ~40–67%
per-draw success turn a coin-flip into a near-certain hit. **This is the direct cure for the
run-to-run variance the baseline measured.**

Equally important, it **separates variance-limited from capability-limited problems**. d2 p2 and
d3 p2 stay 0/3 under 3× the samples — more shots don't help because the model never produces a
correct candidate for them. The baseline flagged these two as "a reachability ceiling to watch";
this answers it: they are a genuine capability ceiling, not variance. That is where a stronger
model or a different technique is needed, not more sampling.

Zero regression: 0 wrong, 0 overfit, 0 unverified in both arms.

## Mechanism note (oracle vs no-oracle)

On problems with a cached accepted answer, self-consistency here means *more shots, accept any
draw that matches the oracle* — not a majority vote (the oracle decides). The classic majority
vote over the executed answer matters for **unseen** problems with no oracle; that is the
answer-based-consensus follow-up, and the candidate-pool / executed-answer plumbing this PR adds is
its foundation.

## Cost

samp3 spent 2.4× the wall clock (8474 s vs 3518 s) and ~2× the tokens (367k vs 183k) for the +22
points — 3× generation, minus the runs that solve early. Reliability is bought with compute; the
`samples_per_model` knob makes that trade explicit and sweepable.

## Not measured here: the prompt hardening

Both arms carry the hardened `solve()`-contract prompt, so this A/B says **nothing** about it — the
"no solve()" error count was 6 in both. It is a reasonable, low-risk change kept for the
convention-following 30%, but its effect is unmeasured and is **not** claimed as a win. A clean
old-prompt-vs-new A/B would be needed to justify it on evidence.

## Reproduce

```
venv/bin/python experiment.py --problems 2024:1-3 --trials 3 \
  --config "name=samp1,models=qwen2.5-coder:7b,temperature=0.7,samples_per_model=1" \
  --config "name=samp3,models=qwen2.5-coder:7b,temperature=0.7,samples_per_model=3"
```
