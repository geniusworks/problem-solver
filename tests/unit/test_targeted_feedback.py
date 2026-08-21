"""Failure-specific repair feedback: right message per failure mode, gated.

The default repair message for a timed-out run says the answer was not
accepted, which does not tell the model that the problem is SPEED -- so it
resubmits the same too-slow approach. 2024 d15 p2 and 2025 d9 p2 resisted 11
and 10 configurations that way, and temperature did not help
(dev/progress/temperature-diversity-negative.md).

Gated by SolverConfig.targeted_feedback so it can be A/B'd: a behaviour
change outside fingerprint() would let two different experiments share a hash.
"""

import types

import pytest

import shared.solver as solver_module
from shared.experiment.config import SolverConfig


def _solver(**config_kwargs) -> solver_module.BaseSolver:
    s = solver_module.BaseSolver.__new__(solver_module.BaseSolver)
    s.config = SolverConfig(name="t", **config_kwargs)
    return s


def _result(error=None, output=""):
    return types.SimpleNamespace(error=error, output=output)


TIMEOUT = _result(error="Solution timed out after 60 seconds")
CRASH = _result(error="IndexError: list index out of range")


class TestTimeoutDetection:
    def test_recognises_both_execution_paths(self):
        assert solver_module._is_timeout_error("Solution timed out after 60 seconds")
        assert solver_module._is_timeout_error("Execution timed out after 5 seconds")

    def test_does_not_fire_on_ordinary_errors(self):
        assert not solver_module._is_timeout_error("IndexError: list index out of range")
        assert not solver_module._is_timeout_error("")


class TestFeedbackGating:
    def test_disabled_by_default_keeps_the_old_message(self):
        fb = _solver()._build_execution_feedback("m", [], [], TIMEOUT, None)
        assert "timed out" in fb
        assert "PERFORMANCE failure" not in fb
        assert "asymptotically faster" not in fb

    def test_enabled_adds_guidance_on_timeout(self):
        fb = _solver(targeted_feedback=True)._build_execution_feedback(
            "m", [], [], TIMEOUT, None
        )
        assert "PERFORMANCE failure" in fb
        assert "asymptotically faster" in fb
        assert "Do NOT resubmit the same algorithm" in fb

    def test_enabled_does_NOT_fire_on_a_crash(self):
        """A crash is a correctness bug; efficiency advice would misdirect repair."""
        fb = _solver(targeted_feedback=True)._build_execution_feedback(
            "m", [], [], CRASH, None
        )
        assert "IndexError" in fb
        assert "PERFORMANCE failure" not in fb

    def test_enabled_does_NOT_fire_on_a_wrong_answer(self):
        fb = _solver(targeted_feedback=True)._build_execution_feedback(
            "m", [], [], _result(output="123"), "123"
        )
        assert "PERFORMANCE failure" not in fb

    def test_notes_when_examples_passed(self):
        """Examples pass + full input times out is the classic scaling signature."""
        case = types.SimpleNamespace(expected_output="7")
        fb = _solver(targeted_feedback=True)._build_execution_feedback(
            "m", [case], [_result(output="7")], TIMEOUT, None
        )
        assert "CORRECT on the small example but does not scale" in fb

    def test_omits_the_scaling_note_when_examples_also_failed(self):
        case = types.SimpleNamespace(expected_output="7")
        fb = _solver(targeted_feedback=True)._build_execution_feedback(
            "m", [case], [_result(error="boom")], TIMEOUT, None
        )
        assert "PERFORMANCE failure" in fb
        assert "does not scale" not in fb


class TestConfigIsHonest:
    def test_the_flag_changes_the_fingerprint(self):
        """Behaviour-affecting fields must enter fingerprint() (Milestone B)."""
        off = SolverConfig(name="x", targeted_feedback=False)
        on = SolverConfig(name="x", targeted_feedback=True)
        assert off.fingerprint() != on.fingerprint()

    def test_default_is_the_historical_behaviour(self):
        assert SolverConfig(name="x").targeted_feedback is False


class TestWrongAnswerGuidance:
    """The dominant real failure mode: code runs cleanly and computes the wrong thing.

    Across the two hardest recorded problems, 80 of 132 attempts were wrong
    answers and NONE was a timeout -- which is why the first version of this
    feature, which only handled timeouts, was inert on them
    (dev/progress/CORRECTION-d15p2-is-not-a-wall.md).
    """

    WRONG = _result(output="99999")

    def test_disabled_by_default(self):
        fb = _solver()._build_execution_feedback("m", [], [], self.WRONG, "99999")
        assert "still not accepted" in fb
        assert "INCORRECT" not in fb

    def test_enabled_echoes_what_the_model_produced(self):
        fb = _solver(targeted_feedback=True)._build_execution_feedback(
            "m", [], [], self.WRONG, "99999"
        )
        assert "produced: 99999" in fb
        assert "INCORRECT" in fb
        assert "Do NOT make a cosmetic edit" in fb

    def test_does_not_fire_on_timeout_path(self):
        """A timeout gets efficiency guidance, not wrong-answer guidance."""
        fb = _solver(targeted_feedback=True)._build_execution_feedback(
            "m", [], [], TIMEOUT, None
        )
        assert "PERFORMANCE failure" in fb
        assert "cosmetic edit" not in fb

    def test_never_leaks_the_expected_answer(self):
        """Structural guarantee: the oracle answer is not passed to this function.

        Handing the model its target would make the overfit gate the only thing
        between us and a hardcoded 'solution', and would invalidate every
        measurement taken with the flag on.
        """
        import inspect
        sig = inspect.signature(
            solver_module.BaseSolver._build_execution_feedback
        ).parameters
        assert "expected" not in sig and "known_answer" not in sig
        fb = _solver(targeted_feedback=True)._build_execution_feedback(
            "m", [], [], self.WRONG, "99999"
        )
        assert "1597035" not in fb  # a real accepted answer, for illustration
