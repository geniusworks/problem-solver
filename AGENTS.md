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
- **Never conclude anything from `--trials 1` — including smoke tests.** The pipeline is
  non-deterministic: 4 of 6 problems flip between solved and unsolved across byte-identical configs
  (`dev/progress/baseline-2024-d1-3.md`). A single pass is a plumbing check, not a measurement. This
  has caused a real false alarm — a one-shot smoke returned 0/2 right after an Ollama upgrade and
  looked exactly like a runtime regression; `--trials 3` on the same config returned 6/6
  (`dev/progress/ollama-0.32.14-runtime-check.md`). Pre-run checks use `--trials 3`.
- **The oracle is authoritative.** Nothing counts as solved without independent verification against
  the cached accepted answer; keep `dev/verify_solutions.py` green.
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
  Correct your own record when a later run disproves an earlier claim, and say so in the doc — a
  falsified claim is replaced with the correction, not silently deleted. A documentation mistake
  (wrong count, stale status, overstated wording about existing data) is fixed in place with no
  note: the docs are the source of truth for the project, not a log of their own edits.
- **Don't narrate the prose.** Never add a phrase whose only job is to observe something the
  presentation, form, or wording already makes evident — *stated plainly*, *scoped precisely*, *in
  plain English*, *held plainly*, *to be clear*, *put simply*, or a heading that estimates its own
  reading time. If a passage is plain, it reads as plain; saying so adds a word and no information.
  Name the content instead: "Six findings and their numbers", not "Six findings, each a
  plain-language claim first, then the numbers".
- **Run tests:** `PYTHONPATH=. venv/bin/pytest -q`.
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
