"""What a child process running model-written code may see and use.

Every path that executes generated code goes through here: the solve-loop
executor (shared/execution.py), the oracle (shared/verification.py) and the
Part One example check (shared/problem_context.py). A leaf module, importing
only config, so each of them can depend on it without a cycle.

Two things are constrained:

- **The environment.** `shared.config` runs load_dotenv() at import, so the
  solver's own os.environ holds AOC_SESSION (and any API keys). A child
  inherits os.environ by default, which handed the session cookie to every
  program a model wrote. Children now get `child_env()`: enough to start
  Python, nothing from .env.
- **Resources.** CPU time, file size, process count and (on Linux) address
  space, via setrlimit in the child before it execs. macOS ignores the
  address-space limit, so memory is also watched from outside: the runners
  below poll the child's physical footprint and kill it above the same cap.
  The footprint counts compressed pages, which resident size does not: a grid
  of zeros compresses so well that a draft can show a few GB resident while
  holding tens of GB. A
  draft that grows without bound (brute force over a huge grid can pass 8 GB in
  seconds) otherwise exhausts the machine; six at once froze a 64 GB Mac.

Not constrained: network access and reads elsewhere on the filesystem. Solutions
run as the user, with the user's permissions; the environment scrub removes the
one secret the process itself carried.
"""

import asyncio
import ctypes
import os
import subprocess
import sys
import time
from typing import Any, Dict, List, Optional, Tuple

import psutil

from shared.config import RESOURCES_CONFIG

# Variables a Python child needs to start and behave predictably. Everything
# else in os.environ is withheld.
_PASSED_THROUGH = ("PATH", "LANG", "LC_ALL", "LC_CTYPE", "TMPDIR", "SYSTEMROOT")

MAX_FILE_BYTES = 64 * 1024 * 1024

# How often a running child's memory is checked.
_POLL_SECONDS = 0.2

TIMED_OUT = "timed out"
OVER_MEMORY = "over the memory cap"


def child_env() -> Dict[str, str]:
    """The environment for a process that runs model-written code."""
    env = {name: os.environ[name] for name in _PASSED_THROUGH if name in os.environ}
    # No stray .pyc files next to generated solutions.
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    return env


def resource_limiter(
    max_memory_mb: int, max_processes: int, cpu_seconds: int
) -> Optional[Any]:
    """Build a preexec_fn that constrains generated code in the child process.

    Applied limits, and what is genuinely enforced:

    - RLIMIT_CPU     CPU-seconds. Backstops the wall-clock timeout against a busy
                     loop that ignores SIGTERM.
    - RLIMIT_FSIZE   Maximum file size the solution can write.
    - RLIMIT_NPROC   Process count, so a runaway solution cannot fork-bomb.
    - RLIMIT_AS      Address space. Works on Linux; **silently unavailable on
                     macOS**, where setting it makes the interpreter fail to
                     start. Memory is therefore not capped on darwin.

    Returns None on platforms without the resource module (Windows).
    """
    try:
        import resource
    except ImportError:  # pragma: no cover - Windows
        return None

    max_memory_bytes = max(max_memory_mb, 1) * 1024 * 1024

    def _apply() -> None:
        # Each limit is applied independently: an unsupported one must not
        # prevent the others from taking effect.
        for limit_name, value in (
            ("RLIMIT_CPU", (cpu_seconds, cpu_seconds)),
            ("RLIMIT_FSIZE", (MAX_FILE_BYTES, MAX_FILE_BYTES)),
            ("RLIMIT_NPROC", (max_processes, max_processes)),
            ("RLIMIT_AS", (max_memory_bytes, max_memory_bytes)),
        ):
            limit = getattr(resource, limit_name, None)
            if limit is None:
                continue
            try:
                resource.setrlimit(limit, value)
            except (ValueError, OSError):
                continue

    return _apply


def configured_limiter(timeout_seconds: float) -> Optional[Any]:
    """`resource_limiter` with the limits from config/resources.yaml."""
    execution = RESOURCES_CONFIG.get("execution", {})
    return resource_limiter(
        execution.get("max_memory_mb", 512),
        execution.get("max_processes", 1),
        cpu_seconds=max(int(timeout_seconds), 1),
    )


def memory_cap_bytes() -> int:
    """The per-process memory cap from config/resources.yaml (execution.max_memory_mb)."""
    return max(int(RESOURCES_CONFIG.get("execution", {}).get("max_memory_mb", 512)), 1) * 1024 * 1024


_LIBPROC = ctypes.CDLL("/usr/lib/libproc.dylib") if sys.platform == "darwin" else None


def footprint_bytes(pid: int) -> int:
    """A process's physical footprint (resident plus compressed), as Activity Monitor
    shows it; resident size where libproc is unavailable."""
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


async def communicate_capped(
    process: "asyncio.subprocess.Process", timeout: float, max_bytes: int, min_free: int = 0
) -> Tuple[Optional[str], bytes, bytes]:
    """Wait for `process`, stopping it past `timeout` seconds, past `max_bytes` of physical
    footprint, or when the machine has less than `min_free` bytes available.

    Returns (stopped, stdout, stderr): stopped is None when the process finished
    on its own, else TIMED_OUT or OVER_MEMORY. A timed-out process gets SIGTERM
    and five seconds before SIGKILL; one over the cap is killed at once.
    """
    output = asyncio.ensure_future(process.communicate())
    deadline = time.monotonic() + timeout
    stopped: Optional[str] = None
    while not output.done():
        if (footprint_bytes(process.pid) > max_bytes
                or (min_free and psutil.virtual_memory().available < min_free)):
            stopped = OVER_MEMORY
            process.kill()
            break
        if time.monotonic() > deadline:
            stopped = TIMED_OUT
            process.terminate()
            try:
                await asyncio.wait_for(asyncio.shield(output), timeout=5)
            except asyncio.TimeoutError:
                process.kill()
            break
        await asyncio.sleep(_POLL_SECONDS)
    stdout, stderr = await output
    return stopped, stdout or b"", stderr or b""


def run_capped(
    args: List[str], cwd: str, timeout: float, max_bytes: int
) -> Tuple[Optional[str], "subprocess.CompletedProcess[str]"]:
    """Synchronous `communicate_capped` for code run with subprocess (text output).

    Starts `args` with child_env() and configured_limiter(timeout). Returns
    (stopped, completed); stopped is None, TIMED_OUT or OVER_MEMORY.
    """
    process = subprocess.Popen(
        args, cwd=cwd, env=child_env(), preexec_fn=configured_limiter(timeout),
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
    )
    deadline = time.monotonic() + timeout
    stopped: Optional[str] = None
    while True:
        try:
            stdout, stderr = process.communicate(timeout=_POLL_SECONDS)
            break
        except subprocess.TimeoutExpired:
            pass
        if stopped:
            continue
        if footprint_bytes(process.pid) > max_bytes:
            stopped = OVER_MEMORY
            process.kill()
        elif time.monotonic() > deadline:
            stopped = TIMED_OUT
            process.kill()
    return stopped, subprocess.CompletedProcess(args, process.returncode, stdout, stderr)
