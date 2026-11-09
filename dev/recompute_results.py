"""Recompute the published figures from the committed tables, and check the docs.

Each claim below is computed from `dev/results/*.csv` (written by
`dev/export_results.py`) and compared with the value the docs publish; the
exact published text must also appear in every file listed for it. A doc and its
number cannot drift apart without this failing. CI runs it with --check.

    venv/bin/python dev/recompute_results.py           # print every claim
    venv/bin/python dev/recompute_results.py --check   # exit 1 on any mismatch

To change a published figure: change the docs, update the claim here, same PR.
"""

import argparse
import csv
import json
import math
import re
import sys
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple

REPO_ROOT = Path(__file__).resolve().parent.parent
RESULTS = REPO_ROOT / "dev" / "results"
REFERENCE = "qwen3.8:27b"


# -- data -----------------------------------------------------------------

def _rows(name: str) -> List[dict]:
    with open(RESULTS / name, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


RUNS: Dict[str, Dict[str, Any]] = {
    r["run"]: {**r, "config": json.loads(r["config"])} for r in _rows("runs.csv")
}
TRIALS = _rows("trials.csv")
ATTEMPTS = _rows("attempts.csv")


def run_named(prefix: str) -> str:
    matches = [name for name in RUNS if name.startswith(prefix)]
    if len(matches) != 1:
        raise LookupError(f"{prefix!r} matches {len(matches)} runs")
    return matches[0]


def outcomes(runs: Sequence[str], problems: Sequence[str], reached_only: bool = False) -> List[str]:
    wanted, cells = set(runs), set(problems)
    found = [t["outcome"] for t in TRIALS if t["run"] in wanted and t["problem_id"] in cells]
    return [o for o in found if o != "not_reached"] if reached_only else found


def solved(found: Sequence[str]) -> Tuple[int, int]:
    return sum(o == "solved" for o in found), len(found)


def frac(pair: Tuple[int, int]) -> str:
    return f"{pair[0]}/{pair[1]}"


def reference_runs(context: str, samples: Optional[int] = None) -> List[str]:
    """Runs of the reference model alone, by prompt context (and draft count)."""
    picked = []
    for name, run in RUNS.items():
        config = run["config"]
        models = config.get("models") or []
        if isinstance(models, str):
            models = [m for m in models.split(",") if m]
        if list(models) != [REFERENCE] or config.get("problem_context", "legacy") != context:
            continue
        if samples is None or config.get("samples_per_model") == samples:
            picked.append(name)
    return picked


# -- statistics -----------------------------------------------------------

def fisher_greater(a: int, n1: int, b: int, n2: int) -> float:
    """One-sided Fisher exact: P(group 2 has >= b successes), margins fixed."""
    total = a + b
    denominator = math.comb(n1 + n2, total)
    return sum(math.comb(n2, x) * math.comb(n1, total - x)
               for x in range(b, min(total, n2) + 1) if 0 <= total - x <= n1) / denominator


def fisher_combined(*p_values: float) -> float:
    """Fisher's method for two p-values (chi-square, 4 degrees of freedom)."""
    statistic = -2 * sum(math.log(p) for p in p_values)
    return math.exp(-statistic / 2) * (1 + statistic / 2)


# -- the claims -----------------------------------------------------------

RESCAN = "20261101T031131Z_m5pro-aoc-rescan-p2-k1"
RESCAN_CELLS = (["2024_day%02d_part2" % d for d in (6, 9, 11, 13, 14, 17, 18, 20, 21, 22, 24)]
                + ["2025_day%02d_part2" % d for d in (2, 4, 10, 11)])


def corpus_runs() -> str:
    return f"{len(RUNS)} recorded experiment runs"


def corpus_attempts() -> str:
    return f"{len(ATTEMPTS):,} candidate attempts"


def corpus_hours() -> str:
    hours = sum(float(r["duration_seconds"]) for r in RUNS.values()) / 3600
    return f"~{round(hours / 5) * 5} GPU-hours"


def corpus_tokens() -> str:
    tokens = sum(int(a["input_tokens"] or 0) + int(a["output_tokens"] or 0) for a in ATTEMPTS)
    return f"{tokens / 1e6:.1f}M tokens"


def ledger_size() -> str:
    text = (REPO_ROOT / "solutions" / "README.md").read_text(encoding="utf-8")
    verified = text.split("<!-- end verified rows -->", 1)[0]
    rows = re.findall(r"(?m)^\|\s*20\d\d\s*\|", verified)
    return f"{len(rows)} verified solutions"


def headline_matched() -> str:
    """Single drafts, same cells: legacy trials against the rescan, Part 2 reached."""
    legacy = reference_runs("legacy", samples=1)
    rescan = [run_named(RESCAN)]
    cells = [c for c in RESCAN_CELLS
             if outcomes(legacy, [c]) and outcomes(rescan, [c], reached_only=True)]
    before = solved(outcomes(legacy, cells))
    after = solved(outcomes(rescan, cells, reached_only=True))
    return f"{len(cells)} cells: {frac(before)} -> {frac(after)}"


def headline_all_trials() -> str:
    before = solved(outcomes(reference_runs("legacy"), RESCAN_CELLS))
    after = solved(outcomes([run_named(RESCAN)], RESCAN_CELLS, reached_only=True))
    return f"{frac(before)} -> {frac(after)}"


def d19_ab() -> str:
    cell = ["2024_day19_part2"]
    before = solved(outcomes([run_named("20261013T033144Z_m5pro-d19p2-k1-n20")], cell))
    after = solved(outcomes([run_named("20261014T001948Z_m5pro-aoc-d19-k1-n20")], cell, True))
    p = fisher_greater(*before, *after)
    return f"{frac(before)} -> {frac(after)}, p = {p:.1e}"


def arm1_original() -> str:
    band = ["2024_day13_part1", "2024_day13_part2", "2024_day15_part1", "2024_day15_part2"]
    k1 = solved(outcomes([run_named("20260817T095800Z_band-classify-samp1"),
                          run_named("20260817T141238Z_k1_")], band))
    k3 = solved(outcomes([run_named("20260817T212058Z_k3_")], band))
    blind = solved(outcomes([run_named("20260818T082725Z_parallel3")], band))
    cells = ["2025_day09_part1", "2025_day11_part2"]
    k1_25 = solved(outcomes([run_named("20260818T193613Z_scan2025"),
                             run_named("20260819T061605Z_band2025")], cells))
    k3_25 = solved(outcomes([run_named("20260819T112247Z_k3-2025")], cells))
    p24, p25 = fisher_greater(*k1, *k3), fisher_greater(*k1_25, *k3_25)
    return (f"{frac(k1)} -> {frac(k3)} (blind {frac(blind)}), p {p24:.3f}; "
            f"2025 {frac(k1_25)} -> {frac(k3_25)}, p {p25:.3f}; combined {fisher_combined(p24, p25):.3f}")


def arm1_corrected() -> str:
    cells = ["2024_day09_part2", "2024_day14_part2", "2024_day17_part2", "2024_day24_part1",
             "2024_day24_part2", "2025_day04_part2", "2025_day10_part2"]
    k1 = solved(outcomes([run_named(RESCAN)], cells, reached_only=True))
    k3 = solved(outcomes([run_named("20261101T094316Z_m5pro-aoc-band-k3")], cells, True))
    return f"{frac(k1)} -> {frac(k3)}"


def arm2() -> str:
    def per_solution(run: str) -> Tuple[float, float]:
        trials = [t for t in TRIALS if t["run"] == run]
        drafts = [a for a in ATTEMPTS if a["run"] == run and int(a["repair_iteration"] or 0) == 0]
        wins = sum(t["outcome"] == "solved" for t in trials)
        seconds = sum(float(t["wall_clock_seconds"] or 0) for t in trials)
        tokens = sum(int(a["input_tokens"] or 0) + int(a["output_tokens"] or 0) for a in drafts)
        return seconds / wins, tokens / wins

    strong_s, strong_t = per_solution(run_named("20260823T024401Z_econ-generalist-k3"))
    cheap_s, cheap_t = per_solution(run_named("20260823T042804Z_econ-moe-k12"))
    # A lower bound on the token ratio is rounded down, never up.
    floor = math.floor(cheap_t / strong_t * 100) / 100
    return (f"{strong_s:,.0f} s vs {cheap_s:,.0f} s ({cheap_s / strong_s:.2f}x); "
            f"{strong_t:,.0f} vs >={cheap_t:,.0f} tokens (>={floor:.2f}x)")


def arm3() -> str:
    cell = ["2024_day14_part2"]
    muse = solved(outcomes([run_named("20261107T035120Z_m5pro-d14p2-muse")], cell, True))
    ref = solved(outcomes([run_named("20261102T232634Z_m5pro-d14p2-ref")], cell, True))
    return f"{frac(muse)} vs {frac(ref)}, p {2 * fisher_greater(*ref, *muse):.4f}"


@dataclass
class Claim:
    name: str
    compute: Callable[[], str]
    expected: str
    published: Dict[str, Sequence[str]]  # file -> exact text that must appear in it


CLAIMS = [
    Claim("corpus runs", corpus_runs, "89 recorded experiment runs",
          {"RESULTS.md": ["89 recorded experiment runs"]}),
    Claim("corpus attempts", corpus_attempts, "3,098 candidate attempts",
          {"RESULTS.md": ["3,098 candidate attempts"]}),
    Claim("corpus GPU-hours", corpus_hours, "~195 GPU-hours", {"RESULTS.md": ["~195 GPU-hours"]}),
    Claim("corpus tokens", corpus_tokens, "38.1M tokens", {"RESULTS.md": ["38.1M tokens"]}),
    Claim("ledger", ledger_size, "69 verified solutions",
          {"README.md": ["**69 verified solutions**"], "RESULTS.md": ["69 oracle-verified solutions"],
           "assets/social-preview.html": ["69 verified solutions"]}),
    Claim("headline, matched single drafts", headline_matched, "13 cells: 2/53 -> 29/37",
          {"README.md": ["2 of 53 trials solved to 29 of 37", "| 2/53 | **29/37** |"],
           "RESULTS.md": ["2 of 53\n  trials solved to 29 of 37", "| 2/53 | **29/37** |"],
           "assets/social-preview.html": ["4%", "78%"]}),
    Claim("headline, all trials", headline_all_trials, "13/71 -> 32/40",
          {"RESULTS.md": ["those Part 2s were 13/71 on\nrecord and 32/40 after"]}),
    Claim("d19 p2 controlled A/B", d19_ab, "6/20 -> 19/19, p = 2.6e-06",
          {"RESULTS.md": ["| 6/20 | **19/19** (one-sided Fisher p = 2.6e-6) |"],
           "README.md": ["| 6/20 | **19/19** |"]}),
    Claim("arm 1, original harness", arm1_original,
          "10/24 -> 9/12 (blind 7/12), p 0.061; 2025 2/8 -> 6/6, p 0.009; combined 0.005",
          {"RESULTS.md": ["| 2024 alone | 10/24 → 9/12 | **p ≈ 0.061 — marginal** |",
                          "| 2025 replication | 2/8 → 6/6 | **p ≈ 0.009** |",
                          "**p ≈ 0.005**"]}),
    Claim("arm 1, corrected harness", arm1_corrected, "9/19 -> 11/21",
          {"RESULTS.md": ["9/19 at one draft and 11/21 at\nthree"]}),
    Claim("arm 2", arm2,
          "1,389 s vs 891 s (0.64x); 38,460 vs >=119,068 tokens (>=3.09x)",
          {"RESULTS.md": ["| 7/8 | **891 s** (0.64×) | ≥119,068 (≥3.09×) |", "1,389 s"],
           "README.md": ["| 7/8 | **891 s** (0.64×) | ≥119,068 (≥3.09×) |"]}),
    Claim("arm 3 decider", arm3, "10/10 vs 1/10, p 0.0001",
          {"RESULTS.md": ["10/10 against the reference's 1/10 in the decider, p = 0.0001"]}),
]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--check", action="store_true", help="exit 1 on any mismatch")
    args = parser.parse_args()

    failures = 0
    for claim in CLAIMS:
        computed = claim.compute()
        problems = [] if computed == claim.expected else [f"computed {computed!r}"]
        for relative, texts in claim.published.items():
            content = (REPO_ROOT / relative).read_text(encoding="utf-8")
            problems += [f"{relative} lacks {text!r}" for text in texts if text not in content]
        failures += bool(problems)
        print(f"{'FAIL' if problems else 'ok  '}  {claim.name}: {claim.expected}")
        for problem in problems:
            print(f"        {problem}")
    print(f"{len(CLAIMS) - failures} of {len(CLAIMS)} claims match")
    return 1 if failures and args.check else 0


if __name__ == "__main__":
    sys.exit(main())
