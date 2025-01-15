"""Base solver class for Advent of Code problems."""

import logging
import os
import json
from pathlib import Path
from typing import List, Optional, Dict, Any
from datetime import datetime

from shared.config import ValidationError
from shared.execution import SolutionExecutor, TestCase
from shared.llm.local import OllamaProvider
from shared.parser import parse_problem_text
from shared.utils import fetch_problem_text, ensure_input_file
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
            # Create solution directory
            day_dir = self.workspace_dir / "years" / str(year) / f"day{day:02d}"
            solutions_dir = day_dir / "solutions"
            solutions_dir.mkdir(parents=True, exist_ok=True)

            # Check for existing successful solution unless force=True
            if not force:
                existing_solution = await self._get_existing_solution(year, day, part)
                if existing_solution:
                    logging.info("Using existing successful solution")
                    return await self.solution_executor.execute_solution(
                        existing_solution, year, day
                    )

            # Parse problem
            problem_text = await fetch_problem_text(year, day)
            if not problem_text:
                logging.error("Failed to fetch problem text")
                return None
            
            problem = parse_problem_text(problem_text)

            # Analyze problem characteristics
            characteristics = self._analyze_problem_characteristics(problem)
            
            # Get recommended strategies
            strategies, effectiveness = self.submission_manager.get_recommended_strategies(
                problem_text, characteristics
            )
            
            # Record start time for performance tracking
            start_time = datetime.now()

            # Generate solution with strategic guidance
            solution_code = await self.model.generate_solution(
                problem,
                strategies=strategies,
                strategy_effectiveness=effectiveness
            )
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
                        create_strategy_prompt(problem, strategies),
                        self.model.get_model_info(),
                        {
                            "examples": {
                                "passed": example_passed,
                                "results": example_results
                            },
                            "full_input": {
                                "passed": full_passed,
                                "result": full_result
                            }
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
            
        # Check all solution files
        for solution_file in solutions_dir.glob("solution_*.json"):
            try:
                with open(solution_file, "r") as f:
                    solution_data = json.load(f)
                    
                # Check if this is for the right part and was successful
                if (solution_data["metadata"]["part"] == part and
                    solution_data["submission"]["success"]):
                    return solution_data["code"]
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
                "part": part
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
                "part": part
            },
            "strategy_analysis": {
                "applied_strategies": strategies,
                "problem_analysis": analysis["problem_characteristics"],
                "optimization_notes": analysis["optimization_suggestions"]
            }
        }
        
        # Create solutions directory if it doesn't exist
        solutions_dir = self.workspace_dir / "years" / str(year) / f"day{day:02d}" / "solutions"
        solutions_dir.mkdir(parents=True, exist_ok=True)
        
        # Save solution file
        solution_file = solutions_dir / f"solution_{timestamp}.json"
        with open(solution_file, "w") as f:
            json.dump(solution_data, f, indent=2)

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
