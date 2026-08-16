# Cross-machine benchmark — AoC solve rates by model

The durable, committed record of what this project has measured, **keyed by machine**, so results
from different hardware compare apples-to-apples. The raw per-run JSONs live in `dev/experiments/`
(gitignored); the numbers below are the source of truth. Each row is one experiment run and links to
its full write-up in `dev/progress/`.

**How to add a machine:** fill in a row in *Machines*, run the reproduce commands (bottom), and append
result rows tagged with the machine `id`. Keep config columns identical across machines so a row on
`m2max-32` lines up with the same row on `m1-16`.

## Machines

| id | chip | RAM | cores | macOS | ollama | usable for models | notes |
|----|------|-----|-------|-------|--------|-------------------|-------|
| **m1-16** | Apple M1 | 16 GB | 8 | 26.5.2 (25F84) | 0.32.0 | ~dense-14B Q4 (~10 GB); ~10–11 GB usable after macOS | all runs below unless noted |
| **m2max-32** | Apple M2 Max | 32 GB | 12 | 26.6.1 (25G76) | 0.32.11 | ~dense-30B / 30B-MoE Q4 — `qwen2.5-coder:32b` (19 GB) and `qwen3-coder:30b` (18 GB) both resident, 100% GPU | bring-up 2026-08-15 (`m2max-handoff.md` §3); Python 3.14; cold learning DB. **ollama 0.32.11 cannot pull `qwen3.8:27b`** — needs a newer runtime |

## Which models fit each machine (measured)

**m1-16 — fits & works** (Q4_K_M unless noted): `qwen2.5-coder:7b` (4.7 GB), `qwen3.5:9b` (6.6 GB),
`gemma4:12b` (7.6 GB), `phi4` (9.1 GB, tight), plus the small early-pool coders (`deepseek-coder:6.7b`,
`llama3.1:8b`).

**m1-16 — does NOT work** (swaps / incompatible; removed): `qwen2.5-coder:32b` (19.9 GB, swaps),
`qwq:32b` (19.9 GB, swaps), `llama3.3:70b` (42.5 GB, swaps), `qwen3-coder-next` (80B MoE, 51.7 GB,
swaps), `deepseek-r1:14b` (9 GB — *fits* but reasoning-native: ignores `think=false`, over-reasons,
inline `<think>` format incompatible with the pipeline). **These are the models to try on m2max-32.**

## Results (machine × model × config → solve rate)

All 2024, temperature 0.7 unless noted; "samp" = `samples_per_model`; "tk-off" = `enable_thinking=false`.

| machine | model (Q4_K_M) | config | problem set | trials | solved | rate | source |
|---------|----------------|--------|-------------|--------|--------|------|--------|
| m1-16 | qwen2.5-coder:7b | default samp1 | d1–3 | 5 | 12/30 | 40% | `baseline-2024-d1-3.md` |
| m1-16 | qwen2.5-coder:7b | samp1 | d1–3 | 3 | 7/18 | 39% | `milestone-e-self-consistency.md` |
| m1-16 | qwen2.5-coder:7b | **samp3** | d1–3 | 3 | 11/18 | **61%** | `milestone-e-self-consistency.md` |
| m1-16 | qwen2.5-coder:7b | samp3 | d4–7 | 1 | 1/8 | 12% | `scale-2024-d4-7.md` |
| m1-16 | qwen2.5-coder:7b | samp3 | d8–12 | 1 | 2/10 | 20% | `benchmark-2024-d1-12.md` |
| m1-16 | qwen3.5:9b | tk-off samp1 | d1–7 | 1 | 6/14 | 43% | `reasoning-model-9b.md` |
| m1-16 | qwen3.5:9b | tk-off samp1 | d4–7 | 1 | 2/8 | 25% | `model-bakeoff-gemma4-vs-9b.md` |
| m1-16 | qwen3.5:9b | **tk-off samp3** | d4–7 | 1 | 5/8 | **62%** | `9b-confirmation-d4-7.md` |
| m1-16 | gemma4:12b | tk-off samp1 | d4–7 | 1 | 5/8 | 62% | `model-bakeoff-gemma4-vs-9b.md` |
| m1-16 | gemma4:12b | **tk-off samp3** | d4–7 | 1 | 5/8 | **62%** | `gemma4-samp3-confirmation.md` |
| m1-16 | gemma4:12b + qwen3.5:9b | tk-off samp3 **ensemble** | d4–7 | 1 | 5/8 | 62% | `ensemble-samp3-d4-7.md` |
| **m2max-32** | **qwen2.5-coder:32b** | **tk-off samp3** | d4–7 | 1 | **4/8** | **50%** | `m2max-qwen25coder32b-d4-7.md` |

### Headline reads (m1-16)

- **Self-consistency is the biggest orchestration win:** samp1 → samp3 on d1–3 lifts 39% → 61%.
- **Model matters more than the original baseline assumed:** on the hard d4–7 days, `qwen2.5-coder:7b`
  gets 1/8; both `qwen3.5:9b` and `gemma4:12b` reach 5/8. The "7B is too weak past the easy problems"
  was measured, not assumed.
- **gemma4:12b and qwen3.5:9b are co-leaders at 5/8 — a tie, not a gemma4 win** (`gemma4-samp3-confirmation.md`).
  The deciding test (gemma4 samp3 vs the 9b's 5/8) came back **5/8**: gemma4 matched but did not beat
  the 9b, and did not crack d5 p2 / d6 p2. gemma4's edge is *per-draw efficiency* (it reached 5/8 at
  samples=1), not a higher ceiling.
- **Ensemble tested — the 6/8 union did NOT hold** (`ensemble-samp3-d4-7.md`). A combined
  `gemma4:12b|qwen3.5:9b` samp3 run got **5/8**, same as gemma4 alone, at ~2.2× wall. Both models
  fully participated, but neither solved d7 p2 this run: the 9b's earlier d7 p2 "crack" was a
  low-probability draw, not a robust competency, so there was nothing stable for the ensemble to pool.
  Decorrelated-error ensembling pays only when members' distinct solves are *reproducible* — the lever
  for d7 p2 is more samples or a stronger model, not a second same-tier model.
- **Hard ceiling that no m1-16 model has cracked:** 2024 d5 p2 and d6 p2 (d6 p2 is Python-speed-bound
  even with a correct brute force). These are the natural first targets for a stronger model on
  m2max-32.

### Headline reads (m2max-32)

- **The 30B tier did NOT beat 16 GB — `qwen2.5-coder:32b` samp3 got 4/8, *below* the M1's 5/8**
  (`m2max-qwen25coder32b-d4-7.md`). It solved every Part 1 and no Part 2, cracking neither d5 p2 nor
  d6 p2. Its solved set is exactly the M1 leaders' set minus **d4 p2**, where it produced nine
  wrong answers with no convergence — a problem `qwen3.5:9b` (6.6 GB) solves.
- **Size within a generation is not the lever.** A 32B code-specialist from late 2024 loses to 9B/12B
  models from a newer generation on the same set. What lifted 1/8 → 5/8 on the M1 was newer models,
  not bigger ones; scaling the old generation up does not reproduce it.
- **The "efficiency-bound" story needs qualifying.** For this model, d5 p2 failed on **input
  parsing** in all 7 attempts (`invalid literal for int(): '93|48'`) — it never reached an
  algorithm, let alone a slow one. Two of five d7 p2 attempts died the same way. Only d6 p2 still
  fits the timeout narrative.
- **Generation-vs-size is the sharper follow-up:** `qwen3.8:27b` (2026-08-14, 18 GB) is smaller than
  the 32B but two generations newer. **Blocked:** ollama 0.32.11 refuses the pull, needing a runtime
  upgrade that would change a recorded machine variable mid-series.
- **12 verified solutions** recorded (`solutions/README.md`), oracle-clean throughout.

## What to run on m2max-32 (the next machine)

> **Running on the M2 Max? Start with `dev/benchmarks/m2max-handoff.md`** — full operational handoff
> (setup, exact commands, the pass@k thesis-test design, and the gotchas). The summary below stands.


The point of 32 GB is the model tier that swamps 16 GB. Suggested first runs, all at samp3, d4–7
(directly comparable to the m1-16 rows above):

1. `qwen2.5-coder:32b` (Q4, ~20 GB) — the code-specialized 32B the M1 couldn't hold.
2. `qwen3-coder:30b` (MoE, ~18 GB — the tag for Qwen3-Coder-30B-A3B; confirmed to pull fine,
   2026-08-15) — the current-gen local coder leader that needs the headroom.
3. Re-run `gemma4:12b` / `qwen3.5:9b` samp3 there too, to separate *machine speed* from *model
   capability* (same model, more RAM → faster, same solve rate expected).

The decisive question for m2max-32: does a bigger model crack **d5 p2 / d6 p2**, which every 16 GB
model failed?

## Reproduce (same on any machine)

```
# self-consistency A/B (d1-3)
venv/bin/python experiment.py --problems 2024:1-3 --trials 3 \
  --config "name=samp1,models=<MODEL>,temperature=0.7,samples_per_model=1" \
  --config "name=samp3,models=<MODEL>,temperature=0.7,samples_per_model=3"

# hard-days capability run (d4-7, the cross-machine comparison set)
venv/bin/python experiment.py --problems 2024:4-7 --trials 1 \
  --config "name=<MODEL>-samp3,models=<MODEL>,temperature=0.7,samples_per_model=3,enable_thinking=false"

# verify every recorded solution against the oracle
venv/bin/python dev/verify_solutions.py
```

Add `enable_thinking=false` for reasoning models (qwen3.5, etc.) or they over-reason and never emit
code. Record wall clock alongside solve rate — on a faster machine the same model should keep its
solve rate but run quicker; a *capability* gain shows up only as more problems solved.
