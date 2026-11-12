"""Replay recorded runs through the real solver, with the recorded programs standing in for the model.

A behaviour-preserving change to the solver (a refactor) must leave every trial's sequence of
attempts unchanged. This checks that without a GPU: for each trial in result files saved with
--include-replay, a stand-in model returns the drafts and repairs that trial recorded, in the
order the solver asks for them, while everything else is the real code path of an experiment
run: problem preparation, consensus, the executor, the oracle, the feedback written into each
repair, the attempt records and the runner's independent final score.

Each trial yields one JSON line: the final outcome, each attempt's stage, repair round, draft,
outcome, error kind and example verdict, a hash of the problem the model would be shown, and a
hash of each repair's feedback. Two replays are compared with --compare; the first replay of a
run against the run itself with --against-recorded.

Nothing is written outside a temporary workspace: the ledger writer is replaced, the learning
database lives in the workspace (which links to the real years/ for the inputs), and generated
code runs in the sandbox as in any run.

    venv/bin/python dev/replay_solver.py dev/experiments/*_m5pro-d9p2-speed-*.json > base.jsonl
    venv/bin/python dev/replay_solver.py --compare base.jsonl after.jsonl
    venv/bin/python dev/replay_solver.py --against-recorded base.jsonl dev/experiments/*_m5pro-d9p2-speed-*.json
"""

import argparse
import asyncio
import dataclasses
import hashlib
import importlib.util
import json
import logging
import sys
import tempfile
from pathlib import Path
from typing import Any, Dict, Iterable, Iterator, List, Optional, Tuple

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from shared.experiment.config import SolverConfig  # noqa: E402

_spec = importlib.util.spec_from_file_location("export_results", REPO / "dev" / "export_results.py")
assert _spec and _spec.loader
_export = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_export)
error_kind = _export.error_kind

UNCHANGED = "repair returned the code unchanged"


class Diverged(Exception):
    """The solver asked for something the recorded trial does not hold. The solver catches
    model exceptions, so the model also keeps the message for the replay to report."""


def _digest(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


def _problem_digest(problem: Any) -> str:
    """What the model would be shown: the parsed problem the prompt is built from."""
    examples = [(str(getattr(e, "input_data", "")), str(getattr(e, "expected_output", "")))
                for e in getattr(problem, "examples", []) or []]
    return _digest(json.dumps([
        getattr(problem, "title", ""), getattr(problem, "description", ""),
        getattr(problem, "supplement", ""), getattr(problem, "final_question", ""), examples,
    ], default=str))


class RecordedModel:
    """Returns one trial's recorded drafts, then each draft's recorded repairs."""

    def __init__(self, attempts: List[Dict[str, Any]], workspace: Optional[Path] = None) -> None:
        model_attempts = [a for a in attempts if a.get("stage") in ("generate", "repair")]
        self.drafts: Dict[int, Dict[int, Dict[str, Any]]] = {}
        for attempt in model_attempts:
            draft = int(attempt.get("draft_index") or 0)
            self.drafts.setdefault(draft, {})[int(attempt.get("repair_iteration") or 0)] = attempt
        self.next_draft = 0
        self.current: Dict[int, Optional[str]] = {}
        self.rounds: Dict[int, int] = {}
        self.problem_digests: List[str] = []
        self.feedback: List[Tuple[int, int, str]] = []
        self.last_token_usage = {"input_tokens": 0, "output_tokens": 0}
        self.last_prompt: Optional[str] = None
        self.last_raw_response: Optional[str] = None
        self.diverged: List[str] = []
        # Tracebacks in the feedback name the temporary workspace, whose path differs on every
        # replay; it is hashed as a placeholder so two replays of the same trial compare equal.
        # The resolved path (/private/var/... on macOS) first: it contains the unresolved one.
        self.workspace_paths = sorted({str(workspace), str(workspace.resolve())},
                                      key=len, reverse=True) if workspace else []

    def _without_workspace(self, text: str) -> str:
        for path in self.workspace_paths:
            text = text.replace(path, "<workspace>")
        return text

    def _diverge(self, message: str) -> Diverged:
        self.diverged.append(message)
        return Diverged(message)

    async def generate_solution(self, problem: Any, year: int, day: int,
                                strategies: Any = None, strategy_effectiveness: Any = None) -> str:
        draft = self.next_draft
        self.next_draft += 1
        self.problem_digests.append(_problem_digest(problem))
        recorded = self.drafts.get(draft, {}).get(0)
        if recorded is None:
            raise self._diverge(f"draft {draft} asked for; none recorded")
        if not recorded.get("code"):
            raise RuntimeError(recorded.get("error") or "no candidate")
        self.current[draft] = recorded["code"]
        self.rounds[draft] = 0
        return str(recorded["code"])

    async def improve_solution(self, solution: str, problem: Any,
                               feedback: Optional[str] = None) -> str:
        draft = next((d for d, code in self.current.items() if code == solution), None)
        if draft is None:
            raise self._diverge("repair asked for code no recorded draft holds")
        self.rounds[draft] += 1
        round_ = self.rounds[draft]
        self.feedback.append((draft, round_, _digest(self._without_workspace(feedback or ""))))
        recorded = self.drafts.get(draft, {}).get(round_)
        if recorded is None:
            raise self._diverge(f"repair {round_} of draft {draft} asked for; none recorded")
        if not recorded.get("code"):
            if (recorded.get("error") or "") == UNCHANGED:
                self.current[draft] = None
                return solution
            raise RuntimeError(recorded.get("error") or "no candidate")
        self.current[draft] = recorded["code"]
        return str(recorded["code"])


def _attempt_row(attempt: Dict[str, Any]) -> List[Any]:
    return [attempt.get("stage"), int(attempt.get("repair_iteration") or 0),
            attempt.get("draft_index"), attempt.get("outcome"), error_kind(attempt),
            attempt.get("examples_passed"), attempt.get("examples_total")]


def _config(recorded: Dict[str, Any]) -> SolverConfig:
    known = {f.name for f in dataclasses.fields(SolverConfig)}
    return SolverConfig(**{k: v for k, v in recorded.items() if k in known})


async def replay_trial(run: Dict[str, Any], result: Dict[str, Any], workspace: Path) -> Dict[str, Any]:
    import shared.solver as solver_module
    from shared.experiment.runner import run_problem

    config = _config(run["config"])
    solver = solver_module.BaseSolver(workspace, config=config)
    model = RecordedModel(result["attempts"], workspace)
    name = (config.models or ("model",))[0]
    solver.models = {name: model}  # type: ignore[dict-item]
    replayed = await run_problem(solver, result["year"], result["day"], result["part"],
                                 config, trial=result["trial"])
    rows = [_attempt_row(dataclasses.asdict(a) | {"outcome": a.outcome.value})
            for a in replayed.attempts]
    line = {"run": run["config"]["name"], "trial": result["trial"],
            "outcome": replayed.outcome.value, "attempts": rows,
            "problem": sorted(set(model.problem_digests)), "feedback": model.feedback}
    if model.diverged:
        line["diverged"] = model.diverged
    return line


def _trials(paths: Iterable[str]) -> Iterator[Tuple[Dict[str, Any], Dict[str, Any]]]:
    for path in paths:
        run = json.loads(Path(path).read_text())
        for result in run["results"]:
            if result.get("outcome") == "not_reached":
                continue
            missing = [a for a in result["attempts"]
                       if a.get("stage") in ("generate", "repair") and a.get("outcome") != "no_candidate"
                       and not a.get("code")]
            if missing:
                raise SystemExit(f"{path}: attempts without code; replay needs --include-replay")
            yield run, result


async def replay(paths: List[str], done: set) -> None:
    import shared.solver as solver_module

    solver_module.record_solution = lambda *args, **kwargs: None  # never touch the ledger
    with tempfile.TemporaryDirectory(prefix="problem-solver-replay-") as tmp:
        # Runs use the repository as their workspace; the executor finds each input under
        # <workspace>/years. A link to the real years/ keeps that, while the learning database
        # and scratch files land in the temporary workspace instead of the live ones.
        (Path(tmp) / "years").symlink_to(REPO / "years", target_is_directory=True)
        (Path(tmp) / "tmp").mkdir()  # the executor's scratch area, as in the repository
        for run, result in _trials(paths):
            key = (run["config"]["name"], result["trial"])
            if key in done:
                continue
            print(json.dumps(await replay_trial(run, result, Path(tmp))), flush=True)


def _load(path: str) -> Dict[Tuple[str, int], Dict[str, Any]]:
    rows = [json.loads(line) for line in Path(path).read_text().splitlines() if line.startswith("{")]
    return {(r["run"], r["trial"]): r for r in rows}


def compare(a_path: str, b_path: str) -> int:
    a, b = _load(a_path), _load(b_path)
    differ = [k for k in sorted(set(a) | set(b)) if a.get(k) != b.get(k)]
    for key in differ:
        print(f"DIFFER {key[0]} trial {key[1]}")
        for field in ("outcome", "attempts", "problem", "feedback"):
            left, right = (a.get(key) or {}).get(field), (b.get(key) or {}).get(field)
            if left != right:
                print(f"  {field}:\n    {left}\n    {right}")
    print(f"{len(set(a) | set(b)) - len(differ)} of {len(set(a) | set(b))} trials identical")
    return 1 if differ else 0


def against_recorded(replay_path: str, paths: List[str]) -> int:
    replayed = _load(replay_path)
    same = differ = 0
    for run, result in _trials(paths):
        key = (run["config"]["name"], result["trial"])
        if key not in replayed:
            continue
        recorded = {"outcome": result["outcome"],
                    "attempts": [_attempt_row(a) for a in result["attempts"]]}
        line = replayed[key]
        if (line["outcome"], line.get("attempts")) == (recorded["outcome"], recorded["attempts"]):
            same += 1
            continue
        differ += 1
        print(f"DIFFER {key[0]} trial {key[1]}\n  recorded {recorded}\n  replayed "
              f"{ {'outcome': line['outcome'], 'attempts': line.get('attempts')} }")
    print(f"{same} of {same + differ} trials as recorded")
    return 1 if differ else 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("results", nargs="*")
    parser.add_argument("--compare", nargs=2, metavar=("A", "B"))
    parser.add_argument("--against-recorded", metavar="REPLAY")
    parser.add_argument("--done", help="an earlier replay output whose trials are skipped")
    args = parser.parse_args()
    if args.compare:
        return compare(*args.compare)
    if args.against_recorded:
        return against_recorded(args.against_recorded, args.results)
    logging.basicConfig(level=logging.WARNING)
    done = set(_load(args.done)) if args.done else set()
    asyncio.run(replay(args.results, done))
    return 0


if __name__ == "__main__":
    sys.exit(main())
