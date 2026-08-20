# Temperature is not the lever: a clean negative result

**Raising `temperature` from 0.7 to 1.0 did nothing for the two problems that resist sampling, and
slightly hurt one that did not.** 6/12 → **5/12**. Nine hours of compute to remove a plausible option
from the roadmap.

This tests — and falsifies — a specific hypothesis this project derived from its own data.

- **Config:** `models=qwen3.8:27b, temperature=1.0, samples_per_model=3, enable_thinking=false`
  (fingerprint `f5292ef44909`), 3 trials, 2024 d15 + 2025 d9 (both parts each).
- **Baseline: not re-run.** Temperature enters the config fingerprint, and the identical
  `temperature=0.7` k3 arm already covers these four parts (`passk-ab-d13-d15.md`,
  `passk-replication-2025.md`), so only the 1.0 arm was needed. Halved the cost of the comparison.
- **Cost:** 32,249 s (9h). **0 wrong / 0 unverified / 0 overfit.**
- **Run:** `dev/experiments/20260820T010917Z_temp10-k3_f5292ef44909.json` (gitignored).

## Result

| problem | role | temp 0.7 @ k3 | **temp 1.0 @ k3** | verdict |
|---------|------|---------------|-------------------|---------|
| 2024 d15 p1 | sometimes | 3/3 (100%) | **2/3 (67%)** | slightly worse |
| **2024 d15 p2** | **wall** | 0/3 | **0/3** | unmoved — now **0/11** overall |
| 2025 d9 p1 | sometimes | 3/3 (100%) | **3/3 (100%)** | unchanged |
| **2025 d9 p2** | **wall** | 0/3 | **0/3** | unmoved — now **0/10** overall |
| **total** | | **6/12** | **5/12** | **no gain** |

## The hypothesis this kills

From the pass@k A/B, 2024 d15 p2 failed 0/3 at k=3 despite a 33% single-draw rate — an outcome with
probability ~0.03 if draws were independent. The reading recorded at the time was **correlated
draws**: *"sampling multiplies draws, not diversity … where failure is systematic rather than
stochastic, extra draws re-roll the same die."* The stated next lever was diversity, with
temperature named as the cheapest instrument.

**The diagnosis may well be right. Temperature is not the fix.** Sampling more wildly from the same
flawed understanding produces noisier variants of the same wrong approach, not a different approach.

The distinction now worth carrying:

- **Parameter-level diversity** (temperature, top-p) perturbs token selection *within* an approach.
  **Tested. Does not help these failures.**
- **Strategy-level diversity** (prompting explicitly for a different algorithm; a genuinely
  different model) changes *which* approach is attempted. **Untested — and better motivated now
  that the cheap alternative is ruled out.**

## The walls are now the project's most reproducible results

**2024 d15 p2: 0/11. 2025 d9 p2: 0/10.** Across `samples_per_model` ∈ {1,3},
`max_repair_iterations` ∈ {0,2}, and `temperature` ∈ {0.7,1.0} — one problem per year, never solved
once. These are not noisy failures; they are stable properties of this model on these problems, and
they remain the sharpest available benchmark for any future claim to have decorrelated draws.

## On being wrong four times

This is the fourth hypothesis in this line of work to be falsified by the next run:

1. *"Insight problems won't fall to sampling"* — falsified by 2024 d13 p2 (1/6 → 3/3).
2. *"Voting buys execution reliability, not ideas"* — falsified by the same problem.
3. *"Failure mode predicts whether a problem is sometimes-solvable"* — falsified by the 2025 band
   (crash-class d11 p2 *is* a "sometimes"; three of four wrong-answer problems are walls).
4. *"Correlated draws → temperature will decorrelate them"* — falsified here.

The consistent pattern: **mechanistic stories about *why* these models fail have repeatedly failed
to predict what actually helps.** Direct measurement has been the only reliable guide. That is an
argument for keeping the A/B discipline expensive-but-first, not for theorising harder.

Recording a negative result at this length is deliberate. It cost nine hours, it removes a real
option, and the next person to think "just raise the temperature" should find this instead of
repeating it.

## Reproduce

```
venv/bin/python experiment.py --problems 2024:15,2025:9 --trials 3 \
  --config "name=temp10-k3,models=qwen3.8:27b,temperature=1.0,samples_per_model=3,enable_thinking=false"
```
