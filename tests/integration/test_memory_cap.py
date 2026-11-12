"""Generated code is stopped at the memory cap on every execution path.

macOS ignores RLIMIT_AS, so before the watchdog a draft that grew without bound
ran until the machine thrashed: six at once froze a 64 GB Mac. On Linux the
kernel limit may stop the same draft first (MemoryError); either way the run
ends early and its error names memory, never a timeout.
"""

import asyncio
import sys
import time

import pytest

import shared.execution as execution_module
import shared.sandbox as sandbox
from shared.execution import SolutionExecutor
from shared.problem_context import _run_on_example
from shared.solver import _is_timeout_error

CAP_MB = 200
LIMITS = {"execution": {"timeout_seconds": 30, "max_memory_mb": CAP_MB, "max_processes": 1}}

# Grows by 50 MB every 0.2 s, slowly enough that the 0.2 s poll sees it pass the cap.
GROWS = (
    "import time\n"
    "blocks = []\n"
    "while True:\n"
    "    blocks.append(bytearray(50 * 1024 ** 2))\n"
    "    time.sleep(0.2)\n"
)


@pytest.fixture(autouse=True)
def small_cap(monkeypatch):
    monkeypatch.setattr(execution_module, "RESOURCES_CONFIG", LIMITS)
    monkeypatch.setattr(sandbox, "RESOURCES_CONFIG", LIMITS)


def test_the_solve_loop_executor_stops_a_draft_at_the_cap(tmp_path):
    (tmp_path / "input.txt").write_text("1\n")
    module = tmp_path / "grows.py"
    module.write_text(GROWS)

    result = asyncio.run(asyncio.wait_for(
        SolutionExecutor(tmp_path).execute_solution(module, str(tmp_path / "input.txt")), timeout=25))

    assert result.error is not None
    assert "memory" in result.error.lower()
    assert not _is_timeout_error(result.error)


def test_the_synchronous_runner_stops_a_draft_at_the_cap(tmp_path):
    (tmp_path / "grows.py").write_text(GROWS)

    stopped, done = sandbox.run_capped(
        [sys.executable, "grows.py"], cwd=str(tmp_path), timeout=25,
        max_bytes=sandbox.memory_cap_bytes())

    assert stopped == sandbox.OVER_MEMORY or "MemoryError" in done.stderr


def test_the_synchronous_runner_returns_a_normal_run(tmp_path):
    stopped, done = sandbox.run_capped(
        [sys.executable, "-c", "print(6)"], cwd=str(tmp_path), timeout=10,
        max_bytes=sandbox.memory_cap_bytes())

    assert stopped is None
    assert (done.returncode, done.stdout.strip()) == (0, "6")


def test_the_synchronous_runner_stops_at_the_timeout(tmp_path):
    stopped, _ = sandbox.run_capped(
        [sys.executable, "-c", "import time; time.sleep(30)"], cwd=str(tmp_path), timeout=1,
        max_bytes=sandbox.memory_cap_bytes())

    assert stopped == sandbox.TIMED_OUT


def test_the_example_check_stops_a_draft_at_the_cap_not_the_timeout():
    start = time.monotonic()
    assert _run_on_example(GROWS, "1\n", timeout=25) is None
    assert time.monotonic() - start < 15


def test_the_footprint_counts_memory_a_process_holds():
    import os
    held = bytearray(300 * 1024 ** 2)
    for i in range(0, len(held), 16384):
        held[i] = 1
    assert sandbox.footprint_bytes(os.getpid()) > 300 * 1024 ** 2
