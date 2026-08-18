# Frontier scan: `qwen3.8:27b` on 2024 d8–15 — 9/16, and a usable frontier at last

**Headline: 56% (9/16).** The model that swept d4–7 at 100% drops to 56% here, so **d8–15 contains a
real frontier** — which is what the pass@k A/B has been blocked on. It also produced **seven new
verified solutions in a single run**: the ledger goes **14 → 21**, and to **22** once d13 p1's
overfit rejection was investigated and overturned (below). Oracle-clean throughout.

- **Config:** `models=qwen3.8:27b, temperature=0.7, samples_per_model=1, enable_thinking=false`
  (fingerprint `5b33a3519b5d`), 1 trial, 2024 d8–15 (16 problem-parts).
- **Machine:** `m2max-32`, ollama 0.32.14. **Cost:** 10,811 s (3h), 373,420 tokens.
- **Run:** `dev/experiments/20260817T035512Z_scan-qwen38-samp1_5b33a3519b5d.json` (gitignored).
- **Ledger:** +7 (d8 p1, d8 p2, d10 p2, d12 p1, d12 p2, d14 p1, d15 p1) → **21 correct, 0 wrong**.

This is a **locator, not a measurement**: one draw per problem, deliberately, to find where the model
stops being reliable. Nothing here classifies a problem as "sometimes" — that needs `--trials`, and
is the next run. (The `--trials 3` rule in `AGENTS.md` bans *concluding* from one trial, not spending
one to decide where to aim.)

## Result

| problem | verdict | wall | attempt split |
|---------|---------|------|---------------|
| d8 p1 | **OK** 423 | 336 s | 1 solved |
| d8 p2 | **OK** 1287 | 787 s | 1 solved |
| d9 p1 | none | 900 s | **1 no_candidate** |
| d9 p2 | none | 927 s | 2 wrong |
| d10 p1 | **OK** 482 | 565 s | 1 solved |
| d10 p2 | **OK** 1094 | 727 s | 1 solved |
| d11 p1 | **OK** 229043 | 239 s | 1 solved |
| d11 p2 | none | 523 s | 3 wrong |
| d12 p1 | **OK** 1546338 | 240 s | 1 solved |
| d12 p2 | **OK** 978590 | 834 s | 1 solved |
| d13 p1 | **CHEAT** 37680 *(correct answer, refused)* | 360 s | 1 overfit |
| d13 p2 | none | 942 s | 1 error, 1 wrong |
| d14 p1 | **OK** 228410028 | 505 s | 1 solved |
| d14 p2 | none | 301 s | 1 wrong |
| d15 p1 | **OK** 1577255 | 343 s | 1 solved |
| d15 p2 | none | **2282 s** | 3 wrong |

## The failures are two different kinds, and that matters for the A/B

**Implementation-fiddly** — the approach is obvious, the bookkeeping is not:
- **d9 p1/p2** (disk fragmentation). Block-level accounting that is easy to state and easy to get
  subtly wrong. p1 is the only **`no_candidate`** in the scan — 900 s and nothing extractable, which
  is unusual for this model and worth a look.
- **d15 p2** (widened warehouse) — the longest run at 2,282 s, 3 wrong; likely part execution-bound.

**Insight-required** — Part 1's approach must be *abandoned*:
- **d11 p2** — naive simulation explodes; needs memoised counting by stone value. 3 wrong.
- **d13 p2** — `+10000000000000` kills brute force; needs solving the 2×2 system algebraically. 1
  error, 1 wrong.

**Under-specified** — a category of its own:
- **d14 p2** ("find the Christmas tree"). The oracle can score it, but the *problem* never defines
  the target, so extra draws sample toward nothing in particular. **A poor pass@k candidate** on
  those grounds, regardless of how it behaves.

The prediction worth testing: sampling should help the fiddly problems (many near-misses, one draw
gets the bookkeeping right) and do little for the insight ones (either the model reaches for the
right idea or it doesn't). If that holds, it sharpens the thesis considerably — voting buys
*execution reliability*, not *insight*. If d11 p2 or d13 p2 falls to sampling, that is the stronger
result, and the more surprising one.

## d13 p1: the overfit gate fired on a correct answer

Refused with:

```
Solution code contains a long line from example 1 input as a literal: 'Button A: X+94, Y+34'
```

The answer `37680` is **correct for the full input**, and code that merely hardcodes example data
cannot produce that. The likely reading is a general algorithm that also embedded the example in a
docstring or self-test, tripping a heuristic that only asks *whether* an example literal appears,
not *where*.

**Confirmed a false positive and fixed** (`overfit-gate-false-positive.md`): the check ran against
raw source and never asked *where* the literal appeared. A hand-written, unambiguously general
solution with the example only in its docstring is flagged by the old code. Comments and docstrings
are now stripped before the identical checks run — the bar is unchanged, and both real pre-oracle
cheat fixtures still trip it. Re-running d13 p1 produced a clean draw that passed: **now recorded,
ledger 22**. Note the exposure is model-specific: `qwen3.8:27b` writes its reasoning into comments,
so the habit that helps it solve hard problems is what tripped a gate reading prose as code.

## What this unblocks

1. **The pass@k A/B has a band at last:** d9 p1, d9 p2, d11 p2, d13 p2, d15 p2 (d14 p2 excluded on
   the grounds above). First it needs `--trials 3` at samp1 to separate *sometimes* from *never* —
   only the former can show a pass@k effect.
2. **d8–15 is a working capability instrument** at 56%, where d4–7 is exhausted at 100%.
3. **2025 is unusable offline** — all 14 cached days have scraped answers but **no `input.txt`**.
   Worth fetching before it is needed, not during a run.
4. **Run scans with `--include-replay` when a gate rejection is plausible.** The source of a refused
   solution is exactly what is needed to audit the refusal, and it is the one thing not kept: the
   original d13 p1 code is gone, so the false positive had to be proved by reconstruction.

## Reproduce

```
venv/bin/python experiment.py --problems 2024:8-15 --trials 1 \
  --config "name=scan-qwen38-samp1,models=qwen3.8:27b,temperature=0.7,samples_per_model=1,enable_thinking=false"
```
