# k1 against k3 on the "sometimes" band under the site's conditions: 9/19 → 11/21

Step (e) of the re-earn plan (`PLAN.md`, M5 Pro step 4). The rescan (`m5pro-rescan-part2-aoc.md`)
left a band of cells the reference solved in some trials and not others at
`samples_per_model=1`. This run puts the same cells at `samples_per_model=3`.

`m5pro-aoc-band-k3`, fingerprint `839b40f0bfa8`, 3 trials, each Part Two after its Part One;
2026-11-01, GPU free, 34,244 s
(`dev/experiments/20261101T094316Z_m5pro-aoc-band-k3_839b40f0bfa8.json`).

```
venv/bin/python experiment.py --problems 2024:9.2,2024:14.2,2024:17.2,2024:24.2,2025:4.2,2025:10.2 --trials 3 \
  --config "name=m5pro-aoc-band-k3,samples_per_model=3,models=qwen3.8:27b,temperature=0.7,enable_thinking=false,enable_fallback_models=false"
```

2025 d9 p2, the other band cell, already has k3 data (3/5, `part2-prompt-omits-part1.md`) and no
k1 data under `example_tests=page`, so it is not in the comparison.

## Result

| cell | k1 trials (rescan) | k3 trials | k3 first drafts | failures at k3 |
|---|---|---|---|---|
| 2024 d9 p2 | 2/3 | 3/3 | 8/9 | one too low |
| 2024 d14 p2 | 2/3 | 1/3 | **1/9** | 15 too low, 1 too high |
| 2024 d17 p2 | 1/3 | 1/3 | **1/9** | 10 too low, 5 timeouts, 4 wrong |
| 2024 d24 p1 | 1/3 | 3/3 | 9/9 | none |
| 2024 d24 p2 | 0/1 reached | **0/3** | **0/9** | 15 timeouts, 4 wrong, 5 no code |
| 2025 d4 p2 | 2/3 | 3/3 | 9/9 | none |
| 2025 d10 p2 | 1/3 | **0/3** | **0/9** | 12 timeouts, 5 crashes, 6 wrong |
| **total** | **9/19** | **11/21** | | |

All six Part 1s run as prerequisites were solved in every trial. No trial was solved by a repair in
either run; every solve was a first draft.

- **Three drafts did not measurably beat one.** 9 of 19 trials at k1 against 11 of 21 at k3.
  The difference is noise at three trials per cell.
- **The band is not a band.** At the draft level the cells split in two. Three are solved by
  almost every draft (d9 p2 8/9, d24 p1 9/9, 2025 d4 p2 9/9). Four are
  solved by almost none (d14 p2 1/9, d17 p2 1/9, d24 p2 0/9, 2025 d10 p2 0/9). The k1 rates of
  1/3 and 2/3 that put them in the band were three-trial samples.
- **This is what independent draws predict.** Pooling both runs' first drafts gives per-draft
  rates of 3/12 for d14 p2, 2/12 for d17 p2 and 1/12 for 2025 d10 p2. Independent draws then
  predict 58%, 42% and 23% at k3; measured 1/3, 1/3 and 0/3. Three draws lift a low per-draft
  rate very little, and a high one has little room to rise. Sampling pays only where the
  per-draft rate is in between, and 2025 d9 p2 (3 of 9 first drafts) is the one cell measured
  there under the new defaults.
- **Repair rescued nothing.** The hard cells drew many repair rounds with true example feedback
  and the too-high/too-low hint: 2024 d14 p2 had 15 too-low answers and no repair was
  accepted.
- **The hard cells fail on speed as often as on reasoning.** 2024 d24 p2 and 2025 d10 p2 had 27
  timeouts at 60 s between them, out of 51 failed attempts.

## What this changes

- **Arm 1 under the site's conditions** has one cell at a mid-range per-draft rate: 2025 d9
  p2. A powered k1-vs-k3 needs that cell at more trials, or more cells found at that rate.
- **Arm-3 entry cells confirmed**, the reference at most 1 of 3 at k3: 2024 d24 p2 (0/3,
  0/9 drafts), 2025 d10 p2 (0/3, 0/9), 2024 d14 p2 (1/3, 1/9) and d17 p2 (1/3, 1/9). Add 2024
  d21 p1 (0/3 at k1, 0/4 on record), not re-run here. 2024 d24 p1 leaves the list (3/3 at k3).
