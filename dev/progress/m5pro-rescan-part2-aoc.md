# Rescan of the reference's failing Part 2s under the site's conditions: 13/71 → 32/40

Step (d) of the re-earn plan (`PLAN.md`, M5 Pro step 4): every Part 2 that `qwen3.8:27b` had
failed or only sometimes solved, re-run under the new defaults. Those Part 2s were all posed
without the Part 1 statement (`part2-prompt-omits-part1.md`), so their record measured the prompt
as much as the model.

`m5pro-aoc-rescan-p2-k1`, fingerprint `1ac712678732`, `samples_per_model=1`, 3 trials, each Part
Two after its Part One in the same trial; 2026-11-01, GPU free, 20,798 s
(`dev/experiments/20261101T031131Z_m5pro-aoc-rescan-p2-k1_1ac712678732.json`).

```
venv/bin/python experiment.py \
  --problems 2024:6.2,2024:9.2,2024:11.2,2024:13.2,2024:14.2,2024:17.2,2024:18.2,2024:20.2,2024:21.2,2024:22.2,2024:24.2,2025:2.2,2025:4.2,2025:10.2,2025:11.2 \
  --trials 3 \
  --config "name=m5pro-aoc-rescan-p2-k1,samples_per_model=1,models=qwen3.8:27b,temperature=0.7,enable_thinking=false,enable_fallback_models=false"
```

**Scope.** Every Part 2 with at least one reference-model failure in `dev/experiments/`, minus
those already re-run (2024 d15, d16, d19; 2025 d9) and the two days with no Part 2 (2024 d25,
2025 d12). Part 2s failed only by other models (2024 d1–5, d7) are not in it.

## Result

"Legacy" is every reference-model trial on record for that Part 2, at any k.

| Part 2 | legacy | new defaults, k1 | Part 1, same trials | now |
|---|---|---|---|---|
| 2024 d6 | 4/5 | 3/3 | 3/3 | reliable |
| 2024 d9 | 0/4 | 2/3 | 3/3 | sometimes |
| 2024 d11 | 0/4 | 3/3 | 3/3 | reliable |
| 2024 d13 | 5/14 | 3/3 | 3/3 | reliable |
| 2024 d14 | 0/1 | 2/3 | 3/3 | sometimes |
| 2024 d17 | 0/4 | 1/3 | 3/3 | sometimes |
| 2024 d18 | 0/4 | 3/3 | 3/3 | reliable |
| 2024 d20 | 0/4 | 3/3 | 3/3 | reliable |
| 2024 d21 | 0/4 | not reached ×3 | **0/3** | Part 1 wall |
| 2024 d22 | 0/4 | 3/3 | 3/3 | reliable |
| 2024 d24 | 0/4 | 0/1 (2 not reached) | 1/3 | Part 1 sometimes |
| 2025 d2 | 0/4 | 3/3 | 3/3 | reliable |
| 2025 d4 | 0/4 | 2/3 | 3/3 | sometimes |
| 2025 d10 | 0/4 | 1/3 | 3/3 | sometimes |
| 2025 d11 | 4/7 | 3/3 | 3/3 | reliable |
| **total** | **13/71** | **32/40 reached** | 40/45 | |

- **The Part 2 record was mostly the prompt.** 13 of 71 legacy trials against 32 of 40 reached
  now. Eight of the fifteen are solved every time; ten of the twelve that the reference had
  never solved now have been.
- **Every Part 2 solve was a first draft.** No repair was accepted.
- **Ledger 56 → 66, 0 wrong** (`dev/verify_solutions.py`): ten first verified Part 2s (2024 d9,
  d11, d14, d17, d18, d20, d22; 2025 d2, d4, d10).
- **The surviving failure is a Part 1.** 2024 d21 p1 is 0/3 here and 0/4 on record, with wrong
  answers both too high and too low, each failing the example test. Part 1 prompts were not
  affected by the defect, so this wall stands as measured. *(2026-11-06: it is the reference's wall, not
  the task's; `muse-glimmer:30b` solved d21 p1 and p2 in 1 of 3 trials,
  `arm3-precheck-muse-glimmer-30b.md`.)* 2024 d24 p1 is 1/3; its one Part 2
  attempt timed out twice and then gave a wrong answer.

### How the "sometimes" cells fail

| cell | failed trials | what happened |
|---|---|---|
| 2024 d9 p2 | 1 | draft crashed on the example; repair returned it unchanged |
| 2024 d14 p2 | 1 | too low; repair unchanged (this part has no example result) |
| 2024 d17 p2 | 2 | each: a too-low draft that failed the example, then two repairs that passed it and timed out |
| 2025 d4 p2 | 1 | too high, failed the example; repair unchanged |
| 2025 d10 p2 | 2 | one: three attempts passed the example and timed out; one: three passed it and crashed on the full input |

Speed is the common limit: 2024 d17 and 2025 d10 reach a program that passes the example and
then run out of the 60 s timeout, as 2025 d9 p2 does (`part2-prompt-omits-part1.md`).

## What this changes

- **The Part 1/Part 2 cliff is not established.** Under the site's conditions the reference
  solves 32 of 40 of its hardest Part 2s, against 40 of 45 of their Part 1s.
- **The band for k1-vs-k3 (step (e))**, under the new defaults: 2024 d9 p2, d14 p2, d17 p2,
  d24 p1; 2025 d4 p2, d10 p2; and 2025 d9 p2 (3 of 9 first drafts at k3).
- **Arm-3 entry cells (step (f))**, cells the reference solved at most 1 of 3: 2024 d21 p1 (0/3),
  d24 p1 (1/3), d17 p2 (1/3); 2025 d10 p2 (1/3). Three trials is thin for "reliably misses";
  the k3 runs of step (e) firm these up before a candidate is measured against them.
- **Not measured here:** Part 2s failed only by smaller models, and Part 1s other than those
  run as prerequisites.
