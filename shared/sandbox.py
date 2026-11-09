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
  space, via setrlimit in the child before it execs.

Not constrained: network access and reads elsewhere on the filesystem. Solutions
run as the user, with the user's permissions; the environment scrub removes the
one secret the process itself carried.
"""

import os
from typing import Any, Dict, Optional

from shared.config import RESOURCES_CONFIG

# Variables a Python child needs to start and behave predictably. Everything
# else in os.environ is withheld.
_PASSED_THROUGH = ("PATH", "LANG", "LC_ALL", "LC_CTYPE", "TMPDIR", "SYSTEMROOT")

MAX_FILE_BYTES = 64 * 1024 * 1024


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
