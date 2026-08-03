#!/usr/bin/env python3
"""Run the solver over a problem set under one or more configurations.

Examples:
    # one configuration over 2024 days 1-6
    venv/bin/python experiment.py --problems 2024:1-6

    # A/B two configurations and print a comparison
    venv/bin/python experiment.py --problems 2024:1-4 \\
        --config name=three-models,max_primary_models=3 \\
        --config name=six-models,max_primary_models=6

    # replay-only: score what is already recorded, without calling any model
    venv/bin/python experiment.py --problems 2024:1-6 --dry-run
"""

import argparse
import asyncio
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

REPO_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(REPO_ROOT))

from shared.experiment import ExperimentResult, Outcome, SolverConfig  # noqa: E402
from shared.experiment.runner import (  # noqa: E402
    compare,
    parse_problem_set,
    run_experiment,
)

SYMBOL = {
    Outcome.SOLVED: "OK   ",
    Outcome.WRONG: "WRONG",
    Outcome.UNVERIFIED: "?    ",
    Outcome.OVERFIT: "CHEAT",
    Outcome.NO_CANDIDATE: "none ",
    Outcome.ERROR: "ERROR",
}

# Fields that are ints/floats/bools rather than strings, for --config parsing.
_INT_FIELDS = {
    "max_primary_models", "samples_per_model", "max_repair_iterations",
    "min_consensus_models", "execution_timeout",
}
_FLOAT_FIELDS = {"consensus_threshold", "temperature"}
_BOOL_FIELDS = {
    "enable_fallback_models", "enable_collaborative_improvement",
    "require_oracle", "submit_solutions",
}


def parse_config(spec: str) -> SolverConfig:
    """Parse a 'key=value,key=value' configuration override string."""
    overrides: Dict[str, Any] = {}
    for pair in spec.split(","):
        pair = pair.strip()
        if not pair:
            continue
        if "=" not in pair:
            raise ValueError(f"Malformed config override {pair!r}; expected key=value")
        key, value = (part.strip() for part in pair.split("=", 1))

        if key == "models":
            overrides[key] = tuple(m.strip() for m in value.split("|") if m.strip())
        elif key in _INT_FIELDS:
            overrides[key] = int(value)
        elif key in _FLOAT_FIELDS:
            overrides[key] = float(value)
        elif key in _BOOL_FIELDS:
            overrides[key] = value.lower() in {"1", "true", "yes", "on"}
        else:
            overrides[key] = value

    return SolverConfig.from_env(**overrides)


def parse_args(argv=None):
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        "--problems", required=True,
        help="Problem set, e.g. '2024:1-6' or '2024:3.2,2024:5'",
    )
    parser.add_argument(
        "--config", action="append", default=[], metavar="K=V,...",
        help="Configuration overrides; repeat to compare configurations",
    )
    parser.add_argument(
        "--reference-model", default=None,
        help="Capability reference, run outside the normal solve path. Use it to "
             "tell a harness bug from a model limitation.",
    )
    parser.add_argument(
        "--out", type=Path, default=None,
        help="Directory to write result JSON into (default: dev/experiments)",
    )
    parser.add_argument("--include-replay", action="store_true",
                        help="Persist prompts and generated code for replay")
    parser.add_argument("--dry-run", action="store_true",
                        help="Score existing recorded solutions without calling a model")
    parser.add_argument("--debug", action="store_true")
    return parser.parse_args(argv)


async def _dry_run(problems, config) -> ExperimentResult:
    """Score already-recorded solutions -- no model calls, no network."""
    from shared.experiment.results import AttemptRecord, ProblemResult
    from shared.experiment.runner import problem_id
    from shared.experiment.runner import VERDICT_TO_OUTCOME
    from shared.verification import verify_solution_file

    experiment = ExperimentResult(
        config_name=config.name,
        config_fingerprint=config.fingerprint(),
        config=config.to_dict(),
        started_at=datetime.now(timezone.utc).isoformat(),
    )

    for year, day, part in problems:
        pid = problem_id(year, day, part)
        path = REPO_ROOT / "solutions" / f"{pid}.py"
        if not path.exists():
            path = REPO_ROOT / "years" / str(year) / f"day{day:02d}" / f"{pid}.py"

        if not path.exists():
            outcome, answer, expected = Outcome.NO_CANDIDATE, None, None
        else:
            verified = verify_solution_file(path, year, day, part)
            outcome = VERDICT_TO_OUTCOME[verified.verdict]
            answer, expected = verified.actual, verified.expected

        result = ProblemResult(
            problem_id=pid, year=year, day=day, part=part,
            config_fingerprint=config.fingerprint(),
            outcome=outcome, answer=answer, expected=expected,
        )
        result.attempts.append(
            AttemptRecord(
                model="recorded", problem_id=pid,
                config_fingerprint=config.fingerprint(),
                outcome=outcome, answer=answer, expected=expected,
            )
        )
        experiment.results.append(result)
        print(f"  {SYMBOL[outcome]}  {pid:22} {str(answer or '-'):>16}  expected {expected or '-'}")

    experiment.finished_at = datetime.now(timezone.utc).isoformat()
    return experiment


async def async_main(args) -> int:
    logging.basicConfig(
        level=logging.DEBUG if args.debug else logging.WARNING,
        format="%(levelname)s %(message)s",
    )

    problems = parse_problem_set(args.problems)
    specs = args.config or ["name=default"]
    configs = [parse_config(spec) for spec in specs]
    if args.reference_model:
        configs = [c.with_overrides(reference_model=args.reference_model) for c in configs]

    out_dir = args.out or (REPO_ROOT / "dev" / "experiments")
    experiments: List[ExperimentResult] = []

    for config in configs:
        print(f"\n=== {config} over {len(problems)} problem(s) ===")

        if args.dry_run:
            experiment = await _dry_run(problems, config)
        else:
            def report(result):
                print(
                    f"  {SYMBOL[result.outcome]}  {result.problem_id:22} "
                    f"{str(result.answer or '-'):>16}  "
                    f"expected {result.expected or '-'}  "
                    f"({result.wall_clock_seconds:.1f}s)"
                )

            experiment = await run_experiment(
                problems, config, REPO_ROOT, debug=args.debug, on_result=report
            )

        experiments.append(experiment)

        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        path = out_dir / f"{stamp}_{config.name}_{config.fingerprint()}.json"
        experiment.save(path, include_replay=args.include_replay)
        print(f"  -> {path.relative_to(REPO_ROOT)}")

    print()
    print(compare(experiments))

    for experiment in experiments:
        per_model = experiment.per_model()
        if len(per_model) <= 1:
            continue
        print(f"\nper-model ({experiment.config_name}):")
        for model, stats in per_model.items():
            print(
                f"  {model:24} {stats['solved']}/{stats['attempts']} "
                f"({stats['solve_rate']:.0%})  {stats['wall_clock_seconds']:.0f}s"
            )
    print()

    # Non-zero when anything was claimed but not verified, so this can gate CI.
    return 1 if any(e.claimed_minus_verified for e in experiments) else 0


def main() -> int:
    return asyncio.run(async_main(parse_args()))


if __name__ == "__main__":
    raise SystemExit(main())
