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
import dataclasses
import typing
import asyncio
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

REPO_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(REPO_ROOT))

from shared.experiment import ExperimentResult, Outcome, ProblemResult, SolverConfig  # noqa: E402
from shared.experiment.runner import (  # noqa: E402
    compare,
    drop_parts_without_puzzle,
    with_part_one_prerequisites,
    parse_problem_set,
    problem_id,
    run_experiment,
)

SYMBOL = {
    Outcome.SOLVED: "OK   ",
    Outcome.WRONG: "WRONG",
    Outcome.UNVERIFIED: "?    ",
    Outcome.OVERFIT: "CHEAT",
    Outcome.NO_CANDIDATE: "none ",
    Outcome.ERROR: "ERROR",
    Outcome.HARNESS_ERROR: "BUG  ",
    Outcome.NOT_REACHED: "skip ",
}

def _fields_of_type(*types: Any) -> frozenset:
    """SolverConfig fields declared with one of `types` (or Optional of one), for --config parsing.

    Read from the dataclass so a new field is parsed by its declared type. A hand-kept list
    once missed `targeted_feedback`, so `targeted_feedback=false` became the string "false",
    which is truthy: the guidance was on whatever the flag said."""
    hints = typing.get_type_hints(SolverConfig)
    wanted = set(types) | {Optional[t] for t in types}
    return frozenset(f.name for f in dataclasses.fields(SolverConfig) if hints[f.name] in wanted)


_INT_FIELDS = _fields_of_type(int)
_FLOAT_FIELDS = _fields_of_type(float)
_BOOL_FIELDS = _fields_of_type(bool)
_TRUE, _FALSE = {"1", "true", "yes", "on"}, {"0", "false", "no", "off"}


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
            if value.lower() not in _TRUE | _FALSE:
                raise ValueError(f"{key}={value!r} is not a boolean; use true or false")
            overrides[key] = value.lower() in _TRUE
        else:
            overrides[key] = value

    return SolverConfig.from_env(**overrides)


def parse_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
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
        "--out", type=Path, default=None,
        help="Directory to write result JSON into (default: dev/experiments)",
    )
    parser.add_argument("--trials", type=int, default=1, metavar="N",
                        help="Run each problem N times; the pipeline is non-deterministic, "
                             "so a single run is not evidence (default 1)")
    parser.add_argument("--include-replay", action="store_true",
                        help="Persist prompts and generated code for replay")
    parser.add_argument("--dry-run", action="store_true",
                        help="Score existing recorded solutions without calling a model")
    parser.add_argument("--debug", action="store_true")
    return parser.parse_args(argv)


async def _dry_run(problems: List[Tuple[int, int, int]], config: SolverConfig) -> ExperimentResult:
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


def _shown(path: Path) -> Path:
    """A path relative to the repo when it is inside it, as given otherwise."""
    try:
        return path.relative_to(REPO_ROOT)
    except ValueError:
        return path


async def async_main(args: argparse.Namespace) -> int:
    logging.basicConfig(
        level=logging.DEBUG if args.debug else logging.WARNING,
        format="%(levelname)s %(message)s",
    )

    problems, not_puzzles = drop_parts_without_puzzle(parse_problem_set(args.problems))
    if not_puzzles:
        names = ", ".join(problem_id(*spec) for spec in not_puzzles)
        print(f"skipping {len(not_puzzles)} part(s) with no puzzle on the page: {names}")
    specs = args.config or ["name=default"]
    configs = [parse_config(spec) for spec in specs]

    out_dir = args.out or (REPO_ROOT / "dev" / "experiments")
    experiments: List[ExperimentResult] = []

    for config in configs:
        if config.problem_context == "aoc":
            run_set = with_part_one_prerequisites(problems)
            added = [spec for spec in run_set if spec not in problems]
            if added:
                names = ", ".join(problem_id(*spec) for spec in added)
                print(f"adding {len(added)} Part One(s) that a requested Part Two needs: {names}")
        else:
            run_set = problems
        print(f"\n=== {config} over {len(run_set)} problem(s) ===")

        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        path = out_dir / f"{stamp}_{config.name}_{config.fingerprint()}.json"

        if args.dry_run:
            experiment = await _dry_run(problems, config)
            experiment.save(path, include_replay=args.include_replay)
        else:
            def report(result: ProblemResult) -> None:
                trial = f"[t{result.trial}] " if args.trials > 1 else ""
                print(
                    f"  {trial}{SYMBOL[result.outcome]}  {result.problem_id:22} "
                    f"{str(result.answer or '-'):>16}  "
                    f"expected {result.expected or '-'}  "
                    f"({result.wall_clock_seconds:.1f}s)",
                    flush=True,
                )

            print(f"  results are saved after each one to {_shown(path)}", flush=True)
            experiment = await run_experiment(
                problems, config, REPO_ROOT, debug=args.debug,
                on_result=report, trials=args.trials,
                save_to=path, include_replay=args.include_replay,
            )

        experiments.append(experiment)
        print(f"  -> {_shown(path)}")

    print()
    print(compare(experiments))

    for experiment in experiments:
        # Per-problem stability is the point of running trials: a problem solved
        # 2 of 5 times says something a single run cannot.
        if experiment.trials > 1:
            print(f"\nper-problem ({experiment.config_name}, {experiment.trials} trials):")
            for pid, s in experiment.per_problem().items():
                mark = " " if s["stable"] else "~"  # ~ = flips across trials
                print(
                    f"  {mark} {pid:22} {s['solved']}/{s['trials']} "
                    f"({s['solve_rate']:.0%})  {','.join(s['outcomes'])}"
                )

        per_model = experiment.per_model()
        if len(per_model) > 1:
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
