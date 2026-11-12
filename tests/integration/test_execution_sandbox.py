"""Isolation properties for running model-generated code.

The solver executes code written by an LLM. These tests pin the properties that
keep that from touching the host process: validation must not execute anything,
subprocess arguments must not be interpolated into source, and a runaway solution
must be killed and reaped.
"""

import asyncio
import os
from pathlib import Path

import pytest

from shared.errors import ExecutionError
from shared.execution import SolutionExecutor, _build_resource_limiter

REPO_ROOT = Path(__file__).resolve().parent.parent.parent

SOLVE_WITH_SIDE_EFFECT = '''
import os
os.environ["PWNED_BY_GENERATED_CODE"] = "yes"

def solve():
    return 1

if __name__ == "__main__":
    print(solve())
'''

NO_SOLVE_FUNCTION = 'print("this module has no solve function")\n'

SLOW_SOLUTION = '''
import time

def solve():
    time.sleep(120)
    return 1

if __name__ == "__main__":
    print(solve())
'''


@pytest.fixture
def executor():
    return SolutionExecutor(REPO_ROOT)


class TestValidationDoesNotExecute:
    async def test_module_level_side_effects_do_not_run_in_process(self, executor):
        """Validation used to import the module, running arbitrary code in-process."""
        os.environ.pop("PWNED_BY_GENERATED_CODE", None)

        ok, _ = await executor.prepare_solution(
            "2024_day01_part1", SOLVE_WITH_SIDE_EFFECT, [], model_name="test"
        )

        assert ok is True
        assert "PWNED_BY_GENERATED_CODE" not in os.environ

    async def test_missing_solve_function_is_rejected(self, executor):
        with pytest.raises(ExecutionError):
            await executor.prepare_solution(
                "2024_day01_part1", NO_SOLVE_FUNCTION, [], model_name="test"
            )

    async def test_syntax_error_is_rejected(self, executor):
        with pytest.raises(ExecutionError):
            await executor.prepare_solution(
                "2024_day01_part1", "def solve( :\n    pass\n", [], model_name="test"
            )


class TestSubprocessIsolation:
    async def test_quote_in_path_cannot_inject_code(self, executor, tmp_path):
        """Paths were interpolated into a source string; a quote escaped the literal."""
        weird_dir = tmp_path / "it's a dir"
        weird_dir.mkdir()
        input_file = weird_dir / "input.txt"
        input_file.write_text("1 2\n")

        module = tmp_path / "sol.py"
        module.write_text(
            'def solve():\n    return 42\n\nif __name__ == "__main__":\n    print(solve())\n'
        )

        result = await executor.execute_solution(module, str(input_file))

        assert result.error is None
        assert result.output.strip() == "42"

    async def test_timeout_kills_and_reaps(self, executor, tmp_path, monkeypatch):
        """terminate() without wait() left zombies and never killed stubborn code."""
        import shared.execution as execution_module

        monkeypatch.setattr(
            execution_module, "RESOURCES_CONFIG",
            {"execution": {"timeout_seconds": 1, "max_memory_mb": 512, "max_processes": 8}},
        )

        input_file = tmp_path / "input.txt"
        input_file.write_text("1\n")
        module = tmp_path / "slow.py"
        module.write_text(SLOW_SOLUTION)

        result = await asyncio.wait_for(
            executor.execute_solution(module, str(input_file)), timeout=30
        )

        assert result.error is not None
        assert "timed out" in result.error.lower()


class TestResourceLimiter:
    def test_limiter_is_callable_and_survives_unsupported_limits(self):
        """macOS rejects RLIMIT_AS; the other limits must still apply."""
        limiter = _build_resource_limiter(512, 8, cpu_seconds=10)
        assert limiter is None or callable(limiter)

    async def test_limited_subprocess_still_runs_normal_code(self, executor, tmp_path):
        """A limiter that breaks ordinary solutions would be worse than none."""
        input_file = tmp_path / "input.txt"
        input_file.write_text("1 2 3\n")
        module = tmp_path / "sol.py"
        module.write_text(
            "def solve():\n"
            "    return sum(int(x) for x in open('input.txt').read().split())\n"
            '\nif __name__ == "__main__":\n    print(solve())\n'
        )

        result = await executor.execute_solution(module, str(input_file))

        assert result.error is None
        assert result.output.strip() == "6"


class TestRunsAwayFromTheAnswers:
    """A candidate runs in an empty directory with only a copy of its input.

    The input's own directory holds the accepted answers and the ledger's verified solutions;
    a candidate run there could read them by relative path.
    """

    async def test_a_candidate_cannot_see_the_files_beside_its_input(self, executor, tmp_path):
        (tmp_path / "input.txt").write_text("1 2 3\n")
        (tmp_path / "answers.json").write_text('{"1": "6"}')
        module = tmp_path / "peek.py"
        module.write_text(
            "import os\n"
            "print(sorted(os.listdir('.')))\n"
            "print(os.path.exists('answers.json'))\n"
        )

        result = await executor.execute_solution(module, str(tmp_path / "input.txt"))

        assert result.error is None
        listing, can_see_answers = result.output.strip().splitlines()
        assert listing == "['input.txt']"
        assert can_see_answers == "False"

    async def test_the_input_is_still_readable_both_ways(self, executor, tmp_path):
        (tmp_path / "input.txt").write_text("1 2 3\n")
        module = tmp_path / "sol.py"
        module.write_text(
            "import sys\n"
            "a = open('input.txt').read()\n"
            "b = open(sys.argv[1]).read()\n"
            "print(sum(int(x) for x in a.split()) if a == b else 'differ')\n"
        )

        result = await executor.execute_solution(module, str(tmp_path / "input.txt"))

        assert (result.error, result.output.strip()) == (None, "6")


class TestTheOracleRunsAwayFromTheAnswers:
    """The oracle's own runner (the ledger gate and the experiment runner's final score) gets the
    same empty directory as the solve loop. It ran in the problem directory until 2026-11-12,
    where a program could read the accepted answer and pass both the oracle and the overfit gate,
    which looks only for the answer as a literal in the source."""

    def test_a_program_that_reads_the_answer_file_is_not_accepted(self, tmp_path, monkeypatch):
        import json

        from shared import config
        from shared.verification import Verdict, verify_solution_code

        monkeypatch.setattr(config, "BASE_DIR", tmp_path)
        problem_dir = tmp_path / "years" / "2099" / "day01"
        problem_dir.mkdir(parents=True)
        (problem_dir / config.INPUT_FILE).write_text("1 2 3\n")
        (problem_dir / config.ANSWERS_FILE).write_text(json.dumps({"1": "424242"}))
        reads_answer = "import json\nprint(json.load(open('answers.json'))['1'])\n"

        result = verify_solution_code(reads_answer, 2099, 1, 1)

        assert result.verdict is not Verdict.CORRECT
        assert result.actual != "424242"

    def test_a_program_that_reads_input_txt_still_passes(self, tmp_path, monkeypatch):
        import json

        from shared import config
        from shared.verification import Verdict, verify_solution_code

        monkeypatch.setattr(config, "BASE_DIR", tmp_path)
        problem_dir = tmp_path / "years" / "2099" / "day01"
        problem_dir.mkdir(parents=True)
        (problem_dir / config.INPUT_FILE).write_text("1 2 3\n")
        (problem_dir / config.ANSWERS_FILE).write_text(json.dumps({"1": "6"}))
        sums = "print(sum(int(x) for x in open('input.txt').read().split()))\n"

        assert verify_solution_code(sums, 2099, 1, 1).verdict is Verdict.CORRECT
