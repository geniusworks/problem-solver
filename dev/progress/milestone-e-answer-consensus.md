# Answer-based consensus — the no-oracle candidate selector

Milestone E, built *after* measuring that it works. On problems with a cached accepted
answer the oracle decides, so consensus is irrelevant there; it matters for the
submission phase (F), where there is no oracle and the solver must pick one candidate
from several. The plan's rule is "re-add orchestration only with harness evidence", so
the evidence came first.

## The evidence (offline, no new run)

The self-consistency samp3 run already recorded every candidate's *executed* answer, so
"would a majority vote have picked the correct answer?" is answerable from that JSON
without generating anything. Over the 11 solved problem-trials (those with at least one
correct candidate):

- **plurality vote == correct: 10 / 11 (91%)**
- strict-majority (> half) == correct: 8 / 11

The one miss is instructive: `2024 d2 p1` had two wrong candidates agree on `1000` and
outvote the single correct `421`. That is the technique's inherent failure mode — wrong
answers *can* agree — and it is why the implementation requires a quorum before consensus
is allowed to override the quality heuristic.

## What was built

`BaseSolver._select_candidate(validated, quality_scores, known_answer)` centralises the
choice among candidates that passed verification:

- **With an oracle** — every validated candidate already matches the accepted answer, so
  code quality just breaks the tie (unchanged behaviour).
- **Without an oracle** — group the candidates by executed answer; if the plurality answer
  has at least `min_consensus_models` (default 2) votes, pick the highest-quality candidate
  that produced it; otherwise fall back to highest quality. This is the answer-based
  consensus the plan called for, and it rides directly on the candidate-pool / executed-
  answer plumbing the self-consistency PR added.

Five unit tests pin the selector: oracle→quality, plurality preference over a
higher-quality minority answer, no-quorum fallback, the documented wrong-agreement failure
mode, and abstention by answer-less candidates.

## Why no live A/B here

Its effect is only visible where there is no oracle — the submission phase (F), which is
deferred and needs a fresh `AOC_SESSION`. The retrospective 10/11 is the evidence that
justifies having it ready; a live A/B belongs with F, on genuinely unseen problems, where
the plurality answer is the *only* signal.
