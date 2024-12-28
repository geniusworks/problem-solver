"""Module for executing and validating generated solutions."""

import asyncio
import importlib.util
import logging
import os
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from shared.quality.code_formatter import format_code

logger = logging.getLogger(__name__)

@dataclass
class TestCase:
    """Test case for validating a solution."""
    input_data: str
    expected_output: str
    description: Optional[str] = None

@dataclass
class ExecutionResult:
    """Result of executing a solution."""
    output: str
    runtime_ms: float
    error: Optional[str] = None
    memory_mb: Optional[float] = None

class SolutionExecutor:
    """Handles execution and validation of generated solutions."""

    def __init__(self, workspace_dir: str):
        """Initialize the solution executor.
        
        Args:
            workspace_dir: Base directory for solution files.
        """
        self.workspace_dir = Path(workspace_dir)
        self.temp_dir = Path(tempfile.mkdtemp(prefix="aoc_solutions_"))

    async def prepare_solution(
        self,
        problem_id: str,
        source_code: str,
        test_cases: List[TestCase]
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
            formatted_code, format_success = format_code(source_code)
            if not format_success:
                logger.warning("Code formatting failed, proceeding with original code")
                formatted_code = source_code
            
            # Log the formatted code for debugging
            logger.debug("Formatted code:\n%s", formatted_code)
            
            # Write the solution to a temporary file
            module_path.write_text(formatted_code)
            
            # Try to import it to check for syntax errors
            spec = importlib.util.spec_from_file_location(
                f"solution_{problem_id}",
                module_path
            )
            if not spec or not spec.loader:
                return False, "Failed to create module specification"
            
            module = importlib.util.module_from_spec(spec)
            sys.modules[spec.name] = module
            spec.loader.exec_module(module)
            
            # Verify it has a solve function
            if not hasattr(module, "solve"):
                return False, "Solution must contain a solve() function"
            
            # Run test cases
            for test_case in test_cases:
                result = await self.execute_solution(
                    module_path,
                    test_case.input_data
                )
                if result.error:
                    return False, f"Test case failed: {result.error}"
                if result.output.strip() != test_case.expected_output.strip():
                    return False, (
                        f"Test case failed: expected {test_case.expected_output}, "
                        f"got {result.output}"
                    )
            
            return True, None
            
        except Exception as e:
            return False, f"Failed to prepare solution: {str(e)}"

    async def execute_solution(
        self,
        solution_path: Path,
        input_data: str,
        timeout_seconds: int = 10
    ) -> ExecutionResult:
        """Execute a solution with given input data.
        
        Args:
            solution_path: Path to the solution module
            input_data: Input data to pass to the solution
            timeout_seconds: Maximum execution time in seconds
            
        Returns:
            ExecutionResult containing output and execution metrics
        """
        # Create a temporary file for input data
        input_path = self.temp_dir / "input.txt"
        input_path.write_text(input_data)
        
        # Create subprocess to run solution
        start_time = asyncio.get_event_loop().time()
        
        try:
            process = await asyncio.create_subprocess_exec(
                sys.executable,
                str(solution_path),
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env={
                    **os.environ,
                    "AOC_INPUT_FILE": str(input_path)
                }
            )
            
            try:
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(),
                    timeout=timeout_seconds
                )
                runtime = (asyncio.get_event_loop().time() - start_time) * 1000
                
                if process.returncode != 0:
                    return ExecutionResult(
                        output="",
                        runtime_ms=runtime,
                        error=f"Process failed: {stderr.decode()}"
                    )
                
                return ExecutionResult(
                    output=stdout.decode().strip(),
                    runtime_ms=runtime
                )
                
            except asyncio.TimeoutError:
                try:
                    process.kill()
                except ProcessLookupError:
                    pass
                return ExecutionResult(
                    output="",
                    runtime_ms=timeout_seconds * 1000,
                    error="Solution timed out"
                )
                
        except Exception as e:
            return ExecutionResult(
                output="",
                runtime_ms=0,
                error=f"Execution failed: {str(e)}"
            )

    async def run_against_full_input(
        self,
        problem_id: str,
        year: int,
        day: int,
        source_code: str
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
            self.workspace_dir / 
            str(year) / 
            f"day{day:02d}" / 
            "input.txt"
        )
        
        if not input_file.exists():
            return ExecutionResult(
                output="",
                runtime_ms=0,
                error=f"Input file not found: {input_file}"
            )
        
        # Create solution module
        module_path = self.temp_dir / f"{problem_id}.py"
        module_path.write_text(source_code)
        
        return await self.execute_solution(
            module_path,
            input_file.read_text()
        )

    def cleanup(self) -> None:
        """Clean up temporary files."""
        try:
            for file in self.temp_dir.glob("*"):
                file.unlink()
            self.temp_dir.rmdir()
        except Exception as e:
            logger.error("Failed to cleanup temporary files: %s", str(e))

    def extract_test_cases(self, problem_text: str) -> List[TestCase]:
        """Extract test cases from problem description.
        
        Args:
            problem_text: Problem description text
            
        Returns:
            List of extracted test cases
        """
        # This is a placeholder - we'll need to implement sophisticated
        # parsing of problem descriptions to extract example inputs and
        # expected outputs
        test_cases = []
        
        # Look for common patterns in problem descriptions
        # For example:
        # "For example:" followed by input data and "answer:" or "output:"
        
        # For now, return an empty list
        return test_cases
