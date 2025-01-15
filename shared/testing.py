"""Solution testing framework."""

import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Union, Dict
import json
import config
import time
import psutil
import resource


@dataclass
class PerformanceMetrics:
    """Performance metrics for a test run."""
    execution_time: float  # in seconds
    peak_memory: float    # in MB
    cpu_percent: float    # average CPU usage


@dataclass
class TestResult:
    """Result of a test run."""

    passed: bool
    input_data: str
    expected_output: str
    actual_output: Optional[str] = None
    error_message: Optional[str] = None
    performance: Optional[PerformanceMetrics] = None


def measure_performance(func):
    """Decorator to measure execution time and resource usage."""
    def wrapper(*args, **kwargs):
        process = psutil.Process()
        start_time = time.time()
        start_memory = process.memory_info().rss / 1024 / 1024  # Convert to MB
        
        try:
            result = func(*args, **kwargs)
        finally:
            end_time = time.time()
            end_memory = process.memory_info().rss / 1024 / 1024
            cpu_percent = process.cpu_percent()
            
            # Create performance metrics
            metrics = PerformanceMetrics(
                execution_time=end_time - start_time,
                peak_memory=max(end_memory - start_memory, 0),  # Avoid negative values
                cpu_percent=cpu_percent
            )
            
            # Attach metrics to result if it's a TestResult
            if isinstance(result, TestResult):
                result.performance = metrics
                
        return result
    return wrapper


class SolutionTester:
    """Tests solutions against examples and actual input."""

    def __init__(self, solution_path: Path):
        self.solution_path = solution_path
        self.results: List[TestResult] = []

    @measure_performance
    def run_test(
        self, input_data: str, expected_output: str, timeout: int = 5
    ) -> TestResult:
        """Run a single test case."""
        try:
            # Create temporary input file
            input_file = self.solution_path.parent / "test_input.txt"
            with open(input_file, "w") as f:
                f.write(input_data)

            # Run solution
            result = subprocess.run(
                ["python", str(self.solution_path)],
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=str(self.solution_path.parent),
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
            )

        except subprocess.TimeoutExpired:
            test_result = TestResult(
                passed=False,
                input_data=input_data,
                expected_output=expected_output,
                error_message="Solution timed out",
            )

        except Exception as e:
            test_result = TestResult(
                passed=False,
                input_data=input_data,
                expected_output=expected_output,
                error_message=str(e),
            )

        self.results.append(test_result)
        return test_result

    def load_examples(self) -> List[Dict[str, str]]:
        """Load all examples from the examples directory."""
        examples_dir = self.solution_path.parent / config.EXAMPLES_DIR
        if not examples_dir.exists():
            return []
            
        examples = []
        for example_file in sorted(examples_dir.glob("example_*.json")):
            with open(example_file) as f:
                example_data = json.load(f)
                examples.append(example_data)
                
        return examples

    def run_all_examples(self) -> Dict[str, TestResult]:
        """Run solution against all examples."""
        examples = self.load_examples()
        results = {}
        
        for i, example in enumerate(examples, 1):
            result = self.run_test(
                example["input"],
                example["expected_output"]
            )
            results[f"example_{i}"] = result
            
        return results

    def run_all_tests(self, test_cases: List[Dict[str, str]]) -> bool:
        """Run all test cases and return overall success."""
        all_passed = True
        for test in test_cases:
            result = self.run_test(
                input_data=test["input"], expected_output=test["expected"]
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
            if result.performance:
                lines.append(f"Execution Time: {result.performance.execution_time:.2f}s")
                lines.append(f"Peak Memory: {result.performance.peak_memory:.2f}MB")
                lines.append(f"CPU Usage: {result.performance.cpu_percent:.2f}%")

        return "\n".join(lines)
