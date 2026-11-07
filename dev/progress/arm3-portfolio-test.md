# Arm 3 portfolio test: `qwen3.8:27b` with `muse-glimmer:30b` (registered, stage A not yet run)

Arm 3 claims that models from different makers fail on different problems, so a mix of them
covers more than any one. `muse-glimmer:30b` is the first candidate to pass the entry criterion
and its decider: 2024 d14 p2, 10/10 against the reference's 1/10
(`arm3-precheck-muse-glimmer-30b.md`). This doc registers how the claim is tested from here.

## Design, and why

- **Equal budget.** An ensemble of 3 reference drafts and 3 muse drafts makes 6 drafts per
  cell. Compared with either model alone at 3, it measures 6 draws against 3, not diversity. The
  ensemble is compared with each model alone at 6 drafts.
- **A portfolio, not a cell.** With independent draws, on any single cell the better model at 6
  drafts does at least as well as 3 + 3 of the two. A mix can beat both models only summed over
  cells where the better model differs. So far the difference runs one way: muse wins 2024 d14
  p2, and no cell is known where the reference beats muse. If none exists, choosing muse gives all
  the gain and an ensemble adds nothing; that is recorded as the arm-3 result.

Stages:

| stage | what | GPU time |
|---|---|---|
| **A** | Muse alone on cells the reference solves reliably or sometimes, to find cells where the reference wins | about 6–12 h, in three batches |
| **B** | Choose about 6 cells with winners in both directions; register predictions for each arm from per-draft rates | none |
| **C** | On those cells, 3 trials each: the ensemble at 3 + 3, the reference alone at 6, muse alone at 6. Arm 3 holds if the ensemble's total beats both. | about 20–27 h, splittable per cell and arm |

If stage A finds no cell where the reference wins, stage C is not run. Runs split by cells, never
by trials: every run keeps `--trials 3`.

## Stage A

Muse at `samples_per_model=1`, 3 trials, each Part Two after its Part One. Fingerprint
`a9ae29f29a7a` (as its plumbing check and decider; the name is not part of it).

```
B="models=muse-glimmer:30b,temperature=0.7,samples_per_model=1,enable_thinking=false,enable_fallback_models=false"
venv/bin/python experiment.py --problems 2024:6.2,2024:9.2,2024:11.2,2024:13.2,2024:15.2 --trials 3 --config "name=m5pro-arm3-muse-sweep-b1,$B"
venv/bin/python experiment.py --problems 2024:16.2,2024:18.2,2024:19.2,2024:20.2,2024:22.2 --trials 3 --config "name=m5pro-arm3-muse-sweep-b2,$B"
venv/bin/python experiment.py --problems 2025:2.2,2025:4.2,2025:9.2,2025:11.2 --trials 3 --config "name=m5pro-arm3-muse-sweep-b3,$B"
```

About 2–4 h per batch. The cells are every Part 2 the reference has re-run under the new
defaults, minus the five entry cells muse has already run. The reference's record on them:

| cells | reference, new defaults | source |
|---|---|---|
| 2024 d6, d11, d13, d18, d20, d22 p2; 2025 d2, d11 p2 | 3/3 each at k1 | `m5pro-rescan-part2-aoc.md` |
| 2024 d9 p2, 2025 d4 p2 | 2/3 at k1, 3/3 at k3 | rescan, `m5pro-band-k1-vs-k3-aoc.md` |
| 2024 d15 p2, d16 p2 | 3/3 | `part2-prompt-omits-part1.md` |
| 2024 d19 p2 | 19/19 | `part2-prompt-omits-part1.md` |
| 2025 d9 p2 | 3/5 at k3 | `part2-prompt-omits-part1.md` |

The prerequisite Part 1s count too: the reference solves all of them every time except where
noted in those docs.

**A reference-favoured cell** (Part 1 or Part 2): muse solves it in at most 1 of 3 trials, and
the reference in at least 2 of 3 on record. As with the entry criterion, a cell that qualifies
goes through a 10-trial k1 decider for both models before it enters the portfolio. The selection
bias runs the other way here: these cells were chosen because the reference solves them.

**Prediction (registered 2026-11-06, before stage A):** between 1 and 3 reference-favoured cells
among the 14, most likely among the reference's harder ones (2024 d15 p2, d16 p2; 2025 d9 p2).
Muse solves at least 2 of 3 trials on the rest.

## Result

Not yet run.
