"""Base solver class for Advent of Code problems."""

import logging
import os
import json
from pathlib import Path
from typing import List, Optional, Dict, Any, Union
from datetime import datetime

from shared.errors import ValidationError
from shared.execution import SolutionExecutor, TestCase
from shared.llm.local import OllamaProvider
from shared.parser import parse_problem_text
from shared.utils import fetch_problem_text, ensure_input_file, ensure_problem_files
from shared.validator import SubmissionError
from shared.strategies import get_strategies_for_problem, create_strategy_prompt
from shared.submission import SubmissionManager, SubmissionResult


class BaseSolver:
    """Base class for solving AoC problems."""

    def __init__(self, workspace_dir: Path) -> None:
        """Initialize the base solver.

        Args:
            workspace_dir: Workspace directory path
        """
        self.workspace_dir = workspace_dir
        self.solution_executor = SolutionExecutor(workspace_dir)
        self.submission_manager = SubmissionManager(workspace_dir)
        self.model = OllamaProvider()

    async def solve_problem(
        self, year: int, day: int, part: int, force: bool = False
    ) -> Optional[str]:
        """Solve an Advent of Code problem."""
        try:
            # Validate year and day against current time
            current_date = datetime.now()
            if year > current_date.year or (
                year == current_date.year
                and (
                    current_date.month < 12  # Not December yet
                    or (current_date.month == 12 and day > current_date.day)  # Future day in December
                )
            ):
                raise ValueError(f"Problem for year {year} day {day} is not available yet")

            # Create solution directory
            day_dir = self.workspace_dir / "years" / str(year) / f"day{day:02d}"
            solutions_dir = day_dir / "solutions"
            solutions_dir.mkdir(parents=True, exist_ok=True)

            # Ensure all problem files exist
            problem_files = await ensure_problem_files(year, day)
            
            # Check for existing successful solution unless force=True
            if not force:
                existing_solution = await self._get_existing_solution(year, day, part)
                if existing_solution:
                    logging.info("Using existing successful solution")
                    return await self.solution_executor.execute_solution(
                        existing_solution, year, day
                    )

            # Get problem text and parse it
            problem_text, _ = await fetch_problem_text(year, day, part)
            parsed_problem = parse_problem_text(problem_text)

            # Analyze problem characteristics
            characteristics = self._analyze_problem_characteristics(parsed_problem)
            
            # Get recommended strategies
            strategies, effectiveness = self.submission_manager.get_recommended_strategies(
                problem_text, characteristics
            )
            
            # Record start time for performance tracking
            start_time = datetime.now()

            # Generate solution with strategic guidance
            solution_code = await self.model.generate_solution(
                parsed_problem,
                strategies=strategies,
                strategy_effectiveness=effectiveness
            )
            generation_time = (datetime.now() - start_time).total_seconds()

            # Test solution
            test_result = await self.solution_executor.test_solution(
                solution_code, year, day, parsed_problem.examples
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

            # Collect execution metrics
            execution_metrics = {
                'generation_time': generation_time,
                'execution_time': execution_time,
                'memory_usage': full_result.performance.max_memory if full_result and full_result.performance else 0.0
            }

            # Handle submission if full test passed
            if full_passed:
                can_submit, wait_time = self.submission_manager.can_submit(year, day, part)
                if not can_submit:
                    logging.info(f"Waiting {wait_time}s before submitting...")
                    return None

                try:
                    success, message = await self.submission_manager.submit_solution(year, day, part, full_answer)
                    submission_result = SubmissionResult(
                        was_correct=success,
                        cooldown_seconds=wait_time if not success else None,
                        error_message=message if not success else None,
                        execution_metrics=execution_metrics,
                        strategies_used=strategies
                    )
                    
                    # Record submission and update learning system
                    self.submission_manager.record_submission(
                        year, day, part,
                        submission_result,
                        execution_metrics,
                        strategies
                    )

                    # Save solution details
                    await self._save_solution(
                        solution_code,
                        create_strategy_prompt(parsed_problem, strategies),
                        self.model.get_model_info(),
                        {
                            "examples": {
                                "passed": example_passed,
                                "results": example_results
                            },
                            "full_input": {
                                "passed": full_passed,
                                "result": full_result
                            },
                            "execution_time": execution_time,
                            "memory_usage": full_result.performance.max_memory if full_result and full_result.performance else 0.0
                        },
                        {
                            "success": success,
                            "message": message
                        },
                        year,
                        day,
                        part,
                        strategies,
                        {
                            "problem_characteristics": characteristics,
                            "optimization_suggestions": []
                        }
                    )

                    if submission_result and submission_result.get("success"):
                        solutions_dir = self.workspace_dir / "years" / str(year) / f"day{day:02d}" / "solutions"
                        solutions_dir.mkdir(exist_ok=True)
                        
                        solution_file = solutions_dir / f"part{part}.py"
                        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                        with open(solution_file, "w") as f:
                            f.write(f'''"""
Solution for Advent of Code {year} Day {day} Part {part}
Created by Martin Diekhoff
https://github.com/geniusworks

Generated and verified by the Advent of Code solver.
Timestamp: {timestamp}
"""

{solution_code}
''')

                    if success:
                        return full_answer
                    else:
                        logging.error(f"Submission failed: {message}")
                        return None

                except SubmissionError as e:
                    logging.error(f"Submission error: {str(e)}")
                    return None

            return None

        except Exception as e:
            logging.error(f"Error solving problem: {str(e)}")
            return None

    async def _get_existing_solution(
        self, year: int, day: int, part: int
    ) -> Optional[str]:
        """Check for existing successful solution.
        
        Args:
            year: Problem year
            day: Problem day
            part: Problem part
            
        Returns:
            The solution code if a successful solution exists, None otherwise
        """
        solutions_dir = self.workspace_dir / "years" / str(year) / f"day{day:02d}" / "solutions"
        if not solutions_dir.exists():
            return None
            
        # First check for final solution
        solution_file = solutions_dir / f"part{part}.py"
        if solution_file.exists():
            with open(solution_file, "r") as f:
                return f.read()
                
        # If no final solution, check attempts
        attempts_dir = self.workspace_dir / "years" / str(year) / f"day{day:02d}" / "attempts"
        if not attempts_dir.exists():
            return None
            
        # Check all attempt files
        for attempt_file in attempts_dir.glob("attempt_*.json"):
            try:
                with open(attempt_file, "r") as f:
                    attempt_data = json.load(f)
                    
                # Check if this is for the right part and was successful
                if (attempt_data["metadata"]["part"] == part and
                    attempt_data["submission"]["success"]):
                    return attempt_data["code"]
            except (json.JSONDecodeError, KeyError):
                continue
                
        return None

    async def _save_solution(
        self,
        code: str,
        prompt: str,
        model_info: Dict[str, Any],
        test_results: Dict[str, Any],
        submission_result: Dict[str, Any],
        year: int,
        day: int,
        part: int,
        strategies: List[Dict[str, Any]],
        analysis: Dict[str, Any]
    ) -> None:
        """Save solution details to JSON file."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        solution_data = {
            "code": code,
            "prompt": prompt,
            "model": model_info,
            "test_results": test_results,
            "status": {
                "examples_passed": test_results["examples"]["passed"],
                "full_passed": test_results["full_input"]["passed"],
                "part": part,
                "attempt_number": len(list(self.workspace_dir / "years" / str(year) / f"day{day:02d}" / "attempts".glob("attempt_*.json"))) + 1
            },
            "submission": {
                "submitted": submission_result is not None,
                "success": submission_result.get("success", False) if submission_result else False,
                "message": submission_result.get("message", "") if submission_result else "",
                "timestamp": timestamp
            },
            "metadata": {
                "timestamp": timestamp,
                "year": year,
                "day": day,
                "part": part,
                "execution_time": test_results.get("execution_time"),
                "memory_usage": test_results.get("memory_usage")
            },
            "strategy_analysis": {
                "applied_strategies": strategies,
                "problem_analysis": analysis["problem_characteristics"],
                "optimization_notes": analysis["optimization_suggestions"],
                "improvements_made": [],  # List of improvements made in this attempt
                "known_issues": [],       # List of known issues with this attempt
                "next_steps": []          # Suggested next steps if this attempt failed
            }
        }
        
        # Create attempts directory if it doesn't exist
        attempts_dir = self.workspace_dir / "years" / str(year) / f"day{day:02d}" / "attempts"
        attempts_dir.mkdir(parents=True, exist_ok=True)
        
        # Save attempt file
        attempt_file = attempts_dir / f"attempt_{timestamp}.json"
        with open(attempt_file, "w") as f:
            json.dump(solution_data, f, indent=2)
            
        # If the solution was successful, also save it to solutions/
        if solution_data["submission"]["success"]:
            solutions_dir = self.workspace_dir / "years" / str(year) / f"day{day:02d}" / "solutions"
            solutions_dir.mkdir(parents=True, exist_ok=True)
            
            # Create the final solution file
            part_num = solution_data["metadata"]["part"]
            solution_file = solutions_dir / f"part{part_num}.py"
            
            # Add documentation to the solution code
            solution_code = f'''"""
Solution for Part {part_num}

Generated on: {timestamp}
Model used: {model_info["name"]}
Performance:
- Example cases: {"✓" if test_results["examples"]["passed"] else "✗"}
- Full input: {"✓" if test_results["full_input"]["passed"] else "✗"}

Problem characteristics:
{json.dumps(analysis["problem_characteristics"], indent=2)}

Strategy analysis:
{json.dumps(strategies, indent=2)}
"""

{code}
'''
            with open(solution_file, "w") as f:
                f.write(solution_code)

    def _analyze_problem_characteristics(self, problem: Any) -> Dict[str, float]:
        """Analyze problem characteristics for strategy selection."""
        characteristics = {}
        
        # Analyze input size
        input_size = len(problem.examples[0].input_data) if problem.examples else 0
        characteristics['input_size'] = float(input_size)
        
        # Analyze complexity indicators
        text = problem.description.lower()
        characteristics.update({
            'graph_complexity': float('graph' in text or 'path' in text),
            'math_complexity': float('calculate' in text or 'formula' in text),
            'string_processing': float('string' in text or 'text' in text),
            'grid_operations': float('grid' in text or 'matrix' in text),
            'optimization_required': float('minimum' in text or 'maximum' in text)
        })
        
        return characteristics


async def solve_problem(year: int, day: int, part: int) -> Union[str, int]:
    """Solve the specified Advent of Code problem.
    
    Args:
        year: The year of the problem
        day: The day of the problem
        part: The part of the problem (1 or 2)
        
    Returns:
        The solution to the problem
        
    Raises:
        ValidationError: If the problem parameters are invalid
        SessionError: If there is an issue with the session
        InputError: If there is an issue with the input
        SubmissionError: If there is an issue with submission
        ExecutionError: If there is an issue executing the solution
    """
    solver = BaseSolver(Path.cwd())
    return await solver.solve_problem(year, day, part)
