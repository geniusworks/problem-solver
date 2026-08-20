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
| **m2max-32** | Apple M2 Max | 32 GB | 12 | 26.6.1 (25G76) | **0.32.14** (was 0.32.11 until 2026-08-16) | ~dense-30B / 30B-MoE Q4 — `qwen2.5-coder:32b` (19 GB), `qwen3-coder:30b` (18 GB), `qwen3.8:27b` (17 GB), all 100% GPU | bring-up 2026-08-15 (`m2max-handoff.md` §3); Python 3.14; cold learning DB. **The 4/8 and 6/8 rows below ran on 0.32.11**; upgraded to pull `qwen3.8:27b`, which 0.32.11 refuses. Upgrade verified behaviour-neutral: 6/6 on a 3-trial control (`ollama-0.32.14-runtime-check.md`) |

## Which models fit each machine (measured)

**m1-16 — fits & works** (Q4_K_M unless noted): `qwen2.5-coder:7b` (4.7 GB), `qwen3.5:9b` (6.6 GB),
`gemma4:12b` (7.6 GB), `phi4` (9.1 GB, tight), plus the small early-pool coders (`deepseek-coder:6.7b`,
`llama3.1:8b`).

**m1-16 — does NOT work** (swaps / incompatible; removed): `qwen2.5-coder:32b` (19.9 GB, swaps),
`qwq:32b` (19.9 GB, swaps), `llama3.3:70b` (42.5 GB, swaps), `qwen3-coder-next` (80B MoE, 51.7 GB,
swaps), `deepseek-r1:14b` (9 GB — *fits* but reasoning-native: ignores `think=false`, over-reasons,
inline `<think>` format incompatible with the pipeline). **These are the models to try on m2max-32.**

## Results (machine × model × config → solve rate)

> **Fingerprint note (2026-08-20):** adding the `efficiency_feedback` field to `SolverConfig`
> changed every config hash — the k3 settings recorded as `bb22870d2a6d` in earlier findings now
> hash to `ea658112193a`. Nothing about those runs changed: `efficiency_feedback=False` is exactly
> the behaviour they had, so they remain valid baselines. Only the hash moved. Fingerprints identify
> a *config space*, and that space genuinely grew.

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
| **m2max-32** | **qwen3-coder:30b** (MoE) | **tk-off samp3** | d4–7 | 1 | **6/8** | **75%** | `m2max-qwen3coder30b-d4-7.md` |
| **m2max-32** | **qwen3.8:27b** (generalist)† | **tk-off samp3** | d4–7 | 1 | **8/8** | **100%** | `m2max-qwen38-27b-d4-7.md` |
| **m2max-32** | **qwen3.8:27b** | tk-off **samp1** | **2025** d1–12 | 1 | **16/23** | **70%** | `generality-2025-scan.md` |
| **m2max-32** | **qwen3.8:27b** | tk-off **samp1** | **2025** band d2/4/9/10/11 | 3 | 14/30 | 47% | `band-2025-classification.md` |
| **m2max-32** | **qwen3.8:27b** | tk-off **samp3** | **2025** d9/d11 | 3 | **9/12** | **75%** | `passk-replication-2025.md` |
| **m2max-32** | **qwen3.8:27b** | tk-off samp3 **temp 1.0** | 2024 d15 + 2025 d9 | 3 | 5/12 | 42% | `temperature-diversity-negative.md` |

† ran on ollama **0.32.14**; the two rows above ran on 0.32.11. Upgrade verified behaviour-neutral
(6/6 on a 3-trial control, `ollama-0.32.14-runtime-check.md`).

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
- **`qwen3-coder:30b` (MoE) is the project's best result: 6/8 (75%)** — the first capability gain any
  hardware or model change has bought (`m2max-qwen3coder30b-d4-7.md`). It **cracked d5 p2, which no
  model or config had ever solved** (+1 ledger entry, now 13), plus d4 p2 and d7 p2 that the dense
  32B missed — in **39 min vs the 32B's 2h12m**.
- **Generation beats size, under a controlled comparison.** Same machine, runtime, config, problem
  set and day: the *smaller* 18 GB MoE scored 6/8 where the 19 GB dense 2024-generation model scored
  4/8, at 3.4× less wall-clock. Read "model capability" as *generation*, not parameter count.
- **"d5 p2 / d6 p2 are efficiency-bound" is retired.** The winning d5 p2 solution is a Kahn's-
  algorithm topological sort — a *better algorithm*, not a faster one. d6 p2 is now the only
  uncracked problem on the set, and even it failed via immediate `TypeError`s (6/6), not timeouts.
- **Failure style differs by model and it matters:** the dense 32B produced 27 confidently-wrong
  answers vs 5 errors; the MoE produced 4 wrong vs 11 crashes. For a proposer–verifier loop, crashes
  are the cheaper failure — detectable, and they carry an actionable traceback into repair.
- **Cross-model parsing trap:** day 5's two-section input (`a|b` rules, blank line, `1,2,3` updates)
  broke *both* models — the 32B on `'93|48'` (7/7 attempts, d5 p2), the MoE on `'75,47,61,53,29'`
  (3/4 attempts, d5 p1). Model-independent, and attackable by prompt/harness — a real orchestration
  lever rather than a capability wall.
- **`qwen3.8:27b` swept the set 8/8 (100%) — d4–7 is now retired as a capability instrument**
  (`m2max-qwen38-27b-d4-7.md`). It cracked **d6 p2, the last problem nothing had ever solved**
  (ledger now 14). Per-attempt it is in a different league: **20/24 = 83%** of its candidates verify,
  against the MoE's 45% and the dense 32B's 22%.
- **The generation ladder is monotonic, and runs backwards to size:** 19 GB dense 2024 specialist
  4/8 → 18 GB MoE newer specialist 6/8 → **17 GB dense 2026 *generalist* 8/8**. The winner is the
  smallest and is not a coder, so the effect is general model quality, not code specialization.
- **Strongest pass@k evidence to date:** attempt ordering gives **pass@1 = 6/8, pass@3 = 8/8**, and
  the two problems sampling bought were **d5 p2 and d6 p2 — the two hardest on the set**. Easy
  problems solved 3/3, where extra draws add nothing. Exactly the predicted shape, now replicated
  across two models and two architectures. Still not the controlled A/B.
- **Cost caveat:** Qwen3.8 is the *slowest* (2h 40m vs the MoE's 39 m). Best capability, worst
  wall-clock; the MoE remains the efficient choice per unit compute.
- **THE FINDINGS GENERALISE — first out-of-sample year.** `qwen3.8:27b` on **AoC 2025 d1–12**
  (never measured) scored **16/23 (70%)**, adding **16 verified solutions → ledger 41**
  (`generality-2025-scan.md`). A real frontier exists out of sample; the **Part 1/Part 2 cliff
  recurs** (83% vs 55%, six of seven misses are Part 2s); and **day 9 fell in both years**, both
  times by computing wrong answers rather than crashing.
- **THE CENTRAL CLAIM REPLICATES OUT OF SAMPLE.** k1→k3 on the 2025 band: **d9 p1 25%→100%** and
  **d11 p2 33%→100%**, while the wall (d9 p2) held at 0 and the control (d11 p1) stayed 100%
  (`passk-replication-2025.md`). Stronger than a 2024 repeat because **2025 was the unfavourable
  venue** — its frontier is bimodal (4 reliable / 2 sometimes / 4 walls vs 2024's 5-of-8
  near-misses), flagged in advance as working against sampling. It replicated anyway.
- **A standing boundary, now with one member per year:** 2024 d15 p2 (**0/11**) and 2025 d9 p2
  (**0/10**) resist every configuration tried — k ∈ {1,3}, repair ∈ {0,2}, temperature ∈ {0.7,1.0}.
- **Temperature is NOT the lever (negative result).** 0.7 → 1.0 at k3 moved neither wall and slightly
  hurt a working problem: **6/12 → 5/12** (`temperature-diversity-negative.md`). Parameter-level
  diversity perturbs tokens within an approach; these failures appear to need **strategy-level**
  diversity (prompt for a different algorithm, or a different model) — untested.
  **Caveat: 70% vs 2024's 56% is set composition, not a year difference** — 2025 d1–12 includes the
  easy early days, 2024 d8–15 does not. The *structure* transfers; the rate is not comparable.
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
