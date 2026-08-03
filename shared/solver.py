"""Base solver class for Advent of Code problems."""

import logging
import os
import json
from pathlib import Path
from typing import List, Tuple, Optional, Dict, Any, Union
from datetime import datetime
from enum import Enum
import requests
from requests import RequestException
from shared.errors import ValidationError, ExecutionError
from shared.execution import SolutionExecutor, TestCase
from shared.llm.local import OllamaProvider
from shared.parser import parse_problem_text
from shared.utils import fetch_problem_text, ensure_input_file, ensure_problem_files, ensure_problem_directory_structure, record_solution
from shared.validator import SubmissionError
from shared.strategies import get_strategies_for_problem, create_strategy_prompt
from shared.submission import SubmissionManager, SubmissionResult
from learning.database import LearningDatabase

logger = logging.getLogger(__name__)

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
        # Enable or disable collaborative improvement via environment flag
        self.enable_collaborative_improvement = os.getenv(
            "ENABLE_COLLABORATIVE_IMPROVEMENT", "false"
        ).lower() in {"1", "true", "yes", "on"}
        
        # Initialize all available models, preferring those actually installed in Ollama
        model_names = self._resolve_available_models()
        self.models = {
            model: OllamaProvider(model=model, debug=debug)
            for model in model_names
        }

    def _resolve_available_models(self) -> List[str]:
        """Determine which configured local models are available via Ollama.

        If Ollama is unreachable or returns an unexpected response, fall back to the
        statically configured AVAILABLE_MODELS list. If Ollama is reachable but none
        of the configured models are installed, raise a clear error so users know
        which models to install.
        """
        host = os.getenv("OLLAMA_HOST", "http://localhost:11434")
        url = f"{host.rstrip('/')}/api/tags"

        try:
            response = requests.get(url, timeout=5)
            response.raise_for_status()
            data = response.json()
            installed = {
                m.get("name")
                for m in data.get("models", [])
                if isinstance(m, dict) and m.get("name")
            }

            if not installed:
                # Nothing reported; keep configured list
                return list(OllamaProvider.AVAILABLE_MODELS)

            # Intersect configured models with installed models, preserving order
            filtered = [
                model
                for model in OllamaProvider.AVAILABLE_MODELS
                if model in installed
            ]

            if not filtered:
                configured = ", ".join(OllamaProvider.AVAILABLE_MODELS)
                raise RuntimeError(
                    "No configured local models are installed in Ollama at "
                    f"{host}. Please install at least one of: {configured}"
                )

            return filtered
        except RequestException:
            # Ollama not reachable; keep configured list so environments without
            # Ollama can still run tests and other parts of the system.
            return list(OllamaProvider.AVAILABLE_MODELS)
        except ValueError:
            # Malformed JSON or unexpected response; fall back to configured list
            return list(OllamaProvider.AVAILABLE_MODELS)

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
                    problem_id = f"{year}_day{day:02d}_part{part}"
                    result = await self.solution_executor.run_against_full_input(
                        problem_id, year, day, part, existing_solution
                    )
                    if result.error is None:
                        return result.output.strip()
                    logging.warning(
                        "Existing solution failed on full input (%s); falling back to full solve",
                        result.error,
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
            consensus_answer: Optional[str] = None
            quality_scores: Dict[str, float] = {}
            analyzer = None
            if answers:
                # Get quality metrics for all solutions
                from shared.quality.code_quality import CodeQualityAnalyzer
                analyzer = CodeQualityAnalyzer()
                
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

            # If no consensus, optionally try collaborative improvement
            if len(answers) > 0 and self.enable_collaborative_improvement:
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

            # If we still have answers but no consensus or collaborative improvement result,
            # run each candidate through execution-based validation against examples and
            # full input, and prefer the first that passes.
            if answers:
                # Build execution test cases from parsed examples when available
                exec_test_cases: List[TestCase] = []
                for example in getattr(parsed_problem, "examples", []) or []:
                    input_data = getattr(example, "input_data", None)
                    expected_output = getattr(example, "expected_output", None)
                    if input_data is None or expected_output in (None, ""):
                        continue
                    exec_test_cases.append(
                        TestCase(
                            input_data=str(input_data),
                            expected_output=str(expected_output),
                            description=getattr(example, "description", None),
                        )
                    )

                # Ground truth for the full input, when this problem has already
                # been accepted on the user's AoC account. This is the strongest
                # oracle available and needs no submission.
                from shared.ground_truth import get_known_answer

                known_answer = get_known_answer(year, day, part)

                # A candidate can only be accepted if something can actually judge
                # it. Without an oracle, acceptance would degrade to "ran without
                # crashing", which is how stubs were previously recorded as solved.
                if not exec_test_cases and known_answer is None:
                    logger.error(
                        "No correctness oracle for year %d day %02d part %d: no example "
                        "has a known expected output and no accepted answer is cached. "
                        "Refusing to accept any candidate as solved.",
                        year, day, part,
                    )
                    return None

                max_repair_iterations = int(os.getenv("MAX_REPAIR_ITERATIONS", "2"))
                current_candidates: Dict[str, str] = dict(answers)

                for iteration in range(max_repair_iterations + 1):
                    validated_candidates: List[Tuple[str, str]] = []
                    feedback_by_model: Dict[str, str] = {}

                    for model_name, solution in current_candidates.items():
                        try:
                            example_results, full_result, full_answer = (
                                await self.solution_executor.test_solution(
                                    solution_code=solution,
                                    year=year,
                                    day=day,
                                    part=part,
                                    test_cases=exec_test_cases,
                                    model_name=model_name,
                                    debug=self.debug,
                                    force_full_input=known_answer is not None,
                                )
                            )

                            # Oracle hierarchy. The accepted AoC answer is authoritative
                            # when we have it; examples are then advisory, because the
                            # parser can mis-pair an expected output with the wrong
                            # <pre> block (2024 day 5 part 1 attaches 143 to the updates
                            # fragment; day 6 part 1 attaches 41 to the solution diagram)
                            # and a bad example must never veto a correct answer.
                            # Without ground truth, examples are the only oracle and
                            # every one of them must pass.
                            examples_failed = bool(example_results) and any(
                                r.error is not None for r in example_results
                            )
                            if examples_failed and known_answer is None:
                                feedback_by_model[model_name] = self._build_execution_feedback(
                                    model_name,
                                    exec_test_cases,
                                    example_results,
                                    full_result,
                                    full_answer,
                                )
                                continue
                            if not full_result or full_result.error is not None:
                                feedback_by_model[model_name] = self._build_execution_feedback(
                                    model_name,
                                    exec_test_cases,
                                    example_results,
                                    full_result,
                                    full_answer,
                                )
                                continue
                            if not full_answer:
                                feedback_by_model[model_name] = self._build_execution_feedback(
                                    model_name,
                                    exec_test_cases,
                                    example_results,
                                    full_result,
                                    full_answer,
                                )
                                continue
                            if known_answer is not None and full_answer.strip() != known_answer.strip():
                                logger.info(
                                    "%s rejected: produced %r, accepted answer is %r",
                                    model_name, full_answer.strip(), known_answer.strip(),
                                )
                                feedback_by_model[model_name] = self._build_execution_feedback(
                                    model_name,
                                    exec_test_cases,
                                    example_results,
                                    full_result,
                                    full_answer,
                                )
                                continue

                            validated_candidates.append((model_name, solution))
                        except Exception as e:
                            # Do not swallow silently: a bug in the executor here is
                            # indistinguishable from "the candidate failed", which
                            # makes the solver look like it simply found no answer.
                            logger.warning(
                                "Error testing candidate from %s: %s: %s",
                                model_name, type(e).__name__, e,
                            )
                            continue

                    if validated_candidates:
                        # If we have quality scores from earlier, prefer the highest; otherwise
                        # fall back to the first validated candidate.
                        if quality_scores:
                            validated_candidates.sort(
                                key=lambda item: quality_scores.get(item[0], 0.0),
                                reverse=True,
                            )
                        chosen_model, chosen_solution = validated_candidates[0]
                        record_solution(year, day, part, chosen_model, chosen_solution)
                        return chosen_solution

                    if iteration >= max_repair_iterations:
                        break

                    improved_candidates: Dict[str, str] = {}
                    for model_name, solution in current_candidates.items():
                        if model_name not in feedback_by_model:
                            continue
                        model = self.models.get(model_name)
                        improve_fn = getattr(model, "improve_solution", None) if model else None
                        if not callable(improve_fn):
                            continue
                        try:
                            improved_code = await improve_fn(
                                solution,
                                parsed_problem,
                                feedback_by_model[model_name],
                            )
                            if improved_code and improved_code != solution:
                                improved_candidates[model_name] = improved_code
                        except Exception:
                            continue

                    if not improved_candidates:
                        break

                    current_candidates = improved_candidates

            # If we get here, all primary model candidates failed execution validation.
            # Try fallback models that weren't in the primary set.
            fallback_models = [
                name for name in self.models.keys()
                if name not in primary_models
            ]
            
            if fallback_models:
                logging.info("")
                logging.info(
                    f"All primary models failed execution validation. "
                    f"Trying {len(fallback_models)} fallback model(s): {fallback_models}"
                )
                
                for model_name in fallback_models:
                    model = self.models[model_name]
                    try:
                        logging.info("")
                        logging.info(f"Trying fallback model: {model_name}")
                        logging.info("")
                        
                        solution = await model.generate_solution(
                            parsed_problem,
                            year,
                            day,
                            strategies=strategies,
                            strategy_effectiveness=effectiveness
                        )
                        
                        # Run execution-based validation directly
                        exec_test_cases_fb: List[TestCase] = []
                        for example in getattr(parsed_problem, "examples", []) or []:
                            input_data = getattr(example, "input_data", None)
                            expected_output = getattr(example, "expected_output", None)
                            if input_data is None or expected_output in (None, ""):
                                continue
                            exec_test_cases_fb.append(
                                TestCase(
                                    input_data=str(input_data),
                                    expected_output=str(expected_output),
                                    description=getattr(example, "description", None),
                                )
                            )
                        
                        example_results, full_result, full_answer = (
                            await self.solution_executor.test_solution(
                                solution_code=solution,
                                year=year,
                                day=day,
                                part=part,
                                test_cases=exec_test_cases_fb,
                                model_name=model_name,
                                debug=self.debug,
                            )
                        )
                        
                        # Check if this solution passes
                        examples_ok = not example_results or all(
                            r.error is None for r in example_results
                        )
                        full_ok = full_result and full_result.error is None and full_answer
                        
                        if examples_ok and full_ok:
                            logging.info(f"Fallback model {model_name} produced valid solution!")
                            
                            # Update learning DB
                            if not self.db:
                                from learning import LearningDatabase
                                self.db = LearningDatabase(self.learning_dir)
                            self.db.update_model_performance(
                                model_name=model_name,
                                metrics={
                                    "quality_score": 5.0,
                                    "response_time": 0.0,
                                    "cost": 0.0,
                                    "complexity_score": 0.0,
                                    "maintainability_score": 0.0,
                                    "error_handling_score": 0.0
                                },
                                success=True,
                                problem_type=problem_type,
                                role="primary"
                            )
                            
                            record_solution(year, day, part, model_name, solution)
                            return solution
                        else:
                            logging.info(f"Fallback model {model_name} failed execution validation")
                            # Update learning DB with failure
                            if not self.db:
                                from learning import LearningDatabase
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
                            
                    except Exception as e:
                        logging.warning(f"Fallback model {model_name} failed: {str(e)}")
                        continue
            
            # If we get here, we failed to solve the problem
            self._print_consensus_summary(answers, failures, None, [])
            return None

        except Exception as e:
            raise  # Let the error propagate to the top level

    def _build_execution_feedback(
        self,
        model_name: str,
        exec_test_cases: List[TestCase],
        example_results: List[Any],
        full_result: Optional[Any],
        full_answer: Optional[str],
    ) -> str:
        lines: List[str] = []
        lines.append(f"Execution feedback for model {model_name}.")
        if exec_test_cases:
            lines.append("Example test results:")
            max_examples = 3
            for idx, (test_case, result) in enumerate(
                zip(exec_test_cases, example_results), start=1
            ):
                if idx > max_examples:
                    break
                expected = str(getattr(test_case, "expected_output", "")).strip()
                if getattr(result, "error", None):
                    lines.append(
                        f"- Example {idx}: ERROR: {getattr(result, 'error', '')}"
                    )
                else:
                    actual = str(getattr(result, "output", "")).strip()
                    lines.append(
                        f"- Example {idx}: expected '{expected}', got '{actual}'"
                    )
        else:
            if example_results and any(getattr(r, "error", None) for r in example_results):
                lines.append("Execution failed on examples with no structured test cases.")
        if full_result is not None:
            if getattr(full_result, "error", None):
                lines.append(f"Full input run ERROR: {getattr(full_result, 'error', '')}")
            elif not full_answer:
                lines.append("Full input run completed but produced an empty answer.")
            else:
                lines.append("Full input run completed but the answer is still not accepted.")
        return "\n".join(lines)

    def _get_problem_type(self, characteristics: Dict[str, Any]) -> str:
        """Determine the problem type from characteristics.

        This is a lightweight heuristic classifier that maps the
        numeric characteristics produced by `_analyze_problem_characteristics`
        into coarse problem type strings used by the learning DB.
        """
        # Prioritize more specific structural signals first
        if characteristics.get("grid_operations", 0.0) > 0.0:
            return "grid"
        if characteristics.get("graph_complexity", 0.0) > 0.0:
            return "graph"
        if characteristics.get("math_complexity", 0.0) > 0.0:
            return "math"
        if characteristics.get("string_processing", 0.0) > 0.0:
            return "string"
        if characteristics.get("optimization_required", 0.0) > 0.0:
            return "optimization"
        return "general"

    def _get_top_models(self, problem_type: str, role: str, limit: int = 3, min_success_rate: float = 0.5) -> list[str]:
        """Get top performing models for a specific problem type and role."""
        logging.info(
            f"Getting top models for problem_type={problem_type}, role={role}, "
            f"limit={limit}, min_success_rate={min_success_rate}"
        )
        if not self.db:
            self.db = LearningDatabase(self.learning_dir)

        raw_models = self.db.get_top_models(problem_type, role, limit, min_success_rate)
        if raw_models:
            available = [m for m in raw_models if m in self.models]
            missing = [m for m in raw_models if m not in self.models]
            if missing:
                logging.info(
                    "Filtered out unavailable models for role %s: %s", role, missing
                )
            if available:
                logging.info("Top models after filtering: %s", available[:limit])
                return available[:limit]

        # Cold-start or all suggested models unavailable: fall back to local models
        fallback = list(self.models.keys())[:limit]
        logging.info(f"Top models: [] -> using fallback models {fallback}")
        return fallback

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
        day_dir = self.workspace_dir / "years" / str(year) / f"day{day:02d}"

        canonical_name = f"{year}_day{day:02d}_part{part}.py"
        canonical_path = day_dir / canonical_name
        if canonical_path.exists():
            with open(canonical_path, "r") as f:
                return f.read()

        solutions_dir = day_dir / "solutions"
        if solutions_dir.exists():
            solution_file = solutions_dir / f"part{part}.py"
            if solution_file.exists():
                with open(solution_file, "r") as f:
                    return f.read()

        attempts_dir = day_dir / "attempts"
        if not attempts_dir.exists():
            return None

        for attempt_file in attempts_dir.glob("attempt_*.json"):
            try:
                with open(attempt_file, "r") as f:
                    attempt_data = json.load(f)

                if (
                    attempt_data["metadata"].get("part") == part
                    and attempt_data["submission"].get("success")
                ):
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
