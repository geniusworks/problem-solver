# AGENTS.md — instructions for AI coding agents

Tool-neutral agent instructions (read natively by Windsurf, Cursor, Codex, Copilot, Aider, etc.).
Claude Code reads these via the one-line `@AGENTS.md` import in `CLAUDE.md`.

## What this project is

A research **platform for measuring LLM orchestration**, using Advent of Code as its testbed. It
runs local models (Ollama) against a correctness **oracle** with repeat trials, so every claim is
measured, not asserted. Secondarily, it's an AoC solver. See `README.md` for the full picture.

## Environment (important)

- **Always use the project venv.** Run Python as `venv/bin/python ...` (or activate the venv first).
  Never rely on a bare `python`/`python3` on PATH — this machine has a legacy Intel `python2` at
  `/usr/local/bin/python`.
- **Use full paths for other executables** where PATH is ambiguous (e.g. `/opt/homebrew/bin/gh` — a
  shell function can otherwise shadow `gh`).
- Models run via **local Ollama** (`http://localhost:11434`); the venv Python is native **arm64**.

## Where things live

- `PLAN.md` — the forward roadmap and "Next steps for the maintainer".
- `dev/progress/checkpoint.md` — the **live status snapshot**. Read it at the start of a work
  session; update it (and the roadmap) as work lands so the docs never go stale.
- `dev/progress/*.md` — the committed findings (baselines, A/Bs, the capability frontier).
- `dev/benchmarks/cross-machine-results.md` — solve-rate results keyed by machine.
- `dev/benchmarks/m2max-handoff.md` — **if you are running on the M2 Max / 32 GB (or any >16 GB
  machine), read this first.** Operational handoff: what the M1 established, the two experiments to
  run (30B capability + the pass@k thesis test), exact setup/commands, and the gotchas.
- `dev/docs/architecture.md` — design overview.

## How to work here

- **Measure before building.** New orchestration ideas are A/B'd through the harness
  (`experiment.py --trials N`, comparing `SolverConfig` fingerprints), with a committed result set
  and a written delta in `dev/progress/`. Don't add capability on faith.
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
  - `PLAN.md` — re-point the roadmap when a blocker clears or a priority resolves.
  - `README.md` — only when a *claim* it makes changes (findings, status, thesis).
  - `dev/benchmarks/m2max-handoff.md` and other operational docs — correct anything a real run
    disproves.
  Correct your own record when a later run disproves an earlier claim, and say so in the doc — a
  falsified claim is replaced with the correction, not silently deleted.
- **Run tests:** `PYTHONPATH=. venv/bin/pytest -q`.
- **Never commit secrets or PII.** Configuration goes through `.env` (gitignored); see `.env.example`.

## Reproducing experiments

```
venv/bin/python experiment.py --problems 2024:4-7 --trials 1 \
  --config "name=<run>,models=<MODEL>,temperature=0.7,samples_per_model=3,enable_thinking=false"
```
Add `enable_thinking=false` for reasoning models or they over-reason and never emit code.
