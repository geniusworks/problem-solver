"""Base solver class for Advent of Code problems."""

import logging
import os
import json
from pathlib import Path
from typing import List, Tuple, Optional, Dict, Any, Union
from datetime import datetime
from enum import Enum
from shared.errors import ValidationError, ExecutionError
from shared.execution import SolutionExecutor, TestCase
from shared.llm.local import OllamaProvider
from shared.parser import parse_problem_text
from shared.utils import fetch_problem_text, ensure_input_file, ensure_problem_files, ensure_problem_directory_structure, record_solution
from shared.validator import SubmissionError
from shared.strategies import get_strategies_for_problem, create_strategy_prompt
from shared.submission import SubmissionManager, SubmissionResult
from learning.database import LearningDatabase

class ModelRole(Enum):
    PRIMARY = 1
    REVIEWER = 2
    VALIDATOR = 3


class AttemptResult:
    def __init__(
        self,
        model_name: str,
        role: ModelRole,
        response_time: float,
        code_quality: float,
        was_successful: bool,
        cost: float
    ) -> None:
        self.model_name = model_name
        self.role = role
        self.response_time = response_time
        self.code_quality = code_quality
        self.was_successful = was_successful
        self.cost = cost


class ModelSelector:
    def __init__(self, metrics_file: str, models_per_role: int) -> None:
        self.metrics_file = metrics_file
        self.models_per_role = models_per_role
        self.metrics = self._load_metrics()

    def _load_metrics(self) -> Dict[str, Any]:
        try:
            with open(self.metrics_file, "r") as f:
                return json.load(f)
        except FileNotFoundError:
            return {
                ModelRole.PRIMARY.name: [],
                ModelRole.REVIEWER.name: [],
                ModelRole.VALIDATOR.name: []
            }

    def save_metrics(self) -> None:
        with open(self.metrics_file, "w") as f:
            json.dump(self.metrics, f, indent=2)

    def get_models_for_role(self, role: ModelRole) -> List[str]:
        return [m["model_name"] for m in self.metrics[role.name]]

    def record_attempt(self, result: AttemptResult) -> None:
        role_metrics = self.metrics[result.role.name]
        existing_metric = next((m for m in role_metrics if m["model_name"] == result.model_name), None)
        if existing_metric:
            existing_metric["response_time"] = (existing_metric["response_time"] + result.response_time) / 2
            existing_metric["code_quality"] = (existing_metric["code_quality"] + result.code_quality) / 2
            existing_metric["success_rate"] = (existing_metric["success_rate"] + result.was_successful) / 2
            existing_metric["cost"] = (existing_metric["cost"] + result.cost) / 2
        else:
            role_metrics.append({
                "model_name": result.model_name,
                "response_time": result.response_time,
                "code_quality": result.code_quality,
                "success_rate": result.was_successful,
                "cost": result.cost
            })
        role_metrics.sort(key=lambda m: m["response_time"] + m["cost"])
        self.metrics[result.role.name] = role_metrics[:self.models_per_role]
        self.save_metrics()


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
        
        # Initialize learning system
        self.learning_dir = workspace_dir / "learning"
        self.learning_dir.mkdir(parents=True, exist_ok=True)
        self.strategy_optimizer = None
        self.db = None
        
        # Initialize all available models
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

            # Temporary for debugging purposes
            if self.debug:
                logging.info("Problem text for part %d:", part)
                logging.info(problem_text)

            # Analyze problem characteristics
            characteristics = self._analyze_problem_characteristics(parsed_problem)
            
            # Get recommended strategies
            strategies, effectiveness = self.submission_manager.get_recommended_strategies(
                problem_text, characteristics
            )
            
            # Get top performing models for each role based on problem type
            problem_type = self._get_problem_type(characteristics)
            primary_models = self._get_top_models(problem_type, "primary", limit=3)
            reviewer_models = self._get_top_models(problem_type, "reviewer", limit=3)
            validator_models = self._get_top_models(problem_type, "validator", limit=3)
            
            # Try each primary model and collect answers
            answers = {}
            failures = []
            
            logging.info("")
            logging.info(f"Attempting solution with top {len(primary_models)} primary model(s)")

            for model_name in primary_models:
                if model_name not in self.models:
                    logging.warning(f"Model {model_name} not available, skipping")
                    continue
                    
                model = self.models[model_name]
                try:
                    logging.info("")
                    logging.info(f"Trying primary model: {model_name}")
                    logging.info("")

                    # Record start time for performance tracking
                    start_time = datetime.now()
                    
                    # Generate solution
                    solution = await model.generate_solution(
                        parsed_problem,
                        year,
                        day,
                        strategies=strategies,
                        strategy_effectiveness=effectiveness
                    )
                    
                    # Calculate metrics
                    end_time = datetime.now()
                    response_time = (end_time - start_time).total_seconds()
                    
                    # Analyze code quality
                    from shared.quality.code_quality import CodeQualityAnalyzer
                    analyzer = CodeQualityAnalyzer()
                    quality_metrics = analyzer.analyze(solution)
                    
                    # Validate solution
                    is_valid = True
                    validation_errors = []
                    for validator_name in validator_models:
                        if validator_name in self.models:
                            validator = self.models[validator_name]
                            try:
                                if not await validator.validate_solution(solution, parsed_problem.test_cases):
                                    is_valid = False
                                    validation_errors.append(f"Failed {validator_name} validation")
                            except Exception as e:
                                validation_errors.append(f"{validator_name} validation error: {str(e)}")
                    
                    if is_valid:
                        answers[model_name] = solution
                        
                        # Record successful attempt in learning system
                        if not self.db:
                            from learning import LearningDatabase
                            self.db = LearningDatabase(self.learning_dir)
                        self.db.update_model_performance(
                            model_name=model_name,
                            metrics={
                                "quality_score": quality_metrics.overall_score * 10.0,  # Convert to 0-10 scale
                                "response_time": response_time,
                                "cost": 0.0,  # Local models have no cost
                                "complexity_score": quality_metrics.cyclomatic_complexity,
                                "maintainability_score": quality_metrics.maintainability_index,
                                "error_handling_score": quality_metrics.error_handling_score
                            },
                            success=True,
                            problem_type=problem_type,
                            role="primary"
                        )
                    else:
                        failures.append((model_name, "; ".join(validation_errors)))
                        
                        # Record failed attempt in learning system
                        if not self.db:
                            from learning import LearningDatabase
                            self.db = LearningDatabase(self.learning_dir)
                        self.db.update_model_performance(
                            model_name=model_name,
                            metrics={
                                "quality_score": quality_metrics.overall_score * 10.0,
                                "response_time": response_time,
                                "cost": 0.0,
                                "complexity_score": quality_metrics.cyclomatic_complexity,
                                "maintainability_score": quality_metrics.maintainability_index,
                                "error_handling_score": quality_metrics.error_handling_score
                            },
                            success=False,
                            problem_type=problem_type,
                            role="primary"
                        )
                        
                except Exception as e:
                    failures.append((model_name, str(e)))
                    if not self.db:
                        self.db = LearningDatabase(self.learning_dir)
                    self.db.update_model_performance(
                        model_name=model_name,
                        metrics={
                            "quality_score": 0.0,
                            "response_time": 0.0,
                            "cost": 0.0,
                            "complexity_score": 0.0,
                            "maintainability_score": 0.0,
                            "error_handling_score": 0.0
                        },
                        success=False,
                        problem_type=problem_type,
                        role="primary"
                    )

            # If we have answers, try to reach consensus
            if answers:
                # Get quality metrics for all solutions
                from shared.quality.code_quality import CodeQualityAnalyzer
                analyzer = CodeQualityAnalyzer()
                quality_scores = {}
                
                for model_name, solution in answers.items():
                    metrics = analyzer.analyze(solution)
                    quality_scores[model_name] = metrics.overall_score
                
                # Weight solutions by quality score when determining consensus
                weighted_answers = {}
                for model_name, solution in answers.items():
                    weight = quality_scores[model_name]
                    weighted_answers[model_name] = (solution, weight)
                
                consensus_answer = self._get_weighted_consensus_answer(weighted_answers)
                if consensus_answer:
                    # Record the consensus in the solution directory
                    record_solution(
                        year, day, part, "consensus", consensus_answer
                    )
                    return consensus_answer

            # If no consensus, try collaborative improvement
            if len(answers) > 0:
                # Select best solution as starting point based on quality score
                best_model = max(quality_scores.items(), key=lambda x: x[1])[0]
                best_answer = answers[best_model]
                
                # Initialize collaborative improvement
                from shared.llm.collaborative import CollaborativeImprovement
                collaborator = CollaborativeImprovement(
                    [self.models[name] for name in reviewer_models if name in self.models],
                    max_iterations=3
                )
                
                try:
                    # Attempt collaborative improvement
                    improved_candidate = await collaborator.improve_solution(best_answer)
                    
                    if improved_candidate and improved_candidate.solution != best_answer:
                        # Analyze improvement impact
                        original_metrics = analyzer.analyze(best_answer)
                        improved_metrics = analyzer.analyze(improved_candidate.solution)
                        impact_score = improved_metrics.overall_score - original_metrics.overall_score
                        
                        # Record improvement attempt
                        if not self.db:
                            from learning import LearningDatabase
                            self.db = LearningDatabase(learning_dir)
                        self.db.record_improvement(
                            problem_id=f"{year}_day{day:02d}_part{part}",
                            model_name=improved_candidate.author,
                            improvement_type="collaborative",
                            impact_score=impact_score
                        )
                        
                        # Validate improved solution
                        validation_success = True
                        for validator_name in validator_models:
                            if validator_name in self.models:
                                validator = self.models[validator_name]
                                try:
                                    if not await validator.validate_solution(
                                        improved_candidate.solution,
                                        parsed_problem.test_cases
                                    ):
                                        validation_success = False
                                        break
                                except Exception:
                                    validation_success = False
                                    break
                                    
                        if validation_success:
                            return improved_candidate.solution
                except Exception as e:
                    logging.warning(f"Collaborative improvement failed: {str(e)}")

            # If we get here, we failed to solve the problem
            self._print_consensus_summary(answers, failures, None, [])
            return None

        except Exception as e:
            raise  # Let the error propagate to the top level

    def _get_problem_type(self, characteristics: Dict[str, Any]) -> str:
        """Determine the problem type from characteristics."""
        # TODO: Implement proper problem type classification
        return "general"

    def _get_top_models(self, problem_type: str, role: str, limit: int = 3, min_success_rate: float = 0.5) -> list[str]:
        """Get top performing models for a specific problem type and role."""
        logging.info(f"Getting top models for problem_type={problem_type}, role={role}, limit={limit}, min_success_rate={min_success_rate}")
        if not self.db:
            self.db = LearningDatabase(self.learning_dir)
        models = self.db.get_top_models(problem_type, role, limit, min_success_rate)
        if not models:
            # Cold-start fallback: use available local models if DB has no entries meeting threshold
            fallback = list(self.models.keys())[:limit]
            logging.info(f"Top models: [] -> using fallback models {fallback}")
            return fallback
        logging.info(f"Top models: {models}")
        return models

    def _get_weighted_consensus_answer(
        self, weighted_answers: Dict[str, Tuple[str, float]]
    ) -> Optional[str]:
        """Get consensus answer from multiple model outputs, weighted by confidence.
        
        Args:
            weighted_answers: Dictionary mapping model names to (answer, weight) tuples
            
        Returns:
            The consensus answer if one exists, None otherwise
        """
        if not weighted_answers:
            return None
            
        # Group identical answers and sum their weights
        answer_groups: Dict[str, float] = {}
        for model_name, (answer, weight) in weighted_answers.items():
            if answer in answer_groups:
                answer_groups[answer] += weight
            else:
                answer_groups[answer] = weight
                
        # Find answer with highest total weight
        best_answer = max(answer_groups.items(), key=lambda x: x[1])[0]
        best_weight = answer_groups[best_answer]
        
        # Only return consensus if weight is significantly higher than others
        total_weight = sum(answer_groups.values())
        if best_weight / total_weight >= 0.6:  # At least 60% agreement
            return best_answer
            
        return None



        if len(consensus_answers) == 1 and max_count >= 2:
            return consensus_answers[0]
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
                logging.info(f"  {model}: {data}")
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
