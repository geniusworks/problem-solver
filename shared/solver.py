"""Base solver class for Advent of Code problems."""

import logging
import os
import tempfile
from pathlib import Path
from typing import List, Optional, Dict
from datetime import datetime
import json

from aiohttp import ClientError

from shared.config import ValidationError
from shared.execution import SolutionExecutor, TestCase
from shared.llm.local import OllamaProvider
from shared.parser import parse_problem_text
from shared.utils import fetch_problem_text, ensure_input_file
from shared.validator import submit_solution, SubmissionError


class BaseSolver:
    """Base class for solving AoC problems."""

    def __init__(self, workspace_dir: Path) -> None:
        """Initialize the base solver.

        Args:
            workspace_dir: Workspace directory path
        """
        self.workspace_dir = workspace_dir
        self.solution_executor = SolutionExecutor(workspace_dir)
        self.model = OllamaProvider()

    async def solve_problem(
        self, year: int, day: int, part: int, force: bool = False
    ) -> Optional[str]:
        """Solve an Advent of Code problem."""
        try:
            # Create solution directory (simplified structure)
            day_dir = self.workspace_dir / "years" / str(year) / f"day{day:02d}"
            solutions_dir = day_dir / "solutions"
            solutions_dir.mkdir(parents=True, exist_ok=True)

            # Parse and solve
            problem_text = await fetch_problem_text(year, day)
            problem = parse_problem_text(problem_text)

            # Record start time for performance tracking
            start_time = datetime.now()

            # Generate solution
            solution_code = await self.model.generate_solution(problem)
            generation_time = (datetime.now() - start_time).total_seconds()

            # Test solution
            test_result = await self.solution_executor.test_solution(
                solution_code, year, day, problem.examples
            )
            execution_time = (
                datetime.now() - start_time
            ).total_seconds() - generation_time

            # Unpack test results
            (
                example_passed,
                full_passed,
                example_results,
                full_result,
                full_answer,
            ) = test_result

            # Prepare solution info
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            solution_info = {
                "code": solution_code,
                "prompt": self.model.last_prompt,
                "model": {
                    **self.model.model_info,
                    "parameters": {
                        "temperature": float(os.getenv("DEFAULT_TEMPERATURE", "0.1")),
                        "max_tokens": int(os.getenv("MAX_TOKENS", "2000")),
                    },
                    "generation_time": generation_time,
                },
                "test_results": {
                    "examples": {
                        "passed": example_passed,
                        "inputs": [
                            {
                                "input_data": ex.input_data,
                                "expected_output": ex.expected_output,
                                "description": (
                                    ex.description
                                    if hasattr(ex, "description")
                                    else None
                                ),
                            }
                            for ex in problem.examples
                        ],
                        "expected": [ex.expected_output for ex in problem.examples],
                        "actual": [output.output for output in example_results],
                        "performance": [
                            output.performance.to_dict() if output.performance else None
                            for output in example_results
                        ],
                    },
                    "full_input": {
                        "passed": full_passed,
                        "answer": full_answer,
                        "performance": (
                            full_result.performance.to_dict()
                            if full_result and full_result.performance
                            else None
                        ),
                    },
                },
                "status": {
                    "examples_passed": example_passed,
                    "full_passed": full_passed,
                    "part": part,
                },
                "submission": {
                    "submitted": False,
                    "success": None,
                    "message": None,
                    "timestamp": None,
                    "validation_feedback": None,
                },
                "metadata": {
                    "timestamp": timestamp,
                    "year": year,
                    "day": day,
                    "part": part,
                },
            }

            # Save solution (single location)
            solution_file = solutions_dir / f"solution_{timestamp}.json"
            with open(solution_file, "w") as f:
                json.dump(solution_info, f, indent=2)

            # Handle submission if full test passed
            if full_passed:
                try:
                    success, message = await submit_solution(
                        year, day, part, full_answer
                    )
                    solution_info["submission"].update(
                        {
                            "submitted": True,
                            "success": success,
                            "message": message,
                            "timestamp": datetime.now().strftime("%Y%m%d_%H%M%S"),
                            "validation_feedback": {
                                "error_type": message.split('.')[0] if not success else None,
                                "suggested_checks": message.split('\n')[1:] if not success else None
                            }
                        }
                    )
                    if success:
                        logging.info("Solution submitted successfully: %s", message)
                    else:
                        logging.warning("Solution submission failed: %s", message)
                except ValidationError as e:
                    solution_info["submission"].update(
                        {
                            "submitted": True,
                            "success": False,
                            "message": str(e),
                            "timestamp": datetime.now().strftime("%Y%m%d_%H%M%S"),
                            "validation_feedback": {
                                "error_type": str(e).split('.')[0],
                                "suggested_checks": str(e).split('\n')[1:]
                            }
                        }
                    )
                    logging.error("Error submitting solution: %s", str(e))

                # Update solution file with submission results
                with open(solution_file, "w") as f:
                    json.dump(solution_info, f, indent=2)

            return full_answer if full_passed else None

        except Exception as e:
            logging.error("Error solving problem: %s", str(e))
            return None

    def _create_prompt(self, description: str, test_cases: List[TestCase]) -> str:
        """Create a prompt for the LLM.

        Args:
            description: Problem description
            test_cases: List of test cases

        Returns:
            Prompt string
        """
        # Convert test cases to dicts for serialization
        test_cases_dict = [test_case.to_dict() for test_case in test_cases]
        prompt = """You are a Python code generator for Advent of Code solutions. Follow these rules exactly:

1. Output ONLY Python code, no markdown, no comments, no explanations
2. Code MUST start with necessary imports (always include 're' for parsing)
3. Code MUST define a solve() function that:
   - Reads input from os.environ["AOC_INPUT_FILE"]
   - Handles variations between example and full input format
   - Extracts numbers/data robustly using regex where needed
   - Returns the final answer as a single number or string
4. Ensure your solution:
   - Validates all input assumptions
   - Handles edge cases explicitly
   - Uses precise arithmetic operations
   - Processes ALL valid cases in the input
   - Verifies loop boundary conditions
5. Common pitfalls to avoid:
   - Missing elements in collections
   - Incorrect sequence/array indices
   - Imprecise floating point operations
   - Incomplete input parsing
   - Early termination conditions
6. No print statements except in __main__ block
"""
        prompt += description

        if test_cases_dict:
            prompt += "\n\nExample test cases:\n"
            for i, test in enumerate(test_cases_dict, 1):
                prompt += f"\nTest {i}:\n"
                prompt += f"Input:\n{test['input_data']}\n"
                prompt += f"Expected output: {test['expected_output']}\n"

        return prompt

    def _format_test_cases(self, test_cases: List[TestCase]) -> str:
        """Format test cases for the prompt.

        Args:
            test_cases: List of test cases to format

        Returns:
            Formatted test cases string
        """
        result = []
        for i, test in enumerate(test_cases, 1):
            test_dict = test.to_dict()  # Convert TestCase to dict
            result.extend(
                [
                    f"Test Case {i}:",
                    "Input:",
                    test_dict["input_data"],
                    "Expected Output:",
                    test_dict["expected_output"],
                    "",
                ]
            )
        return "\n".join(result)


def test_serialization():
    test_case = TestCase(
        input_data="199\n200\n208\n210\n200\n207\n240\n269\n260\n263",
        expected_output="7",
        description="Example test case for depth measurement.",
    )
    serialized = test_case.to_dict()
    print(serialized)


def test_serialization2():
    test_case = TestCase(
        input_data="199\n200\n208\n210\n200\n207\n240\n269\n260\n263",
        expected_output="7",
        description="Example test case for depth measurement.",
    )
    serialized = test_case.to_dict()
    print(serialized)


if __name__ == "__main__":
    test_serialization()
    test_serialization2()
