# Handoff: M1 16 GB → M2 Max 32 GB testing

**Audience:** a future agent (likely me, without this conversation's memory) picking up the project
on the **MacBook M2 Max / 32 GB** to run the experiments the M1 could not. Read this top-to-bottom
before running anything; it is the operational companion to `dev/benchmarks/cross-machine-results.md`
(the results table) and `dev/progress/checkpoint.md` (live status).

This file is internal (not referenced from the public `README.md`).

---

## 1. Where the M1 work landed (so you don't repeat it)

The platform is complete and sound (oracle, overfit gate, `--trials`, self-consistency, answer
consensus). On **M1 16 GB** the measured frontier on 2024 **d4–7** is:

- **`gemma4:12b` and `qwen3.5:9b` are co-leaders at 5/8** (thinking off, samp3). A tie, not a win.
- **d5 p2 and d6 p2 are uncracked by every 16 GB config** — the model finds the idea but the code is
  too slow for the full input (d6 p2 is Python-speed-bound even with a correct brute force); a 5×
  timeout recovered nothing. This is a capability/efficiency limit, not a harness limit.
- **d7 p2 is marginal** — solved only on lucky low-probability draws (gemma4 got it at samp1 but not
  samp3; the 9b got it once; the ensemble got it in *neither* run).
- **Cheap M1 orchestration levers are exhausted:** self-consistency (won, 39%→61%), thinking-off
  (won), timeout (no help), and a **same-tier ensemble (no help** — `ensemble-samp3-d4-7.md`: 5/8,
  ~2.2× cost, because the "complementary" solve was noise).
- **12 verified solutions** in the ledger (`solutions/README.md`), oracle-clean; `verify_solutions`
  is 12/12.

The upshot: on 16 GB, capability is the binding constraint past the easy problems, and the *central
thesis* (does voting help at a **strong** model's own frontier?) is untestable here because the
strong models don't fit. That is the M2 Max's job.

## 2. The two questions to answer on the M2 Max

**Q1 — Capability: does a 30B-class model crack what no 16 GB model could?**
Directly comparable to the M1 rows: run a strong model at samp3 on 2024 **d4–7** and see if it
exceeds 5/8 and, specifically, cracks **d5 p2 / d6 p2**.

**Q2 — The central open thesis: does sampling+voting still add correctness at a *strong* model's own
frontier (pass@k > pass@1)?** This is the load-bearing experiment for the whole "does orchestrated
voting scale?" question (README section of that name). Method in §5.

## 3. Setup on the M2 Max

```bash
# from the repo root
MODEL_TIER=32 ./scripts/setup.sh      # venv + deps + .env scaffold + pulls the 32 GB tier
```

The 32 GB tier pulls (verify tags at https://ollama.com/library if any 404 — they drift):
- `qwen2.5-coder:32b`  (~20 GB Q4 — the code-specialized 32B the M1 couldn't hold)
- `qwen3-coder:30b`    (30B-MoE current-gen local coder; the cross-machine plan calls it
  `Qwen3-Coder-30B-A3B` — confirm the exact Ollama tag)
- plus the M1 models (`gemma4:12b`, `qwen3.5:9b`, `qwen2.5-coder:7b`) so you can re-run them for a
  **machine-speed vs capability** separation (same model, more RAM → faster, *same* solve rate).

Notes:
- **You must bring `years/` with you — this is the one step a fresh clone cannot do for you.**
  `years/` is gitignored, so the cached problem HTML, puzzle *inputs*, and the scraped accepted
  answers (the oracle's ground truth) do **not** come with the repo. On a machine without it,
  `verify_solutions.py` reports `0 correct, 0 wrong, 12 error — missing input file`, and no
  experiment can be scored. Two ways to fix it, in order of preference:
  1. **Copy it from the M1** (exact reproduction, no network, no AoC load):
     `rsync -av <m1-host>:~/Herd/problem-solver/years/ years/`
  2. **Re-fetch** with `AOC_SESSION` set in `.env`. This works because AoC renders
     `Your puzzle answer was …` into the page of any day *that account* has solved, which is where
     `shared/ground_truth.py` gets the oracle from. **It must be the same AoC account as the M1** —
     inputs are per-account, so a different cookie yields different inputs and different answers,
     and the results stop being comparable to the M1 rows.
  Earlier revisions of this doc said `AOC_SESSION` is optional and the oracle "runs fully offline".
  That was only true *on the M1*, where `years/` already existed locally.
- The venv Python must be native **arm64** (`venv/bin/python`), never a bare `python`/`python3`
  (there's a legacy Intel `python2` on PATH). See `AGENTS.md`.
- **The M2 Max started from a cold `learning/solver.db`** (2026-08-15). The M1's warm copy came
  across and is preserved at `learning/solver.m1-warm-20260815.db` (gitignored, like every `*.db`);
  the live DB was deleted and `LearningDatabase` re-created it from `schema.sql`. This matters less
  than it sounds: the M1 DB's *only* populated table was `model_performance` (27 rows) —
  `strategy_weights` and `strategy_results` were **empty**, so the strategy-effectiveness weighting
  in `StrategyRecommender` had never actually been active on any M1 run. The warm data only fed
  `_get_top_models` ranking, which a single-model `models=` run doesn't exercise. So M1↔M2 runs stay
  comparable; restore the backup over `solver.db` if you ever need the exact M1 state.
- **`gh` is not installed on the M2 Max.** `AGENTS.md` mentions `/opt/homebrew/bin/gh`; that was the
  M1. Push the branch and open the PR in a browser, or `brew install gh`.
- **Python 3.14 works** (verified on the M2 Max, 2026-08-15) after two dependency fixes landed:
  `pydantic` was pinned to `==2.5.2`, which has no cp314 wheel and forced a doomed from-source Rust
  build, and `coverage==7.3.3` contradicted `pytest-cov==6.2.1` (`needs >=7.5`) — that second one
  made `requirements-dev.txt` uninstallable on *every* machine. If `setup.sh` ever fails building a
  wheel again, re-run it against an older interpreter: `PYTHON=python3.12 ./scripts/setup.sh`.
- Sanity check before big runs: `PYTHONPATH=. venv/bin/python dev/verify_solutions.py` → expect
  `12 correct, 0 wrong`. And `PYTHONPATH=. venv/bin/pytest -q` → expect green: **186 passed** with
  `years/` present (2026-08-15). Without `years/` you get `162 passed, 24 skipped` — those 24 are
  data-dependent and skip themselves, so a green-but-skipping suite is the tell that the oracle data
  never made it onto the machine.

## 4. Exact commands (Q1 — capability, directly comparable to M1)

```bash
# 30B at samp3 on the M1 comparison set. Does it beat 5/8? Crack d5p2/d6p2?
venv/bin/python experiment.py --problems 2024:4-7 --trials 1 \
  --config "name=qwen25c32b-samp3,models=qwen2.5-coder:32b,temperature=0.7,samples_per_model=3,enable_thinking=false"

# repeat for the MoE coder
venv/bin/python experiment.py --problems 2024:4-7 --trials 1 \
  --config "name=qwen3coder30b-samp3,models=qwen3-coder:30b,temperature=0.7,samples_per_model=3,enable_thinking=false"
```

## 5. Exact design (Q2 — the pass@k-vs-pass@1 thesis test)

The thesis is scale-invariant only if voting still helps where the *strong* model is uncertain. So:

1. **Find the strong model's frontier band** — the problems it solves *sometimes but not always*. Do
   a broad, cheap scan first (samp1, 1 trial) across a wide range, e.g. 2024 d1–15 or d8–20:
   ```bash
   venv/bin/python experiment.py --problems 2024:8-20 --trials 1 \
     --config "name=scan,models=qwen2.5-coder:32b,temperature=0.7,samples_per_model=1,enable_thinking=false"
   ```
   From the result, pick the **"sometimes"** problems (not the ones it always or never solves). If
   d5 p2 / d6 p2 / d7 p2 are now *sometimes*-solved by the 30B, they're ideal targets.
2. **Compare pass@1 vs pass@k on that band, with repeats.** `samples_per_model=N` *is* pass@N in one
   run (draw N, verify, keep the best). Use `--trials` to estimate the probability:
   ```bash
   venv/bin/python experiment.py --problems 2024:<frontier-band> --trials 5 \
     --config "name=k1,models=qwen2.5-coder:32b,temperature=0.7,samples_per_model=1,enable_thinking=false" \
     --config "name=k3,models=qwen2.5-coder:32b,temperature=0.7,samples_per_model=3,enable_thinking=false" \
     --config "name=k5,models=qwen2.5-coder:32b,temperature=0.7,samples_per_model=5,enable_thinking=false"
   ```
   **The thesis holds if k3/k5 solve the "sometimes" problems at a materially higher rate than k1.**
   Report per-problem k/5 (the harness prints any/all across trials). A flat line (k3 ≈ k1 on the
   frontier band) would be evidence *against* scale-invariance — record either honestly.
3. Temperature matters for pass@k (need diverse draws). 0.7 is the standing default; if k>1 shows no
   spread, try 0.8–1.0 and note it.

## 6. Where and how to record results

1. **Fill in the machine row** in `dev/benchmarks/cross-machine-results.md` → *Machines* table:
   `m2max-32` (chip, RAM 32, cores, macOS version, ollama version, usable-model note). Get these from
   the actual machine (`sysctl -n hw.memsize`, `sw_vers`, `ollama --version`).
2. **Append result rows** tagged `m2max-32`, keeping the config columns identical to the m1-16 rows
   so they line up (same model/config → same row shape on both machines).
3. **Write a finding doc** in `dev/progress/` for each substantive result (e.g.
   `m2max-30b-d4-7.md`, `m2max-passk-thesis.md`), following the house style: state the config, the
   measured numbers, an honest headline, and correct any prior claim the data disproves.
4. **Update `dev/progress/checkpoint.md`** (the live status) and, if a claim in `README.md` changes,
   update the README too (keep docs fresh per PR).
5. One PR per finding; verify the ledger stays clean (`dev/verify_solutions.py`).

## 7. Gotchas & lessons (these cost real time on the M1)

- **The model list is PIPE-separated, not comma:** `models=gemma4:12b|qwen3.5:9b`. `--config` splits
  `key=value` pairs on commas, so a comma inside `models=` mis-parses. (`experiment.py:parse_config`.)
- **Always `enable_thinking=false`** for reasoning models, or they emit tens of thousands of chars of
  chain-of-thought and never reach the code (`done_reason=length`). This applies to qwen3.x and any
  reasoning-native model; confirm the 30B's behavior early.
- **`enable_fallback_models` defaults to `True`.** A single-model config can fall back to *other*
  installed models. For a clean single-model number, verify from the run JSON that only your model
  produced candidates (per-problem `candidate_models`), or set `enable_fallback_models=false`.
- **A single-sample solve on a hard problem is often luck.** Use `--trials` (≥5) and/or `samples>1`
  before believing any Part-2 solve is a real capability. This bit us twice (gemma4 & 9b d7 p2).
- **Reboots kill both the run and the monitor.** A long run is launched detached (`nohup … &`) and
  survives the session ending, but **not** a machine reboot — and the completion Monitor does **not**
  survive a session teardown either. After any interruption, don't assume it's still running: check
  `ps`, the log tail, and whether a `*_<config>_*.json` result file exists in `dev/experiments/`
  (that JSON is written only on normal completion). Re-launch if incomplete.
- **Result JSONs live in `dev/experiments/` (gitignored).** They carry per-problem, per-candidate
  `model`/outcome/token data — the authoritative record of *which model solved what*. The `.log` file
  is buffered and mostly pylint noise until the final summary table; trust the JSON.
- **The ledger records the *first* model to solve a problem.** A later model re-solving an already
  recorded problem does not change attribution — don't read the ledger's model column as "the only
  model that can solve this."
- **Wall clock:** 30B models are slow. The M1 ensemble run was ~9 h for 8 problems at samp3. Budget
  hours, launch detached, and prefer narrow problem sets for the pass@k sweep.

## 8. Key files to read first (fresh session)

- `AGENTS.md` — environment rules (venv, full paths) and where things live.
- `dev/progress/checkpoint.md` — live status snapshot.
- `dev/benchmarks/cross-machine-results.md` — the results table + the m2max run plan.
- `dev/progress/`: `gemma4-samp3-confirmation.md`, `ensemble-samp3-d4-7.md`,
  `9b-confirmation-d4-7.md`, `9b-timeout-investigation.md` — the frontier findings.
- `README.md` §"Does orchestrated voting scale?" — the thesis this testing is meant to settle.
