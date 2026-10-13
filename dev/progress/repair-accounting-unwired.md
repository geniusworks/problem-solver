# Repair records still repeated their draft's cost — the August fix never reached the record

**Headline: every repair record in every result JSON to date carries its draft's token counts,
wall-clock and quality score, not its own. 642 of 642 repair records across 64 artifacts.** The
2026-08-22 fix (`token-accounting-fix.md`) corrected the provider and was tested at the provider;
the solver never read the corrected value. Found 2026-10-12 while reading the k3 artifact for
`m5pro-passk-2024-d16-25.md`, fixed the same day.

## The defect

`OllamaProvider.improve_solution` has set `last_token_usage` correctly since August. But
`BaseSolver._execute_and_repair` recorded every attempt, at every repair iteration, from two
dicts filled once at draft time:

```python
tokens = generation_tokens.get(cand_id, {})            # the draft's
wall_clock_seconds=generation_times.get(cand_id, 0.0)  # the draft's
quality_score=quality_scores.get(cand_id)              # the draft's
```

Nothing wrote the repair call's usage or duration back. The symptom is the one the August doc
quoted, unchanged — a draft and its repairs with identical counts and different answers:

```
2024 d19 p2, trial 1 of the k3 run, one candidate:
stage:    generate          repair 1          repair 2
answer:   (crash)           (crash)           705756472327497
tokens:   15,875            15,875            15,875
seconds:  325.4             325.4             325.4
```

The August tests asserted on `provider.last_token_usage`. No test asserted on an `AttemptRecord`,
so the tests passed while the artifact stayed wrong.

## The fix

`_execute_and_repair` now times each `improve_solution` call, reads `last_token_usage` after it,
and records the next iteration's attempt with those. A repair record's `quality_score` is `None`:
the score was computed on the draft and no repair is scored.
`test_solver_uses_repair_loop_when_all_initial_candidates_fail` asserts on the records themselves
and fails without the change.

**Still unrecorded:** a repair call that raises, or returns the code unchanged, produces no
candidate and so no record. Its tokens are spent and appear nowhere. Recording them means adding
attempt records, which changes `attempts` and `mean_attempts_to_solve` against the whole history;
left as a logged gap.

## What is and is not affected

| quantity | status |
|---|---|
| solved / wrong / unverified / overfit, every solve rate | **unaffected** |
| per-problem and per-run wall-clock (`wall_clock_seconds` on a result, `total_wall_clock_seconds`) | **unaffected** — timed by the runner around the whole solve |
| tokens and time on `generate` records | **sound** |
| tokens and time on `repair` records | **wrong**: a copy of the draft's |
| `total_tokens` per result and per run | **wrong** by the repair share; direction unknown |
| `per_model.wall_clock_seconds` | **wrong**: sums the copies (11,959 s reported for a 10,124 s run) |

Across the corpus, 8.59M of 22.75M recorded tokens (38%) sit on repair records. A repair is one
call carrying the failed code and its feedback; a draft is an analysis call plus an implementation
call. Which is larger was not known when this was written, so the old totals are neither upper
nor lower bounds. *(First measurement, 2026-10-12, `m5pro-d19p2-power.md`: a repair cost about a
quarter of a draft — 1.5–2.1k tokens against 7k — on one problem and one model. If that holds
elsewhere the old totals overstate, and arm 2's ratio lies between 3.10× and 3.35×.)* **The
draft-only sum is a firm lower bound on a run's true cost**, and is what the corrections below use.

## Claims that rested on token totals

- **Arm 2, "loses 3.35× on tokens"** (`economic-arm-moe-vs-generalist.md`). The generalist arm
  made no repairs, so its 307,684 is sound. The MoE arm's 901,111 includes 67,635 copied onto 5
  repair records; its drafts alone are 833,476, or 119,068 per verified solution. **The ratio is
  at least 3.10×**, and higher by whatever the five repairs really cost. The direction and rough
  size of the finding stand; the figure 3.35× is not a measurement.
- **Arm-3 pre-check, "no token penalty"** (`arm3-precheck-qwen36-35b.md`). 44–48% of both arms'
  totals were copies. On drafts alone: candidate 803,969 for 7 solves (115k each), reference
  770,638 for 6 (128k each). The observation survives on the sound part of the data and remains
  unmeasured on the repair part.
- **m5pro run totals.** Draft-only tokens, with the share of the reported total that was copied:
  calibration 861,171 (5%), scan 362,965 (41%), band 568,750 (57%), k3 on the band 542,718 (19%).
- **`RESULTS.md` corpus line, "16.3M tokens"** counts copies; it is an order of magnitude, not a
  total.

No solve-rate finding, no time finding and no ledger entry changes.
