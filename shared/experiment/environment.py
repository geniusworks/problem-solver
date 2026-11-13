"""What a run ran on, recorded alongside its results.

The config fingerprint identifies the solver settings. It does not identify the
model weights, the Ollama build, the formatter that rewrites every candidate, or
the machine, and each of those has changed results before (an Ollama upgrade
looked like a regression; autopep8 2.0.4 silently stopped formatting on Python
3.13). This is written into each result file, outside the fingerprint, so two
runs with one fingerprint can still be told apart.

Every field is best-effort: a probe that fails records None and never stops a run.
"""

import os
import platform
import subprocess
import sys
from datetime import datetime, timezone
from importlib import metadata
from pathlib import Path
from typing import Any, Dict, Iterable, Optional

from shared import config

REPO_ROOT = Path(__file__).resolve().parent.parent.parent

# Packages whose version can change what a run measures.
_PACKAGES = ("autopep8", "black", "pylint", "radon", "aiohttp", "beautifulsoup4")


def _command(args: Iterable[str]) -> Optional[str]:
    try:
        done = subprocess.run(list(args), capture_output=True, text=True, timeout=5,
                              cwd=REPO_ROOT, check=False)
    except (OSError, subprocess.SubprocessError):
        return None
    return done.stdout.strip() or None if done.returncode == 0 else None


def _package_versions() -> Dict[str, Optional[str]]:
    versions: Dict[str, Optional[str]] = {}
    for name in _PACKAGES:
        try:
            versions[name] = metadata.version(name)
        except metadata.PackageNotFoundError:
            versions[name] = None
    return versions


def _ollama(models: Iterable[str]) -> Dict[str, Any]:
    """Ollama's host, its version and the digest of each model the run uses. The host is
    recorded because it is read from OLLAMA_HOST, outside the config fingerprint: the same
    model name served from another machine shares the fingerprint."""
    import requests

    host = os.getenv("OLLAMA_HOST", "http://localhost:11434").rstrip("/")
    info: Dict[str, Any] = {"host": host, "version": None, "models": {}}
    try:
        info["version"] = requests.get(f"{host}/api/version", timeout=3).json().get("version")
        tags = requests.get(f"{host}/api/tags", timeout=3).json().get("models", [])
    except Exception:  # unreachable, or not Ollama: record what we have
        return info
    digests = {m.get("name"): m.get("digest") for m in tags}
    info["models"] = {name: digests.get(name) for name in models}
    return info


def _machine() -> Dict[str, Any]:
    machine: Dict[str, Any] = {
        "platform": platform.platform(),
        "arch": platform.machine(),
        "cpu": None,
        "memory_bytes": None,
    }
    if sys.platform == "darwin":
        machine["cpu"] = _command(["sysctl", "-n", "machdep.cpu.brand_string"])
        memory = _command(["sysctl", "-n", "hw.memsize"])
        machine["memory_bytes"] = int(memory) if memory and memory.isdigit() else None
    else:
        machine["cpu"] = platform.processor() or None
    return machine


def capture_environment(models: Iterable[str]) -> Dict[str, Any]:
    """Snapshot of everything outside the config that can change a result."""
    commit = _command(["git", "rev-parse", "HEAD"])
    status = _command(["git", "status", "--porcelain", "--untracked-files=no"])
    return {
        "captured_at": datetime.now(timezone.utc).isoformat(),
        "python": platform.python_version(),
        "packages": _package_versions(),
        "ollama": _ollama(list(models)),
        "machine": _machine(),
        "git": {"commit": commit, "dirty": bool(status)},
        # "" is the maintainer's account; a name is a separate account with its own inputs.
        "aoc_account": config.account_name(),
    }
