import pytest

from shared.solver import BaseSolver


def _make_solver() -> BaseSolver:
    # Create a BaseSolver instance without running __init__
    return BaseSolver.__new__(BaseSolver)  # type: ignore[arg-type]


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
