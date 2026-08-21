# Targeted wrong-answer feedback: no gain — and a sharper rule for what to try next

**Telling the model its answer is wrong, and that a clean-running wrong answer usually means a
misread requirement, did not help.** 6/12 → **5/12**, with one previously-reliable problem slipping.

Unlike the first version of this feature, **the intervention definitely fired**: the new guidance
appears in **49 of 70** attempt records. This is a real null, not an inert flag.

- **Config:** `models=qwen3.8:27b, temperature=0.7, samples_per_model=3, enable_thinking=false,
  targeted_feedback=true` (fingerprint `81a0271ba1a6`), 3 trials, 2024 d15 + 2025 d9.
- **Baseline:** the existing k3 arms (behaviourally `targeted_feedback=False`).
- **Cost:** 32,555 s (9h). **0 wrong / 0 unverified / 0 overfit.**
- **Run:** `dev/experiments/20260821T223817Z_targetedfb-k3_81a0271ba1a6.json` (gitignored).

## Result

| problem | role | baseline | **with guidance** | |
|---------|------|----------|-------------------|---|
| 2024 d15 p1 | control | 3/3 | **3/3** | unchanged |
| 2024 d15 p2 | ~12% problem | 0/3 | **0/3** | unchanged |
| 2025 d9 p1 | control | 3/3 | **2/3** | slipped |
| 2025 d9 p2 | wall | 0/3 | **0/3** | unchanged (now **0/13**) |
| **total** | | **6/12** | **5/12** | **no gain** |

The shape is identical to the temperature result: targets unmoved, one working problem down a notch.
At n=3 that slip is within noise — but it is now the **second** intervention to show it.

## Why it plausibly failed: no new information

The guidance told the model that its answer was wrong and that the cause was probably a misread
requirement. **The model already knew the answer was rejected** — that is what the default message
says. The addition named a *category* of error without identifying *which* requirement was misread,
and the one piece of information that would resolve it — the expected answer — **cannot be supplied
without destroying the measurement**. Handing the model its target would make the overfit gate the
only barrier to a hardcoded "solution".

So the intervention was exhortation, not information. It asked the model to notice a mistake it had
no new means of noticing.

## The rule this yields (five falsified hypotheses in, the pattern is the finding)

1. *"Insight problems won't fall to sampling"* — falsified (2024 d13 p2, 1/6 → 3/3).
2. *"Voting buys execution reliability, not ideas"* — falsified by the same problem.
3. *"Failure mode predicts sometimes-solvability"* — falsified by the 2025 band.
4. *"Correlated draws → temperature will decorrelate them"* — falsified (`temperature-diversity-negative.md`).
5. *"Better-worded repair feedback will help"* — falsified here.

Read together they are sharper than any one of them:

> **Interventions that add no new information do not help, however well-targeted the wording.**
> Temperature added variance without information. This added exhortation without information. The
> two things that *have* worked add real information: **sampling** contributes genuinely independent
> draws, and **repair** contributes an actual traceback.

**This is a usable filter for the roadmap.** Before running anything, ask: *what does the model
learn that it did not already know?* If the answer is "nothing", expect a null.

Under that filter:

- **Prompt variants** ("optimise for time complexity", "propose three approaches") — **demoted**.
  Same class as this experiment: rewording without new information. Cheap, but now low prior.
- **Cross-generation model mixing** — **promoted**. A second model's differing answer *is* new
  information, and it is arm 3 of the README thesis (decorrelated portfolios), still untested.
- **Feeding back a failing case the model has not seen** — **promoted**, and the strongest fit for
  the filter. Both target problems pass the worked example and fail the real input, so the
  distinguishing case is precisely what the model never sees. Constructing one without leaking the
  answer is the hard part and the interesting design problem.

## Limits

- Two target problems, 3 trials, one model. A null here is not proof of no effect anywhere.
- One of the two targets (2024 d15 p2) is a ~12% problem, so its 0/3 is weak evidence either way
  (`CORRECTION-d15p2-is-not-a-wall.md`). Only 2025 d9 p2's 0/3 speaks to a genuine wall.
- The control slip (d9 p1 3/3 → 2/3) is n=3 and should not be read as a measured cost.

## Reproduce

```
venv/bin/python experiment.py --problems 2024:15,2025:9 --trials 3 \
  --config "name=targetedfb-k3,models=qwen3.8:27b,temperature=0.7,samples_per_model=3,enable_thinking=false,targeted_feedback=true"
```
