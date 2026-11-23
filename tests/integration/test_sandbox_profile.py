"""With execution.deny_network set, model-written code has no network on any path; with
execution.confine_files set, it reaches no file outside its own run.

Every path that runs generated code (the solve loop, the inline executor, the oracle, the
Part One example check, and the rerun tool) is started through shared.sandbox.sandboxed().
The network tests have the child connect to a socket this process is listening on; the file
tests have it read and write files beside, but outside, its run.
"""

import asyncio
import importlib.util
import json
import socket
import sys
from pathlib import Path

import pytest

from shared import config, problem_context, sandbox
from shared.execution import SolutionExecutor, execute_solution
from shared.verification import verify_solution_code

pytestmark = pytest.mark.skipif(sys.platform != "darwin", reason="the profile is macOS's sandbox-exec")

SCRIPT = Path(__file__).resolve().parents[2] / "dev" / "rerun_timeouts.py"


@pytest.fixture(autouse=True)
def unconfined(monkeypatch):
    """Both settings off unless a test turns one on."""
    for variable in ("DENY_NETWORK", "CONFINE_FILES"):
        monkeypatch.delenv(variable, raising=False)
    execution = sandbox.RESOURCES_CONFIG.setdefault("execution", {})
    for key in ("deny_network", "confine_files"):
        monkeypatch.setitem(execution, key, False)


@pytest.fixture
def port():
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind(("127.0.0.1", 0))
    server.listen(8)
    yield server.getsockname()[1]
    server.close()


def connects(port):
    return f"""import socket

def solve(data=None):
    try:
        socket.create_connection(("127.0.0.1", {port}), timeout=5).close()
        return "connected"
    except OSError:
        return "denied"

if __name__ == "__main__":
    print(solve())
"""


def run_every_path(code, tmp_path, monkeypatch):
    """What each launch path printed for `code`."""
    monkeypatch.setattr(config, "BASE_DIR", tmp_path)
    problem_dir = tmp_path / "years" / "2099" / "day01"
    problem_dir.mkdir(parents=True)
    (problem_dir / config.INPUT_FILE).write_text("x\n")
    (problem_dir / config.ANSWERS_FILE).write_text(json.dumps({"1": "unknown"}))
    module = tmp_path / "solution.py"
    module.write_text(code)

    spec = importlib.util.spec_from_file_location("rerun_timeouts", SCRIPT)
    rerun = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(rerun)

    solve_loop = asyncio.run(SolutionExecutor(tmp_path, timeout=20).execute_solution(
        module, problem_dir / config.INPUT_FILE))
    return {
        "solve loop": solve_loop.output.strip().splitlines()[-1],
        "inline": asyncio.run(execute_solution(code, "x\n", timeout=20)).output.strip(),
        "oracle": verify_solution_code(code, 2099, 1, 1).actual,
        "examples": problem_context._run_on_example(code, "x\n"),
        "rerun": asyncio.run(rerun.run_capped(code, problem_dir / config.INPUT_FILE, 20,
                                              sandbox.memory_cap_bytes()))[1].strip(),
    }


def test_every_path_is_denied_the_network_when_set(tmp_path, monkeypatch, port):
    monkeypatch.setenv("DENY_NETWORK", "true")
    printed = run_every_path(connects(port), tmp_path, monkeypatch)
    assert printed == dict.fromkeys(printed, "denied")


def test_off_by_default_the_paths_are_unchanged(tmp_path, monkeypatch, port):
    printed = run_every_path(connects(port), tmp_path, monkeypatch)
    assert printed == dict.fromkeys(printed, "connected")


def test_the_limits_still_apply_under_the_profile(tmp_path, monkeypatch):
    monkeypatch.setenv("DENY_NETWORK", "true")
    module = tmp_path / "busy.py"
    module.write_text("while True:\n    pass\n")
    result = asyncio.run(SolutionExecutor(tmp_path, timeout=1).execute_solution(module, module))
    assert "timed out" in result.error


def test_no_profile_means_no_run(monkeypatch):
    monkeypatch.setenv("DENY_NETWORK", "true")
    monkeypatch.setattr(sandbox.shutil, "which", lambda name: None)
    monkeypatch.setattr(sandbox.sys, "platform", "linux")
    with pytest.raises(RuntimeError, match="sandbox-exec"):
        sandbox.sandboxed([sys.executable, "-c", "pass"], ".")


def reaches(outside):
    """A program that reports, on one line, which files beyond its own run it reached."""
    return f"""import os
from pathlib import Path

def attempt(action):
    try:
        action()
        return "reached"
    except OSError:
        return "denied"

def solve(data=None):
    outside = Path(r"{outside}")
    results = [
        attempt(lambda: (outside / "secret.txt").read_text()),
        attempt(lambda: (outside / "written.txt").write_text("x")),
        attempt(lambda: os.listdir(Path.home())),
        attempt(lambda: Path(r"{REPO / 'README.md'}").read_text()),
        "own " + attempt(lambda: (Path("scratch.txt").write_text("x"), Path("scratch.txt").read_text())),
    ]
    return ",".join(results)

if __name__ == "__main__":
    print(solve())
"""


REPO = Path(__file__).resolve().parents[2]


def test_every_path_is_confined_to_its_own_files_when_set(tmp_path, monkeypatch):
    monkeypatch.setenv("CONFINE_FILES", "true")
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "secret.txt").write_text("accepted answer")
    printed = run_every_path(reaches(outside), tmp_path, monkeypatch)
    assert printed == dict.fromkeys(printed, "denied,denied,denied,denied,own reached")
    assert not (outside / "written.txt").exists()


def test_unconfined_by_default_the_paths_reach_every_file(tmp_path, monkeypatch):
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "secret.txt").write_text("accepted answer")
    printed = run_every_path(reaches(outside), tmp_path, monkeypatch)
    assert printed == dict.fromkeys(printed, "reached,reached,reached,reached,own reached")


def test_both_settings_together(tmp_path, monkeypatch, port):
    monkeypatch.setenv("DENY_NETWORK", "true")
    monkeypatch.setenv("CONFINE_FILES", "true")
    printed = run_every_path(connects(port), tmp_path, monkeypatch)
    assert printed == dict.fromkeys(printed, "denied")


def test_a_path_with_a_quote_cannot_widen_the_profile(tmp_path, monkeypatch):
    monkeypatch.setenv("CONFINE_FILES", "true")
    workdir = tmp_path / 'run")(allow file-read-data (subpath "'
    workdir.mkdir()
    secret = tmp_path / "secret.txt"
    secret.write_text("accepted answer")
    stopped, done = sandbox.run_capped(
        [sys.executable, "-c", f"print(open(r'{secret}').read())"], cwd=str(workdir),
        timeout=10, max_bytes=sandbox.memory_cap_bytes())
    assert stopped is None
    assert done.returncode != 0 and "PermissionError" in done.stderr


def test_no_profile_means_no_confined_run(monkeypatch):
    monkeypatch.setenv("CONFINE_FILES", "true")
    monkeypatch.setattr(sandbox.shutil, "which", lambda name: None)
    monkeypatch.setattr(sandbox.sys, "platform", "linux")
    with pytest.raises(RuntimeError, match="sandbox-exec"):
        sandbox.sandboxed([sys.executable, "-c", "pass"], ".")
