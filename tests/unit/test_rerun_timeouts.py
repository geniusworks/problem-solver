"""dev/rerun_timeouts.py picks only first-pass drafts that hit the execution limit."""

import importlib.util
import json
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[2] / "dev" / "rerun_timeouts.py"
spec = importlib.util.spec_from_file_location("rerun_timeouts", SCRIPT)
rerun_timeouts = importlib.util.module_from_spec(spec)
spec.loader.exec_module(rerun_timeouts)

TIMED_OUT = "Solution timed out after 60 seconds"


def attempt(stage, outcome, error=None, code="def solve(d): pass"):
    return {"stage": stage, "outcome": outcome, "error": error, "code": code, "draft_index": 0}


def result_file(tmp_path, attempts):
    run = {"config": {"name": "r"}, "results": [{"problem_id": "2025_day09_part2", "year": 2025,
                                                 "day": 9, "part": 2, "trial": 0,
                                                 "expected": "1", "attempts": attempts}]}
    path = tmp_path / "run.json"
    path.write_text(json.dumps(run))
    return path


def test_only_first_pass_timeouts_are_rerun(tmp_path):
    path = result_file(tmp_path, [
        attempt("generate", "error", TIMED_OUT),
        attempt("generate", "error", "Process failed: IndexError"),
        attempt("generate", "wrong"),
        attempt("repair", "error", TIMED_OUT),
    ])
    picked = list(rerun_timeouts.timed_out_drafts([path]))
    assert [a["stage"] for _, _, a in picked] == ["generate"]
    assert TIMED_OUT in picked[0][2]["error"]


def test_a_run_saved_without_code_is_refused(tmp_path):
    path = result_file(tmp_path, [attempt("generate", "error", TIMED_OUT, code=None)])
    with pytest.raises(SystemExit, match="include-replay"):
        list(rerun_timeouts.timed_out_drafts([path]))


def run(code, tmp_path, timeout=20, max_mb=200):
    import asyncio
    input_file = tmp_path / "input.txt"
    input_file.write_text("1\n")
    return asyncio.run(rerun_timeouts.run_capped(code, input_file, timeout, max_mb * 1024 ** 2))


def test_a_draft_that_keeps_growing_is_killed_at_the_memory_cap(tmp_path):
    # macOS ignores RLIMIT_AS, so without the watchdog this would grow until the machine thrashes.
    grows = "import time\nblocks = []\nwhile True:\n    blocks.append(bytearray(50 * 1024 ** 2))\n    time.sleep(0.2)\n"
    status, _ = run(grows, tmp_path)
    assert status == "over the memory cap"


def test_a_slow_draft_is_stopped_at_the_timeout(tmp_path):
    status, _ = run("import time\ntime.sleep(30)\n", tmp_path, timeout=1)
    assert status == "timed out"


def test_a_draft_that_finishes_returns_its_output(tmp_path):
    code = "import sys\nprint(open(sys.argv[1]).read().strip())\n"
    assert run(code, tmp_path) == ("ok", "1\n")


def test_footprint_counts_the_memory_a_process_holds():
    import os
    held = bytearray(300 * 1024 ** 2)
    for i in range(0, len(held), 16384):
        held[i] = 1
    assert rerun_timeouts.footprint_bytes(os.getpid()) > 300 * 1024 ** 2


def test_a_low_free_memory_floor_stops_a_draft(tmp_path):
    # A floor above the machine's total memory trips at once.
    import asyncio
    import psutil
    input_file = tmp_path / "input.txt"
    input_file.write_text("1\n")
    status, _ = asyncio.run(rerun_timeouts.run_capped(
        "import time\ntime.sleep(30)\n", input_file, 20, 2 ** 40,
        min_free=psutil.virtual_memory().total * 2))
    assert status == "over the memory cap"
