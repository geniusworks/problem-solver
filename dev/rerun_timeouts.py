"""Re-execute timed-out drafts on the full input with a longer limit.

Takes result files saved with --include-replay, picks the first-pass drafts
(stage "generate") that hit the execution limit, and runs each again through the
harness's own executor (sandboxed, same resource limits) with a longer timeout.
Reports how many were correct but slow, wrong, or still too slow.

Memory is not capped by the sandbox on macOS (RLIMIT_AS is unavailable there,
see shared/sandbox.py), and drafts that time out are often brute force that
grows without bound: six of them at once exhausted a 64 GB machine. So each
draft runs under a watchdog that kills it when its physical footprint passes
--max-memory-gb, or when the machine has less than --min-free-gb available,
reported as "over the memory cap". The footprint counts compressed pages,
which resident size does not: a grid of zeros compresses so well that a draft
can show a few GB resident while holding tens of GB.

Each verdict is printed as it lands; --done skips drafts already in an earlier
output file, so a stopped run resumes.

    venv/bin/python dev/rerun_timeouts.py --timeout 600 --jobs 2 --max-memory-gb 8 \
        dev/experiments/*_m5pro-d9p2-rep-k*.json
"""

import argparse
import asyncio
import collections
import ctypes
import json
import sys
import tempfile
import time
from pathlib import Path
from typing import Any, Dict, Iterable, Iterator, Tuple

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

import psutil  # noqa: E402

from shared.config import RESOURCES_CONFIG  # noqa: E402
from shared.sandbox import child_env, resource_limiter  # noqa: E402


Draft = Tuple[str, Dict[str, Any], Dict[str, Any]]


def timed_out_drafts(paths: Iterable[str]) -> Iterator[Draft]:
    for path in paths:
        run = json.loads(Path(path).read_text())
        for result in run["results"]:
            for attempt in result["attempts"]:
                if (attempt.get("stage") == "generate" and attempt["outcome"] == "error"
                        and "timed out" in (attempt.get("error") or "")):
                    if not attempt.get("code"):
                        raise SystemExit(f"{path}: no saved code; rerun needs --include-replay")
                    yield run["config"]["name"], result, attempt


def footprint_bytes(pid: int) -> int:
    """A process's physical footprint (resident plus compressed), as Activity Monitor shows
    it; resident size where libproc is unavailable."""
    if _LIBPROC is not None:
        usage = (ctypes.c_uint64 * 40)()
        # proc_pid_rusage(RUSAGE_INFO_V2): after a 16-byte uuid, ri_phys_footprint is the
        # eighth 64-bit field.
        if _LIBPROC.proc_pid_rusage(pid, 2, ctypes.byref(usage)) == 0:
            return int(usage[9])
    try:
        return int(psutil.Process(pid).memory_info().rss)
    except psutil.Error:
        return 0


_LIBPROC = ctypes.CDLL("/usr/lib/libproc.dylib") if sys.platform == "darwin" else None


async def run_capped(code: str, input_file: Path, timeout: int, max_bytes: int,
                     min_free: int = 0) -> Tuple[str, str]:
    """Run a draft as the harness does (module file, input path as argv, sandboxed env and
    limits), killing it if it outlives `timeout` or its memory passes `max_bytes`.
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
        output = asyncio.ensure_future(process.communicate())
        status = "ok"
        deadline = time.time() + timeout
        while not output.done():
            if (footprint_bytes(process.pid) > max_bytes
                    or psutil.virtual_memory().available < min_free):
                status = "over the memory cap"
            elif time.time() > deadline:
                status = "timed out"
            if status != "ok":
                process.kill()
                break
            await asyncio.sleep(0.2)
        stdout, _ = await output
        if status == "ok" and process.returncode != 0:
            status = "failed"
        return status, stdout.decode()


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
                done.add((row["run"], row["trial"], row["draft_index"]))
    drafts = [d for d in timed_out_drafts(args.results)
              if (d[0], d[1]["trial"], d[2].get("draft_index")) not in done]
    rows = await asyncio.gather(*(rerun(gate, args.timeout, max_bytes, min_free, *d) for d in drafts))
    print(dict(collections.Counter(row["verdict"] for row in rows)), f"of {len(rows)}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("results", nargs="+")
    parser.add_argument("--timeout", type=int, default=600)
    parser.add_argument("--jobs", type=int, default=2)
    parser.add_argument("--max-memory-gb", type=float, default=8.0)
    parser.add_argument("--min-free-gb", type=float, default=8.0)
    parser.add_argument("--done", action="append", help="an earlier output file whose drafts are skipped (repeatable)")
    asyncio.run(main(parser.parse_args()))
