"""Module for executing and validating generated solutions."""

import ast
import logging
import re
import shutil
import subprocess
import sys
import tempfile
import time
import builtins as _bi
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from shared.errors import (
    ExecutionError,
    CompilationError,
    ResourceError,
)
from shared.performance import PerformanceMonitor
from shared.quality.code_formatter import format_code
from shared.tempfiles import TempFileManager
from shared.config import RESOURCES_CONFIG, DEFAULT_EXECUTION_TIMEOUT
from shared.sandbox import (
    OVER_MEMORY, child_env, communicate_capped, configured_limiter, cpu_limit_seconds, sandboxed,
    memory_cap_bytes, resource_limiter,
)
import asyncio

logger = logging.getLogger(__name__)


@dataclass
class TestCase:
    """Test case for validating a solution."""

    input_data: str
    expected_output: str
    description: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert the TestCase instance to a dictionary for JSON serialization."""
        return {
            "input_data": self.input_data,
            "expected_output": self.expected_output,
            "description": self.description,
        }


@dataclass
class PerformanceMetrics:
    """Timing/resource metrics for one solution run.

    Relocated here from the deleted shared/testing.py: this is the shape
    ExecutionResult.performance actually carries. (ExecutionResult was
    previously annotated with an unrelated, incompatible PerformanceMetrics
    from shared.performance that it never constructed.)
    """

    execution_time: float  # seconds
    peak_memory: float     # MB
    cpu_percent: float     # average CPU usage


@dataclass
class ExecutionResult:
    """Result of executing a solution."""

    output: str
    performance: Optional[PerformanceMetrics] = None
    error: Optional[str] = None


# Kept under its old name: tests and callers import it from here.
_build_resource_limiter = resource_limiter


# The entry point appended to generated solutions.
#
# Arity-aware because models define either solve() or solve(input_path), and
# tolerant of a missing argv because saved solutions are also run directly with
# no arguments (dev/verify_solutions.py does exactly that). A previous second
# copy of this block in the provider hardcoded solve(sys.argv[1]), so any
# solution carrying it died with IndexError when verified standalone.
STANDARD_MAIN_BLOCK = (
    'if __name__ == "__main__":\n'
    '    import sys, inspect\n'
    '    sig = inspect.signature(solve)\n'
    '    params = len(sig.parameters)\n'
    '    if params == 0:\n'
    '        print(solve())\n'
    '    elif params == 1:\n'
    '        arg = sys.argv[1] if len(sys.argv) > 1 else "input.txt"\n'
    '        print(solve(arg))\n'
    '    else:\n'
    '        raise TypeError("solve() must take 0 or 1 arguments")'
)


def _last_nonempty_line(output: str) -> str:
    """Return the answer a solution printed.

    Generated solutions sometimes emit progress or debug lines before the answer,
    so the answer is taken from the last non-empty line rather than the whole
    stream.
    """
    lines = [line.strip() for line in (output or "").splitlines() if line.strip()]
    return lines[-1] if lines else ""


async def execute_solution(code: str, input_data: str, timeout: int = 5) -> "ExecutionResult":
    """Execute inline solution code against provided input data.

    This is a convenience wrapper used by tests. It writes the given code to a
    temporary module, writes the input data to a temporary file, executes the
    module by invoking its `solve(input_data: str)` function, and returns the
    output along with basic performance metrics (PerformanceMetrics).

    Raises built-in TimeoutError on timeout to match test expectations.
    """
    repo_root = Path(__file__).parent.parent
    temp_manager = TempFileManager(repo_root)

    module_path = temp_manager.create_temp_file("inline_solution.py")
    module_path.write_text(code)

    input_path = temp_manager.create_temp_file("inline_input.txt")
    input_path.write_text(input_data)

    # Build a small runner that executes solve() from the written module
    runner = (
        "import sys; "
        f"ns={{}}; exec(open(r'{str(module_path)}').read(), ns); "
        f"data=open(r'{str(input_path)}').read(); "
        "print(ns['solve'](data))"
    )

    start = time.time()
    try:
        process = await asyncio.create_subprocess_exec(
            *sandboxed([sys.executable, "-c", runner]),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=str(module_path.parent),
            env=child_env(),
            preexec_fn=configured_limiter(timeout),
        )

        cap = memory_cap_bytes()
        stopped, stdout, stderr = await communicate_capped(process, timeout, cap)
        if stopped == OVER_MEMORY:
            return ExecutionResult(output="", performance=None, error=_over_memory_error(cap))
        if stopped:
            # Raise the builtin TimeoutError so callers/tests can catch it.
            raise _bi.TimeoutError(f"Execution timed out after {timeout} seconds")

        if process.returncode != 0:
            error_msg = stderr.decode() if stderr else "Unknown error"
            return ExecutionResult(output="", performance=None, error=f"Process failed: {error_msg}")

        elapsed = time.time() - start
        # Provide minimal, test-compatible metrics; values aren't validated in tests
        perf = PerformanceMetrics(execution_time=elapsed, peak_memory=0.0, cpu_percent=0.0)
        return ExecutionResult(output=stdout.decode().strip(), performance=perf, error=None)

    except Exception as e:
        # Propagate built-in TimeoutError so tests can catch it
        if isinstance(e, _bi.TimeoutError):
            raise
        return ExecutionResult(output="", performance=None, error=str(e))

def _over_memory_error(cap_bytes: int) -> str:
    """The error for a run stopped at the memory cap. It says "memory", never "timed out",
    so repair feedback does not mistake it for a slow but bounded program."""
    return f"Solution exceeded the memory cap of {cap_bytes // (1024 * 1024)} MB and was stopped"


class SolutionExecutor:
    """Handles execution and validation of generated solutions."""

    def __init__(self, workspace_dir: Path, timeout: Optional[int] = None) -> None:
        """Initialize the solution executor.

        Args:
            workspace_dir: Workspace directory path
            timeout: Per-execution timeout in seconds. None falls back to the
                configured default (resources.yaml execution.timeout_seconds).
        """
        self.workspace_dir = workspace_dir
        self.timeout = timeout
        self.temp_manager = TempFileManager(workspace_dir)
        self.performance_monitor = PerformanceMonitor()

    async def prepare_solution(
        self, problem_id: str, source_code: str, test_cases: List[TestCase], model_name: str = ""
    ) -> Tuple[bool, Optional[str]]:
        """Prepare and validate a solution.

        Args:
            problem_id: Unique identifier for the problem (e.g., "2021_day1_part1")
            source_code: Generated solution code
            test_cases: List of test cases to validate against
            model_name: Name of the model generating this solution

        Returns:
            Tuple of (is_valid, error_message)
        """
        # Create a temporary module for this solution
        model_suffix = f"_{model_name.replace(':', '_')}" if model_name else ""
        module_path = self.temp_manager.create_temp_file(f"{problem_id}{model_suffix}.py")

        try:
            # Format the code before validation
            formatted_code, success = format_code(source_code)
            if not success:
                raise CompilationError("Failed to format code")

            # Add model attribution comment
            if model_name:
                formatted_code = f"# Generated by model: {model_name}\n{formatted_code}"

            # Ensure proper __main__ block usage while supporting solve() with 0 or 1 args
            main_block = STANDARD_MAIN_BLOCK

            if "__main__" in formatted_code:
                # Replace any existing main block with our standardized version
                formatted_code = re.sub(
                    r"if\s+__name__\s*==\s*['\"]__main__['\"]\s*:.+?(?=(?:\n\S|\Z))",
                    main_block,
                    formatted_code,
                    flags=re.DOTALL
                )
            else:
                # Add our main block if none exists
                formatted_code += f"\n\n{main_block}"

            # Log the formatted code for debugging
            logger.debug("Generated solution code:\n%s", formatted_code)

            # Validate syntax and structure by parsing, never by executing.
            #
            # This used to import the generated module with spec.loader.exec_module,
            # which ran model-written code inside the solver's own process -- after
            # load_dotenv() had already put AOC_SESSION and any API keys into
            # os.environ, and before any timeout or subprocess isolation applied.
            # An AST check answers the same question ("is there a solve function?")
            # without running anything, and additionally cannot be fooled by
            # module-level side effects.
            try:
                tree = ast.parse(formatted_code)
            except SyntaxError as e:
                raise CompilationError(f"Invalid Python syntax: {str(e)}")

            has_solve = any(
                isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
                and node.name == "solve"
                for node in tree.body
            )
            if not has_solve:
                raise CompilationError("Solution must contain a solve() function")

            # Write the solution to a temporary file
            module_path.write_text(formatted_code)

            # Test cases are deliberately NOT run here. They are executed by
            # _run_test_case, which compares against the expected output and writes
            # its input to a scratch directory. The previous implementation ran them
            # here by overwriting the real years/<year>/day<NN>/input.txt and
            # restoring it in a finally block -- a kill mid-run permanently replaced
            # the puzzle input with example data. It also raised on the first
            # mismatch, which short-circuited the full-input run and hid correct
            # solutions whenever an example was mis-parsed.
            return True, None

        except (SyntaxError, IndentationError) as e:
            raise CompilationError(f"Invalid Python syntax: {str(e)}") from e
        except IOError as e:
            raise ExecutionError(f"Failed to write solution file: {str(e)}") from e
        except Exception as e:
            logger.error("Unexpected error preparing solution: %s", str(e))
            raise ExecutionError(str(e)) from e

    async def execute_solution(
        self, module_path: Path, input_path: str
    ) -> ExecutionResult:
        """Execute a solution module with input data.
        
        Args:
            module_path: Path to solution module
            input_path: Path to input data file
            
        Returns:
            ExecutionResult containing output and performance metrics
        """
        try:
            # Get resource limits from config
            timeout = self.timeout or RESOURCES_CONFIG.get("execution", {}).get(
                "timeout_seconds", DEFAULT_EXECUTION_TIMEOUT
            )
            max_memory = RESOURCES_CONFIG.get("execution", {}).get("max_memory_mb", 512)
            max_processes = RESOURCES_CONFIG.get("execution", {}).get("max_processes", 1)

            # Run in a fresh, empty directory holding only a copy of the input. The
            # input's own directory (years/<year>/day<NN>/) also holds the accepted
            # answers and the ledger's verified solutions, which a candidate opening
            # a relative path there could read; none of the saved drafts ever did, but
            # the result must not depend on that.
            with tempfile.TemporaryDirectory(prefix="problem-solver-run-") as workdir:
                run_input = Path(workdir) / "input.txt"
                shutil.copyfile(Path(input_path).resolve(), run_input)

                # Run the module file directly and pass paths as argv.
                #
                # This previously interpolated module_path and input_path into a Python
                # source string ("exec(open('...').read())"), so any path containing a
                # quote broke out of the literal into executable code. It also passed
                # limit=, which is asyncio's StreamReader buffer size, not a memory cap:
                # generated code ran with no resource limits at all.
                process = await asyncio.create_subprocess_exec(
                    *sandboxed([sys.executable, str(Path(module_path).resolve()), str(run_input)]),
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                    cwd=workdir,
                    env=child_env(),
                    preexec_fn=resource_limiter(
                        max_memory, max_processes, cpu_seconds=cpu_limit_seconds(timeout)
                    ),
                )

                stopped, stdout, stderr = await communicate_capped(
                    process, timeout, max_memory * 1024 * 1024
                )
            if stopped == OVER_MEMORY:
                return ExecutionResult("", error=_over_memory_error(max_memory * 1024 * 1024))
            if stopped:
                return ExecutionResult(
                    "", error=f"Solution timed out after {timeout} seconds"
                )
            if process.returncode != 0:
                error_msg = stderr.decode() if stderr else "Unknown error"

                # Enhance error messages for common issues
                if "NameError" in error_msg:
                    if "name 'Union' is not defined" in error_msg:
                        error_msg = "Missing import: Solution uses typing.Union without importing it"
                    elif "name 'chain' is not defined" in error_msg:
                        error_msg = "Missing import: Solution uses itertools.chain without importing it"
                    elif "name 'Optional' is not defined" in error_msg:
                        error_msg = "Missing import: Solution uses typing.Optional without importing it"

                return ExecutionResult("", error=f"Process failed: {error_msg}")

            return ExecutionResult(stdout.decode())

        except Exception as e:
            return ExecutionResult("", error=str(e))

    async def run_against_full_input(
        self, problem_id: str, year: int, day: int, part: int, source_code: str
    ) -> ExecutionResult:
        """Run a solution against the full input data.

        Args:
            problem_id: Unique identifier for the problem
            year: Problem year
            day: Problem day
            part: Problem part
            source_code: Solution source code

        Returns:
            ExecutionResult from running against full input
        """
        input_file = (
            self.workspace_dir / "years" / str(year) / f"day{day:02d}" / "input.txt"
        )

        if not input_file.exists():
            return ExecutionResult(
                output="", performance=None, error=f"Input file not found: {input_file}"
            )

        # Create solution module
        module_path = self.temp_manager.create_temp_file(f"{problem_id}.py")
        module_path.write_text(source_code)

        # Execute the solution
        result = await self.execute_solution(module_path, str(input_file))

        return result

    async def test_solution(
        self,
        solution_code: str,
        year: int,
        day: int,
        part: int,
        test_cases: Optional[List[TestCase]] = None,
        model_name: str = "",
        debug: bool = False,
        force_full_input: bool = False
    ) -> Tuple[List[ExecutionResult], Optional[ExecutionResult], Optional[str]]:
        """Test a solution against example cases and full input.

        Args:
            solution_code: The solution code to test
            year: Problem year
            day: Problem day
            part: Problem part
            test_cases: Optional list of test cases. If None, uses default test cases.
            model_name: Name of the model that generated this solution
            debug: Whether to enable debug output
            force_full_input: Run against the full input even if example runs failed

        Returns:
            Tuple containing:
            - List[ExecutionResult]: Results from example tests
            - Optional[ExecutionResult]: Result from full input test (None if examples failed)
            - Optional[str]: Full input answer if successful, None otherwise
        """
        try:
            problem_id = f"{year}_day{day:02d}_part{part}"
            example_results: List[ExecutionResult] = []
            full_result: Optional[ExecutionResult] = None
            full_answer: Optional[str] = None

            # Validate the solution code
            try:
                is_valid, error = await self.prepare_solution(
                    problem_id, solution_code, test_cases or [], model_name=model_name
                )
            except Exception as e:
                message = str(e)
                example_results.append(
                    ExecutionResult(
                        output="",
                        error=f"Validation failed before examples: {message}",
                    )
                )
                return example_results, None, None

            if not is_valid:
                example_results.append(
                    ExecutionResult(
                        output="",
                        error=(
                            f"Validation failed before examples: {error}"
                            if error
                            else "Validation failed before examples"
                        ),
                    )
                )
                return example_results, None, None

            # Run example tests
            for i, test_case in enumerate(test_cases or [], 1):
                try:
                    result = await self._run_test_case(
                        problem_id, solution_code, test_case, year, day, i
                    )
                    example_results.append(result)
                except Exception as e:
                    example_results.append(
                        ExecutionResult(output="", error=f"Test case {i} error: {str(e)}")
                    )

            # Run against full input if examples pass. When the caller holds a
            # stronger oracle (the accepted AoC answer) it can ask for the full run
            # anyway, so that a mis-parsed example cannot hide a correct solution.
            if force_full_input or all(result.error is None for result in example_results):
                try:
                    full_result = await self.run_against_full_input(
                        problem_id, year, day, part, solution_code
                    )
                    if full_result.error is None:
                        full_answer = full_result.output.strip()
                except Exception as e:
                    full_result = ExecutionResult(
                        output="", error=f"Error running against full input: {str(e)}"
                    )

            return example_results, full_result, full_answer

        except Exception as e:
            logger.error("Unexpected error testing solution: %s", str(e))
            return [], None, None

    async def _run_test_case(
        self, problem_id: str, solution_code: str, test_case: TestCase, year: int, day: int, test_case_index: int
    ) -> ExecutionResult:
        # Create solution module
        module_path = self.temp_manager.create_temp_file(f"{problem_id}.py")
        module_path.write_text(solution_code)

        # Create test input file
        input_file = self._create_test_input(test_case.input_data)

        # Execute the solution
        result = await self.execute_solution(module_path, str(input_file))

        if result.error is not None:
            return result

        # Compare against the expected answer. Without this an example run only
        # proved the code did not crash, which is how hardcoded stubs and wrong
        # algorithms were previously accepted as validated solutions.
        expected = (test_case.expected_output or "").strip()
        if not expected:
            return result

        actual = _last_nonempty_line(result.output)
        if actual != expected:
            return ExecutionResult(
                output=result.output,
                performance=result.performance,
                error=(
                    f"Test case {test_case_index} failed: "
                    f"expected {expected!r}, got {actual!r}"
                ),
            )

        return result

    def _create_test_input(self, input_data: str) -> str:
        # Create a temporary file for input data
        input_path = self.temp_manager.create_temp_file("input.txt")
        input_path.write_text(input_data)
        return str(input_path)

    def cleanup(self) -> None:
        """Clean up temporary files."""
        self.temp_manager.cleanup()

    def extract_test_cases(self, problem_text: str) -> List[Dict[str, Any]]:
        """Extract test cases from problem text."""
        test_cases = []
        current_example = None

        # Split into sections by double newlines
        sections = problem_text.split("\n\n")
        for section in sections:
            # Look for example header
            if "Example" in section or "example" in section:
                # Look for number block
                number_block = re.search(r"(?m)^(\d+\n)+\d+$", section)
                if number_block:
                    current_example = {
                        "description": section,
                        "input": number_block.group(0),
                    }
                    continue

            # Look for output
            if current_example:
                output_match = re.search(
                    r"(?m)(?:answer|output|result).*?[is:]?\s*[*]?(\d+)[*]?",
                    section,
                    re.IGNORECASE,
                )
                if output_match:
                    test_case = TestCase(
                        description=current_example["description"],
                        input_data=current_example["input"],
                        expected_output=output_match.group(1),
                    )
                    test_cases.append(test_case.to_dict())
                    current_example = None

        return test_cases

    def get_test_results(self, solution_code: str, year: int, day: int) -> Dict[str, Any]:
        """Get test results for a solution.
        
        Args:
            solution_code: Solution code to test
            year: Problem year
            day: Problem day
            
        Returns:
            Dictionary containing test results
        """
        return {
            "examples": {
                "passed": True,  # TODO: Implement example test cases
                "results": []
            },
            "full_input": {
                "passed": True,  # TODO: Implement full input test
                "result": None
            },
            "execution_time": 0,  # TODO: Track actual execution time
            "memory_usage": 0  # TODO: Track actual memory usage
        }
