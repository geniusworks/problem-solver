# Correction: 2024 d15 p2 is a ~12% problem, not a wall — and neither "wall" ever timed out

Three related errors, found 2026-08-20 while checking whether a new intervention could fire. They
propagated into `README.md`, `PLAN.md`, `checkpoint.md`, `cross-machine-results.md`,
`temperature-diversity-negative.md` and `passk-replication-2025.md`, and are corrected in place
there with a pointer here.

## Error 1 — "2024 d15 p2 has never solved once" is false. It has solved twice.

The problem-level record across **every** recorded run:

```
2024_day15_part2 — SOLVED 2 of 16 problem-trials  (~12%)
    scan-qwen38-samp1     no_candidate
    band-classify-samp1   SOLVED          <-- this is how it entered the ledger
    band-classify-samp1   no_candidate
    band-classify-samp1   no_candidate
    k1                    SOLVED
    k1                    no_candidate
    k1                    no_candidate
    k3 / parallel3 / temp10-k3   no_candidate  (9 trials)
```

**What went wrong:** the k3-style arms (k3, parallel3, temp10-k3) all returned 0/3, and I summed
*those* into "0/9 … 0/11" and then restated it as "never solved once". The samp1 arms, where it did
solve, were left out of the count. The contradiction was visible the whole time — **d15 p2 is in the
ledger**, which it could only be by solving.

**Correct characterisation:** a **very-low-rate "sometimes"** (~12% per problem-trial), not a wall.

**2025 d9 p2 is genuinely 0/10** and remains a wall on current evidence. So the "standing boundary,
one member per year" framing was **half right**: there is one confirmed wall, not two.

## Error 2 — neither problem has ever timed out

Across every recorded attempt:

| problem | wrong | error | no_candidate | solved | **attempts whose error mentions "timed out"** |
|---|---|---|---|---|---|
| 2024 d15 p2 | 42 | 15 | 9 | 2 | **0** |
| 2025 d9 p2 | 38 | 26 | 0 | 0 | **0** |

They fail by **computing wrong answers** and by **crashing** — never by exceeding the execution
timeout.

## Error 3 — "execution-bound" was inferred from the wrong number

`passk-ab-d13-d15.md` called d15 p2 "the most execution-bound problem in the band (3,337–3,677 s per
k3 trial)". That wall-clock is **generation plus repair** (3 samples × ~1,000 s each, plus repair
rounds), not execution. Given Error 2, no attempt ever hit an execution timeout. **Long wall-clock
was read as slow *code* when it was slow *generation*.**

## Consequences

1. **The efficiency-feedback intervention could never fire on these problems.** It triggers only on
   timeouts (`shared/solver.py`, `_is_timeout_error`). It was built and launched against two
   benchmarks that never time out. The A/B was stopped once this was found; it would have measured
   an inert flag and produced a false negative. The code and its ten tests are correct — they are
   aimed at a failure mode these problems do not exhibit.
2. **The temperature negative result is weaker than stated, in one direction.** Failing to solve a
   **~12%** problem in 3 trials is unremarkable (p ≈ 0.68 of missing all three by chance), where
   failing to solve a *true wall* would have been meaningful. The headline of that finding —
   6/12 → 5/12, no gain, and one working problem slightly worse — **stands**; but d15 p2's 0/3 there
   is weak evidence, and only 2025 d9 p2's 0/3 speaks to a genuine wall.
3. **"Sampling multiplies draws, not diversity" is now supported by one problem, not two.** It may
   still be right; it rests on 2025 d9 p2 alone.

## Why it survived

The counts were accumulated narratively across many messages ("now 0/8… now 0/11") rather than
recomputed from the run artifacts. Every individual arm's 0/3 was true; the running total silently
dropped the arms where the problem solved. **A tally maintained by addition in prose is not a
measurement.** The fix that found it — recomputing from every `dev/experiments/*.json` — takes
seconds and should precede any claim of the form "N/M across all configurations".

`dev/analyze_passk.py` reads the same artifacts and could be extended to print per-problem
cross-run records; that would make this class of error structurally hard to repeat.

## Standing facts after correction

- **2024 d15 p2** — ~12% "sometimes" (2/16). Fails by wrong answer (42) and crash (15). Never times out.
- **2025 d9 p2** — genuine wall, 0/10. Fails by wrong answer (38) and crash (26). Never times out.
- **Neither is execution-bound** on the available evidence.
