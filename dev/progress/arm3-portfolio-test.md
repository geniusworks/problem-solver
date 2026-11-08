# Arm 3 portfolio test: `qwen3.8:27b` with `muse-glimmer:30b` — no cell favours the reference; stage C not run

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

## Stage A result (2026-11-08): two reference-favoured cells; the prediction held

Three runs, fingerprint `a9ae29f29a7a`, 3 trials each, GPU free, 21,076 s in all, 1.11M tokens:
`dev/experiments/20261107T064550Z_m5pro-arm3-muse-sweep-b1_a9ae29f29a7a.json`,
`20261107T153106Z_m5pro-arm3-muse-sweep-b2_a9ae29f29a7a.json`,
`20261108T071536Z_m5pro-arm3-muse-sweep-b3_a9ae29f29a7a.json`. 74 of 82 reached cells solved; 0
wrong, 0 overfit; ledger unchanged (68).

| Part 2 | muse, k1 | reference on record | Part 1, muse |
|---|---|---|---|
| 2024 d6 | 2/3 | 3/3 k1 | 3/3 |
| 2024 d9 | 3/3 | 2/3 k1, 3/3 k3 | 3/3 |
| 2024 d11 | 3/3 | 3/3 k1 | 3/3 |
| 2024 d13 | 3/3 | 3/3 k1 | 3/3 |
| **2024 d15** | **1/3** | **3/3 k3** | 3/3 |
| 2024 d16 | 2/3 | 3/3 | 3/3 |
| 2024 d18 | 3/3 | 3/3 k1 | 3/3 |
| 2024 d19 | 3/3 | 19/19 | 3/3 |
| **2024 d20** | **1/3** (1 not reached) | **3/3 k1, 3 of 3 drafts** | 2/3 |
| 2024 d22 | 3/3 | 3/3 k1 | 3/3 |
| 2025 d2 | 3/3 | 3/3 k1 | 3/3 |
| 2025 d4 | 3/3 | 2/3 k1, 3/3 k3 | 3/3 |
| 2025 d9 | 1/3 (1 not reached) | 3/5 k3, 3 of 9 drafts | 2/3 |
| 2025 d11 | 3/3 | 3/3 k1 | 3/3 |
| **total** | **34/42** | | **40/42** |

- **Two cells favour the reference, within the predicted 1–3**: 2024 d15 p2 and d20 p2. The
  location was half right: d15 p2 was named, d20 p2 was not; d16 p2 (2/3) does not qualify.
- **2025 d9 p2 does not qualify.** The reference's 3/5 is under 2 of 3, and at k3; its per-draft
  rate is 3 of 9, about what muse showed at k1.
- **The two qualifying cells are thin.** On d15 p2 both failures were too-low answers that repair
  did not move. On d20 p2 one trial was not reached (d20 p1 failed) and one produced no code.
  The reference's d15 p2 record is at k3, against muse at k1.
- **Two of muse's eight failures produced no code because the reply hit the output length
  limit** (`done_reason=length`, d6 p2 and d20 p2). That counts against muse under the harness's
  token cap, not as a wrong answer.
- **On cells the reference solves, muse is close to it:** 34 of 42 Part 2 trials and 40 of 42
  Part 1s, against a reference record of 2/3 or better on every cell.

## Deciders: 2024 d15 p2 and d20 p2 at k1, 10 trials each (registered 2026-11-08, before the runs)

```
B="temperature=0.7,samples_per_model=1,enable_thinking=false,enable_fallback_models=false"
venv/bin/python experiment.py --problems 2024:15.2 --trials 10 --config "name=m5pro-d15p2-ref-k1-n10,models=qwen3.8:27b,$B"
venv/bin/python experiment.py --problems 2024:15.2 --trials 10 --config "name=m5pro-d15p2-muse-k1-n10,models=muse-glimmer:30b,$B"
venv/bin/python experiment.py --problems 2024:20.2 --trials 10 --config "name=m5pro-d20p2-ref-k1-n10,models=qwen3.8:27b,$B"
venv/bin/python experiment.py --problems 2024:20.2 --trials 10 --config "name=m5pro-d20p2-muse-k1-n10,models=muse-glimmer:30b,$B"
```

Four runs, about 1.5–2.5 h each, runnable one at a time. Same rules as the entry deciders: a
trial whose Part One fails counts as a Part Two not solved.

- **Rule:** the reference's lead holds on a cell if it solves more Part Twos than muse,
  one-sided Fisher exact p < 0.05 (for example 10 against 6 or fewer, 9 against 4, 8 against 3).
  A cell enters the portfolio only if its lead holds.
- **Prediction, 2024 d15 p2: the lead does not hold.** Expected reference 4–8 of 10, muse 1–4.
  The reference's 3/3 was at k3, with no per-draft count on record, and its old-prompt per-draft
  rate was about 1 in 8.
- **Prediction, 2024 d20 p2: the lead does not hold.** Expected reference 9–10 of 10, muse 5–8:
  muse's two misses were a missed Part One and a length cut-off, not wrong answers.
- **If neither holds,** no cell favours the reference, stage C is not run, and arm 3 is recorded
  as one-way dominance on these cells.

## Decider results (2026-11-08): neither lead holds; the prediction held

| cell | reference, k1 | muse, k1 | one-sided p | lead holds |
|---|---|---|---|---|
| 2024 d15 p2 | **0/10** (0 of 7 reached) | 1/3 in stage A; decider not run | — | no |
| 2024 d20 p2 | **9/10** (9 of 9 reached) | **6/10** (6 of 7 reached) | 0.15 | no |

Runs: `m5pro-d15p2-ref-k1-n10`, `1ac712678732`, 6,862 s, 765k tokens
(`dev/experiments/20261108T140905Z_m5pro-d15p2-ref-k1-n10_1ac712678732.json`);
`m5pro-d20p2-ref-k1-n10`, `1ac712678732`, 6,123 s, 515k tokens
(`20261108T162848Z_m5pro-d20p2-ref-k1-n10_1ac712678732.json`); `m5pro-d20p2-muse-k1-n10`,
`a9ae29f29a7a`, 8,476 s, 448k tokens (`20261108T181103Z_m5pro-d20p2-muse-k1-n10_a9ae29f29a7a.json`).

- **2024 d15 p2: the reference solved none.** Its Part One was 7/10; of the 7 Part Twos reached,
  4 gave wrong answers and 3 crashed, and no repair was accepted. A reference at 0/10 cannot
  solve more than muse, so **muse's d15 p2 decider was not run**: one of the four registered runs,
  dropped because no result of it could change the decision. Muse's 1/3 in stage A is the better
  record.
- **2024 d20 p2: 9/10 against 6/10, p = 0.15.** The reference is ahead, not shown to be. Muse's
  four misses were three failed Part Ones (Part One 7/10, against the reference's 9/10) and one
  Part Two with a wrong answer; of the Part Twos it reached it solved 6 of 7, three of them by
  repair.
- **Correction, the reference's d15 p2 record.** Its 3/3 at k3 under the new defaults
  (`part2-prompt-omits-part1.md`) came from a run with a shared GPU that left only a log. Here, at
  k1 and GPU free, it is 0 of 7 reached. A per-draft rate low enough for 0 of 7 makes 3/3 at k3
  unlikely; the 3/3 stands as logged but does not describe the reference's rate on this cell.

## Result: no cell favours the reference; stage C not run

Arm 3 needed cells where each model beats the other. Muse beats the reference on 2024 d14 p2
(10/10 against 1/10) and solved 2024 d21, which the reference never has. No cell was found where
the reference beats muse: of the two candidates from stage A, one went to muse and one is not
separable at 10 trials. On these cells, choosing muse gives the gain an ensemble could, so the
ensemble against each model at equal draws was not run.

What this does not show: that an ensemble cannot beat its best member somewhere. Differences
smaller than 9/10 against 4/10 are not detected at 10 trials, and the cells are those the
reference solves or once failed, not a sample of all problems.
