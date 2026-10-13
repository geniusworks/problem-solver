# m5pro-64: k1 vs k3 on the 2024 d16–25 band — **all four cells as predicted, on thin evidence**

**Headline: the one informative problem, d19 p2, went from 1/4 at k=1 to 2/3 at k=3; the other
"sometimes" problem went 3/3, the wall stayed at 0, the control held.** That matches the prediction
registered in `m5pro-band-2024-d16-25.md` before the run. It is the third test of the central
claim and the second out of sample, and it agrees in direction without adding much weight: the
difference on d19 p2 alone has a one-sided Fisher p of 0.37.

- **Config:** `models=qwen3.8:27b, temperature=0.7, samples_per_model=3, enable_thinking=false,
  enable_fallback_models=false` (fingerprint `d0e67ebf4cee`, the calibration run's), 3 trials,
  2024 d19 p1, d19 p2, d20 p1, d16 p2.
- **Machine:** `m5pro-64`, ollama 0.34.4.
- **Cost:** 10,124 s wall (2h 49m), 47 attempts. The recorded token total (671,116) is not
  reliable: repair records repeat their draft's token count, a defect found while reading this
  artifact and fixed separately.
- **Run:** `dev/experiments/20261013T022941Z_m5pro-k3-d16-25-qwen38_d0e67ebf4cee.json`
  (gitignored).
- **Baseline (k1):** the scan draw plus three band trials per problem, fingerprint `62ee65d6b521`.
- 8/12 solved. 0 wrong / 0 unverified / 0 overfit. No new problems solved; ledger stays at 54.

## Result

| problem | role | pass@1 (pooled) | **pass@3** | registered | |
|---|---|---|---|---|---|
| **d19 p2** | sometimes | 1/4 (25%) | **2/3** | at least 2 of 3 | held |
| d20 p1 | sometimes, little headroom | 3/4 (75%) | **3/3** | 3/3 | held |
| d16 p2 | wall | 0/4 | **0/3** | 0/3 | held (now 0/7) |
| d19 p1 | control | 1/1 | **3/3** | 3/3 | held |

## What the drafts show

Each k3 trial writes three first drafts before any repair, so the artifact holds nine independent
first drafts per problem.

| problem | first drafts correct (this run) | with the k1 record |
|---|---|---|
| d19 p1 | 9/9 | 10/10 |
| d20 p1 | 9/9 | 12/13 |
| d19 p2 | 1/9 | 2/13 (15%) |
| d16 p2 | 0/9 | 0/13 |

- **d19 p2's two solves came by two routes.** Trial 3 was solved by its third draft, which is the
  sampling mechanism. Trial 1 was solved by the second repair round of a draft that had crashed;
  none of its three first drafts was correct. Counting first drafts alone, k3 solved one trial of
  three. At a 15% draft rate, three independent drafts solve 39% of the time, not the 58% the
  registered curve assumed from 1/4.
- **That repair is the first to convert on this band.** The scan and band runs went 0 for 41;
  this run went 1 for 11. More drafts give repair more starting points, so k=3 can help through
  repair as well as through the draw. The record cannot separate the two routes at n=3.
- **d16 p2 fails the same way every time.** All 13 first drafts on record, and every repair but
  one, answered `682` against an accepted `568`. Thirteen independent drafts agreeing on one wrong
  number is a shared misreading of the problem, not sampling noise, and no value of k addresses
  it. This is the best-characterised wall in the project.
- **d20 p1's one k1 miss looks like the outlier.** 12 of 13 first drafts are correct.

## Reading it

The three-way structure repeated: sampling helped where the outcome was uncertain, did nothing
for the wall, and was unnecessary for the control. With one informative problem at n=3, that is
agreement, not confirmation. The claim's weight still rests on `passk-ab-d13-d15.md` and
`passk-replication-2025.md`; the status of arm 1 does not change.

## Next: a powered k1 vs k3 on d19 p2 alone (registered before it runs)

*Run 2026-10-12; result in `m5pro-d19p2-power.md`: k1 6/20, k3 10/20, both predictions held.*

One problem, many trials, both arms run fresh on the same code and machine.

- **k1 arm:** `samples_per_model=1`, 20 trials (fingerprint `62ee65d6b521`).
- **k3 arm:** `samples_per_model=3`, 20 trials (fingerprint `d0e67ebf4cee`), run straight after.
- Both run on the solver with repair accounting fixed (`repair-accounting-unwired.md`), so these
  are also the first artifacts whose repair records carry their own tokens.
- **Prediction:** k1 solves 2 to 7 of 20 (the record is 1/4 by trial, 2/13 by first draft). k3
  solves more trials than k1, and at least 7 of 20. If first drafts are independent at rate p,
  three of them solve 1 − (1 − p)³ of trials before repair: 39% at p = 0.15, 58% at p = 0.25.
- **What would count against the claim:** k3 at or below k1's count. With 20 per arm, a true
  20% against 50% is detected at p < 0.05 about half the time, so a small k3 lead that misses
  significance is inconclusive, not a refutation.
- **Also read off:** how many k3 solves come from a first draft and how many from repair, which
  the three-trial run could not separate.
