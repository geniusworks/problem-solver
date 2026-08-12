"""Answer-based consensus: the no-oracle candidate selector.

With a ground-truth oracle, any validated candidate already produced the accepted
answer, so quality breaks the tie. Without one (the submission-phase case), the
solver groups candidates by their *executed* answer and prefers the plurality.
The samp3 A/B data showed this picks the correct answer 10 of 11 times; the miss
is two wrong candidates agreeing, which is why a quorum is required before
consensus overrides quality.
"""

import pytest

from shared.solver import BaseSolver
from shared.experiment import SolverConfig


@pytest.fixture
def solver(tmp_path, monkeypatch):
    # No real models needed to exercise the pure selector.
    monkeypatch.setattr(BaseSolver, "_resolve_available_models", lambda self: [])
    return BaseSolver(tmp_path, config=SolverConfig())


class TestSelectCandidate:
    def test_oracle_picks_highest_quality(self, solver):
        # Both already match the accepted answer, so quality decides.
        validated = [("a", "codeA", "111"), ("b", "codeB", "111")]
        quality = {"a": 0.2, "b": 0.9}
        assert solver._select_candidate(validated, quality, known_answer="111") == ("b", "codeB")

    def test_no_oracle_prefers_the_plurality_answer(self, solver):
        # Two candidates agree on 42, one on 99. Consensus takes a 42 candidate
        # even though the lone 99 candidate scores higher on quality.
        validated = [("a", "cA", "42"), ("b", "cB", "42"), ("c", "cC", "99")]
        quality = {"a": 0.1, "b": 0.2, "c": 0.9}
        cand, code = solver._select_candidate(validated, quality, known_answer=None)
        # Best-quality within the winning (42) group is b.
        assert (cand, code) == ("b", "cB")

    def test_no_oracle_without_quorum_falls_back_to_quality(self, solver):
        # All answers distinct -> none reaches min_consensus_models (2) -> quality.
        validated = [("a", "cA", "1"), ("b", "cB", "2"), ("c", "cC", "3")]
        quality = {"a": 0.1, "b": 0.9, "c": 0.5}
        assert solver._select_candidate(validated, quality, known_answer=None) == ("b", "cB")

    def test_no_oracle_consensus_can_pick_a_wrong_answer(self, solver):
        # The inherent failure mode (the samp3 day02p1 miss): two wrong candidates
        # agree on 1000 and outvote the single correct 421.
        validated = [("a", "cA", "1000"), ("b", "cB", "1000"), ("c", "cC", "421")]
        quality = {"a": 0.1, "b": 0.1, "c": 0.9}
        _, code = solver._select_candidate(validated, quality, known_answer=None)
        assert code in ("cA", "cB")

    def test_no_oracle_ignores_candidates_without_an_answer(self, solver):
        # A candidate that produced no answer casts no vote.
        validated = [("a", "cA", "42"), ("b", "cB", None), ("c", "cC", "42")]
        quality = {"a": 0.5, "b": 0.9, "c": 0.4}
        cand, _ = solver._select_candidate(validated, quality, known_answer=None)
        assert cand in ("a", "c")
