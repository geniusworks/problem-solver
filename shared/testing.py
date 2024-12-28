"""Solution testing framework."""

import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Union, Dict

@dataclass
class TestResult:
    """Result of a test run."""
    passed: bool
    input_data: str
    expected_output: str
    actual_output: Optional[str] = None
    error_message: Optional[str] = None
    execution_time: Optional[float] = None

class SolutionTester:
    """Tests solutions against examples and actual input."""
    
    def __init__(self, solution_path: Path):
        self.solution_path = solution_path
        self.results: List[TestResult] = []
    
    def run_test(self, 
                 input_data: str, 
                 expected_output: str,
                 timeout: int = 5) -> TestResult:
        """Run a single test case."""
        try:
            # Create temporary input file
            input_file = self.solution_path.parent / "test_input.txt"
            with open(input_file, 'w') as f:
                f.write(input_data)
            
            # Run solution
            result = subprocess.run(
                ["python", str(self.solution_path)],
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=str(self.solution_path.parent)
            )
            
            # Clean up
            input_file.unlink()
            
            # Check output
            actual_output = result.stdout.strip()
            passed = actual_output == str(expected_output).strip()
            
            test_result = TestResult(
                passed=passed,
                input_data=input_data,
                expected_output=expected_output,
                actual_output=actual_output,
                error_message=result.stderr if result.stderr else None,
                execution_time=None  # TODO: Add timing
            )
            
        except subprocess.TimeoutExpired:
            test_result = TestResult(
                passed=False,
                input_data=input_data,
                expected_output=expected_output,
                error_message="Solution timed out",
                execution_time=timeout
            )
        
        except Exception as e:
            test_result = TestResult(
                passed=False,
                input_data=input_data,
                expected_output=expected_output,
                error_message=str(e)
            )
        
        self.results.append(test_result)
        return test_result
    
    def run_all_tests(self, test_cases: List[Dict[str, str]]) -> bool:
        """Run all test cases and return overall success."""
        all_passed = True
        for test in test_cases:
            result = self.run_test(
                input_data=test["input"],
                expected_output=test["expected"]
            )
            if not result.passed:
                all_passed = False
        return all_passed
    
    def generate_report(self) -> str:
        """Generate a report of all test results."""
        lines = ["Test Results:"]
        
        for i, result in enumerate(self.results, 1):
            lines.append(f"\nTest {i}:")
            lines.append(f"Status: {'PASSED' if result.passed else 'FAILED'}")
            lines.append(f"Input:\n{result.input_data}")
            lines.append(f"Expected Output: {result.expected_output}")
            if result.actual_output:
                lines.append(f"Actual Output: {result.actual_output}")
            if result.error_message:
                lines.append(f"Error: {result.error_message}")
            if result.execution_time:
                lines.append(f"Execution Time: {result.execution_time:.2f}s")
        
        return "\n".join(lines)
