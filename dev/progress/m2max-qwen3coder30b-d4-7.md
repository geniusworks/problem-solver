# m2max-32: `qwen3-coder:30b` samp3 on 2024 d4–7 — **6/8, the first capability gain**

**Headline: 6/8 (75%) — the best result this project has recorded, and the first time a hardware or
model change actually bought new problems.** It beats the M1's 5/8 ceiling, cracks **d5 p2 — which
no model or config had ever solved** — and does it in **39 minutes against the dense 32B's 2h12m**.

The model that did it is *smaller* than the one that failed yesterday: `qwen3-coder:30b` is an 18 GB
MoE (~3B active parameters/token); `qwen2.5-coder:32b` is 19 GB dense and scored 4/8.

- **Config:** `models=qwen3-coder:30b, temperature=0.7, samples_per_model=3, enable_thinking=false`
  (fingerprint `0a52ac2e6977`), 1 trial, 2024 d4–7.
- **Machine:** `m2max-32` (M2 Max, 32 GB, macOS 26.6.1, **ollama 0.32.11**, Python 3.14) — same
  runtime as the 32B run, so the two are directly comparable.
- **Cost:** 2,346 s wall (39 m), 29 candidate attempts, 261,304 tokens.
- **Run:** `dev/experiments/20260816T160545Z_qwen3coder30b-samp3_0a52ac2e6977.json` (gitignored).
- **Ledger:** **+1 — the first new verified solution since the M1**, `2024 day 5 part 2 = 5502`.
  `verify_solutions` is **13 correct, 0 wrong**. 0 wrong / 0 unverified / 0 overfit recorded.

## The result

| problem | `qwen3-coder:30b` (MoE, 18 GB) | `qwen2.5-coder:32b` (dense, 19 GB) | m1-16 best |
|---------|-------------------------------|-----------------------------------|-----------|
| d4 p1 | **OK** (135 s) | OK (623 s) | OK |
| d4 p2 | **OK** 1822 (130 s) | **none** (1057 s, 9 wrong) | OK |
| d5 p1 | **none** (243 s) | OK (902 s) | OK |
| d5 p2 | **OK 5502 (1070 s) — FIRST EVER** | none (599 s) | none |
| d6 p1 | **OK** (200 s) | OK (992 s) | OK |
| d6 p2 | **none** (252 s) | none (2041 s) | none |
| d7 p1 | **OK** (138 s) | OK (712 s) | OK |
| d7 p2 | **OK** (178 s) | none (993 s) | none* |
| **total** | **6/8 (75%)** | 4/8 (50%) | 5/8 (62%) |
| **wall** | **2,346 s** | 7,918 s | ~14,000–20,000 s |

\* d7 p2 was solved once on the M1 by `qwen3.5:9b` and once by gemma4 at samp1, but never
reproducibly — `ensemble-samp3-d4-7.md` records both leaders missing it.

## Four findings

### 1. Generation beats size, decisively

Yesterday's 32B run suggested it; this confirms it under a controlled comparison — same machine,
same runtime, same config, same problem set, same day. The newer, *smaller*, cheaper model solved
**+2 problems** the dense 32B missed (d4 p2, d7 p2) plus one nothing had ever solved (d5 p2), at
**3.4× less wall-clock**. The project's claim that "past the easy problems the bottleneck is model
capability" survives, but "capability" must be read as *model generation*, not parameter count.

### 2. d5 p2 is cracked — and it was never really "efficiency-bound"

The M1 concluded d5 p2 and d6 p2 were algorithm-efficiency ceilings (`9b-timeout-investigation.md`).
The winning solution (`solutions/2024_day05_part2.py`) is a **Kahn's-algorithm topological sort** —
it doesn't beat a timeout, it uses a better algorithm. What was missing was never speed on a known
approach; it was *finding the right approach*. d6 p2 is now the only genuinely uncracked problem on
this set.

### 3. This model fails by crashing, not by being confidently wrong — and that is better

Attempt-level outcomes, versus the 32B on the identical set:

| | solved | wrong | error | no_candidate |
|---|---|---|---|---|
| `qwen3-coder:30b` | 13 | 4 | 11 | 1 |
| `qwen2.5-coder:32b` | 9 | **27** | 5 | 0 |

The dense 32B produced confidently wrong answers (27); the MoE produces code that crashes (11). For
a proposer–verifier pipeline this is a meaningful asymmetry: a crash is cheap to detect, carries an
actionable traceback into the repair prompt, and can never be mistaken for a solution. A plausible
wrong answer is the expensive failure. **d6 p2 illustrates it:** the 32B ground for 2,041 s into
execution timeouts and returned all-zeros; the MoE failed in 252 s with 6/6 immediate
`TypeError: unsupported operand type(s) for +: 'NoneType' and 'int'` — a structural code bug, not a
timeout. Same verdict, 8× cheaper, and far more diagnosable.

### 4. Day 5's input format is a systematic parsing trap — across models

The one problem this model missed that everything else solves is **d5 p1**, and it is **not** a
capability failure — the same model solved d5 p2 minutes later. Three of its four attempts died
parsing the input:

```
ValueError: invalid literal for int() with base 10: '75,47,61,53,29'
ValueError: list.index(x): x not in list
```

Pair that with the 32B, which failed **d5 p2** in all 7 attempts on
`invalid literal for int() with base 10: '93|48'`. Two different models, same day, both crashing on
the two-section input (`a|b` ordering rules, blank line, comma-separated updates). That is a
recurring, model-independent failure mode, and the first thing here that looks addressable by
**prompting or harness** rather than by a bigger model — a genuine orchestration lever, which is
what this project exists to find.

## Unplanned evidence for the central thesis (pass@k > pass@1)

Q2 was supposed to need its own experiment. This run supplied strong preliminary evidence anyway,
because `samples_per_model=3` plus repair means each problem got 3–4 draws, and the per-attempt
records show **which draw won**:

- **d4 p2** — solved by 1 of 3 attempts (2 wrong).
- **d5 p2** — solved by **1 of 4** attempts (1 wrong, 1 error, 1 no-candidate).

Both are the *hard* problems. At `samples_per_model=1` this run would most likely have scored
**4/8 rather than 6/8** — sampling plus verification bought two problems, and it bought them
precisely at the model's frontier, which is exactly the claim the README's "does orchestrated voting
scale?" section says is unproven. Easy problems, by contrast, solved 3/3 (d4 p1, d7 p1, d7 p2) —
voting adds nothing where the model is already reliable, as predicted.

**This is suggestive, not conclusive:** it is one trial, and the counterfactual ("samp1 would have
missed them") is inferred from which draw succeeded, not measured. The controlled samp1-vs-samp3 A/B
at `--trials 5` remains the real test — but the frontier band to run it on is now identified, and
this model has one (d4 p2, d5 p2) where the 32B was bimodal and had none.

## Collateral damage: the solve destroyed a regression fixture

Solving d5 p2 **permanently destroyed the test fixture for d5 p2's old hardcoded stub.** The stub
lived only at `years/2024/day05/2024_day05_part2.py` — gitignored, never committed — and that is
exactly where the solver writes its canonical solution file. `test_hardcoded_stubs_are_rejected`
had been reading its failure data from that path, so the successful run overwrote the artifact the
test existed to pin.

Nothing else is affected (the oracle, ledger, and all other fixtures are intact) and the loss is
recorded rather than papered over:

- The surviving overfit fixture (2024 d3 p2) was moved to **`tests/fixtures/overfit/`** — committed,
  and outside any path the solver writes.
- The d5 p2 case was **removed, not reconstructed**: 186 → 185 tests. A hand-written stand-in would
  be a fabricated artifact, not the real pre-oracle failure, and this project does not manufacture
  its own evidence.
- `solutions/README.md` records what the stub did and that it is gone.

The general rule this cost us: **a test fixture must never live in a directory the solver can
write**, and `years/` is both solver-writable and gitignored, which made the loss unrecoverable.

## What this changes

- **Q1 is answered: yes, a stronger model cracks what 16 GB could not** — but the operative variable
  is generation, not size, and the win came from a model that is smaller *and* 3.4× cheaper to run.
- **d6 p2 stands alone** as the last uncracked problem on the set, and its failure mode has changed
  from "too slow" to "buggy code".
- **Q2 is now runnable and worth running:** `qwen3-coder:30b` has a real "sometimes" band on d4–7.
- **A new orchestration lever surfaced:** structured-input parsing (day-5 shaped) fails across
  models and is attackable in the prompt — testable through the harness like any other A/B.

## Reproduce

```
venv/bin/python experiment.py --problems 2024:4-7 --trials 1 \
  --config "name=qwen3coder30b-samp3,models=qwen3-coder:30b,temperature=0.7,samples_per_model=3,enable_thinking=false"
```
