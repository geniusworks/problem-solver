# Problem Solver

A research platform for **measuring LLM orchestration**, using Advent of Code as its testbed. It
attempts autonomous solutions with local LLMs (via Ollama) and — more importantly — measures how
well different orchestration strategies actually work, against a correctness oracle, with repeat
trials, so results are evidence rather than anecdote.

The project began as an unmeasurable pipeline. Its through-line since has been: **make every claim
measured.** The sections below capture what that produced.

## What it is

Two things, in order of importance:

1. **A measurement platform.** A frozen, fingerprinted `SolverConfig`; an experiment harness
   (`experiment.py`, `shared/experiment/`) that runs a problem set under one or more configs with
   `--trials N`; a correctness **oracle** (`shared/verification.py`, `shared/ground_truth.py`) that
   judges every candidate against the cached accepted AoC answer, with an overfit gate
   (`shared/overfit_detection.py`); and independent verification so *claimed* and *verified* are
   never conflated. This is what lets an orchestration idea be A/B'd for a real delta.

2. **An AoC solver.** `BaseSolver.solve_problem` (`shared/solver.py`) is a short orchestrator over
   four stages — prepare → generate → consensus → execute/repair/fallback — driving local models to
   solve a puzzle and recording verified solutions to a ledger (`solutions/README.md`).

## What the measurements found

Every one of these is a committed A/B or analysis in `dev/progress/`, not an assertion:

- **Single runs are noise.** The pipeline is non-deterministic; across byte-identical configs,
  4 of 6 baseline problems flipped between solved and unsolved. Reporting needs repeat trials.
- **Self-consistency is a real win.** Drawing several samples per model (`samples_per_model`) at
  `temperature>0` lifted the solve rate **39% → 61%** on 2024 d1–3 and took **0 → 3 of 6** problems
  to *solved every trial*. It cures run-to-run variance on problems the model can already sometimes
  solve. (`dev/progress/milestone-e-self-consistency.md`)
- **Answer-based consensus is a good no-oracle selector.** On the sample data, plurality vote over
  the *executed* answer would have picked the correct answer 10/11 times — the selector the
  submission phase needs. (`dev/progress/milestone-e-answer-consensus.md`)
- **The model has a hard capability ceiling.** The winning config on the never-scored 2024 d4–7
  solved only **1 of 8**: the 7B either can't emit runnable code (59% of attempts) or emits
  confidently-wrong code (39%). Self-consistency fixes *variance*, not *capability*. Broader
  coverage needs a stronger model, not more orchestration.
  (`dev/progress/scale-2024-d4-7.md`)

The honest headline: **on this hardware, `qwen2.5-coder:7b` solves the easy end of AoC 2024 reliably
and is genuinely out of depth past it** — a frontier that was assumed for a long time and is now
measured.

## Running an experiment

The platform's primary entry point is `experiment.py`:

```bash
# One config over 2024 days 1-3, 5 trials (the pipeline is non-deterministic)
venv/bin/python experiment.py --problems 2024:1-3 --trials 5 \
    --config "name=baseline,models=qwen2.5-coder:7b"

# A/B two configs and print a comparison (self-consistency isolated)
venv/bin/python experiment.py --problems 2024:1-3 --trials 3 \
    --config "name=samp1,models=qwen2.5-coder:7b,temperature=0.7,samples_per_model=1" \
    --config "name=samp3,models=qwen2.5-coder:7b,temperature=0.7,samples_per_model=3"

# Score already-recorded solutions without calling a model
venv/bin/python experiment.py --problems 2024:1-6 --dry-run
```

`--config` takes `key=value` overrides of `SolverConfig`; every field that enters the config
fingerprint changes what a run does, so two configs with different fingerprints are genuinely
different experiments. Verify the recorded solutions at any time with `dev/verify_solutions.py`.

## Solving a single problem

```bash
python solve.py --year 2024 --day 1 --part 1   # --force to re-solve, --debug for logs
```

## Getting started

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   pip install -r requirements-dev.txt
   ```
2. Install [Ollama](https://ollama.ai) and pull at least one coding model (the solver checks which
   configured models are actually installed and errors clearly if none are):
   ```bash
   ollama pull qwen2.5-coder:7b
   ```
3. `AOC_SESSION` (optional): only needed to **fetch** problems/inputs not already cached under
   `years/`, or to wire the (currently unwired) submission phase. Put it in `.env` (gitignored) —
   see the session-cookie steps below. Cached problems run fully offline, oracle and all.
4. Run tests: `PYTHONPATH=. venv/bin/pytest -q`

To get the session cookie (Safari): enable the Develop menu (Settings → Advanced → "Show features
for web developers"), log in to adventofcode.com, open Web Inspector (⌥⌘I) → Storage → Cookies →
adventofcode.com, and copy the **`session`** value. It is a secret — keep it in `.env`, never commit
it.

## Advent of Code parts and examples

Each AoC day's page has one or two `<article class="day-desc">` blocks — Part 1 uses the first,
Part 2 the second. Only the selected article is parsed and sent to the models, so each part is
solved in isolation (no Part 2 text leaks while solving Part 1). The parser extracts the example
`<pre><code>` block and infers its expected output from the surrounding prose, giving a small-input
oracle alongside the cached full-input answer.

## How the code is organized

```
experiment.py            Experiment harness entry point (--trials, --config, A/B)
solve.py                 Single-problem entry point
shared/
  experiment/            The platform: SolverConfig, results, runner
  verification.py        Correctness oracle (candidate vs accepted answer)
  ground_truth.py        Cached accepted answers
  overfit_detection.py   Overfit gate before a solution is recorded
  solver.py              BaseSolver.solve_problem orchestrator + stages
  aoc.py                 AoC I/O: session, HTTP, problem fetch + cache
  paths.py               Path primitives (leaf module, no cycles)
  ledger.py              Oracle-gated solution recording
  llm/                   Ollama provider (local.py) + prompts.py
  strategy_recommender.py, strategies.py   Strategy seeding
learning/                One SQLite DB: model + strategy performance
submission/              Real AoC submitter -- isolated and UNWIRED (reserved for the solver phase)
solutions/               Verified solutions + the ledger (README.md)
dev/progress/            The measured findings (baselines, A/Bs, the capability frontier)
dev/benchmarks/          Cross-machine results, keyed by hardware (solve rate by model/config)
years/                   Cached problem data (gitignored)
```

`PLAN.md` (repo root) is the forward roadmap; `dev/progress/checkpoint.md` is the live status
snapshot and `dev/docs/architecture.md` the design overview.

## Status

**Working and measured:** the full solve pipeline (fetch → parse → generate → consensus →
execute/verify → repair → fallback), the experiment harness with repeat trials, the correctness
oracle and overfit gate, self-consistency sampling and answer-based consensus, and 5 verified
recorded solutions.

**Deliberately unwired:** the AoC answer submitter (`submission/`) is real and tested in isolation
but not in the solve loop — there is no genuinely-unseen problem to submit against yet (a past
year's puzzles are all already solved on the author's account).

**Blocked on hardware:** the highest-value open experiment — does a stronger model clear the
capability ceiling? — can't run on 16 GB (a 32B model swaps; mid-size models are too slow for a full
sweep). It needs more RAM or a remote endpoint.

## Credits & license

Developed by **Martin Diekhoff**. MIT License — see [LICENSE](LICENSE).
