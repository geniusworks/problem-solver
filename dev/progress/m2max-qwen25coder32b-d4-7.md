# m2max-32: `qwen2.5-coder:32b` samp3 on 2024 d4–7 — the 30B tier did NOT beat 16 GB

**Headline: 4/8 (50%) — *below* the M1's 5/8.** The first experiment the M2 Max was bought to run
answers the handoff's Q1 in the negative for this model. A 32B code-specialist, given twice the RAM
and a machine that runs it entirely on GPU, solved **fewer** problems on the comparison set than
`gemma4:12b` (7.6 GB) and `qwen3.5:9b` (6.6 GB) did on the M1. It cracked **neither** d5 p2 nor
d6 p2, the two problems no 16 GB model has ever solved.

- **Config:** `models=qwen2.5-coder:32b, temperature=0.7, samples_per_model=3, enable_thinking=false`
  (fingerprint `84fed97d4987`), 1 trial, 2024 d4–7.
- **Machine:** `m2max-32` (M2 Max, 32 GB, macOS 26.6.1, ollama 0.32.11, Python 3.14).
- **Cost:** 7,918 s wall (2h 12m), 41 candidate attempts, 317,149 tokens.
- **Run:** `dev/experiments/20260816T065057Z_qwen25c32b-samp3_84fed97d4987.json` (gitignored).
- **Ledger impact:** none — 0 wrong, 0 unverified, 0 overfit; `verify_solutions` stays 12/12.

## The result, against the M1

The 32B's solved set is exactly the M1 leaders' set **minus d4 p2**. It solved every Part 1 and no
Part 2 at all.

| problem | `qwen2.5-coder:32b` (m2max-32) | `gemma4:12b` / ensemble (m1-16) | note |
|---------|-------------------------------|----------------------------------|------|
| d4 p1 | **OK** 2401 (623 s) | OK | |
| d4 p2 | **none** (1057 s) | **OK** 1822 | the whole difference |
| d5 p1 | **OK** 5747 (902 s) | OK | |
| d5 p2 | **none** (599 s) | none | uncracked by everything |
| d6 p1 | **OK** 5331 (992 s) | OK | |
| d6 p2 | **none** (2041 s) | none | uncracked by everything |
| d7 p1 | **OK** 5702958180383 (712 s) | OK | |
| d7 p2 | **none** (993 s) | none | marginal; lucky-draw solves only |
| **total** | **4/8 (50%)** | **5/8 (62%)** | |

## Why it failed — the attempt-level split (the interesting part)

A problem-level `none` (`Outcome.NO_CANDIDATE`) means the solver returned no *accepted* solution. It
does **not** mean the model emitted no code, and here it never did: across 41 attempts the split was
**9 solved / 27 wrong / 5 error**. Generation and extraction were healthy; the code was wrong.

Per failed problem, the answers actually produced:

- **d4 p2 — 9 attempts, 9 wrong, no convergence.** Answers: `2772`(×3), `2179`(×2), `837`, `0`,
  `5488`, `2744` (expected `1822`). The example test failed too (`expected '9', got '122'`, then
  `got '3'`). This is not a near-miss or a sampling accident: the model is confidently and
  variously wrong about the X-MAS diagonal count, nine times, where a 9B model got it right.
- **d5 p2 — 7 attempts, all wrong, and all the same failure:**
  `invalid literal for int() with base 10: '93|48'`. **The model never parsed the input.** Every
  attempt crashed on the `|`-separated ordering rules, caught its own exception, and printed `0`.
- **d6 p2 — 8 attempts (7 wrong, 1 error), every answer `0`** (one `None`). The example test failed
  `expected '6', got '99'`. Longest wall of the run at 2,041 s.
- **d7 p2 — 5 attempts (3 wrong, 2 error).** Two crashed on parsing
  (`invalid literal for int() with base 10: '56083790:'` — the colon after the target value;
  `not enough values to unpack`), two returned `None`, one `0`.

## Two corrections to the project's record

**1. "d5 p2 / d6 p2 are efficiency-bound" is not the whole story.** The M1 finding
(`9b-timeout-investigation.md`) concluded the ceiling on these was algorithm efficiency — the model
finds the idea but the code is too slow. That was true *for the 16 GB models*. It is **not** what
happened here: on d5 p2 the 32B never reached an algorithm at all, failing on `'93|48'` in all seven
attempts. On d7 p2, two of five attempts died the same way, on `'56083790:'`. For this model the
binding failure on those problems is **input parsing**, not execution speed. d6 p2 remains
consistent with the efficiency story (all-`0` answers, the longest wall of the run).

**2. Model size is not the capability lever here.** The project's standing claim — "past the easy
problems the bottleneck is model capability, where stronger models lift the hard days from 1/8 to
5/8" — needs qualifying. A 32B of the *same generation* (`qwen2.5-coder`, late 2024) is worse on this
set than 9B/12B models of a newer generation. What lifted 1/8 → 5/8 on the M1 was newer models, and
this run shows scaling the *old* generation up does not reproduce that gain. Whether a newer
generation at this size does is now the live question (see below).

## A measurement-fidelity issue this surfaced (follow-up)

Generated code frequently wraps its body in `try/except`, prints `An error occurred: <exception>`,
and then prints `0`. The harness scores the printed output, so these **runtime crashes are recorded
as `wrong`, not `error`** — the recorded "answer" is literally
`"An error occurred: invalid literal for int() with base 10: '93|48'\n0"`. The 27-wrong / 5-error
split therefore *understates* crashes and overstates genuine wrong reasoning. This is the same class
of accounting artifact Milestone D1 fixed at the problem level, now visible at the attempt level.
Worth a targeted fix: detect an error-shaped answer and classify it as `error`.

## What this means for the plan

- **Q1 is answered for `qwen2.5-coder:32b`: no.** It does not beat 16 GB and does not crack the two
  hard Part 2s. `qwen3-coder:30b` (MoE, resident, untested) is the remaining planned Q1 model.
- **The sharper experiment is generation, not size.** `qwen3.8:27b` (released 2026-08-14, 18 GB Q4)
  is *smaller* than this 32B but two generations newer — close to a controlled test of the
  qualification above. Blocked on an Ollama upgrade: 0.32.11 refuses the pull ("Please download the
  latest version"). Upgrading changes a recorded machine variable, so it is deliberately deferred
  until the current-runtime runs are done.
- **Q2 (pass@k vs pass@1) is unaffected but needs a different frontier band.** The thesis test needs
  problems the strong model solves *sometimes*. For this model on d4–7 there are none: it solved 4
  problems on every draw and 4 on no draw (`solved_every_time` 4, `solved_at_least_once` 4). A
  bimodal all-or-nothing result gives voting nothing to work with, so the frontier scan must widen
  (the handoff's `2024:8-20`) before Q2 can run.

## Reproduce

```
venv/bin/python experiment.py --problems 2024:4-7 --trials 1 \
  --config "name=qwen25c32b-samp3,models=qwen2.5-coder:32b,temperature=0.7,samples_per_model=3,enable_thinking=false"
```
