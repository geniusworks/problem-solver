"""Base solver class for Advent of Code problems."""

import logging
import os
import json
from pathlib import Path
from typing import List, Optional, Dict, Any, Union
from datetime import datetime

from shared.errors import ValidationError, ExecutionError
from shared.execution import SolutionExecutor, TestCase
from shared.llm.local import OllamaProvider
from shared.parser import parse_problem_text
from shared.utils import fetch_problem_text, ensure_input_file, ensure_problem_files, ensure_problem_directory_structure, record_solution
from shared.validator import SubmissionError
from shared.strategies import get_strategies_for_problem, create_strategy_prompt
from shared.submission import SubmissionManager, SubmissionResult


class BaseSolver:
    """Base class for solving AoC problems."""

    def __init__(self, workspace_dir: Path, debug: bool = False) -> None:
        """Initialize the base solver.

        Args:
            workspace_dir: Workspace directory path
            debug: Enable debug output
        """
        self.workspace_dir = workspace_dir
        self.debug = debug
        self.solution_executor = SolutionExecutor(workspace_dir)
        self.submission_manager = SubmissionManager(workspace_dir)
        self.models = {
            model: OllamaProvider(model=model, debug=debug)
            for model in OllamaProvider.AVAILABLE_MODELS
        }

    async def solve_problem(
        self, year: int, day: int, part: int, force: bool = False
    ) -> Optional[str]:
        """Solve an Advent of Code problem using model consensus."""
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

            logging.info("")
            logging.info(f"Attempting solution for {year}, day {day:02d}, part {part}")
            logging.info("")

            # Create standard directory structure
            dirs = ensure_problem_directory_structure(self.workspace_dir, year, day)
            
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
            problem_text, _, previous_answer = await fetch_problem_text(year, day, part)
            parsed_problem = parse_problem_text(problem_text)

            # Analyze problem characteristics
            characteristics = self._analyze_problem_characteristics(parsed_problem)
            
            # Get recommended strategies
            strategies, effectiveness = self.submission_manager.get_recommended_strategies(
                problem_text, characteristics
            )
            
            # Try each model and collect answers
            answers = {}
            failures = []
            logging.info("")
            logging.info(f"Attempting solution with {len(self.models)} models")
            logging.info("")
            for model_name, model in self.models.items():
                try:
                    # Add blank line before model name
                    logging.info("")
                    # Log which model we're trying
                    logging.info(f"Trying model: {model_name}")
                    logging.info("")  # Add blank line after model name too

                    # Record start time for performance tracking
                    start_time = datetime.now()

                    # Generate solution with strategic guidance
                    solution_code = await model.generate_solution(
                        parsed_problem,
                        year=year,
                        day=day,
                        strategies=strategies,
                        strategy_effectiveness=effectiveness
                    )
                    generation_time = (datetime.now() - start_time).total_seconds()

                    # Check for default implementation
                    if "return len(data)" in solution_code:
                        logging.warning(f"Model {model_name} returned default implementation")
                        raise ExecutionError("Default implementation detected")

                    # Create runtime version with full path
                    execution_code = solution_code.replace(
                        "'input.txt'",
                        f"'{str(self.workspace_dir / 'years' / str(year) / f'day{day:02d}' / 'input.txt')}'"
                    )
                    execution_code = execution_code.replace(
                        '"input.txt"',
                        f'"{str(self.workspace_dir / "years" / str(year) / f"day{day:02d}" / "input.txt")}"'
                    )

                    # Save solution to temp file and execute it
                    temp_file = self.solution_executor.temp_manager.create_temp_file(
                        f"solution_{year}_day{day}_part{part}_{model_name.replace(':', '_')}.py"
                    )
                    temp_file.write_text(execution_code)
                    
                    # Execute the solution
                    answer = await self.solution_executor.execute_solution(
                        temp_file,
                        str(self.workspace_dir / "years" / str(year) / f"day{day:02d}" / "input.txt")
                    )
                    if answer.error:
                        raise ExecutionError(answer.error)

                    # Store successful result with both original and runtime code
                    answers[model_name] = {
                        'model_code': solution_code,  # Original code from model
                        'runtime_code': execution_code,  # Code used for execution
                        'answer': answer.output.strip(),
                        'performance': {
                            'generation_time': generation_time,
                            'execution_time': answer.performance.execution_time if answer.performance else 0,
                            'memory_usage': answer.performance.memory_usage if answer.performance else 0
                        }
                    }
                    
                    # Log successful execution
                    logging.info("")
                    logging.info(f"Model {model_name} succeeded with answer: {answer.output.strip()}")
                    logging.info("")

                except Exception as e:
                    logging.info("")
                    logging.error(f"Model {model_name} failed: {str(e)}")
                    logging.info("")
                    failures.append((model_name, str(e)))
                    continue

            logging.info("")
            logging.info("")

            # Check for consensus (2 or more matching answers)
            answer_counts = {}
            for model_data in answers.values():
                answer = model_data['answer']
                answer_counts[answer] = answer_counts.get(answer, 0) + 1

            consensus_answer = None
            consensus_models = []
            for answer, count in answer_counts.items():
                if count >= 2:  # We have consensus
                    consensus_answer = answer
                    consensus_models = [
                        model for model, data in answers.items()
                        if data['answer'] == answer
                    ]
                    break

            # Print consensus summary once
            self._print_consensus_summary(answers, failures, consensus_answer, consensus_models)

            if consensus_answer:
                # Use the fastest successful solution for submission
                best_model = min(
                    [m for m in consensus_models],
                    key=lambda m: answers[m]['performance']['execution_time']
                )
                best_solution = answers[best_model]

                logging.info(f"Using solution from {best_model} for submission")
                # Handle submission
                can_submit, wait_time = self.submission_manager.can_submit(year, day, part)
                if not can_submit:
                    logging.info(f"Waiting {wait_time}s before submitting...")
                    return None

                try:
                    success, message = await self.submission_manager.submit_solution(
                        year, day, part, consensus_answer
                    )
                    submission_result = SubmissionResult(
                        was_correct=success,
                        cooldown_seconds=wait_time if not success else None,
                        error_message=message if not success else None,
                        execution_metrics=best_solution['performance'],
                        strategies_used=strategies
                    )
                    
                    # Record submission and update learning system
                    self.submission_manager.record_submission(
                        year, day, part,
                        submission_result,
                        best_solution['performance'],
                        strategies
                    )

                    # Save solution details
                    await self._save_solution(
                        best_solution['model_code'],
                        create_strategy_prompt(parsed_problem, strategies),
                        self.models[best_model].get_model_info(),
                        self.solution_executor.get_test_results(best_solution['runtime_code'], year, day),
                        {
                            "success": success,
                            "message": message
                        },
                        year,
                        day,
                        part,
                        [s.to_dict() for s in strategies],  # Convert strategies to dicts
                        {"problem_characteristics": characteristics, "optimization_suggestions": []}
                    )
                    # Save successful attempt
                    await self._save_attempt(
                        best_solution['model_code'],
                        self.models[best_model].last_prompt,
                        self.models[best_model].get_model_info(),
                        self.solution_executor.get_test_results(best_solution['runtime_code'], year, day),
                        {
                            "submitted": True,
                            "success": success,
                            "message": message,
                            "timestamp": datetime.now().strftime("%Y%m%d_%H%M%S")
                        },
                        year,
                        day,
                        part,
                        [s.to_dict() for s in strategies],  # Convert strategies to dicts
                        {"problem_characteristics": characteristics, "optimization_suggestions": []},
                        "submitted"
                    )

                    # Save successful solution with original model code
                    solution_path = self.workspace_dir / "solutions" / str(year) / f"day{day:02d}" / f"part{part}.py"
                    solution_path.parent.mkdir(parents=True, exist_ok=True)
                    solution_path.write_text(best_solution['model_code'])  # Save original model code

                    if success:
                        return consensus_answer
                    else:
                        logging.error(f"Submission failed: {message}")
                        return None

                except SubmissionError as e:
                    logging.error(f"Submission error: {str(e)}")
                    return None

            else:
                # Save the no-consensus state
                for model_name, data in answers.items():
                    await self._save_attempt(
                        data['model_code'],
                        self.models[model_name].last_prompt,
                        self.models[model_name].get_model_info(),
                        self.solution_executor.get_test_results(data['runtime_code'], year, day),
                        None,
                        year,
                        day,
                        part,
                        [s.to_dict() for s in strategies],  # Convert strategies to dicts
                        {"problem_characteristics": characteristics, "optimization_suggestions": []},
                        "no_consensus",
                        "No consensus reached between models"
                    )
                return None

        except Exception as e:
            logging.error(f"Error solving problem: {str(e)}")
            return None

    def _print_consensus_summary(self, answers: Dict[str, Any], failures: List[tuple], consensus_answer: Optional[str], consensus_models: List[str]) -> None:
        """Print a summary of the consensus results."""
        logging.info("")  # Single blank line before summary
        logging.info("Consensus Summary:")
        logging.info("-" * 40)
        logging.info(f"Successful models: {list(answers.keys())}")
        logging.info(f"Failed models: {failures}")
        logging.info("")  # Single blank line after summary

        if consensus_answer:
            logging.info(f"Consensus reached! Answer: {consensus_answer}")
            logging.info(f"Agreeing models: {consensus_models}")
        else:
            logging.info("No consensus reached")
            logging.info("Model answers:")
            for model, data in answers.items():
                logging.info(f"  {model}: {data['answer']}")
            logging.info("")  # Single blank line after answers

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

    def _get_attempts_dir(self, year: int, day: int) -> Path:
        """Get the attempts directory for a given year and day."""
        return self.workspace_dir / "years" / str(year) / f"day{day:02d}" / "attempts"

    def _count_attempts(self, year: int, day: int) -> int:
        """Count the number of attempts for a given year and day."""
        attempts_dir = self._get_attempts_dir(year, day)
        return len(list(attempts_dir.glob("attempt_*.json")))

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
                "attempt_number": self._count_attempts(year, day) + 1
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
        attempts_dir = self._get_attempts_dir(year, day)
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

    async def _save_attempt(
        self,
        code: str,
        prompt: str,
        model_info: Dict[str, Any],
        test_results: Optional[Dict[str, Any]],
        submission_result: Optional[Dict[str, Any]],
        year: int,
        day: int,
        part: int,
        strategies: List[Dict[str, Any]],
        analysis: Dict[str, Any],
        status: str,
        error: Optional[str] = None
    ) -> None:
        """Save attempt details to JSON file.
        
        Args:
            code: Generated solution code
            prompt: Prompt used to generate solution
            model_info: Information about the model used
            test_results: Results from testing, if any
            submission_result: Results from submission, if any
            year: Problem year
            day: Problem day
            part: Problem part
            strategies: Applied strategies
            analysis: Problem analysis
            status: Current status (e.g., 'generated', 'failed_execution', 'no_consensus', 'submitted')
            error: Error message if any
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        attempt_data = {
            "code": code,
            "prompt": prompt,
            "model": model_info,
            "test_results": test_results or {},
            "status": {
                "phase": status,
                "error": error,
                "examples_passed": test_results.get("examples", {}).get("passed", False) if test_results else False,
                "full_passed": test_results.get("full_input", {}).get("passed", False) if test_results else False,
                "part": part,
                "attempt_number": self._count_attempts(year, day) + 1
            },
            "submission": submission_result or {
                "submitted": False,
                "success": False,
                "message": "",
                "timestamp": timestamp
            },
            "metadata": {
                "timestamp": timestamp,
                "year": year,
                "day": day,
                "part": part,
                "execution_time": test_results.get("execution_time") if test_results else None,
                "memory_usage": test_results.get("memory_usage") if test_results else None
            },
            "strategy_analysis": {
                "applied_strategies": strategies,
                "problem_analysis": analysis.get("problem_characteristics", {}),
                "optimization_notes": analysis.get("optimization_suggestions", []),
                "improvements_made": [],
                "known_issues": [],
                "next_steps": []
            }
        }
        
        # Create attempts directory if it doesn't exist
        attempts_dir = self._get_attempts_dir(year, day)
        attempts_dir.mkdir(parents=True, exist_ok=True)
        
        # Save attempt file
        attempt_file = attempts_dir / f"attempt_{timestamp}.json"
        with open(attempt_file, "w") as f:
            json.dump(attempt_data, f, indent=2)

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
