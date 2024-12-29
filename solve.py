"""Main script for solving problems."""

import argparse
import asyncio
import logging
import sys
from typing import NoReturn

from dotenv import load_dotenv

from shared.hardware import HardwareManager
from shared.llm.selection import ModelSelector
from shared.solver import BaseSolver


class ProblemSolver(BaseSolver):
    """Main class for solving AoC problems."""

    def __init__(self) -> None:
        """Initialize the problem solver."""
        super().__init__()
        load_dotenv()

        self.hardware_manager = HardwareManager(
            str(self.workspace_dir / "config/hardware.json")
        )
        self.model_selector = ModelSelector()


async def main() -> int:
    """Main entry point for the solver.

    Returns:
        int: Exit code (0 for success, 1 for failure)
    """
    parser = argparse.ArgumentParser(
        description="Solve problems",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--year", type=int, required=True, help="Problem year")
    parser.add_argument("--day", type=int, required=True, help="Problem day")
    parser.add_argument("--part", type=int, required=True, help="Problem part")
    parser.add_argument(
        "--force", action="store_true", help="Force new solution even if already solved"
    )

    args = parser.parse_args()

    solver = ProblemSolver()
    solution = await solver.solve_problem(args.year, args.day, args.part, args.force)

    if solution:
        print(f"\nSolution: {solution}")
        return 0

    print("\nFailed to find solution")
    return 1


def run() -> NoReturn:
    """Run the main function and exit."""
    # Configure logging
    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    sys.exit(asyncio.run(main()))


if __name__ == "__main__":
    run()
