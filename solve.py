"""Main script for solving Advent of Code problems."""

import argparse
import asyncio
import logging
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Optional, List

from dotenv import load_dotenv

from shared.execution import SolutionExecutor, TestCase
from shared.hardware import HardwareManager
from shared.llm import ModelSelector
from shared.utils import download_input

logger = logging.getLogger(__name__)

class ProblemSolver:
    """Main class for solving AoC problems."""

    def __init__(self):
        """Initialize the problem solver."""
        load_dotenv()
        
        self.workspace_dir = Path(__file__).parent
        self.hardware_manager = HardwareManager(
            str(self.workspace_dir / "config/hardware.json")
        )
        self.model_selector = ModelSelector()
        self.solution_executor = SolutionExecutor(str(self.workspace_dir))

    async def solve_problem(
        self,
        year: int,
        day: int,
        part: int,
        force: bool = False
    ) -> Optional[str]:
        """Solve an Advent of Code problem."""
        problem_id = f"{year}_day{day:02d}_part{part}"
        logger.info("Solving problem %s", problem_id)
        
        try:
            # Download input if needed
            input_data = download_input(year, day)
            
            # Load problem description and test cases
            description, test_cases = self._load_problem_description(
                year,
                day,
                part
            )
            
            # Generate prompt
            prompt = self._create_prompt(description, test_cases)
            
            # For now, return None as we haven't implemented the model yet
            return None
            
        except Exception as e:
            logger.error("Failed to solve problem: %s", str(e))
            return None
        
        finally:
            # Cleanup
            self.solution_executor.cleanup()

    def _create_prompt(
        self,
        description: str,
        test_cases: List[TestCase]
    ) -> str:
        """Create a prompt for the models."""
        return f"""Solve this Advent of Code problem by writing a valid Python solution.

Problem Description:
{description}

Example Test Cases:
{self._format_test_cases(test_cases)}

Requirements:
1. Write ONLY valid Python code that can be executed directly
2. Define a solve() function that reads input from the file specified in the AOC_INPUT_FILE environment variable
3. Process the input according to the problem description
4. The solve() function should return the final answer as a single number or string
5. Handle edge cases and validate input
6. Use efficient algorithms and data structures
7. Include all necessary imports at the top of the file
8. IMPORTANT: The input data may contain annotations or comments in parentheses - make sure to extract only the numeric values

Format your solution like this:
```python
# Required imports
import os
import sys
import re  # For parsing input with annotations
# Add any other imports you need

def solve():
    # Read input
    with open(os.environ["AOC_INPUT_FILE"]) as f:
        input_data = f.read().strip()

    # Parse input, handling any annotations
    # Example: "199 (N/A - no previous measurement)" -> 199
    numbers = []
    for line in input_data.splitlines():
        # Extract just the number from each line
        if match := re.match(r'\\d+', line):
            numbers.append(int(match.group()))

    # Your solution code here
    # Process numbers according to the problem requirements

    # Return the final answer
    return answer

if __name__ == "__main__":
    result = solve()
    print(result)
```

    def _format_test_cases(self, test_cases: List[TestCase]) -> str:
        """Format test cases for the prompt."""
        result = []
        for i, test in enumerate(test_cases, 1):
            result.extend([
                f"Test Case {i}:",
                "Input:",
                test.input_data,
                "Expected Output:",
                test.expected_output,
                ""
            ])
        return "\n".join(result)

    def _load_problem_description(
        self,
        year: int,
        day: int,
        part: int
    ) -> tuple[str, List[TestCase]]:
        """Load problem description and test cases."""
        # For now, just return a simple test case
        return (
            "Count the number of times a depth measurement increases",
            [
                TestCase(
                    "199 (N/A - no previous measurement)\n200\n208\n210\n200\n207\n240\n269\n260\n263",
                    "7"
                )
            ]
        )

async def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Solve Advent of Code problems")
    parser.add_argument("--year", type=int, required=True, help="Problem year")
    parser.add_argument("--day", type=int, required=True, help="Problem day")
    parser.add_argument("--part", type=int, required=True, help="Problem part")
    parser.add_argument(
        "--force",
        action="store_true",
        help="Force new solution even if already solved"
    )
    
    args = parser.parse_args()
    
    solver = ProblemSolver()
    solution = await solver.solve_problem(
        args.year,
        args.day,
        args.part,
        args.force
    )
    
    if solution:
        print(f"\nSolution: {solution}")
    else:
        print("\nFailed to find solution")

if __name__ == "__main__":
    # Configure logging
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    asyncio.run(main())
