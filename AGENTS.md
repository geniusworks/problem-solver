# AGENTS.md — instructions for AI coding agents

Tool-neutral agent instructions (read natively by Windsurf, Cursor, Codex, Copilot, Aider, etc.).
Claude Code reads these via the one-line `@AGENTS.md` import in `CLAUDE.md`.

## What this project is

A research **platform for measuring LLM orchestration**, using Advent of Code as its testbed. It
runs local models (Ollama) against a correctness **oracle** with repeat trials, so every claim is
measured, not asserted. Secondarily, it's an AoC solver. See `README.md` for the full picture.

The larger objective is general problem-solving through orchestration; AoC is the testbed, not the
point. The path beyond it is sequenced as measurements in `PLAN.md`, "Beyond AoC". Until that
section's seam audit defines a problem-and-checker interface, keep AoC specifics (year/day/part,
fetch, the accepted-answer oracle) where they already live rather than spreading them into new
general code.

## Environment (important)

- **Always use the project venv.** Run Python as `venv/bin/python ...` (or activate the venv first).
  Never rely on a bare `python`/`python3` on PATH — if the system `python` resolves to a legacy
  Python 2, a bare invocation fails confusingly.
- **Use full paths for executables where PATH is ambiguous** — a shell function or alias can
  otherwise shadow a tool (e.g. `gh`).
- Models run via **local Ollama** (`http://localhost:11434`); on Apple Silicon, use a native
  **arm64** Python.
- **Python 3.11, installed from `requirements.lock`** — the exact package versions the results
  were measured with. Changing `requirements*.txt` means regenerating the lock (its header says
  how); a changed version on the measurement path (beautifulsoup4, autopep8, black, pylint,
  radon) is an instrument change, so note it in `dev/benchmarks/cross-machine-results.md`.

## Where things live

- `PLAN.md` — the roadmap: what is open now and the path beyond AoC, then the record.
- `dev/progress/checkpoint.md` — the **live status snapshot**. Read it at the start of a work
  session; update it (and the roadmap) as work lands so the docs never go stale.
- `dev/progress/*.md` — the committed findings (baselines, A/Bs, the capability frontier).
- `dev/benchmarks/cross-machine-results.md` — solve-rate results keyed by machine.
- `dev/benchmarks/m2max-handoff.md` — **if you are bringing up a new machine, read this first.**
  The M2 Max bring-up guide (its experiments ran in August 2026): setup, copying `years/` and
  `dev/experiments/`, and the gotchas. What to run now is in `checkpoint.md` and `PLAN.md`.
- `dev/docs/architecture.md` — design overview.

## How to work here

- **Measure before building.** New orchestration ideas are A/B'd through the harness
  (`experiment.py --trials N`, comparing `SolverConfig` fingerprints), with a committed result set
  and a written delta in `dev/progress/`. Don't add capability on faith.
- **Never start a run or a download without the maintainer's go.** Experiments, model pulls and
  package installs all wait for an explicit yes, and so does anything outward-facing (publishing,
  submitting to AoC). After a run, export it (`dev/export_results.py`), write it up and update the
  docs, in one PR.
- **Never conclude anything from `--trials 1` — including smoke tests.** The pipeline is
  non-deterministic: 4 of 6 problems flip between solved and unsolved across byte-identical configs
  (`dev/progress/baseline-2024-d1-3.md`). A single pass is a plumbing check, not a measurement. This
  has caused a real false alarm — a one-shot smoke returned 0/2 right after an Ollama upgrade and
  looked exactly like a runtime regression; `--trials 3` on the same config returned 6/6
  (`dev/progress/ollama-0.32.14-runtime-check.md`). Pre-run checks use `--trials 3`.
- **The oracle is authoritative.** Nothing counts as solved without independent verification against
  the cached accepted answer; keep `dev/verify_solutions.py` green.
- **Model-written code runs only through `shared/sandbox.py`**: an environment without `.env`
  secrets, under resource limits. A new code path that executes generated code uses it; none may
  inherit `os.environ`.
- **An instrument change is recorded before results are compared.** Ollama, a model, the machine,
  or a package on the measurement path (`requirements.lock`) changing goes into
  `dev/benchmarks/cross-machine-results.md`, then the `--trials 3` pre-run check. Where a cheaper
  direct check exists, run it first (the autopep8 upgrade was checked by comparing formatter output
  on all 74 recorded programs: byte-identical).
- **Docs currency is a standing rule, not a courtesy.** This is a research project: a stale doc is
  a wrong claim. Every PR that changes what is true must update the docs that state it, in the same
  PR — never in a later pass. The doc map, so nothing is missed:
  - `dev/progress/checkpoint.md` — live status; update whenever status changes (results, machine,
    blockers).
  - `dev/progress/<finding>.md` — one committed write-up per substantive result.
  - `dev/benchmarks/cross-machine-results.md` — every measured run adds/updates a row; machine
    specs filled in the moment a machine is real, never left *TBD*.
  - `dev/results/*.csv` — every measured run is exported (`venv/bin/python dev/export_results.py`);
    a published figure that changes is updated in `dev/recompute_results.py` in the same PR, and
    `venv/bin/python dev/recompute_results.py --check` must pass (CI runs it).
  - `PLAN.md` — re-point the roadmap when a blocker clears or a priority resolves.
  - `README.md` — only when a *claim* it makes changes (findings, status, thesis).
  - `dev/benchmarks/m2max-handoff.md` and other operational docs — correct anything a real run
    disproves.
  Some facts are repeated across docs: counts (tests, ledger, corpus), versions, and the open
  items. A PR that changes one searches for the old value and updates every occurrence. The
  open-items lists in `PLAN.md`, `checkpoint.md` and README agree: priority order, each item saying
  what it waits on (a maintainer decision, code, or GPU time).
  Correct your own record when a later run disproves an earlier claim, and say so in the doc — a
  falsified claim is replaced with the correction, not silently deleted. A documentation mistake
  (wrong count, stale status, overstated wording about existing data) is fixed in place with no
  note: the docs are the source of truth for the project, not a log of their own edits.
- **Published results lead with what is true now.** Current findings first, the history of how
  they changed below. A headline compares like with like (same draft count, problems and
  settings), or names every difference; its caveat sits beside it, not in a later section. Say
  whether a test is one- or two-sided; round a lower bound down, never up; keep what was measured
  apart from what is argued. Every figure README, RESULTS or the social card publishes is a claim
  in `dev/recompute_results.py`.
- **Standing order: a changed result is updated everywhere it is stated, in the same PR.** A run
  or analysis that moves a published figure (a rate, p-value, interval, verdict, count or corpus
  total) updates README, RESULTS, PLAN, `checkpoint.md`, the `dev/progress/` write-ups that quote
  it, `cross-machine-results.md`, and the social card: `assets/social-preview.html`, then
  `assets/social-preview.png` rendered from it with `venv/bin/python dev/render_social_preview.py`,
  then uploaded by the maintainer under the repo's Settings → General → Social preview (GitHub's
  link preview uses that uploaded copy, not the committed file, and no API can upload it).
  Search for the old value (`git grep`) rather than relying on memory, and add or update the
  claim in `dev/recompute_results.py`; its `--check` fails when a published figure drifts from
  the data or when the PNG was not rendered from the current HTML. A new verdict on a thesis arm
  changes the arm's status line in each of those files, not only the write-up.
- **Prune in the PR that orphans something.** A file, dependency (`requirements*.txt`,
  `requirements.lock`, `mypy.ini`), code path, config section, diagram or doc that nothing uses or
  links any more is deleted in the same PR. History lives in git, not in stale files, and docs
  name only what exists.
- **Check a claim before acting on it**, whoever made it: an outside review, an earlier doc, or
  this agent's own last message. Recompute numbers from `dev/results/`, read the code a claim is
  about, and name the claims that were wrong or overstated.
- **Don't narrate the prose.** Never add a phrase whose only job is to observe something the
  presentation, form, or wording already makes evident — *stated plainly*, *scoped precisely*, *in
  plain English*, *held plainly*, *to be clear*, *put simply*, or a heading that estimates its own
  reading time. If a passage is plain, it reads as plain; saying so adds a word and no information.
  Name the content instead: "Six findings and their numbers", not "Six findings, each a
  plain-language claim first, then the numbers".
- **Tests are part of the change.** Run them with `PYTHONPATH=. venv/bin/pytest -q`. Passing is
  not the same as covering: a PR that adds or changes behaviour adds a test that fails without it,
  and a bug fix adds the test that reproduces the bug. Never weaken, skip or delete a test to make
  it pass. Tests that need `years/` skip when it is absent. CI (tests, `mypy`,
  `dev/recompute_results.py --check`) passes before merge.
- **Never commit secrets or PII.** Configuration goes through `.env` (gitignored); see `.env.example`.

## Reproducing experiments

```
venv/bin/python experiment.py --problems 2024:4-7 --trials 3 \
  --config "name=<run>,models=<MODEL>,temperature=0.7,samples_per_model=3,enable_thinking=false"
```
Add `enable_thinking=false` for reasoning models or they over-reason and never emit code.

To reproduce any result recorded before 2026-10-13, also add
`problem_context=legacy,analysis_temperature=model_default,example_tests=parser`: those runs posed
Part 2 without the Part 1 statement (`dev/progress/part2-prompt-omits-part1.md`), and these
settings keep their fingerprints. The runs of 2026-10-13 itself need only `example_tests=parser`
(`dev/progress/example-tests-mispaired.md`).
