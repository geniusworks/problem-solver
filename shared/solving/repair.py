"""Execute the candidate pool against the oracle, repair what failed, then try fallback models.

Moved out of shared/solver.py (2026-11-12), where it was one 300-line method. The behaviour is
unchanged; the method is split into its rounds: _verify_round runs and records every current
candidate, _repair_round asks each failed one's model for a repair, and _try_fallback_models
runs when every primary candidate and its repairs failed.
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import TYPE_CHECKING, Any, Callable, Dict, List, Optional, Tuple

from shared.execution import TestCase
from shared.experiment import Outcome
from shared.solving.candidates import CandidateMixin, _draft_index, _last_exchange
from shared.solving.state import _Candidates, _Prep

if TYPE_CHECKING:
    from shared.llm.local import OllamaProvider

# The solver's logger, so log records keep the name they had before the move.
logger = logging.getLogger("shared.solver")


@dataclass
class _Oracle:
    """What judges a candidate in this solve: the worked examples and the accepted answer."""

    test_cases: List[TestCase]
    known_answer: Optional[str]


@dataclass
class _Costs:
    """Cost of the call that produced each candidate's *current* code: the draft's at first,
    then each repair's own. Kept apart from the pool's generation_* dicts, which stay the
    draft's."""

    times: Dict[str, float] = field(default_factory=dict)
    tokens: Dict[str, Dict[str, int]] = field(default_factory=dict)
    replay: Dict[str, Tuple[Optional[str], Optional[str]]] = field(default_factory=dict)


class RepairMixin(CandidateMixin):
    """The execute-repair-fallback stage, as BaseSolver uses it."""

    models: Dict[str, "OllamaProvider"]
    # Defined on BaseSolver.
    _record_attempt: Callable[..., Any]
    _record_model_performance: Callable[..., None]
    _record_solution: Callable[..., None]
    _print_consensus_summary: Callable[..., None]

    async def _execute_and_repair(
        self, cands: "_Candidates", quality_scores: Dict[str, float],
        prep: "_Prep", year: int, day: int, part: int,
    ) -> Optional[str]:
        """Execute the candidate pool against the oracle, repair, fall back.

        Returns the accepted solution, or None if nothing passed. The oracle
        (cached accepted answer + worked examples) is established once here
        because the fallback loop needs it too.
        """
        # If we still have answers but no consensus or collaborative improvement result,
        # run each candidate through execution-based validation against examples and
        # full input, and prefer the first that passes.
        # The oracle is established once, outside the candidate loops, because
        # the fallback path below needs it too -- it previously had no access
        # to the ground-truth answer and judged candidates on its own weaker
        # criterion.
        exec_test_cases: List[TestCase] = self.build_test_cases(prep.parsed_problem)

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

        oracle = _Oracle(exec_test_cases, known_answer)
        if cands.answers:
            solved = await self._repair_loop(cands, quality_scores, prep, year, day, part, oracle)
            if solved is not None:
                return solved

        # If we get here, all primary model candidates failed execution validation.
        # Try fallback models that weren't in the primary set.
        solved = await self._try_fallback_models(cands, prep, year, day, part, oracle)
        if solved is not None:
            return solved

        # If we get here, we failed to solve the problem
        self._print_consensus_summary(cands.answers, cands.failures, None, [])
        return None

    async def _repair_loop(
        self, cands: "_Candidates", quality_scores: Dict[str, float], prep: "_Prep",
        year: int, day: int, part: int, oracle: _Oracle,
    ) -> Optional[str]:
        """Verify the pool, repair what failed, and repeat up to max_repair_iterations times."""
        costs = _Costs(dict(cands.generation_times), dict(cands.generation_tokens),
                       dict(cands.generation_replay))
        max_repair_iterations = self.config.max_repair_iterations
        current_candidates: Dict[str, str] = dict(cands.answers)

        for iteration in range(max_repair_iterations + 1):
            validated_candidates, feedback_by_model = await self._verify_round(
                current_candidates, iteration, cands, quality_scores, prep, year, day, part,
                oracle, costs,
            )

            if validated_candidates:
                chosen_cand, chosen_solution = self._select_candidate(
                    validated_candidates, quality_scores, oracle.known_answer
                )
                self._record_solution(
                    year, day, part,
                    cands.candidate_models.get(chosen_cand, chosen_cand),
                    chosen_solution,
                )
                return chosen_solution

            if iteration >= max_repair_iterations:
                break

            improved_candidates = await self._repair_round(
                current_candidates, feedback_by_model, iteration, cands, prep, year, day, part,
                oracle, costs,
            )

            if not improved_candidates:
                break

            current_candidates = improved_candidates
        return None

    async def _verify_round(
        self, current_candidates: Dict[str, str], iteration: int, cands: "_Candidates",
        quality_scores: Dict[str, float], prep: "_Prep", year: int, day: int, part: int,
        oracle: _Oracle, costs: _Costs,
    ) -> Tuple[List[Tuple[str, str, Optional[str]]], Dict[str, str]]:
        """Run and record every current candidate. Returns those accepted, with their executed
        answers, and the feedback for each that failed."""
        validated_candidates: List[Tuple[str, str, Optional[str]]] = []
        feedback_by_model: Dict[str, str] = {}

        for cand_id, solution in current_candidates.items():
            # cand_id keys the pool; model_name is the model that
            # produced it, which is what recording/model-lookup use.
            model_name = cands.candidate_models.get(cand_id, cand_id)
            try:
                verdict = await self._verify_candidate(
                    model_name, solution, year, day, part,
                    oracle.test_cases, oracle.known_answer,
                )
                tokens = costs.tokens.get(cand_id, {})
                prompt, raw_response = costs.replay.get(cand_id, (None, None))
                self._record_attempt(
                    model_name, year, day, part, verdict.outcome,
                    stage="repair" if iteration else "generate",
                    draft_index=_draft_index(cand_id),
                    verdict=verdict,
                    answer=verdict.answer,
                    expected=oracle.known_answer,
                    repair_iteration=iteration,
                    wall_clock_seconds=costs.times.get(cand_id, 0.0),
                    # quality_scores were computed on the drafts.
                    quality_score=None if iteration else quality_scores.get(cand_id),
                    code=solution,
                    prompt=prompt,
                    raw_response=raw_response,
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
                        problem_type=prep.problem_type,
                        quality_score=(quality_scores.get(cand_id) or 0.0) * 10.0,
                        response_time=cands.generation_times.get(cand_id, 0.0),
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
                self._record_attempt(
                    model_name, year, day, part, Outcome.HARNESS_ERROR,
                    stage="repair" if iteration else "generate",
                    draft_index=_draft_index(cand_id),
                    expected=oracle.known_answer,
                    repair_iteration=iteration,
                    code=solution,
                    error=f"{type(e).__name__}: {e}",
                )
                continue
        return validated_candidates, feedback_by_model

    async def _repair_round(
        self, current_candidates: Dict[str, str], feedback_by_model: Dict[str, str],
        iteration: int, cands: "_Candidates", prep: "_Prep", year: int, day: int, part: int,
        oracle: _Oracle, costs: _Costs,
    ) -> Dict[str, str]:
        """Ask the model behind each failed candidate for a repair. Returns the repaired code by
        candidate; a repair that yields nothing to run is recorded here, as nothing later will."""
        improved_candidates: Dict[str, str] = {}
        for cand_id, solution in current_candidates.items():
            if cand_id not in feedback_by_model:
                continue
            model = self.models.get(cands.candidate_models.get(cand_id, cand_id))
            improve_fn = getattr(model, "improve_solution", None) if model else None
            if not callable(improve_fn):
                continue
            repair_start = datetime.now()
            stale_usage = getattr(model, "last_token_usage", None)
            repair_error: Optional[str] = None
            improved_code = None
            try:
                improved_code = await improve_fn(
                    solution,
                    prep.parsed_problem,
                    feedback_by_model[cand_id],
                )
            except Exception as e:
                repair_error = f"{type(e).__name__}: {e}"
            repair_seconds = (datetime.now() - repair_start).total_seconds()
            usage = getattr(model, "last_token_usage", None)
            # A call that raised before reporting usage leaves the
            # previous call's counts in place; those are not this call's.
            if repair_error is not None and usage is stale_usage:
                usage = None
            repair_tokens = dict(usage or {"input_tokens": 0, "output_tokens": 0})
            repair_replay = _last_exchange(model)

            if improved_code and improved_code != solution:
                improved_candidates[cand_id] = improved_code
                # The next iteration records this candidate; give it
                # the repair's own cost, not the draft's.
                costs.times[cand_id] = repair_seconds
                costs.tokens[cand_id] = repair_tokens
                costs.replay[cand_id] = repair_replay
            else:
                # The call was made and paid for but yielded nothing to
                # run, so no later iteration will record it.
                self._record_attempt(
                    cands.candidate_models.get(cand_id, cand_id),
                    year, day, part, Outcome.NO_CANDIDATE,
                    stage="repair",
                    draft_index=_draft_index(cand_id),
                    expected=oracle.known_answer,
                    repair_iteration=iteration + 1,
                    wall_clock_seconds=repair_seconds,
                    input_tokens=repair_tokens.get("input_tokens", 0),
                    output_tokens=repair_tokens.get("output_tokens", 0),
                    prompt=repair_replay[0],
                    raw_response=repair_replay[1],
                    error=repair_error or "repair returned the code unchanged",
                )
        return improved_candidates

    async def _try_fallback_models(
        self, cands: "_Candidates", prep: "_Prep", year: int, day: int, part: int,
        oracle: _Oracle,
    ) -> Optional[str]:
        """Draft once with each model outside the primary set, when enable_fallback_models."""
        fallback_models = [
            name for name in self.models.keys()
            if name not in prep.primary_models
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

                    solution: str = await model.generate_solution(
                        prep.parsed_problem,
                        year,
                        day,
                        strategies=prep.strategies,
                        strategy_effectiveness=prep.effectiveness
                    )

                    # Same verifier as the primary path. This branch used to
                    # carry its own copy of the acceptance check, which was
                    # never updated when the ground-truth oracle landed -- so
                    # a fallback model could return a wrong answer as the
                    # solution even when the accepted answer was known.
                    verdict = await self._verify_candidate(
                        model_name, solution, year, day, part,
                        oracle.test_cases, oracle.known_answer,
                    )
                    fb_tokens = getattr(
                        model, "last_token_usage", {"input_tokens": 0, "output_tokens": 0}
                    )
                    self._record_attempt(
                        model_name, year, day, part, verdict.outcome,
                        stage="fallback",
                        draft_index=0,
                        verdict=verdict,
                        answer=verdict.answer,
                        expected=oracle.known_answer,
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
                        problem_type=prep.problem_type,
                        response_time=cands.generation_times.get(model_name, 0.0),
                    )

                    if verdict.accepted:
                        logging.info(f"Fallback model {model_name} produced valid solution!")
                        self._record_solution(year, day, part, model_name, solution)
                        return solution
                    else:
                        logging.info(f"Fallback model {model_name} failed execution validation")

                except Exception as e:
                    logging.warning(f"Fallback model {model_name} failed: {str(e)}")
                    continue
        return None
