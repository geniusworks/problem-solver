#!/usr/bin/env python3
"""Main script for solving problems with enhanced features."""

import argparse
import asyncio
import logging
import os
import sys
from pathlib import Path
from typing import NoReturn

from shared.solver import solve_problem
from shared.utils import setup_logging


class ProblemSolver:
    """Main class for solving AoC problems with enhanced features."""


def parse_args() -> argparse.Namespace:
    """Parse command line arguments.

    Returns:
        Parsed arguments
    """
    parser = argparse.ArgumentParser(
        description="Solve contest problems",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--year", type=int, required=True, help="Problem year")
    parser.add_argument("--day", type=int, required=True, help="Problem day")
    parser.add_argument("--part", type=int, required=True, help="Problem part")
    parser.add_argument(
        "--force", action="store_true", help="Force new solution even if already solved"
    )
    parser.add_argument(
        "--debug", action="store_true", help="Enable debug logging"
    )
    return parser.parse_args()


async def async_main() -> int:
    """Async main entry point for the solver.

    Returns:
        int: Exit code (0 for success, 1 for failure)
    """
    args = parse_args()
    
    # Set up logging
    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)
        logging.getLogger("shared").setLevel(logging.DEBUG)
    
    try:
        solution = await solve_problem(args.year, args.day, args.part)
        print(f"\nSolution: {solution}")
        return 0
    except Exception as e:
        logging.error(f"Error solving problem: {e}")
        return 1


def main() -> NoReturn:
    """Main entry point that sets up logging and runs the async main function."""
    # Set up logging
    setup_logging()
    
    # Disable noisy loggers
    logging.getLogger("asyncio").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("charset_normalizer").setLevel(logging.WARNING)

    # Run async main
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    try:
        exit_code = asyncio.run(async_main())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\nOperation cancelled by user")
        sys.exit(1)


if __name__ == "__main__":
    main()
