"""Base solver class for Advent of Code problems."""

import logging
import os
import json
from pathlib import Path
from dataclasses import dataclass, field
from typing import List, Tuple, Optional, Dict, Any
from datetime import datetime
import requests
from requests import RequestException
from shared.execution import SolutionExecutor, TestCase
from shared.llm.local import OllamaProvider
from shared.parser import parse_problem_text
from shared.aoc import fetch_problem_text, ensure_problem_files, ensure_problem_directory_structure
from shared.ledger import record_solution
from shared.strategy_recommender import StrategyRecommender
from learning.database import LearningDatabase
from shared.experiment import AttemptRecord, Outcome, SolverConfig

logger = logging.getLogger(__name__)


def _known_answer(year: int, day: int, part: int) -> Optional[str]:
    """Accepted AoC answer for this part, if it is cached locally."""
    from shared.ground_truth import get_known_answer

    return get_known_answer(year, day, part)


@dataclass
class CandidateVerdict:
    """Judgement on one generated candidate, from _verify_candidate."""

    accepted: bool
    outcome: Outcome
    answer: Optional[str] = None
    feedback: Optional[str] = None
    example_results: List[Any] = field(default_factory=list)


class BaseSolver:
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
        self.db = None
        self.enable_collaborative_improvement = self.config.enable_collaborative_improvement
        # Per-model trace of the most recent solve, consumed by the experiment
        # harness. Reset at the start of each solve_problem call.
        self.attempts: List[AttemptRecord] = []

        # Initialize all available models, preferring those actually installed in Ollama
        model_names = self._resolve_available_models()
        self.models = {
            model: OllamaProvider(
                model=model, debug=debug,
                temperature=self.config.temperature,
                num_ctx=self.config.num_ctx,
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
            strategies, effectiveness = self.strategy_recommender.get_recommended_strategies(
                problem_text, characteristics
            )
            
            # Get top performing models for each role based on problem type
            problem_type = self._get_problem_type(characteristics)
            primary_models = self._get_top_models(
                problem_type, "primary", limit=self.config.max_primary_models
            )
            # Reviewer models feed the (default-off) collaborative-improvement
            # path. The old "validator" role is gone: it drove a stub that always
            # returned True; acceptance is decided by execution against the oracle.
            reviewer_models = self._get_top_models(problem_type, "reviewer", limit=3)

            # Try each primary model and collect answers. With self-consistency
            # (samples_per_model > 1) a model contributes several candidates, so
            # the pool is keyed by candidate id, not model name; candidate_models
            # maps each back to the model that produced it, which is what the
            # learning DB and the ledger must record against.
            answers = {}
            candidate_models: Dict[str, str] = {}
            # Generation wall-clock per candidate: the only cost signal local
            # models expose, since the Ollama CLI reports no token counts.
            generation_times: Dict[str, float] = {}
            generation_tokens: Dict[str, Dict[str, int]] = {}
            failures = []
            
            logging.info("")
            logging.info(f"Attempting solution with top {len(primary_models)} primary model(s)")

            for model_name in primary_models:
                if model_name not in self.models:
                    logging.warning(f"Model {model_name} not available, skipping")
                    continue
                    
                model = self.models[model_name]
                # Self-consistency: draw samples_per_model candidates from this
                # model. Each draw is independent -- a sample that raises records
                # its own no-candidate failure and does not abort the rest.
                for sample_idx in range(self.config.samples_per_model):
                    cand_id = (
                        model_name if self.config.samples_per_model == 1
                        else f"{model_name}#s{sample_idx}"
                    )
                    candidate_models[cand_id] = model_name
                    try:
                        logging.info("")
                        logging.info(f"Trying primary model: {cand_id}")
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
                        generation_times[cand_id] = response_time
                        # Token usage the model just reported (analysis + impl
                        # calls), so the attempt records real cost, not a zero.
                        generation_tokens[cand_id] = getattr(
                            model, "last_token_usage", {"input_tokens": 0, "output_tokens": 0}
                        )

                        # Every candidate enters the pool; correctness is decided
                        # by execution against the oracle further down, and the
                        # model's performance is recorded there against that
                        # verdict -- not here, where it has only produced text.
                        answers[cand_id] = solution

                    except Exception as e:
                        failures.append((cand_id, str(e)))
                        # A model that never produced usable code is a distinct
                        # failure from one whose code ran and gave a wrong answer,
                        # and it is a real (verified) failure to record. It still
                        # spent tokens getting there, so record them.
                        tokens = getattr(
                            model, "last_token_usage", {"input_tokens": 0, "output_tokens": 0}
                        )
                        self._record_attempt(
                            model_name, year, day, part, Outcome.NO_CANDIDATE,
                            stage="generate",
                            error=f"{type(e).__name__}: {e}",
                            input_tokens=tokens.get("input_tokens", 0),
                            output_tokens=tokens.get("output_tokens", 0),
                        )
                        self._record_model_performance(
                            model_name, success=False, problem_type=problem_type
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
                    # Consensus is agreement about *code*, which says nothing
                    # about whether the code is correct. This branch used to
                    # return here without ever executing it, bypassing the whole
                    # oracle. Verify before accepting.
                    consensus_verdict = await self._verify_candidate(
                        "consensus", consensus_answer, year, day, part,
                        self.build_test_cases(parsed_problem),
                        _known_answer(year, day, part),
                    )
                    self._record_attempt(
                        "consensus", year, day, part, consensus_verdict.outcome,
                        stage="consensus",
                        answer=consensus_verdict.answer,
                        code=consensus_answer,
                        error=None if consensus_verdict.accepted else consensus_verdict.feedback,
                    )
                    if not consensus_verdict.accepted:
                        logger.info(
                            "Consensus candidate rejected by verification (%s); "
                            "continuing to execution-based selection.",
                            consensus_verdict.outcome.value,
                        )
                        consensus_answer = None

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
                            self.db = LearningDatabase(self.learning_dir)
                        self.db.record_improvement(
                            problem_id=f"{year}_day{day:02d}_part{part}",
                            model_name=improved_candidate.author,
                            improvement_type="collaborative",
                            impact_score=impact_score
                        )
                        
                        # Accept the improved candidate only if it passes the same
                        # oracle as every other path. This previously ran the
                        # stub validator (validate_solution -> return True) and
                        # returned unverified code -- the exact oracle-bypass hole
                        # closed on the consensus path. Verification, not a fake
                        # gate, decides acceptance.
                        improved_verdict = await self._verify_candidate(
                            improved_candidate.author or "collaborative",
                            improved_candidate.solution,
                            year, day, part,
                            self.build_test_cases(parsed_problem),
                            _known_answer(year, day, part),
                        )
                        if improved_verdict.accepted:
                            record_solution(
                                year, day, part,
                                improved_candidate.author or "collaborative",
                                improved_candidate.solution,
                            )
                            return improved_candidate.solution
                except Exception as e:
                    logging.warning(f"Collaborative improvement failed: {str(e)}")

            # If we still have answers but no consensus or collaborative improvement result,
            # run each candidate through execution-based validation against examples and
            # full input, and prefer the first that passes.
            # The oracle is established once, outside the candidate loops, because
            # the fallback path below needs it too -- it previously had no access
            # to the ground-truth answer and judged candidates on its own weaker
            # criterion.
            exec_test_cases: List[TestCase] = self.build_test_cases(parsed_problem)

            # Ground truth for the full input, when this problem has already been
            # accepted on the user's AoC account. The strongest oracle available,
            # and it needs no submission.
            from shared.ground_truth import get_known_answer

            known_answer = get_known_answer(year, day, part)

            # A candidate can only be accepted if something can actually judge it.
            # Without an oracle, acceptance degrades to "ran without crashing",
            # which is how stubs were previously recorded as solved.
            if self.config.require_oracle and not exec_test_cases and known_answer is None:
                logger.error(
                    "No correctness oracle for year %d day %02d part %d: no example "
                    "has a known expected output and no accepted answer is cached. "
                    "Refusing to accept any candidate as solved.",
                    year, day, part,
                )
                return None

            if answers:
                max_repair_iterations = self.config.max_repair_iterations
                current_candidates: Dict[str, str] = dict(answers)

                for iteration in range(max_repair_iterations + 1):
                    validated_candidates: List[Tuple[str, str]] = []
                    feedback_by_model: Dict[str, str] = {}

                    for cand_id, solution in current_candidates.items():
                        # cand_id keys the pool; model_name is the model that
                        # produced it, which is what recording/model-lookup use.
                        model_name = candidate_models.get(cand_id, cand_id)
                        try:
                            verdict = await self._verify_candidate(
                                model_name, solution, year, day, part,
                                exec_test_cases, known_answer,
                            )
                            tokens = generation_tokens.get(cand_id, {})
                            self._record_attempt(
                                model_name, year, day, part, verdict.outcome,
                                stage="repair" if iteration else "generate",
                                answer=verdict.answer,
                                expected=known_answer,
                                repair_iteration=iteration,
                                wall_clock_seconds=generation_times.get(cand_id, 0.0),
                                quality_score=quality_scores.get(cand_id),
                                code=solution,
                                input_tokens=tokens.get("input_tokens", 0),
                                output_tokens=tokens.get("output_tokens", 0),
                                # Persist why a candidate failed (traceback / expected-vs-got).
                                # error is kept in the result JSON without --include-replay, so
                                # the wrong-vs-error split is diagnosable from every run.
                                error=None if verdict.accepted else verdict.feedback,
                            )
                            # Record the model's verified performance once, on its
                            # initial candidate (repair iterations re-test the same
                            # candidates and would double-count).
                            if iteration == 0:
                                self._record_model_performance(
                                    model_name,
                                    success=verdict.accepted,
                                    problem_type=problem_type,
                                    quality_score=(quality_scores.get(cand_id) or 0.0) * 10.0,
                                    response_time=generation_times.get(cand_id, 0.0),
                                )
                            if not verdict.accepted:
                                if verdict.feedback:
                                    feedback_by_model[cand_id] = verdict.feedback
                                continue

                            # Keep the executed answer too: without an oracle it
                            # is what answer-based consensus votes on.
                            validated_candidates.append((cand_id, solution, verdict.answer))
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
                        chosen_cand, chosen_solution = self._select_candidate(
                            validated_candidates, quality_scores, known_answer
                        )
                        record_solution(
                            year, day, part,
                            candidate_models.get(chosen_cand, chosen_cand),
                            chosen_solution,
                        )
                        return chosen_solution

                    if iteration >= max_repair_iterations:
                        break

                    improved_candidates: Dict[str, str] = {}
                    for cand_id, solution in current_candidates.items():
                        if cand_id not in feedback_by_model:
                            continue
                        model = self.models.get(candidate_models.get(cand_id, cand_id))
                        improve_fn = getattr(model, "improve_solution", None) if model else None
                        if not callable(improve_fn):
                            continue
                        try:
                            improved_code = await improve_fn(
                                solution,
                                parsed_problem,
                                feedback_by_model[cand_id],
                            )
                            if improved_code and improved_code != solution:
                                improved_candidates[cand_id] = improved_code
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

            if fallback_models and self.config.enable_fallback_models:
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
                        
                        # Same verifier as the primary path. This branch used to
                        # carry its own copy of the acceptance check, which was
                        # never updated when the ground-truth oracle landed -- so
                        # a fallback model could return a wrong answer as the
                        # solution even when the accepted answer was known.
                        verdict = await self._verify_candidate(
                            model_name, solution, year, day, part,
                            exec_test_cases, known_answer,
                        )
                        fb_tokens = getattr(
                            model, "last_token_usage", {"input_tokens": 0, "output_tokens": 0}
                        )
                        self._record_attempt(
                            model_name, year, day, part, verdict.outcome,
                            stage="fallback",
                            answer=verdict.answer,
                            expected=known_answer,
                            code=solution,
                            input_tokens=fb_tokens.get("input_tokens", 0),
                            output_tokens=fb_tokens.get("output_tokens", 0),
                            error=None if verdict.accepted else verdict.feedback,
                        )

                        # Record the fallback model's verified outcome the same
                        # way the primary path does -- against the verdict, not at
                        # generation time.
                        self._record_model_performance(
                            model_name,
                            success=verdict.accepted,
                            problem_type=problem_type,
                            response_time=generation_times.get(model_name, 0.0),
                        )

                        if verdict.accepted:
                            logging.info(f"Fallback model {model_name} produced valid solution!")
                            record_solution(year, day, part, model_name, solution)
                            return solution
                        else:
                            logging.info(f"Fallback model {model_name} failed execution validation")

                    except Exception as e:
                        logging.warning(f"Fallback model {model_name} failed: {str(e)}")
                        continue
            
            # If we get here, we failed to solve the problem
            self._print_consensus_summary(answers, failures, None, [])
            return None

        except Exception as e:
            raise  # Let the error propagate to the top level

    # ------------------------------------------------------------------
    # Pipeline stages
    #
    # solve_problem was a single ~540-line method. These are the stages it
    # decomposes into, each independently testable. The important one is
    # _verify_candidate: the main loop and the fallback loop previously each
    # had their own copy of the acceptance logic, and only the main one was
    # updated when the ground-truth oracle landed -- so a fallback model could
    # still return a wrong answer as the solution.
    # ------------------------------------------------------------------

    def _select_candidate(
        self,
        validated: List[Tuple[str, str, Optional[str]]],
        quality_scores: Dict[str, float],
        known_answer: Optional[str],
    ) -> Tuple[str, str]:
        """Choose one candidate from those that passed verification.

        With a ground-truth oracle every validated candidate already produced
        the accepted answer, so code quality just breaks the tie. Without one
        (the submission-phase case), group candidates by their executed answer
        and prefer the plurality -- answer-based consensus. On the samp3 A/B data
        this picked the correct answer for 10 of 11 solved problem-trials; the
        one miss was two wrong candidates agreeing, which is the technique's
        inherent failure mode, so a quorum of min_consensus_models is required
        before consensus overrides quality.
        """
        def best_by_quality(items: List[Tuple[str, str, Optional[str]]]) -> Tuple[str, str]:
            ranked = sorted(
                items, key=lambda it: quality_scores.get(it[0], 0.0), reverse=True
            )
            return ranked[0][0], ranked[0][1]

        if known_answer is not None:
            return best_by_quality(validated)

        from collections import Counter
        counts = Counter(
            (ans or "").strip() for _, _, ans in validated if ans and ans.strip()
        )
        if counts:
            top_answer, top_n = counts.most_common(1)[0]
            if top_n >= self.config.min_consensus_models:
                agreeing = [
                    it for it in validated if (it[2] or "").strip() == top_answer
                ]
                logger.info(
                    "answer-based consensus selected %r (%d of %d candidates agree)",
                    top_answer, top_n, len(validated),
                )
                return best_by_quality(agreeing)

        # No answer reached quorum: fall back to the highest-quality candidate.
        return best_by_quality(validated)

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
        input_tokens: int = 0,
        output_tokens: int = 0,
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
            wall_clock_seconds=wall_clock_seconds,
            quality_score=quality_score,
            code=code,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
        )
        self.attempts.append(record)
        return record

    @staticmethod
    def build_test_cases(parsed_problem: Any) -> List[TestCase]:
        """Examples usable as an oracle: those with a known expected output."""
        cases: List[TestCase] = []
        for example in getattr(parsed_problem, "examples", []) or []:
            input_data = getattr(example, "input_data", None)
            expected_output = getattr(example, "expected_output", None)
            if input_data is None or expected_output in (None, ""):
                continue
            cases.append(
                TestCase(
                    input_data=str(input_data),
                    expected_output=str(expected_output),
                    description=getattr(example, "description", None),
                )
            )
        return cases

    async def _verify_candidate(
        self,
        model_name: str,
        solution: str,
        year: int,
        day: int,
        part: int,
        test_cases: List[TestCase],
        known_answer: Optional[str],
    ) -> "CandidateVerdict":
        """Run one candidate and judge it against the best available oracle.

        Oracle hierarchy: the accepted AoC answer wins when known, because the
        parser can mis-pair an expected output with the wrong <pre> block and a
        bad example must never veto a correct answer. Without ground truth,
        every example must pass -- they are the only oracle available.
        """
        example_results, full_result, full_answer = (
            await self.solution_executor.test_solution(
                solution_code=solution,
                year=year,
                day=day,
                part=part,
                test_cases=test_cases,
                model_name=model_name,
                debug=self.debug,
                force_full_input=known_answer is not None,
            )
        )

        def _reject(outcome: Outcome) -> "CandidateVerdict":
            return CandidateVerdict(
                accepted=False,
                outcome=outcome,
                answer=full_answer,
                feedback=self._build_execution_feedback(
                    model_name, test_cases, example_results, full_result, full_answer
                ),
                example_results=example_results,
            )

        examples_failed = bool(example_results) and any(
            r.error is not None for r in example_results
        )
        if examples_failed and known_answer is None:
            return _reject(Outcome.WRONG)
        if not full_result or full_result.error is not None:
            return _reject(Outcome.ERROR)
        if not full_answer:
            return _reject(Outcome.NO_CANDIDATE)

        if known_answer is not None:
            if full_answer.strip() != known_answer.strip():
                logger.info(
                    "%s rejected: produced %r, accepted answer is %r",
                    model_name, full_answer.strip(), known_answer.strip(),
                )
                return _reject(Outcome.WRONG)
            outcome = Outcome.SOLVED
        else:
            # Examples all passed, but nothing confirms the full-input answer.
            outcome = Outcome.UNVERIFIED

        return CandidateVerdict(
            accepted=True,
            outcome=outcome,
            answer=full_answer,
            feedback=None,
            example_results=example_results,
        )

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
            
        # Group identical answers, summing weights and counting distinct models
        answer_groups: Dict[str, float] = {}
        models_per_answer: Dict[str, int] = {}
        for model_name, (answer, weight) in weighted_answers.items():
            answer_groups[answer] = answer_groups.get(answer, 0.0) + weight
            models_per_answer[answer] = models_per_answer.get(answer, 0) + 1

        # Find answer with highest total weight
        best_answer = max(answer_groups.items(), key=lambda x: x[1])[0]
        best_weight = answer_groups[best_answer]

        # Agreement requires more than one voter. A lone candidate holds 100% of
        # the total weight, so it cleared the threshold trivially and was
        # returned as "consensus" -- which is not consensus, it is a single
        # unreviewed opinion.
        agreeing = models_per_answer[best_answer]
        if agreeing < self.config.min_consensus_models:
            logger.info(
                "No consensus: best answer has %d agreeing model(s), need %d.",
                agreeing, self.config.min_consensus_models,
            )
            return None

        # Only return consensus if weight is significantly higher than others.
        #
        # Every weight is a code-quality score, so all of them are 0.0 when
        # quality analysis fails -- which is exactly what happens when the
        # generated code is unparseable. Dividing here then raised
        # ZeroDivisionError and aborted the whole solve, turning a recoverable
        # bad-candidate case into a hard failure. With no usable weights there is
        # no evidence of agreement, so there is no consensus.
        total_weight = sum(answer_groups.values())
        if total_weight <= 0:
            logger.warning(
                "No usable quality weights for consensus (all %d candidate(s) scored "
                "0.0); treating as no consensus.",
                len(answer_groups),
            )
            return None

        if best_weight / total_weight >= self.config.consensus_threshold:
            return best_answer

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

