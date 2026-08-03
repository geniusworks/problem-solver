import pytest

from shared.experiment import SolverConfig
from shared.solver import BaseSolver


def _make_solver() -> BaseSolver:
    # Create a BaseSolver instance without running __init__, which would probe
    # Ollama. Consensus reads the threshold from the config, so attach one.
    solver = BaseSolver.__new__(BaseSolver)  # type: ignore[arg-type]
    solver.config = SolverConfig()  # type: ignore[attr-defined]
    return solver


def test_weighted_consensus_no_answers_returns_none():
    solver = _make_solver()
    result = solver._get_weighted_consensus_answer({})
    assert result is None


def test_weighted_consensus_single_answer_always_selected():
    solver = _make_solver()
    weighted_answers = {"model-a": ("42", 0.1)}
    result = solver._get_weighted_consensus_answer(weighted_answers)
    assert result == "42"


def test_weighted_consensus_prefers_higher_weight_answer():
    solver = _make_solver()
    weighted_answers = {
        "model-a": ("42", 0.7),
        "model-b": ("13", 0.3),
    }
    result = solver._get_weighted_consensus_answer(weighted_answers)
    assert result == "42"


def test_weighted_consensus_requires_sixty_percent_threshold():
    solver = _make_solver()
    weighted_answers = {
        "model-a": ("42", 0.5),
        "model-b": ("13", 0.5),
    }
    result = solver._get_weighted_consensus_answer(weighted_answers)
    assert result is None


def test_weighted_consensus_groups_identical_answers_by_weight():
    solver = _make_solver()
    weighted_answers = {
        "model-a": ("42", 0.3),
        "model-b": ("42", 0.3),
        "model-c": ("13", 0.4),
    }
    # 42 has total weight 0.6, 13 has 0.4 => 42 should win
    result = solver._get_weighted_consensus_answer(weighted_answers)
    assert result == "42"


def test_all_zero_weights_does_not_raise():
    """Quality analysis returns 0.0 for every candidate when the generated code
    is unparseable. Dividing by the total then raised ZeroDivisionError and
    aborted the entire solve, turning a recoverable bad-candidate case into a
    hard failure. Found by the first live run against Ollama."""
    solver = _make_solver()

    result = solver._get_weighted_consensus_answer(
        {"model-a": ("code-a", 0.0), "model-b": ("code-b", 0.0)}
    )

    assert result is None


def test_threshold_comes_from_config():
    solver = BaseSolver.__new__(BaseSolver)  # type: ignore[arg-type]
    solver.config = SolverConfig(consensus_threshold=0.9)  # type: ignore[attr-defined]

    # 2 of 3 weight = 0.67, below a 0.9 threshold
    result = solver._get_weighted_consensus_answer(
        {"a": ("x", 1.0), "b": ("x", 1.0), "c": ("y", 1.0)}
    )

    assert result is None
