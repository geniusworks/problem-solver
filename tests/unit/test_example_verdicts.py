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


# -- No accepted answer cached: the AoC 2026 nightly (require_oracle=false) -----------------
#
# The registration scores every recorded answer once one is accepted, so an attempt must keep
# its full-input answer even when a worked example fails, and a part with no checkable example
# must still be attempted. With the default (require_oracle=true) neither happens.


def verify_unseen(solver, monkeypatch, example_results, full_answer):
    calls = {}

    async def fake_test_solution(**kwargs):
        calls.update(kwargs)
        return example_results, ExecutionResult(output=full_answer), full_answer

    monkeypatch.setattr(solver.solution_executor, "test_solution", fake_test_solution)
    verdict = asyncio.run(solver._verify_candidate("m", "code", 2099, 1, 1, CASES, None))
    return verdict, calls["force_full_input"]


@pytest.fixture
def unseen_solver(tmp_path, monkeypatch):
    monkeypatch.setattr(BaseSolver, "_resolve_available_models", lambda self: [])
    return BaseSolver(tmp_path, config=SolverConfig(require_oracle=False))


def test_without_an_oracle_a_failed_example_keeps_the_answer_unverified(unseen_solver, monkeypatch):
    verdict, forced = verify_unseen(unseen_solver, monkeypatch, [OK, BAD], "7")
    assert forced is True
    assert (verdict.accepted, verdict.outcome, verdict.answer) == (False, Outcome.UNVERIFIED, "7")
    assert (verdict.examples_passed, verdict.examples_total) == (1, 2)


def test_without_an_oracle_passing_examples_is_still_only_unverified(unseen_solver, monkeypatch):
    verdict, _ = verify_unseen(unseen_solver, monkeypatch, [OK, OK], "7")
    assert (verdict.accepted, verdict.outcome) == (True, Outcome.UNVERIFIED)


def test_by_default_a_failed_example_still_rejects_without_running_the_input(solver, monkeypatch):
    verdict, forced = verify_unseen(solver, monkeypatch, [OK, BAD], "7")
    assert forced is False
    assert (verdict.accepted, verdict.outcome) == (False, Outcome.WRONG)


def _no_oracle_run(solver, monkeypatch):
    from shared.solving.state import _Candidates, _Prep
    import shared.ground_truth

    monkeypatch.setattr(shared.ground_truth, "get_known_answer", lambda *a: None)
    reached = []

    async def repair_loop(*args):
        reached.append(args[-1])
        return "program"

    async def no_fallback(*args):
        return None

    monkeypatch.setattr(solver, "_repair_loop", repair_loop)
    monkeypatch.setattr(solver, "_try_fallback_models", no_fallback)
    monkeypatch.setattr(solver, "_print_consensus_summary", lambda *a: None)
    cands = _Candidates(answers={"m": "code"})
    solved = asyncio.run(solver._execute_and_repair(cands, {}, _Prep(), 2099, 1, 2))
    return solved, reached


def test_without_an_oracle_a_part_with_no_checkable_example_is_attempted(unseen_solver, monkeypatch):
    solved, reached = _no_oracle_run(unseen_solver, monkeypatch)
    assert solved == "program"
    assert len(reached) == 1 and reached[0].known_answer is None


def test_by_default_a_part_with_no_oracle_is_refused(solver, monkeypatch):
    solved, reached = _no_oracle_run(solver, monkeypatch)
    assert solved is None and reached == []
