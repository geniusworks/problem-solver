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
import hashlib
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


def _wilson(successes: int, n: int, z: float = 1.959964) -> Tuple[float, float]:
    p = successes / n
    centre = p + z * z / (2 * n)
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return (centre - half) / (1 + z * z / n), (centre + half) / (1 + z * z / n)


def newcombe(a: int, n1: int, b: int, n2: int) -> str:
    """95% Newcombe hybrid-score interval for b/n2 - a/n1, in points: the lower bound rounded
    down, the upper to the nearest point."""
    p1, p2 = a / n1, b / n2
    (l1, u1), (l2, u2) = _wilson(a, n1), _wilson(b, n2)
    low = (p2 - p1) - math.sqrt((p2 - l2) ** 2 + (u1 - p1) ** 2)
    high = (p2 - p1) + math.sqrt((u2 - p2) ** 2 + (p1 - l1) ** 2)
    return f"{math.floor(100 * low):+d} to {math.floor(100 * high + 0.5):+d}"


def intervals() -> str:
    """The intervals RESULTS.md quotes beside its main comparisons."""
    pairs = {"d19": (6, 20, 19, 19), "13 cells": (2, 53, 29, 37), "band": (9, 19, 11, 21),
             "decider": (1, 10, 10, 10), "2024": (10, 24, 9, 12), "2025": (2, 8, 6, 6),
             "power": (5, 15, 13, 20), "replication": (13, 35, 16, 35)}
    return "; ".join(f"{name} {newcombe(*counts)}" for name, counts in pairs.items())


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


def arm1_power() -> str:
    """2025 d9 p2, k1 against k3, trials that reached Part 2 (registered test)."""
    cell = ["2025_day09_part2"]
    k1 = solved(outcomes([run_named("20261109T174241Z_m5pro-d9p2-power-aoc-k1")], cell, True))
    k3 = solved(outcomes([run_named("20261109T204015Z_m5pro-d9p2-power-aoc-k3")], cell, True))
    return f"{frac(k1)} -> {frac(k3)}, p {fisher_greater(*k1, *k3):.3f}"


def d9_after_the_fix() -> str:
    """2025 d9 p2, the reference at three drafts with the Part 1 context, every such run."""
    runs = [name for name, run in RUNS.items()
            if run["config"].get("problem_context") == "aoc"
            and run["config"].get("samples_per_model") == 3
            and run["config"].get("models") == ["qwen3.8:27b"]]
    return frac(solved(outcomes(runs, ["2025_day09_part2"], reached_only=True)))


def example_only_selector() -> str:
    """Replication k3 trials: take the first draft (by draft_index) that passes the worked example
    and produces an answer; score it against the oracle beside the oracle's own pick."""
    runs = {name for name in RUNS if "_m5pro-d9p2-rep-k3-b" in name}
    drafts: Dict[Tuple[str, str], List[dict]] = defaultdict(list)
    for a in ATTEMPTS:
        if a["run"] in runs and a["stage"] == "generate":
            drafts[(a["run"], a["trial"])].append(a)
    right = wrong = none = oracle = 0
    for group in drafts.values():
        group.sort(key=lambda a: int(a["draft_index"]))
        oracle += any(a["outcome"] == "solved" for a in group)
        passing = [a for a in group if a["outcome"] in ("solved", "wrong")
                   and a["examples_total"] and a["examples_passed"] == a["examples_total"]
                   and int(a["examples_total"]) > 0]
        if not passing:
            none += 1
        elif passing[0]["outcome"] == "solved":
            right += 1
        else:
            wrong += 1
    return f"{right}/{len(drafts)} right, {wrong} wrong, {none} none; oracle {oracle}/{len(drafts)}"


def replication_timeouts() -> str:
    """2025 d9 p2 replication: drafts that timed out, and timeouts among the attempts the oracle
    rejected, with how many of those had passed the worked example."""
    runs = {name for name in RUNS if "_m5pro-d9p2-rep-k" in name}
    rows = [a for a in ATTEMPTS if a["run"] in runs]
    drafts = [a for a in rows if a["stage"] == "generate"]
    rejected = [a for a in rows if a["outcome"] in ("wrong", "error")]
    timeouts = [a for a in rejected if a["error_kind"] == "timeout"]
    passed = [a for a in timeouts if a["examples_total"] not in ("", "0")
              and a["examples_passed"] == a["examples_total"]]
    drafts_out = sum(a["error_kind"] == "timeout" for a in drafts)
    return (f"{drafts_out} of {len(drafts)} drafts; {len(timeouts)} of {len(rejected)} rejected; "
            f"{len(passed)} passed the example")


def arm1_replication() -> str:
    """2025 d9 p2, k1 against k3, every trial posed Part 2 (registered replication, 7 blocks per arm)."""
    cell = ["2025_day09_part2"]

    def arm(k: str) -> Tuple[int, int]:
        runs = [name for name in RUNS if f"_m5pro-d9p2-rep-{k}-b" in name]
        if len(runs) != 7:
            raise LookupError(f"{k}: {len(runs)} replication blocks, expected 7")
        return solved(outcomes(runs, cell))

    k1, k3 = arm("k1"), arm("k3")
    return f"{frac(k1)} -> {frac(k3)}, p {fisher_greater(*k1, *k3):.2f}"


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


def repair_by_model() -> str:
    """Repair attempts that solved, per model, under the corrected harness."""
    corrected = {name for name, run in RUNS.items()
                 if run["config"].get("problem_context", "legacy") == "aoc"}
    repairs: Dict[str, List[dict]] = defaultdict(list)
    for attempt in ATTEMPTS:
        if attempt["run"] in corrected and int(attempt["repair_iteration"] or 0) > 0:
            repairs[attempt["model"]].append(attempt)
    ref, muse = repairs[REFERENCE], repairs["muse-glimmer:30b"]
    shared = {a["problem_id"] for a in ref} & {a["problem_id"] for a in muse}

    def rate(rows: List[dict]) -> str:
        return f"{sum(a['outcome'] == 'solved' for a in rows)}/{len(rows)}"

    return (f"{rate(ref)} vs {rate(muse)}; same problems "
            f"{rate([a for a in ref if a['problem_id'] in shared])} vs "
            f"{rate([a for a in muse if a['problem_id'] in shared])}")


def repair_share_of_solves() -> str:
    """Solved trials whose winning attempt was a repair, per model, corrected harness."""
    corrected = {name for name, run in RUNS.items()
                 if run["config"].get("problem_context", "legacy") == "aoc"}
    winners: Dict[Tuple[str, str, str], dict] = {}
    for attempt in ATTEMPTS:
        key = (attempt["run"], attempt["problem_id"], attempt["trial"])
        if attempt["run"] in corrected and attempt["outcome"] == "solved" and key not in winners:
            winners[key] = attempt
    counts: Dict[str, List[int]] = defaultdict(lambda: [0, 0])
    for trial in TRIALS:
        winner = winners.get((trial["run"], trial["problem_id"], trial["trial"]))
        if trial["outcome"] == "solved" and winner:
            counts[winner["model"]][0] += int(winner["repair_iteration"] or 0) > 0
            counts[winner["model"]][1] += 1
    ref, muse = counts[REFERENCE], counts["muse-glimmer:30b"]
    return f"{ref[0]} of {ref[1]} vs {muse[0]} of {muse[1]}"


@dataclass
class Claim:
    name: str
    compute: Callable[[], str]
    expected: str
    published: Dict[str, Sequence[str]]  # file -> exact text that must appear in it


CLAIMS = [
    Claim("corpus runs", corpus_runs, "108 recorded experiment runs",
          {"RESULTS.md": ["108 recorded experiment runs", "The corpus is 108 runs"]}),
    Claim("corpus attempts", corpus_attempts, "3,648 candidate attempts",
          {"RESULTS.md": ["3,648 candidate attempts", "3,648 candidate attempts and about 225\nGPU-hours"]}),
    Claim("corpus GPU-hours", corpus_hours, "~225 GPU-hours", {"RESULTS.md": ["~225 GPU-hours"]}),
    Claim("corpus tokens", corpus_tokens, "45.7M tokens", {"RESULTS.md": ["45.7M tokens"]}),
    Claim("95% Newcombe intervals", intervals,
          "d19 +42 to +85; 13 cells +56 to +85; band -24 to +33; decider +48 to +98; "
          "2024 -1 to +57; 2025 +23 to +93; power -2 to +56; replication -14 to +30",
          {"RESULTS.md": ["70 points (95% Newcombe interval\n+42 to +85)", "(75 points, +56 to +85)",
                          "interval\n−24 to +33", "interval +48 to\n  +98", "interval −1 to +57",
                          "+23 to +93", "interval −2 to +56", "interval −14 to +30"]}),
    Claim("ledger", ledger_size, "69 verified solutions",
          {"README.md": ["**69 verified solutions**"], "RESULTS.md": ["69 oracle-verified solutions"],
           "assets/social-preview.html": ["69 verified solutions"]}),
    Claim("headline, matched single drafts", headline_matched, "13 cells: 2/53 -> 29/37",
          {"README.md": ["2 of 53 trials solved to 29 of 37"],
           "RESULTS.md": ["2 of 53\n  trials solved to 29 of 37", "| 2/53 | **29/37** |"]}),
    Claim("headline, all trials", headline_all_trials, "13/71 -> 32/40",
          {"RESULTS.md": ["those Part 2s were 13/71 on\nrecord and 32/40 after"]}),
    Claim("d19 p2 controlled A/B", d19_ab, "6/20 -> 19/19, p = 2.6e-06",
          {"RESULTS.md": ["| 6/20 | **19/19** (one-sided Fisher p = 2.6e-6) |"],
           "README.md": ["took one problem from 6/20 to 19/19"],
           "assets/social-preview.html": ['class="stat">6/20<', 'class="to">19/19<']}),
    Claim("arm 1, original harness", arm1_original,
          "10/24 -> 9/12 (blind 7/12), p 0.061; 2025 2/8 -> 6/6, p 0.009; combined 0.005",
          {"RESULTS.md": ["| 2024 alone | 10/24 → 9/12 (+33 points, 95% interval −1 to +57) | **p ≈ 0.061 — marginal** |",
                          "| 2025 replication | 2/8 → 6/6 (+75 points, +23 to +93) | **p ≈ 0.009** |",
                          "**p ≈ 0.005**"]}),
    Claim("arm 1, corrected harness", arm1_corrected, "9/19 -> 11/21",
          {"RESULTS.md": ["gave 9/19 at one draft and 11/21 at three"]}),
    Claim("arm 1, powered test on 2025 d9 p2", arm1_power, "5/15 -> 13/20, p 0.065",
          {"RESULTS.md": ["| solved | 5/15 (33%) | 13/20 (65%) | **p = 0.065 — inconclusive** |"]}),
    Claim("2025 d9 p2 after the fix, three drafts", d9_after_the_fix, "31/58",
          {"RESULTS.md": ["**31/58** three-draft trials"]}),
    Claim("example-only selector, 2025 d9 p2 replication", example_only_selector,
          "12/35 right, 15 wrong, 8 none; oracle 14/35",
          {"README.md": ["solved 12 of 35 three-draft trials and\n  took a wrong answer in 15, where the oracle solved 14"],
           "RESULTS.md": ["solved 12 of 35 three-draft trials and took a wrong answer in 15"]}),
    Claim("2025 d9 p2 replication timeouts", replication_timeouts,
          "45 of 140 drafts; 138 of 249 rejected; 94 passed the example",
          {"RESULTS.md": ["138 of 249 on 2025 d9 p2", "and 94 of the 138"]}),
    Claim("arm 1, registered replication on 2025 d9 p2", arm1_replication, "13/35 -> 16/35, p 0.31",
          {"RESULTS.md": ["| solved | 13/35 (37%) | 16/35 (46%) | **p = 0.31 — not re-established** |",
                          "replication at 13/35 against 16/35 (one-sided p = 0.31;"],
           "README.md": ["replication gave 13/35 at one draft and 16/35 at three (one-sided p = 0.31;"]}),
    Claim("arm 2", arm2,
          "1,389 s vs 891 s (0.64x); 38,460 vs >=119,068 tokens (>=3.09x)",
          {"RESULTS.md": ["| 7/8 | **891 s** (0.64×) | ≥119,068 (≥3.09×) |", "1,389 s"]}),
    Claim("repair by model", repair_by_model, "13/368 vs 14/80; same problems 12/358 vs 8/67",
          {"RESULTS.md": ["muse's 14 times in 80. On the problems both models repaired, 12 in 358 against 8 in 67"]}),
    Claim("repair share of solves", repair_share_of_solves, "13 of 300 vs 14 of 131",
          {"RESULTS.md": ["13 of the reference's 300 solves came\n  from repair, against 14 of 131",
                          "13 of\nits 300 solved cells were solved by repair", "solved 14 of\nits 131 by repair"],
           "PLAN.md": ["repair produced 13\nof the reference model's 300 solves"]}),
    Claim("arm 3 decider", arm3, "10/10 vs 1/10, p 0.0001",
          {"RESULTS.md": ["10/10 against the reference's 1/10 in the decider (+90 points", "one-sided Fisher p = 0.0001). It also gave"]}),
]


def social_card_rendered() -> List[str]:
    """The PNG was rendered from the current HTML (dev/render_social_preview.py records it)."""
    html = REPO_ROOT / "assets" / "social-preview.html"
    record = REPO_ROOT / "assets" / "social-preview.rendered-from"
    current = hashlib.sha256(html.read_bytes()).hexdigest()
    recorded = record.read_text().split()[1] if record.exists() else None
    if recorded == current:
        return []
    return ["assets/social-preview.png was not rendered from the current HTML; "
            "run venv/bin/python dev/render_social_preview.py"]


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
    card = social_card_rendered()
    for problem in card:
        print(f"FAIL  social card: {problem}")
    failures += bool(card)
    return 1 if failures and args.check else 0


if __name__ == "__main__":
    sys.exit(main())
