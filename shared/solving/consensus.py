"""Source consensus among the drafts, and the default-off collaborative improvement.

Moved out of shared/solver.py unchanged (2026-11-12), except that the accepted answer and the
ledger write are reached through BaseSolver (_accepted_answer, _record_solution), so that the
module-level names in shared.solver stay the ones tests and dev/replay_solver.py replace.
"""

import logging
from typing import TYPE_CHECKING, Any, Callable, Dict, List, Optional, Tuple

from shared.solving.candidates import CandidateMixin
from shared.solving.state import _Candidates, _Prep

if TYPE_CHECKING:
    from shared.llm.local import OllamaProvider
    from learning import LearningDatabase
    from shared.quality.code_quality import CodeQualityAnalyzer

# The solver's logger, so log records keep the name they had before the move.
logger = logging.getLogger("shared.solver")


class ConsensusMixin(CandidateMixin):
    """The consensus stage, as BaseSolver uses it."""

    models: Dict[str, "OllamaProvider"]
    enable_collaborative_improvement: bool
    db: Optional["LearningDatabase"]
    learning_dir: Any
    # Defined on BaseSolver.
    _record_attempt: Callable[..., Any]
    _record_solution: Callable[..., None]
    _accepted_answer: Callable[..., Optional[str]]

    async def _reach_consensus(
        self, cands: "_Candidates", prep: "_Prep", year: int, day: int, part: int,
    ) -> Tuple[Optional[str], Dict[str, float]]:
        """Quality-weighted source consensus, then optional collaborative improvement.

        Returns (accepted solution or None, quality_scores). The scores are
        returned even when nothing is accepted here, because the execution
        stage reuses them to rank candidates.
        """
        answers = cands.answers
        parsed_problem = prep.parsed_problem
        reviewer_models = prep.reviewer_models
        # If we have answers, try to reach consensus
        consensus_answer: Optional[str] = None
        quality_scores: Dict[str, float] = {}
        analyzer: Optional["CodeQualityAnalyzer"] = None
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
                    self._accepted_answer(year, day, part),
                )
                self._record_attempt(
                    "consensus", year, day, part, consensus_verdict.outcome,
                    stage="consensus",
                    verdict=consensus_verdict,
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
                self._record_solution(
                    year, day, part, "consensus", consensus_answer
                )
                return consensus_answer, quality_scores

        # If no consensus, optionally try collaborative improvement
        if len(answers) > 0 and self.enable_collaborative_improvement:
            # answers is non-empty, so the quality pass above created the analyzer.
            assert analyzer is not None
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
                        self._accepted_answer(year, day, part),
                    )
                    if improved_verdict.accepted:
                        self._record_solution(
                            year, day, part,
                            improved_candidate.author or "collaborative",
                            improved_candidate.solution,
                        )
                        return improved_candidate.solution, quality_scores
            except Exception as e:
                logging.warning(f"Collaborative improvement failed: {str(e)}")

        return None, quality_scores

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
