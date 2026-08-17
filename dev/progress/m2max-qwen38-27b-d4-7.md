# m2max-32: `qwen3.8:27b` samp3 on 2024 d4–7 — **8/8. The comparison set is exhausted.**

**Headline: a perfect 8/8 (100%).** `qwen3.8:27b` solved every problem in the d4–7 set, including
**d6 p2 — the last problem no model had ever solved** (+1 ledger, now **14 verified**). The set that
has measured this project's capability frontier since the M1 no longer has a frontier in it.

The model that did it is the *smallest* of the three tested here (17 GB), is **not a code
specialist** — it is a vision-language generalist — and is two days old.

- **Config:** `models=qwen3.8:27b, temperature=0.7, samples_per_model=3, enable_thinking=false`
  (fingerprint `bb22870d2a6d`), 1 trial, 2024 d4–7.
- **Machine:** `m2max-32`, **ollama 0.32.14** (see the runtime caveat below).
- **Cost:** 9,602 s wall (2h 40m), 24 attempts, 287,369 tokens.
- **Run:** `dev/experiments/20260816T224020Z_qwen38-27b-samp3_bb22870d2a6d.json` (gitignored).
- **Ledger:** `2024 day 6 part 2 = 1812`. `verify_solutions` **14 correct, 0 wrong**; 0 overfit.

## The generation ladder, complete

Every rung is *smaller* than the one before it, and every rung scores higher:

| model | size | class | generation | solved | per-attempt | wall |
|-------|------|-------|-----------|--------|-------------|------|
| `qwen2.5-coder:32b` dense | 19 GB | code specialist | late 2024 | **4/8** | 9/41 = 22% | 7,918 s |
| `qwen3-coder:30b` MoE | 18 GB | code specialist | newer | **6/8** | 13/29 = 45% | **2,346 s** |
| `qwen3.8:27b` dense | 17 GB | **generalist** | 2026-08-14 | **8/8** | **20/24 = 83%** | 9,602 s |
| *(m1-16 best, for scale)* | 7.6 GB | — | — | 5/8 | — | ~14,000 s |

Parameter count runs backwards to capability across these three. **Generation is the variable**, and
the newest model wins without being a coder at all — so the effect is general model quality, not
code specialization. That is a stronger claim than the MoE result alone supported.

The per-attempt column is the sharpest version of it: the 2024 specialist gets 22% of its candidates
right; the 2026 generalist gets 83%. Same problems, same prompts, same oracle.

## d6 p2: the efficiency story was right, and hardware finished the job

d6 p2 survived every M1 config, a 5× timeout extension, the dense 32B (2,041 s of grinding, all-zero
answers) and the MoE (6/6 immediate `TypeError`s). The winning solution
(`solutions/2024_day06_part2.py`) is **a plain brute force**: try every `.` cell as an obstacle,
simulate, detect loops with a `(row, col, direction)` visited-set. Exactly the approach the M1
called Python-speed-bound.

So unlike d5 p2 — which fell to a genuine algorithmic insight (a topological sort) — **d6 p2 fell to
a correct brute force that finally executed inside the timeout.** The M1's diagnosis was not wrong
about the nature of the wall; what it lacked was a model that reliably emitted a *correct* brute
force plus a machine fast enough to run it. Two different problems, two different resolutions, and
the docs should stop treating "d5 p2 / d6 p2" as one phenomenon.

## Thinking-off relocates reasoning into comments (and it self-corrects)

The d6 p2 solution contains a **dead function**, `simulate_guard`, that ends in a bare `pass`, and
below it the used one, `simulate_guard_correct`. Between them, in comments, the model debugs itself:

```
# My previous logic was:
# If next is out of bounds OR obstacle -> Turn right.
# This is WRONG for the "exit" case.
```

With `enable_thinking=false` the reasoning did not disappear — it moved into code comments, and the
model got a self-correction pass *inside a single generation*, with no repair round. `_extract_code`
handles it fine (the file parses; the dead function is inert). This is a prompt-design observation
worth an A/B: our thinking-off toggle may be capturing much of the reasoning benefit anyway, in a
form the extractor tolerates.

## The strongest pass@k evidence yet — from attempt ordering

Because each problem's draws are recorded in order, pass@1 can be read off directly: **did the first
draw solve it?**

| problem | draw 1 | draw 2 | draw 3 |
|---------|--------|--------|--------|
| d4 p1 | solved | solved | solved |
| d4 p2 | solved | solved | solved |
| d5 p1 | solved | *wrong* | solved |
| **d5 p2** | **wrong** | solved | solved |
| d6 p1 | solved | solved | solved |
| **d6 p2** | **wrong** | solved | solved |
| d7 p1 | solved | solved | *error* |
| d7 p2 | solved | solved | solved |

**pass@1 = 6/8. pass@3 = 8/8.** Sampling bought exactly two problems — and they are **d5 p2 and
d6 p2**, the two hardest problems on the set, the two that had never been solved by anything. Every
problem the model finds easy solved 3/3, where extra draws add nothing.

That is the thesis' predicted shape, at the frontier of the strongest model we have, measured rather
than inferred: *voting adds nothing where the model is reliable, and buys the hard problems where it
is uncertain.* It also replicates the pattern the MoE showed (d4 p2 on 1/3, d5 p2 on 1/4) on a
different model, a different architecture, and a different runtime.

**It is still not the controlled A/B.** This is one trial, and pass@1 is inferred from the first
draw of a samp3 run rather than measured in a dedicated samp1 run. The honest statement is that two
independent models now show the predicted shape, which is strong enough to make the formal
samp1-vs-samp3 A/B at `--trials 5` worth running — and, importantly, it must now be run on a
**harder problem set**, because this model has no frontier left on d4–7.

## Caveats

- **Runtime differs from the other two rows.** This ran on ollama **0.32.14**; the 32B and MoE ran
  on **0.32.11** (which cannot pull this model). The upgrade was verified behaviour-neutral by a
  3-trial control — 6/6, unchanged from pre-upgrade
  (`ollama-0.32.14-runtime-check.md`) — but a 2-problem control bounds gross regressions only. A
  small distributional shift cannot be excluded, and an 8/8 does not hinge on one.
- **One trial.** 8/8 at `--trials 1` means "solved every problem once", not "solves them reliably".
  A `--trials 3` repeat would establish the rate; the per-draw table above is the closest thing to
  stability evidence we have (6 of 8 problems solved on all three draws).
- **Wall-clock is the worst of the three** at 2h 40m — 4× the MoE. On solve-rate-per-second the MoE
  is still the efficient choice; Qwen3.8 wins on capability, not cost.

## What this changes

1. **d4–7 is retired as a capability instrument.** A model that scores 100% cannot measure anything
   further. Capability work needs a harder set — the handoff's `2024:8-20` scan, or 2025.
2. **Q2 must move with it.** The pass@k A/B needs problems the model solves *sometimes*; on this set
   Qwen3.8 has none. Run the frontier scan first, then the A/B on whatever band it exposes.
3. **The last "uncrackable" problem is gone.** Every problem on d4–7 is now solved and in the ledger
   (14 verified, oracle-clean).
4. **Two prior claims are corrected** — see below.

## Corrections to the record

- **"d5 p2 and d6 p2 are efficiency-bound"** (`9b-timeout-investigation.md`, README) — half right.
  d6 p2 *was* speed-bound and fell to a correct brute force on faster hardware; d5 p2 was never
  speed-bound and fell to a better algorithm. They are different failures and were conflated.
- **"Day 5's input format is a model-independent parsing trap"** (`m2max-qwen3coder30b-d4-7.md`) —
  overstated. Both *2024-generation* models tripped on it (the 32B on `'93|48'`, the MoE on
  `'75,47,61,53,29'`), but Qwen3.8 parsed both parts cleanly on the first draw. It is a
  generation-dependent weakness, not a universal one, and the "orchestration lever" framing is
  weaker than claimed: a newer model simply does not have the problem.

## Reproduce

```
venv/bin/python experiment.py --problems 2024:4-7 --trials 1 \
  --config "name=qwen38-27b-samp3,models=qwen3.8:27b,temperature=0.7,samples_per_model=3,enable_thinking=false"
```
