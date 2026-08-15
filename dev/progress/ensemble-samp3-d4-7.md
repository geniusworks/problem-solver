# Diverse ensemble (gemma4:12b + qwen3.5:9b) samp3 on 2024 d4–7 — the 6/8 union did NOT hold

`gemma4-samp3-confirmation.md` observed that the two 5/8 leaders miss *different* Part 2s (gemma4
cracks d4 p2, the 9b cracks d7 p2) and predicted their **union would be 6/8** — a cheap
decorrelated-error test of the orchestration thesis, runnable on the M1. This run tests it directly.
Config: `models=gemma4:12b|qwen3.5:9b, samples_per_model=3, temperature=0.7, enable_thinking=false`,
2024 d4–7, 1 trial. Run 2026-08-15, wall **32,742 s (~9.1 h)**.

> Note: the first attempt was killed by a machine reboot at d6 (partial log archived as
> `dev/experiments/ensemble-samp3-d4-7.PARTIAL-reboot.log`); this is the clean re-run.

## Result: 5/8 — the prediction failed

```
problem        ensemble       winner        answer
2024 d4 p1     OK             gemma4:12b    2401
2024 d4 p2     OK             gemma4:12b    1822
2024 d5 p1     OK             gemma4:12b    5747
2024 d5 p2     none           —             (expected 5502)
2024 d6 p1     OK             gemma4:12b    5331
2024 d6 p2     none           —             (expected 1812)
2024 d7 p1     OK             gemma4:12b    5702958180383
2024 d7 p2     none           —             (expected 92612386119138)  <- the predicted union solve
```

**5/8 (62%), 0 wrong / 0 unverified / 0 overfit.** Identical set to gemma4 *alone* at samp3. No new
ledger entries (`verify_solutions` stays 12/12).

Both models genuinely participated — verified from the run JSON, not the log summary:

```
per-model (candidate-level)   attempts   solved   wall
gemma4:12b                    34         13       14,261 s
qwen3.5:9b                    37          9       20,550 s
```

Every problem drew 3 candidates from **each** model (more on the failures, via repair). The 9b was
fully in play. But its 9 candidate-solves all landed on the *same five* problems gemma4 already
solved, and on **d7 p2 both models tried 7 candidates each and neither solved it.** The union stayed
at 5/8; the second model added no new problem.

## Why the union failed: the "complementary crack" was variance, not a robust competency

The 6/8 prediction rested on the 9b reliably contributing d7 p2. But the 9b's earlier d7 p2 solve
(in `9b-confirmation-d4-7.md`) was itself a *low-probability draw* — just as gemma4's d7 p2 at
samples=1 was (`gemma4-samp3-confirmation.md`, finding 1). d7 p2 sits so near both models' frontier
that each solves it only *occasionally*; in this run neither model's draws hit it. So there was no
stable "9b solves d7 p2" competency for the ensemble to pool.

This sharpens the orchestration thesis rather than refuting it: **decorrelated-error ensembling
converts to extra solves only when each member's distinct competency is robust, not lucky.** Pooling
two models does not capture a solve that either model only lands by chance — that needs *more
samples on the marginal problem* (raising pass@k for a model that can occasionally solve it), not a
second model that also only occasionally solves it. Diversity helps when the diversity is real
capability; here the apparent complementarity on d7 p2 was noise.

Note the one place it *did* hold: d4 p2 (gemma4's crack) is robust — gemma4 solved it again here —
so the ensemble kept it. The failure was specific to the *unreliable* crack.

## Cost

**~2.2× wall for zero extra solves** on this set: 32,742 s vs gemma4-alone samp3's 15,160 s. On d4–7
the ensemble is strictly worse on cost/benefit than the single best model. (This is a statement about
*this* set, where the models' reliable competencies fully overlap; it is not evidence against
ensembling where members have genuinely robust, distinct strengths.)

## Bottom line

- The cheap-M1 ensemble lever **did not pay off**: 5/8, same as gemma4 alone, at ~2.2× cost.
- The "6/8 union" I predicted in `gemma4-samp3-confirmation.md` **was tested and did not hold** —
  recording the correction.
- Refined takeaway for the thesis (README "Does orchestrated voting scale?"): ensemble diversity is
  not free correctness; it pays only when members' distinct solves are *reproducible*. The lever that
  would actually attack d7 p2 is **more samples on that problem**, or a **stronger model** — both of
  which the m2max-32 / 30B+ runs are positioned to test — not a second same-tier model.

## Reproduce

```
# NOTE: the model list is PIPE-separated (commas separate config key=value pairs).
venv/bin/python experiment.py --problems 2024:4-7 --trials 1 \
  --config "name=ensemble-samp3,models=gemma4:12b|qwen3.5:9b,temperature=0.7,samples_per_model=3,enable_thinking=false"
```
