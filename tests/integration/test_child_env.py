"""Model-written code must not see the solver's secrets.

`shared.config` loads .env into os.environ at import, so AOC_SESSION sits in the
solver's environment. Every path that runs generated code must start the child
with `shared.sandbox.child_env()` instead of inheriting it.
"""

import asyncio
import json

import pytest

from shared import config, problem_context
from shared.execution import SolutionExecutor, execute_solution
from shared.sandbox import child_env
from shared.verification import verify_solution_code

SECRET = "not-a-real-session-cookie"

PRINTS_SESSION = """import os

def solve(data=None):
    return os.environ.get("AOC_SESSION", "absent")

if __name__ == "__main__":
    print(solve())
"""


@pytest.fixture(autouse=True)
def session_in_environment(monkeypatch):
    monkeypatch.setenv("AOC_SESSION", SECRET)


def test_child_env_withholds_the_session_and_keeps_path():
    env = child_env()
    assert "AOC_SESSION" not in env
    assert "PATH" in env


def test_oracle_runner_does_not_pass_the_session(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "BASE_DIR", tmp_path)
    problem_dir = tmp_path / "years" / "2099" / "day01"
    problem_dir.mkdir(parents=True)
    (problem_dir / config.INPUT_FILE).write_text("x\n")
    (problem_dir / config.ANSWERS_FILE).write_text(json.dumps({"1": "absent"}))

    result = verify_solution_code(PRINTS_SESSION, 2099, 1, 1)

    assert result.actual == "absent"


def test_example_runner_does_not_pass_the_session():
    assert problem_context._run_on_example(PRINTS_SESSION, "x\n") == "absent"


def test_inline_executor_does_not_pass_the_session():
    result = asyncio.run(execute_solution(PRINTS_SESSION, "x\n", timeout=20))
    assert result.output.strip() == "absent"


def test_solve_loop_executor_does_not_pass_the_session(tmp_path):
    module = tmp_path / "solution.py"
    module.write_text(PRINTS_SESSION)
    data = tmp_path / "input.txt"
    data.write_text("x\n")

    result = asyncio.run(SolutionExecutor(tmp_path, timeout=20).execute_solution(module, data))

    assert result.output.strip().splitlines()[-1] == "absent"
