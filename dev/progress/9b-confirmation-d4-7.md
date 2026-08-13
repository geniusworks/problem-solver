# Confirmation: qwen3.5:9b (thinking off) clears the 7B's capability ceiling

The direct, apples-to-apples follow-up to the reasoning-model finding: the same samples=3 config the
7B ran on the hard days (2024 d4–7), with only the model swapped. Run 2026-08-13, 6.8 h wall clock,
fully verified offline. Artifact: `dev/experiments/*_9b-samp3_7230164d3354.json` (gitignored).

## Result: 5/8 vs the 7B's 1/8

```
config (2024 d4-7, samples=3)   solved   which
qwen3.5:9b (thinking off)       5/8      d4p1, d5p1, d6p1, d7p1, d7p2
qwen2.5-coder:7b (recorded)     1/8      d6p1
```

The 9b solved **5× as many** of the problems the 7B is capability-limited on, and — the headline —
**cracked `d7 p2`, a genuine Part 2** (bridge-repair: search over operator combinations, `itertools`).
The 7B never solved *any* Part 2 beyond the trivial d1 p2; the 9b reaches into the Part-2 reasoning
class the coder simply couldn't. Three new verified solutions recorded (d4 p1, d5 p1, d7 p2);
`verify_solutions` is now **11/11**. Zero wrong or overfit, as always — the oracle held over a 6.8 h run.

## The ceiling moved up, but there is still a ceiling

d4 p2, d5 p2, d6 p2 stayed unsolved (all `no_candidate`) even for the 9b at 3 samples. So the 9b
raises the frontier substantially without erasing it — the remaining Part 2s of the middle days are
still out of reach here. Attempt mix (31: 6 solved / 10 wrong / 14 no_candidate / 1 error): the 9b
still emits no-solve()/unrunnable code on a chunk of attempts (thinking-off is a blunt switch), so
there is headroom in generation robustness on top of the model gain.

## Cost

6.8 h for 8 problems at samples=3 — the 9b is ~4.5× slower than the 7B, so it is a heavier
instrument. A full-2024 sweep at these settings is impractical on this hardware; scope 9b runs to the
problems that matter.

## Conclusion

Two model questions the project carried for a long time are now answered with evidence:

1. **"Are the 7B models too weak?"** — Yes past the easy problems (measured earlier: 1/8 on d4–7).
2. **"Can we do better on 16 GB without new hardware?"** — **Yes.** `qwen3.5:9b` with thinking
   disabled fits (5.8 GB, 100% GPU) and roughly quintuples the hard-problem solve rate, cracking a
   Part 2 in the process.

**`qwen3.5:9b` (thinking off) is the new baseline model** for this project. The two open directions
from here — both now well-motivated: (a) push generation robustness for the 9b (the 14 no_candidate
are wrapper/parse misses, not reasoning failures); (b) if a still-stronger model is wanted for the
middle-day Part 2s, that remains the bigger-machine / remote-endpoint lever.

## Reproduce

```
venv/bin/python experiment.py --problems 2024:4-7 --trials 1 \
  --config "name=9b-samp3,models=qwen3.5:9b,temperature=0.7,samples_per_model=3,enable_thinking=false"
```
