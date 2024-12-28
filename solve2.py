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
from shared.parser import parse_problem_text
from shared.problem_analysis import ProblemAnalyzer
from shared.llm.prompts import PromptGenerator

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
        self.problem_analyzer = ProblemAnalyzer()
        self.prompt_generator = PromptGenerator()

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
            
            # Load and parse problem description
            problem_dir = Path(f"years/{year}/day{day:02d}")
            problem_file = problem_dir / "problem.txt"
            if not problem_file.exists():
                logger.error("Problem file not found: %s", problem_file)
                return None
            
            problem_text = problem_file.read_text()
            parsed_problem = parse_problem_text(problem_text, year, day, part)
            
            # Generate optimized prompt
            prompt = self.prompt_generator.generate(parsed_problem, self.problem_analyzer)
            
            # Get solution from model
            logger.info("Requesting solution from model...")
            solution = await self.model_provider.generate_solution(prompt)
            
            if not solution:
                logger.error("Failed to get solution from model")
                return None
            
            # Save solution to file
            solution_path = self.solution_executor.temp_dir / "solution.py"
            solution_path.write_text(solution)
            
            # Execute solution
            logger.info("Testing solution...")
            test_passed = await self.solution_executor.test_solution(
                solution_path,
                parsed_problem.examples
            )
            
            if not test_passed:
                logger.error("Solution failed tests")
                return None
            
            # Run against full input
            logger.info("Running against full input...")
            result = await self.solution_executor.execute_solution(
                solution_path,
                input_data
            )
            
            if result.error:
                logger.error("Solution failed: %s", result.error)
                return None
            
            return result.output.strip()
            
        except Exception as e:
            logger.error("Failed to solve problem: %s", str(e))
            return None

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
