"""Base solver class for Advent of Code problems."""

import logging
import re
import os
import json
from pathlib import Path
from typing import TYPE_CHECKING, List, Tuple, Optional, Dict, Any

if TYPE_CHECKING:
    from learning import LearningDatabase
    from shared.quality.code_quality import CodeQualityAnalyzer
from datetime import datetime
import requests
from requests import RequestException
from shared.execution import SolutionExecutor
from shared.llm.local import OllamaProvider
from shared.parser import parse_problem_text, TestCase as StatementExample
from shared import problem_context
from shared.aoc import fetch_problem_text, ensure_problem_files, ensure_problem_directory_structure
from shared.ledger import record_solution
from shared.strategy_recommender import StrategyRecommender
from learning.database import LearningDatabase
from shared.solving.candidates import CandidateVerdict
from shared.solving.consensus import ConsensusMixin
from shared.solving.generation import GenerationMixin
from shared.solving.repair import RepairMixin
from shared.solving.state import _Prep
from shared.solving.feedback import _is_timeout_error  # noqa: F401  # pylint: disable=unused-import
from shared.experiment import AttemptRecord, Outcome, SolverConfig

logger = logging.getLogger(__name__)


def _known_answer(year: int, day: int, part: int) -> Optional[str]:
    """Accepted AoC answer for this part, if it is cached locally."""
    from shared.ground_truth import get_known_answer

    return get_known_answer(year, day, part)


class BaseSolver(GenerationMixin, ConsensusMixin, RepairMixin):
    """Base class for solving AoC problems."""

    def __init__(
        self,
        workspace_dir: Path,
        debug: bool = False,
        config: Optional[SolverConfig] = None,
    ) -> None:
        """Initialize the base solver.

        Args:
            workspace_dir: Workspace directory path
            debug: Enable debug output
            config: Experimental configuration. Defaults to SolverConfig.from_env(),
                which reads the environment variables the solver historically used,
                so existing .env files keep working.
        """
        self.workspace_dir = workspace_dir
        self.debug = debug
        self.config = config if config is not None else SolverConfig.from_env()
        self.solution_executor = SolutionExecutor(
            workspace_dir, timeout=self.config.execution_timeout
        )
        self.strategy_recommender = StrategyRecommender(workspace_dir)

        # Initialize learning system
        self.learning_dir = workspace_dir / "learning"
        self.learning_dir.mkdir(parents=True, exist_ok=True)
        self.strategy_optimizer = None
        self.db: Optional["LearningDatabase"] = None
        self.enable_collaborative_improvement = self.config.enable_collaborative_improvement
        # Per-model trace of the most recent solve, consumed by the experiment
        # harness. Reset at the start of each solve_problem call.
        self.attempts: List[AttemptRecord] = []
        # (year, day) -> the program that solved Part One in the current trial.
        # Set by the experiment harness before it asks for Part Two.
        self.part_one_programs: Dict[Tuple[int, int], str] = {}

        # Initialize all available models, preferring those actually installed in Ollama
        model_names = self._resolve_available_models()
        self.models = {
            model: OllamaProvider(
                model=model, debug=debug,
                temperature=self.config.temperature,
                num_ctx=self.config.num_ctx,
                think=self.config.enable_thinking,
                analysis_temperature=self.config.analysis_temperature,
            )
            for model in model_names
        }

    def _resolve_available_models(self) -> List[str]:
        """Determine which models to use, preferring those installed in Ollama.

        The candidate list is SolverConfig.models when set, otherwise the curated
        OllamaProvider.AVAILABLE_MODELS. Making the config authoritative here is
        what allows an A/B across model sets -- previously the field existed,
        changed the config fingerprint, and had no effect on which models ran.

        If Ollama is unreachable or returns an unexpected response, fall back to
        the candidate list unfiltered. If Ollama is reachable but none of the
        candidates are installed, raise a clear error naming them.
        """
        candidates = list(self.config.models or OllamaProvider.AVAILABLE_MODELS)

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
                # Nothing reported; keep the candidate list
                return candidates

            # Intersect candidates with installed models, preserving order
            filtered = [
                model
                for model in candidates
                if model in installed
            ]

            if not filtered:
                wanted = ", ".join(candidates)
                raise RuntimeError(
                    "None of the requested models are installed in Ollama at "
                    f"{host}. Please install at least one of: {wanted}"
                )

            return filtered
        except RequestException:
            # Ollama not reachable; keep the candidate list so environments
            # without Ollama can still run tests and other parts of the system.
            return candidates
        except ValueError:
            # Malformed JSON or unexpected response; fall back to candidates
            return candidates

    async def solve_problem(
        self, year: int, day: int, part: int, force: bool = False
    ) -> Optional[str]:
        """Solve an Advent of Code problem using model consensus."""
        self.attempts = []
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

            # Stage 1 -- setup: fetch/parse, characterise, pick models (or reuse
            # an already-recorded solution).
            prep = await self._prepare_problem(year, day, part, force)
            if prep.solved is not None:
                return prep.solved
            parsed_problem = prep.parsed_problem
            strategies, effectiveness = prep.strategies, prep.effectiveness
            problem_type = prep.problem_type
            primary_models, reviewer_models = prep.primary_models, prep.reviewer_models

            # Stage 2 -- generation: draw the candidate pool (self-consistency
            # samples fan out here).
            # Stage 2 -- generation: draw the candidate pool (self-consistency
            # samples fan out here).
            cands = await self._generate_candidates(prep, year, day, part)

            # Stage 3 -- source consensus + optional collaborative improvement.
            # Returns an accepted solution (rare) plus the quality scores the
            # execution stage reuses to rank candidates.
            accepted, quality_scores = await self._reach_consensus(
                cands, prep, year, day, part
            )
            if accepted is not None:
                return accepted

            # Stage 3 -- execute candidates against the oracle, repair, and
            # fall back to other models.
            return await self._execute_and_repair(
                cands, quality_scores, prep, year, day, part
            )

        except Exception as e:
            raise  # Let the error propagate to the top level

    # ------------------------------------------------------------------
    # solve_problem stages (extracted for readability; see the orchestrator above)
    # ------------------------------------------------------------------

    async def _prepare_problem(
        self, year: int, day: int, part: int, force: bool
    ) -> _Prep:
        """Setup: reuse an existing solution, else fetch/parse and pick models."""
        ensure_problem_directory_structure(self.workspace_dir, year, day)
        await ensure_problem_files(year, day)

        if not force:
            existing_solution = await self._get_existing_solution(year, day, part)
            if existing_solution:
                logging.info("Using existing successful solution")
                problem_id = f"{year}_day{day:02d}_part{part}"
                result = await self.solution_executor.run_against_full_input(
                    problem_id, year, day, part, existing_solution
                )
                if result.error is None:
                    return _Prep(solved=result.output.strip())
                logging.warning(
                    "Existing solution failed on full input (%s); falling back to full solve",
                    result.error,
                )

        problem_text, _, _ = await fetch_problem_text(year, day, part)
        parsed_problem = parse_problem_text(problem_text)
        if self.config.problem_context == "aoc":
            # Examples and the final question stay those of the part's own
            # article; only what the model reads around them is widened.
            page = problem_context.page_description(
                year, day, part, parsed_problem.description
            )
            if page != parsed_problem.description:
                parsed_problem.description = page
                heading = re.match(r"\s*--- .+? ---", page)
                parsed_problem.title = (
                    heading.group().strip() if heading else parsed_problem.title
                )
            part_one_code = self.part_one_programs.get((year, day))
            parsed_problem.supplement = problem_context.supplement(
                year, day, part, part_one_code=part_one_code
            )
            if self.config.example_tests == "page":
                # The parser pairs a stated result with the code block above it,
                # which is often an illustration; read the pairs off the page
                # instead (dev/progress/example-tests-mispaired.md). Feedback
                # only: the accepted answer decides what is solved.
                pairs = problem_context.statement_examples(year, day, part)
                if pairs is not None:
                    for example in parsed_problem.examples:
                        example.expected_output = ""
                    for given, stated in pairs:
                        match = next(
                            (e for e in parsed_problem.examples
                             if str(e.input_data or "").strip("\n") == given),
                            None,
                        )
                        if match is not None:
                            match.expected_output = stated
                        else:
                            parsed_problem.examples.append(StatementExample(
                                input_data=given,
                                expected_output=stated,
                                order=len(parsed_problem.examples),
                                description="The statement's worked example and its stated result",
                            ))
            else:
                # A Part Two article seldom repeats the worked example it refers
                # to. Offered only with an accepted answer on file, so that a wrong
                # pairing can mislead feedback but can never reject a right answer.
                if (
                    part == 2
                    and _known_answer(year, day, part) is not None
                    and not any(e.expected_output for e in parsed_problem.examples)
                ):
                    paired = problem_context.part_two_example(year, day, part_one_code)
                    if paired is not None:
                        parsed_problem.examples.append(StatementExample(
                            input_data=paired[0],
                            expected_output=paired[1],
                            order=len(parsed_problem.examples),
                            description=(
                                "Part One's worked example, with the result "
                                "Part Two states for it"
                            ),
                        ))
        if self.debug:
            logging.info("Problem text for part %d:", part)
            logging.info(problem_text)

        characteristics = self._analyze_problem_characteristics(parsed_problem)
        strategies, effectiveness = self.strategy_recommender.get_recommended_strategies(
            problem_text, characteristics
        )
        problem_type = self._get_problem_type(characteristics)
        primary_models = self._get_top_models(
            problem_type, "primary", limit=self.config.max_primary_models
        )
        # Reviewer models feed the (default-off) collaborative-improvement path.
        # The old "validator" role is gone: it drove a stub that always returned
        # True; acceptance is decided by execution against the oracle.
        reviewer_models = self._get_top_models(problem_type, "reviewer", limit=3)

        return _Prep(
            parsed_problem=parsed_problem,
            strategies=strategies,
            effectiveness=effectiveness,
            problem_type=problem_type,
            primary_models=primary_models,
            reviewer_models=reviewer_models,
        )

    # ------------------------------------------------------------------
    # Records, and the module-level names the stages reach through BaseSolver
    #
    # The stages live in shared/solving/ (generation, consensus, candidates,
    # repair, feedback). They reach the ledger writer and the accepted answer
    # through _record_solution and _accepted_answer, so the names in this module
    # stay the ones tests and dev/replay_solver.py replace. Verification has one
    # copy, _verify_candidate: the main loop and the fallback loop once each had
    # their own, and only one was updated when the ground-truth oracle landed.
    # ------------------------------------------------------------------

    def _accepted_answer(self, year: int, day: int, part: int) -> Optional[str]:
        """The accepted answer, through this module's _known_answer, which tests replace."""
        return _known_answer(year, day, part)

    def _record_solution(self, year: int, day: int, part: int, model: str, code: str) -> None:
        """Record an accepted solution in the ledger. Looked up on this module, so tests and
        dev/replay_solver.py can replace the ledger writer for every stage at once."""
        record_solution(year, day, part, model, code)

    def _record_model_performance(
        self,
        model_name: str,
        success: bool,
        problem_type: str,
        quality_score: float = 0.0,
        response_time: float = 0.0,
        role: str = "primary",
    ) -> None:
        """Record a model's *verified* performance in the learning DB.

        `success` must reflect whether the candidate was accepted by the oracle,
        not whether the model merely produced code. This used to be recorded at
        generation time with success=True for anything that generated, so
        success_rate measured "returned parseable text", and it was the sole key
        _get_top_models ranked on. The five hand-built copies of this write are
        consolidated here so the signal is defined in one place.
        """
        if not self.db:
            from learning import LearningDatabase  # patchable via learning.LearningDatabase
            self.db = LearningDatabase(self.learning_dir)
        self.db.update_model_performance(
            model_name=model_name,
            metrics={
                "quality_score": quality_score,
                "response_time": response_time,
                "cost": 0.0,
            },
            success=success,
            problem_type=problem_type,
            role=role,
        )

    def _record_attempt(
        self,
        model: str,
        year: int,
        day: int,
        part: int,
        outcome: Outcome,
        *,
        stage: str = "generate",
        answer: Optional[str] = None,
        expected: Optional[str] = None,
        error: Optional[str] = None,
        repair_iteration: int = 0,
        wall_clock_seconds: float = 0.0,
        quality_score: Optional[float] = None,
        code: Optional[str] = None,
        prompt: Optional[str] = None,
        raw_response: Optional[str] = None,
        input_tokens: int = 0,
        output_tokens: int = 0,
        verdict: Optional["CandidateVerdict"] = None,
        draft_index: Optional[int] = None,
    ) -> AttemptRecord:
        """Append one model attempt to the current solve's trace.

        Without this the harness can only see that a problem was solved, not how
        many models it took -- which makes attempts-to-solve and first-try rate
        meaningless. Recording is best-effort telemetry and never affects control
        flow.
        """
        record = AttemptRecord(
            model=model,
            problem_id=f"{year}_day{day:02d}_part{part}",
            config_fingerprint=self.config.fingerprint(),
            outcome=outcome,
            stage=stage,
            answer=answer,
            expected=expected,
            error=error,
            repair_iteration=repair_iteration,
            draft_index=draft_index,
            wall_clock_seconds=wall_clock_seconds,
            quality_score=quality_score,
            code=code,
            prompt=prompt,
            raw_response=raw_response,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            examples_passed=verdict.examples_passed if verdict else None,
            examples_total=verdict.examples_total if verdict else None,
        )
        self.attempts.append(record)
        return record

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
                    return str(attempt_data["code"])
            except (json.JSONDecodeError, KeyError):
                continue

        return None

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

