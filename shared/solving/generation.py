"""Draw the candidate pool: each primary model's drafts, self-consistency samples included.

Moved out of shared/solver.py unchanged (2026-11-12).
"""

import logging
from datetime import datetime
from typing import TYPE_CHECKING, Any, Callable, Dict

from shared.experiment import Outcome, SolverConfig
from shared.solving.candidates import _last_exchange
from shared.solving.state import _Candidates, _Prep

if TYPE_CHECKING:
    from shared.llm.local import OllamaProvider


class GenerationMixin:
    """The generation stage, as BaseSolver uses it."""

    config: SolverConfig
    models: Dict[str, "OllamaProvider"]
    # Defined on BaseSolver.
    _record_attempt: Callable[..., Any]
    _record_model_performance: Callable[..., None]

    async def _generate_candidates(
        self, prep: _Prep, year: int, day: int, part: int
    ) -> _Candidates:
        """Draw the candidate pool. Self-consistency fans out samples here.

        Each draw is independent -- a sample that raises records its own
        no-candidate failure and does not abort the rest. The pool is keyed by
        candidate id; candidate_models maps each back to the producing model,
        which is what the learning DB and ledger record against.
        """
        cands = _Candidates()
        logging.info("")
        logging.info(
            f"Attempting solution with top {len(prep.primary_models)} primary model(s)"
        )

        for model_name in prep.primary_models:
            if model_name not in self.models:
                logging.warning(f"Model {model_name} not available, skipping")
                continue

            model = self.models[model_name]
            for sample_idx in range(self.config.samples_per_model):
                cand_id = (
                    model_name if self.config.samples_per_model == 1
                    else f"{model_name}#s{sample_idx}"
                )
                cands.candidate_models[cand_id] = model_name
                try:
                    logging.info("")
                    logging.info(f"Trying primary model: {cand_id}")
                    logging.info("")

                    start_time = datetime.now()
                    solution = await model.generate_solution(
                        prep.parsed_problem,
                        year,
                        day,
                        strategies=prep.strategies,
                        strategy_effectiveness=prep.effectiveness,
                    )
                    cands.generation_times[cand_id] = (
                        datetime.now() - start_time
                    ).total_seconds()
                    # Token usage the model just reported (analysis + impl calls),
                    # so the attempt records real cost, not a zero.
                    cands.generation_tokens[cand_id] = getattr(
                        model, "last_token_usage", {"input_tokens": 0, "output_tokens": 0}
                    )
                    cands.generation_replay[cand_id] = _last_exchange(model)
                    # Every candidate enters the pool; correctness is decided by
                    # execution against the oracle further down.
                    cands.answers[cand_id] = solution

                except Exception as e:
                    cands.failures.append((cand_id, str(e)))
                    # A candidate that never produced usable code is a distinct,
                    # real (verified) failure to record; it still spent tokens.
                    tokens = getattr(
                        model, "last_token_usage", {"input_tokens": 0, "output_tokens": 0}
                    )
                    prompt, raw_response = _last_exchange(model)
                    self._record_attempt(
                        model_name, year, day, part, Outcome.NO_CANDIDATE,
                        stage="generate",
                        draft_index=sample_idx,
                        error=f"{type(e).__name__}: {e}",
                        prompt=prompt,
                        raw_response=raw_response,
                        input_tokens=tokens.get("input_tokens", 0),
                        output_tokens=tokens.get("output_tokens", 0),
                    )
                    self._record_model_performance(
                        model_name, success=False, problem_type=prep.problem_type
                    )

        return cands
