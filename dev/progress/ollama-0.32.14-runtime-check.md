# Runtime check: ollama 0.32.11 → 0.32.14 is clean (and a lesson about smoke tests)

**Verdict: the upgrade did not change generation behaviour.** `qwen2.5-coder:32b` on 2024 d1,
`--trials 3`, scored **6/6 (100%)** on 0.32.14 — every problem solved on every trial, wall-clock in
the same band as before the upgrade (157–198 s/problem vs 170.6 s pre-upgrade).

The upgrade was needed to pull `qwen3.8:27b`, which 0.32.11 refuses ("Please download the latest
version"). Since the runtime is a recorded machine variable in
`dev/benchmarks/cross-machine-results.md`, it was checked rather than assumed.

## The scare, and why it was wrong

The first check was a `--trials 1` smoke — the same one that passed 2/2 before the upgrade. After
the upgrade it came back **0/2**:

| config `0120a2756ce8` | 0.32.11 | 0.32.14, run 1 | 0.32.14, `--trials 3` |
|---|---|---|---|
| d1 p1 | solved (170.6 s) | **wrong** ×3 → `133294` | **3/3 solved** |
| d1 p2 | solved (191.3 s) | **wrong** ×3 → `0`, `0`, `87471881` | **3/3 solved** |

0/2 on problems that 7B models solve (d1 p1 was originally solved by `deepseek-coder:6.7b`, d1 p2 by
`qwen2.5-coder:7b`) looked like an obvious regression, straight after an obvious cause. It wasn't.
Repeating at `--trials 3` produced 6/6.

**The lesson — which this project had already learned and I failed to apply:** a `--trials 1` check
on a non-deterministic pipeline is not evidence. `baseline-2024-d1-3.md` established at the very
start that **4 of 6 problems flip between solved and unsolved across byte-identical configs**; that
is precisely why `--trials N` was built (Milestone A). Experiments were held to that standard while
*smoke tests* were quietly exempted — and the exempted instrument promptly manufactured a false
regression against a real, causally-plausible suspect. A one-shot pre-run check will eventually send
you chasing a phantom, or (worse, and undetectable) bless a run that happened to get lucky.

**Adopted:** pre-run smoke checks use `--trials 3`. One pass is a syntax check on the plumbing, not
a measurement.

## Second finding: token accounting is stale across repair attempts

Visible in the failed run's attempt records, and independent of the runtime question:

```
2024_day01_part2  attempts: ans='0' ans='0' ans='87471881'
                  tokens:   (4283,876) (4283,876) (4283,876)
```

Three attempts reporting **identical input and output token counts while producing different
answers**. Different generations cannot have identical token counts, so `OllamaProvider`'s
`last_token_usage` is being read stale — carried over from the first call rather than refreshed per
generation — and `_record_attempt` copies it onto every repair attempt.

Why it matters beyond tidiness: **arm 2 of the project's central thesis is an economic claim** —
"many cheap draws plus a verifier beat one expensive pass at equal or lower cost" (README, *Does
orchestrated voting scale?*). That claim is measured in tokens. Any pass@k cost accounting that
includes repair attempts is currently wrong, and wrong in the direction that *understates* the cost
of repair-heavy runs. Wall-clock is unaffected and remains trustworthy.

This was also invisible before now: the pre-upgrade smoke solved on the first attempt, so it had
exactly one attempt per problem and nothing to compare.

**Not yet fixed** — logged here so the next pass@k economics analysis doesn't quietly inherit it.

## Machine record

`m2max-32` now runs **ollama 0.32.14** (upgraded 2026-08-16 from 0.32.11; the old bundle is kept for
rollback). All results recorded before this date — `qwen2.5-coder:32b` 4/8 and `qwen3-coder:30b`
6/8 — ran on **0.32.11** and are unaffected. Given 6/6 on the control, cross-runtime comparison is
reasonable, with the caveat that a 2-problem control bounds gross regressions only; it cannot
exclude a small distributional shift.

## Reproduce

```
venv/bin/python experiment.py --problems 2024:1 --trials 3 \
  --config "name=runtimecheck,models=qwen2.5-coder:32b,temperature=0.7,samples_per_model=1,enable_thinking=false"
```
