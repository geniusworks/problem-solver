"""Export the run artifacts as committed, shareable tables.

`dev/experiments/*.json` are gitignored: they carry the accepted AoC answers,
generated source and execution output, none of which may be published. This
writes what the published figures are computed from, without any of that, to
`dev/results/`:

- runs.csv      one row per result file: name, fingerprint, timing, config
- trials.csv    one row per problem-trial: outcome, wall-clock, tokens
- attempts.csv  one row per model call: model, stage, repair round, outcome, tokens

`dev/recompute_results.py` reads only these tables. Re-run this after every
measured run, in the same PR as its write-up:

    venv/bin/python dev/export_results.py
"""

import argparse
import csv
import json
from collections import defaultdict
from datetime import datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SOURCE = REPO_ROOT / "dev" / "experiments"
TARGET = REPO_ROOT / "dev" / "results"

RUN_FIELDS = ["run", "config_name", "config_fingerprint", "started_at", "finished_at",
              "duration_seconds", "config"]
TRIAL_FIELDS = ["run", "problem_id", "trial", "outcome", "winning_model", "wall_clock_seconds",
                "attempts_to_solve", "total_tokens"]
ATTEMPT_FIELDS = ["run", "problem_id", "trial", "model", "stage", "repair_iteration",
                  "draft_index", "outcome", "input_tokens", "output_tokens",
                  "wall_clock_seconds", "examples_passed", "examples_total", "overfit_flagged"]


def _duration(run: dict) -> float:
    """Wall-clock of the run; summed problem time when it has no timestamps."""
    start, end = run.get("started_at"), run.get("finished_at")
    if start and end:
        return (datetime.fromisoformat(end) - datetime.fromisoformat(start)).total_seconds()
    return sum(r.get("wall_clock_seconds") or 0 for r in run.get("results", []))


def export(source: Path, target: Path) -> dict:
    runs, trials, attempts = [], [], []
    for path in sorted(source.glob("*.json")):
        run = json.loads(path.read_text(encoding="utf-8"))
        config = dict(run.get("config", {}))
        summary = run.get("summary", {})
        runs.append({
            "run": path.name,
            "config_name": summary.get("config_name") or config.get("name"),
            "config_fingerprint": summary.get("config_fingerprint")
                or (run.get("results") or [{}])[0].get("config_fingerprint"),
            "started_at": run.get("started_at"),
            "finished_at": run.get("finished_at"),
            "duration_seconds": round(_duration(run), 1),
            "config": json.dumps(config, sort_keys=True),
        })
        # Files written before trials were numbered list each problem's trials in order.
        seen: defaultdict = defaultdict(int)
        for result in run.get("results", []):
            pid = result["problem_id"]
            trial = result.get("trial", seen[pid])
            seen[pid] += 1
            trials.append({
                "run": path.name, "problem_id": pid, "trial": trial,
                "outcome": result.get("outcome"),
                "winning_model": result.get("winning_model"),
                "wall_clock_seconds": result.get("wall_clock_seconds"),
                "attempts_to_solve": result.get("attempts_to_solve"),
                "total_tokens": result.get("total_tokens"),
            })
            for attempt in result.get("attempts", []):
                attempts.append({
                    "run": path.name, "problem_id": pid, "trial": trial,
                    **{k: attempt.get(k) for k in ATTEMPT_FIELDS[3:]},
                })

    target.mkdir(parents=True, exist_ok=True)
    for name, fields, rows in (("runs.csv", RUN_FIELDS, runs),
                               ("trials.csv", TRIAL_FIELDS, trials),
                               ("attempts.csv", ATTEMPT_FIELDS, attempts)):
        with open(target / name, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fields, lineterminator="\n")
            writer.writeheader()
            writer.writerows(rows)
    return {"runs": len(runs), "trials": len(trials), "attempts": len(attempts)}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--source", type=Path, default=SOURCE)
    parser.add_argument("--target", type=Path, default=TARGET)
    args = parser.parse_args()
    counts = export(args.source, args.target)
    print(", ".join(f"{v} {k}" for k, v in counts.items()), "->", args.target)


if __name__ == "__main__":
    main()
