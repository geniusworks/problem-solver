# A stronger local model that fits 16 GB: qwen3.5:9b (thinking off)

The first test of "does a different/stronger model help?" on hardware we actually have — and the
answer is yes, with a caveat about how to run it.

## The detour: reasoning models over-reason

The first attempt (qwen3.5:9b with thinking on) failed badly: on this project's prompts the model
emitted **26,000–31,000 characters of chain-of-thought**, hit `done_reason=length` before writing any
code, and produced no usable candidate — **2 failed attempts in 81 minutes**. A naive reasoning model
does not drop into a coding pipeline; its reasoning is unbounded and eats the whole output budget.

Fix (PR #18): an `enable_thinking` config toggle → Ollama's `think` param. With `think=false`,
qwen3.5:9b emits a clean solution directly, in a fraction of the time.

## The result (2024 d1–7, samples=1, temperature 0.7)

```
config                       solved   which
qwen3.5:9b (thinking off)    6/14     d1p1, d1p2, d2p1, d3p1, d6p1, d7p1
qwen2.5-coder:7b             2/14     d1p1, d3p1
```

**The 9b solved 3× more than the 7B coder on this run, and cracked `d7 p1` (5702958180383) — a
problem the 7B never solved even across a full samples=3 run.** New verified solution recorded;
`verify_solutions` is now 8/8. The 9b fits comfortably (5.8 GB, 100% GPU on Metal), so this is a real
capability gain **without new hardware**.

## Honest caveats

- **Single-sample noise.** samples=1 is one draw; the 7B's 2/14 is a weak draw (its recorded frontier
  reliably reaches ~5 of the easy problems across trials). So the raw "6 vs 2" overstates the gap.
  The load-bearing evidence is narrower and stronger: **the 9b solved d7 p1, which the 7B failed even
  at samples=3** (`benchmark`/`scale` notes) — that's a capability the coder simply doesn't have here.
- **Cost.** The 9b arm took 15,944 s vs the 7B's 3,528 s — roughly **4.5× slower** even with thinking
  off (it's larger). A self-consistency (samples=3) run with the 9b on d1–7 would be ~13 h, so
  broader/sampled confirmation is expensive and should be scoped deliberately.
- Its attempt mix (25: 6 solved / 11 no_candidate / 5 wrong / 3 error) still shows room — thinking
  off is a blunt switch; a bounded thinking budget might do better than fully off.

## Takeaway

**qwen3.5:9b (thinking off) is a viable, stronger model on 16 GB** — the first evidence that the
capability ceiling can be pushed on this hardware, not only with a bigger machine. Recommended next
step: a scoped samples=3 run of the 9b on the problems the 7B couldn't reach (d4–7), to confirm the
d7 p1 win generalizes and see whether it cracks the other harder days — accepting the ~hours of wall
clock. This makes the 9b (not the 7B) the new baseline candidate for the "improve solve rates" work.

## Reproduce

```
venv/bin/python experiment.py --problems 2024:1-7 --trials 1 \
  --config "name=q9b,models=qwen3.5:9b,temperature=0.7,samples_per_model=1,enable_thinking=false" \
  --config "name=q7b,models=qwen2.5-coder:7b,temperature=0.7,samples_per_model=1"
```
