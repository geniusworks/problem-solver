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
from shared.llm import OllamaProvider
from shared.utils import download_input

logger = logging.getLogger(__name__)

PROMPT_TEMPLATE = """Write Python code to solve this Advent of Code problem:

{description}

Test Cases:
{test_cases}

Your code must:
1. Start with 'import os'
2. Define a solve() function that reads input from os.environ["AOC_INPUT_FILE"]
3. Return a single number or string as the answer
4. Handle edge cases and validate input

Example structure:
import os
import sys

def solve():
    with open(os.environ["AOC_INPUT_FILE"]) as f:
        input_data = f.read().strip()
    return answer

if __name__ == "__main__":
    result = solve()
    print(result)"""

class ProblemSolver:
    """Main class for solving AoC problems."""

    def __init__(self):
        """Initialize the problem solver."""
        load_dotenv()
        
        self.workspace_dir = Path(__file__).parent
        self.hardware_manager = HardwareManager(
            str(self.workspace_dir / "config/hardware.json")
        )
        self.model_provider = OllamaProvider()
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
            
            # Try to generate a solution
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    # Generate solution
                    result = await self.model_provider.generate(prompt)
                    
                    # Validate solution
                    is_valid, error = await self.solution_executor.prepare_solution(
                        problem_id,
                        result.content,
                        test_cases
                    )
                    
                    if is_valid:
                        # Run against full input
                        return await self.solution_executor.run_against_full_input(
                            problem_id,
                            year,
                            day,
                            result.content
                        )
                    else:
                        logger.warning(
                            "Solution failed validation (attempt %d): %s",
                            attempt + 1,
                            error
                        )
                except Exception as e:
                    logger.error(
                        "Error generating solution (attempt %d): %s",
                        attempt + 1,
                        str(e)
                    )
            
            logger.error("Failed to generate valid solution after %d attempts", max_retries)
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
        test_cases_str = "\n".join(
            f"Test Case {i+1}:\nInput:\n{test.input_data}\nExpected Output:\n{test.expected_output}\n"
            for i, test in enumerate(test_cases)
        )
        return PROMPT_TEMPLATE.format(
            description=description,
            test_cases=test_cases_str
        )

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
