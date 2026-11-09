"""The worked examples' verdict is recorded beside the oracle's.

PLAN.md, "Beyond AoC", step 1: to measure how far the results depend on an
exact checker, every verified attempt records how many worked examples it
passed. These pin the cases that matter, including the two where the examples
and the oracle disagree.
"""

import asyncio

import pytest

from shared.execution import ExecutionResult, TestCase as Example
from shared.experiment import SolverConfig
from shared.experiment.results import Outcome
from shared.solver import BaseSolver

ACCEPTED = "6"
CASES = [Example(input_data="1", expected_output="1"), Example(input_data="2", expected_output="2")]
OK = ExecutionResult(output="1")
BAD = ExecutionResult(output="", error="expected 2, got 3")


@pytest.fixture
def solver(tmp_path, monkeypatch):
    monkeypatch.setattr(BaseSolver, "_resolve_available_models", lambda self: [])
    return BaseSolver(tmp_path, config=SolverConfig())


def verify(solver, monkeypatch, example_results, full_answer, cases=CASES, known=ACCEPTED):
    async def fake_test_solution(**kwargs):
        full = ExecutionResult(output=full_answer or "", error=None if full_answer else "timed out")
        return example_results, full, full_answer

    monkeypatch.setattr(solver.solution_executor, "test_solution", fake_test_solution)
    return asyncio.run(solver._verify_candidate("m", "code", 2099, 1, 1, cases, known))


def test_all_examples_pass_and_the_answer_is_accepted(solver, monkeypatch):
    verdict = verify(solver, monkeypatch, [OK, OK], ACCEPTED)
    assert (verdict.outcome, verdict.examples_passed, verdict.examples_total) == (Outcome.SOLVED, 2, 2)


def test_examples_reject_a_correct_answer(solver, monkeypatch):
    verdict = verify(solver, monkeypatch, [OK, BAD], ACCEPTED)
    assert (verdict.outcome, verdict.examples_passed, verdict.examples_total) == (Outcome.SOLVED, 1, 2)


def test_examples_accept_a_wrong_answer(solver, monkeypatch):
    verdict = verify(solver, monkeypatch, [OK, OK], "7")
    assert (verdict.outcome, verdict.examples_passed, verdict.examples_total) == (Outcome.WRONG, 2, 2)


def test_passed_the_examples_then_timed_out(solver, monkeypatch):
    verdict = verify(solver, monkeypatch, [OK, OK], None)
    assert (verdict.outcome, verdict.examples_passed, verdict.examples_total) == (Outcome.ERROR, 2, 2)


def test_validation_failure_counts_no_example_passed(solver, monkeypatch):
    rejected = ExecutionResult(output="", error="Validation failed before examples")
    verdict = verify(solver, monkeypatch, [rejected], None)
    assert (verdict.examples_passed, verdict.examples_total) == (0, 2)


def test_no_usable_example_is_zero_of_zero(solver, monkeypatch):
    verdict = verify(solver, monkeypatch, [], ACCEPTED, cases=[])
    assert (verdict.examples_passed, verdict.examples_total) == (0, 0)


def test_the_attempt_record_carries_the_example_verdict(solver, monkeypatch):
    verdict = verify(solver, monkeypatch, [OK, BAD], ACCEPTED)
    record = solver._record_attempt("m", 2099, 1, 1, verdict.outcome, verdict=verdict)
    assert (record.examples_passed, record.examples_total) == (1, 2)
    assert record.to_dict()["examples_passed"] == 1


def test_attempts_without_a_verdict_leave_it_unrecorded(solver):
    record = solver._record_attempt("m", 2099, 1, 1, Outcome.NO_CANDIDATE)
    assert (record.examples_passed, record.examples_total) == (None, None)
