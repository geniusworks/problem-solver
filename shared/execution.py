"""Module for executing and validating generated solutions."""

import importlib.util
import logging
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from shared.config import (
    ExecutionError,
    TimeoutError,
    CompilationError,
    RuntimeError,
    ResourceError,
)
from shared.performance import PerformanceMonitor, PerformanceMetrics
from shared.quality.code_formatter import format_code

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
class ExecutionResult:
    """Result of executing a solution."""

    output: str
    performance: Optional[PerformanceMetrics] = None
    error: Optional[str] = None


class SolutionExecutor:
    """Handles execution and validation of generated solutions."""

    def __init__(self, workspace_dir: Path):
        """Initialize the solution executor.

        Args:
            workspace_dir: Workspace directory path
        """
        self.workspace_dir = workspace_dir
        self.temp_dir = workspace_dir / ".temp"
        self.temp_dir.mkdir(parents=True, exist_ok=True)
        self.performance_monitor = PerformanceMonitor()

    async def prepare_solution(
        self, problem_id: str, source_code: str, test_cases: List[TestCase]
    ) -> Tuple[bool, Optional[str]]:
        """Prepare and validate a solution.

        Args:
            problem_id: Unique identifier for the problem (e.g., "2021_day1_part1")
            source_code: Generated solution code
            test_cases: List of test cases to validate against

        Returns:
            Tuple of (is_valid, error_message)
        """
        # Create a temporary module for this solution
        module_path = self.temp_dir / f"{problem_id}.py"

        try:
            # Format the code before validation
            formatted_code, _ = format_code(source_code)

            # Log the formatted code for debugging
            logger.debug("Formatted code:\n%s", formatted_code)

            # Write the solution to a temporary file
            module_path.write_text(formatted_code)

            # Try to import it to check for syntax errors
            spec = importlib.util.spec_from_file_location(
                f"solution_{problem_id}", module_path
            )
            if not spec or not spec.loader:
                raise CompilationError("Failed to create module specification")

            module = importlib.util.module_from_spec(spec)
            sys.modules[spec.name] = module
            spec.loader.exec_module(module)

            # Verify it has a solve function
            if not hasattr(module, "solve"):
                raise CompilationError("Solution must contain a solve() function")

            # Run test cases
            for test_case in test_cases:
                # Create test input file in the same directory as the real input
                year, day = re.match(r"(\d+)_day(\d+)", problem_id).groups()
                input_dir = self.workspace_dir / "years" / year / f"day{int(day):02d}"
                input_file = input_dir / "input.txt"

                # Temporarily write test input
                orig_content = None
                if input_file.exists():
                    orig_content = input_file.read_text()
                input_file.write_text(test_case.input_data)

                try:
                    # Set input file path and execute
                    result = await self.execute_solution(module_path, str(input_file))

                    if (
                        result.error
                        or result.output.strip() != test_case.expected_output.strip()
                    ):
                        raise ExecutionError(
                            f"Test case failed: {result.error or 'Output mismatch'}"
                        )

                except (IOError, OSError) as e:
                    logger.error("IO error during test case execution: %s", str(e))
                    raise ExecutionError(str(e)) from e

                finally:
                    # Restore original content
                    if orig_content is not None:
                        input_file.write_text(orig_content)
                    else:
                        input_file.unlink()

            return True, None

        except (SyntaxError, IndentationError) as e:
            raise CompilationError(f"Invalid Python syntax: {str(e)}") from e
        except IOError as e:
            raise ExecutionError(f"Failed to write solution file: {str(e)}") from e
        except Exception as e:
            logger.error("Unexpected error preparing solution: %s", str(e))
            raise ExecutionError(str(e)) from e

    async def execute_solution(
        self, module_path: Path, input_file_path: str
    ) -> ExecutionResult:
        """Execute a solution with the given input.

        Args:
            module_path: Path to the solution module
            input_file_path: Path to the input file

        Returns:
            ExecutionResult containing output and performance metrics
        """
        try:
            # Import the solution module
            spec = importlib.util.spec_from_file_location("solution", module_path)
            if not spec or not spec.loader:
                raise CompilationError("Failed to create module specification")

            module = importlib.util.module_from_spec(spec)
            sys.modules["solution"] = module
            spec.loader.exec_module(module)

            # Execute the solution with performance monitoring
            with self.performance_monitor.monitor():
                result = str(module.solve(input_file_path))

            # Get performance metrics
            metrics = self.performance_monitor.get_metrics()

            return ExecutionResult(output=result, performance=metrics, error=None)

        except subprocess.TimeoutExpired as e:
            raise TimeoutError("Solution execution timed out") from e
        except subprocess.CalledProcessError as e:
            raise RuntimeError(
                f"Solution process failed with exit code {e.returncode}: {str(e)}"
            ) from e
        except MemoryError as e:
            raise ResourceError("Solution exceeded memory limits") from e
        except IOError as e:
            raise ExecutionError(f"IO error during execution: {str(e)}") from e
        except Exception as e:
            logger.error("Unexpected error during execution: %s", str(e))
            raise ExecutionError(str(e)) from e

    async def run_against_full_input(
        self, problem_id: str, year: int, day: int, source_code: str
    ) -> ExecutionResult:
        """Run a solution against the full input data.

        Args:
            problem_id: Unique identifier for the problem
            year: Problem year
            day: Problem day
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
        module_path = self.temp_dir / f"{problem_id}.py"
        module_path.write_text(source_code)

        # Execute the solution
        result = await self.execute_solution(module_path, str(input_file))

        return result

    async def test_solution(
        self,
        solution_code: str,
        year: int,
        day: int,
        test_cases: Optional[List[TestCase]] = None,
    ) -> Tuple[bool, bool, List[ExecutionResult], ExecutionResult, Optional[str]]:
        """Test a solution against example test cases and full input.

        Args:
            solution_code: The solution code to test
            year: Problem year
            day: Problem day
            test_cases: Optional list of test cases. If None, uses default test cases.

        Returns:
            Tuple containing:
            - bool: Whether all example test cases passed
            - bool: Whether full input test passed
            - List[ExecutionResult]: Results from example test cases
            - ExecutionResult: Result from full input test
            - Optional[str]: Full input answer if successful, None otherwise
        """
        problem_id = f"{year}_day{day}"

        # Format and prepare solution
        success, error = await self.prepare_solution(
            problem_id, solution_code, test_cases or []
        )
        if not success:
            logger.error("Solution preparation failed: %s", error)
            return False, False, [], ExecutionResult("", None), None

        # Run example test cases
        example_results = []
        if test_cases:
            for test_case in test_cases:
                result = await self.execute_solution(
                    self.temp_dir / f"{problem_id}.py",
                    self._create_test_input(test_case.input_data),
                )
                example_results.append(result)
                if (
                    result.error
                    or result.output.strip() != test_case.expected_output.strip()
                ):
                    return (
                        False,
                        False,
                        example_results,
                        ExecutionResult("", None),
                        None,
                    )

        # Run full input test
        input_file = (
            self.workspace_dir / "years" / str(year) / f"day{day:02d}" / "input.txt"
        )
        if not input_file.exists():
            logger.error("Full input file not found: %s", input_file)
            return False, False, example_results, ExecutionResult("", None), None

        full_result = await self.execute_solution(
            self.temp_dir / f"{problem_id}.py", str(input_file)
        )

        if full_result.error:
            return True, False, example_results, full_result, None

        return True, True, example_results, full_result, full_result.output.strip()

    def _create_test_input(self, input_data: str) -> str:
        # Create a temporary file for input data
        input_path = self.temp_dir / "input.txt"
        input_path.write_text(input_data)
        return str(input_path)

    def cleanup(self) -> None:
        """Clean up temporary files."""
        try:
            for file in self.temp_dir.glob("*"):
                file.unlink()
            self.temp_dir.rmdir()
        except FileNotFoundError:
            pass  # Directory already removed
        except PermissionError as e:
            logger.warning(
                "Permission error cleaning up directory %s: %s", self.temp_dir, str(e)
            )
        except Exception as e:
            logger.error("Error cleaning up directory %s: %s", self.temp_dir, str(e))

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
