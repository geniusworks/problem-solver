#!/usr/bin/env bash
#
# One-shot setup for running this project on a new machine (macOS / Apple Silicon).
# Creates the venv, installs deps, checks Ollama, and pulls a model tier matched to
# available RAM. Then you can reproduce experiments (see AGENTS.md / the benchmark doc).
#
# Usage:
#   ./scripts/setup.sh                 # auto-detect tier from RAM
#   MODEL_TIER=32 ./scripts/setup.sh   # force a tier (16 | 32 | 64)
#   SKIP_MODELS=1 ./scripts/setup.sh   # env only, no model downloads
#
# Model tiers are what actually FIT (Q4, leaving ~headroom for KV cache + macOS).
# 16 GB caps at ~dense-14B; 32 GB fits the 30-32B class; 64 GB+ fits 70B / large MoE.
# The exact tags for 2026-era models drift -- verify at https://ollama.com/library
# if a pull 404s; the script continues past any model it can't fetch.

set -uo pipefail
cd "$(dirname "$0")/.."
ROOT="$(pwd)"
echo "== Problem Solver setup =="
echo "repo: $ROOT"

# --- 1. Python venv (must be native arm64; avoid a stray Intel python2 on PATH) ---
PY="${PYTHON:-python3}"
if ! command -v "$PY" >/dev/null 2>&1; then
  echo "ERROR: python3 not found. Install it (e.g. 'brew install python@3.11') and retry." >&2
  exit 1
fi
ARCH="$("$PY" -c 'import platform;print(platform.machine())' 2>/dev/null || echo unknown)"
echo "python: $("$PY" --version 2>&1) [$ARCH]"
if [ "$ARCH" != "arm64" ]; then
  echo "WARNING: $PY is '$ARCH', not arm64 -- prefer a native Apple-Silicon python3 (brew's)." >&2
fi
if [ ! -d venv ]; then
  echo "creating venv ..."; "$PY" -m venv venv
fi
echo "installing dependencies ..."
./venv/bin/python -m pip install -q --upgrade pip
# Resolve runtime + dev together: they share pins (e.g. coverage), and installing
# them in two passes lets the second silently downgrade the first. Note this
# script does NOT use `set -e` -- check the status explicitly or a failed install
# gets reported as success and the failure only surfaces much later.
DEV_REQ=(); [ -f requirements-dev.txt ] && DEV_REQ=( -r requirements-dev.txt )
if ! ./venv/bin/python -m pip install -q -r requirements.txt "${DEV_REQ[@]}"; then
  echo "ERROR: dependency install failed (see pip output above)." >&2
  echo "  If a package tried to build from source, your python ($("$PY" --version 2>&1))" >&2
  echo "  is probably newer than a pinned dependency has wheels for. Either install a" >&2
  echo "  supported interpreter and re-run as 'PYTHON=python3.12 ./scripts/setup.sh'," >&2
  echo "  or relax the pin in requirements.txt." >&2
  exit 1
fi
echo "  deps installed."

# --- 2. .env scaffold ---
if [ ! -f .env ] && [ -f .env.example ]; then
  cp .env.example .env
  echo "created .env from .env.example (edit it: AOC_SESSION only needed to fetch new problems)."
fi

# --- 3. Ollama ---
if ! command -v ollama >/dev/null 2>&1; then
  echo "WARNING: 'ollama' not found. Install from https://ollama.ai, then re-run (or SKIP_MODELS=1)." >&2
  MODELS_OK=0
else
  MODELS_OK=1
  # nudge the server awake
  curl -s --max-time 4 http://localhost:11434/api/tags >/dev/null 2>&1 || (ollama serve >/dev/null 2>&1 &) || true
fi

# --- 4. Pick a model tier by RAM ---
RAM_GB=$(( $(sysctl -n hw.memsize 2>/dev/null || echo 0) / 1073741824 ))
if [ -n "${MODEL_TIER:-}" ]; then
  TIER="$MODEL_TIER"
elif   [ "$RAM_GB" -ge 60 ]; then TIER=64
elif   [ "$RAM_GB" -ge 28 ]; then TIER=32
else                              TIER=16
fi
echo "detected RAM: ${RAM_GB} GB  ->  model tier: ${TIER} GB"

# Tiered model lists (each tier is a superset baseline + its bigger models).
# 16 GB: what we measured on M1 -- gemma4:12b and qwen3.5:9b lead; 7b is the baseline.
COMMON_16=( "qwen2.5-coder:7b" "qwen3.5:9b" "gemma4:12b" )
# 32 GB: the class that swamps 16 GB. Verify tags at ollama.com/library.
TIER_32=( "qwen2.5-coder:32b" "qwen3-coder:30b" )
# 64 GB+: 70B dense / large MoE reasoning+coding.
TIER_64=( "qwen2.5-coder:32b" "llama3.3:70b" )

MODELS=( "${COMMON_16[@]}" )
[ "$TIER" -ge 32 ] && MODELS+=( "${TIER_32[@]}" )
[ "$TIER" -ge 64 ] && MODELS+=( "${TIER_64[@]}" )

if [ "${SKIP_MODELS:-0}" = "1" ] || [ "${MODELS_OK:-0}" = "0" ]; then
  echo "skipping model downloads. Tier-${TIER} models to pull manually:"
  printf '  ollama pull %s\n' "${MODELS[@]}"
else
  echo "pulling tier-${TIER} models (continues past any tag that 404s):"
  for m in "${MODELS[@]}"; do
    echo "  -> $m"
    ollama pull "$m" || echo "     (skipped '$m' -- tag not found? check https://ollama.com/library)"
  done
fi

# --- 5. Smoke test ---
echo "== verifying recorded solutions against the oracle =="
PYTHONPATH=. ./venv/bin/python dev/verify_solutions.py || echo "(verify_solutions reported issues -- expected on a fresh clone without cached years/ data)"

cat <<'DONE'

== done ==
Next:
  - Reproduce an experiment (see AGENTS.md / dev/benchmarks/cross-machine-results.md):
      venv/bin/python experiment.py --problems 2024:4-7 --trials 1 \
        --config "name=run,models=<MODEL>,temperature=0.7,samples_per_model=3,enable_thinking=false"
  - On a >16 GB machine, add your results under a new machine id in
    dev/benchmarks/cross-machine-results.md so they compare against the M1 16 GB rows.
DONE
