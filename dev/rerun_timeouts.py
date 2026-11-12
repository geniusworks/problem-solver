"""Re-execute stopped drafts on the full input with a longer limit or a higher memory cap.

Takes result files saved with --include-replay, picks the first-pass drafts
(stage "generate") that the harness stopped, and runs each again through the
harness's own executor (sandboxed, same resource limits) with --timeout and
--max-memory-gb. Reports how many were correct, wrong, or stopped again.

--stopped-by picks which stop: "timeout" (the time limit, the default) or
"memory" (the harness's memory cap). --all-stages adds repairs to the drafts.

Memory is not capped by the sandbox on macOS (RLIMIT_AS is unavailable there,
see shared/sandbox.py), and drafts that time out are often brute force that
grows without bound: six of them at once exhausted a 64 GB machine. So each
draft runs under the sandbox's watchdog, which kills it when its physical
footprint passes --max-memory-gb or the machine has less than --min-free-gb
available, reported as "over the memory cap".

Each verdict is printed as it lands; --done skips drafts already in an earlier
output file, so a stopped run resumes.

    venv/bin/python dev/rerun_timeouts.py --timeout 600 --jobs 2 --max-memory-gb 8 \
        dev/experiments/*_m5pro-d9p2-rep-k*.json
    venv/bin/python dev/rerun_timeouts.py --stopped-by memory --all-stages --timeout 60 \
        --jobs 1 --max-memory-gb 24 dev/experiments/*_m5pro-d9p2-speed-*.json
"""

import argparse
import asyncio
import collections
import json
import sys
import tempfile
import time
from pathlib import Path
from typing import Any, Dict, Iterable, Iterator, Tuple

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from shared.config import RESOURCES_CONFIG  # noqa: E402
from shared.sandbox import child_env, communicate_capped, resource_limiter  # noqa: E402


Draft = Tuple[str, Dict[str, Any], Dict[str, Any]]


# How the harness words each stop in an attempt's error (shared/execution.py).
STOP_MARKERS = {"timeout": "timed out", "memory": "exceeded the memory cap"}


def stopped_drafts(paths: Iterable[str], stopped_by: str = "timeout",
                   all_stages: bool = False) -> Iterator[Draft]:
    marker = STOP_MARKERS[stopped_by]
    for path in paths:
        run = json.loads(Path(path).read_text())
        for result in run["results"]:
            for attempt in result["attempts"]:
                if ((all_stages or attempt.get("stage") == "generate")
                        and attempt["outcome"] == "error"
                        and marker in (attempt.get("error") or "")):
                    if not attempt.get("code"):
                        raise SystemExit(f"{path}: no saved code; rerun needs --include-replay")
                    yield run["config"]["name"], result, attempt


async def run_capped(code: str, input_file: Path, timeout: int, max_bytes: int,
                     min_free: int = 0) -> Tuple[str, str]:
    """Run a draft as the harness does (module file, input path as argv, sandboxed env and
    limits) under the shared watchdog (`shared.sandbox.communicate_capped`).
    Returns (status, stdout) with status "ok", "failed", "timed out" or "over the memory cap"."""
    execution = RESOURCES_CONFIG.get("execution", {})
    with tempfile.TemporaryDirectory() as tmp:
        module = Path(tmp) / "draft.py"
        module.write_text(code)
        process = await asyncio.create_subprocess_exec(
            sys.executable, str(module), str(input_file),
            stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
            cwd=str(input_file.parent), env=child_env(),
            preexec_fn=resource_limiter(execution.get("max_memory_mb", 512),
                                        execution.get("max_processes", 1), cpu_seconds=timeout),
        )
        stopped, stdout, _ = await communicate_capped(process, timeout, max_bytes, min_free)
    if stopped:
        return stopped, stdout.decode()
    return ("ok" if process.returncode == 0 else "failed"), stdout.decode()


async def rerun(gate: asyncio.Semaphore, timeout: int, max_bytes: int, min_free: int, name: str,
                result: Dict[str, Any], attempt: Dict[str, Any]) -> Dict[str, Any]:
    input_file = REPO / "years" / str(result["year"]) / f"day{result['day']:02d}" / "input.txt"
    async with gate:
        start = time.time()
        status, output = await run_capped(attempt["code"], input_file, timeout, max_bytes, min_free)
        elapsed = time.time() - start
    if status == "ok":
        # Compared as the harness compares (shared/solver.py, _verify_candidate).
        verdict = "correct" if output.strip() == str(result["expected"]).strip() else "wrong"
    else:
        verdict = "still timed out" if status == "timed out" else status
    row = {"run": name, "trial": result["trial"], "draft_index": attempt.get("draft_index"),
           "repair_iteration": attempt.get("repair_iteration", 0),
           "verdict": verdict, "seconds": round(elapsed, 1)}
    print(json.dumps(row), flush=True)
    return row


async def main(args: argparse.Namespace) -> None:
    gate = asyncio.Semaphore(args.jobs)
    max_bytes = int(args.max_memory_gb * 1024 ** 3)
    min_free = int(args.min_free_gb * 1024 ** 3)
    done = set()
    for path in args.done or []:
        for line in Path(path).read_text().splitlines():
            if line.startswith("{"):
                row = json.loads(line)
                done.add((row["run"], row["trial"], row["draft_index"],
                          row.get("repair_iteration", 0)))
    drafts = [d for d in stopped_drafts(args.results, args.stopped_by, args.all_stages)
              if (d[0], d[1]["trial"], d[2].get("draft_index"),
                  d[2].get("repair_iteration", 0)) not in done]
    rows = await asyncio.gather(*(rerun(gate, args.timeout, max_bytes, min_free, *d) for d in drafts))
    print(dict(collections.Counter(row["verdict"] for row in rows)), f"of {len(rows)}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("results", nargs="+")
    parser.add_argument("--stopped-by", choices=sorted(STOP_MARKERS), default="timeout")
    parser.add_argument("--all-stages", action="store_true", help="include repairs, not only drafts")
    parser.add_argument("--timeout", type=int, default=600)
    parser.add_argument("--jobs", type=int, default=2)
    parser.add_argument("--max-memory-gb", type=float, default=8.0)
    parser.add_argument("--min-free-gb", type=float, default=8.0)
    parser.add_argument("--done", action="append", help="an earlier output file whose drafts are skipped (repeatable)")
    asyncio.run(main(parser.parse_args()))
