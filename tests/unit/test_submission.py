"""The AoC answer submitter, with the network replaced.

`submission/` is not yet called by the solve loop; these tests cover what wiring
it for a live year relies on: reading AoC's response, honouring its wait, keeping
that wait across restarts, and never posting when submission is off.
"""

import asyncio

import pytest

from shared.errors import SessionError
from submission import manager as manager_module
from submission import validator as validator_module
from submission.manager import SubmissionManager, SubmissionResult
from submission.validator import SolutionValidator


def article(text):
    return f"<html><body><main><article><p>{text}</p></article></main></body></html>"


@pytest.fixture
def validator(tmp_path):
    return SolutionValidator(workspace_dir=tmp_path)


@pytest.mark.parametrize("message,seconds", [
    ("You have 30s left to wait.", 30),
    ("You have 5m 30s left to wait.", 330),
    ("Please wait one minute.", 0),
])
def test_wait_time_is_parsed_from_the_message(validator, message, seconds):
    assert validator._parse_wait_time(message) == seconds


@pytest.mark.parametrize("message,correct,cooldown,error_has", [
    ("That's the right answer! You are one gold star closer.", True, None, None),
    ("You gave an answer too recently; you have to wait after submitting an answer "
     "before trying again. You have 41s left to wait.", False, 41, "Rate limited"),
    ("That's not the right answer; your answer is too high.", False, 60, "too high"),
    ("That's not the right answer; your answer is too low.", False, 60, "too low"),
    ("You don't seem to be solving the right level. Did you already complete it?",
     False, None, "Wrong level"),
    ("Something new.", False, None, "Unknown response"),
])
def test_response_pages_are_classified(validator, message, correct, cooldown, error_has):
    result = asyncio.run(validator._parse_submission_response(article(message)))

    assert result.was_correct is correct
    assert result.cooldown_seconds == cooldown
    if error_has is None:
        assert result.error_message is None
    else:
        assert error_has in result.error_message


def test_cooldown_blocks_then_releases(tmp_path, monkeypatch):
    clock = [manager_module.datetime(2026, 12, 1, 5, 0, 0)]

    class FrozenDatetime(manager_module.datetime):
        @classmethod
        def now(cls, tz=None):
            return clock[0]

    monkeypatch.setattr(manager_module, "datetime", FrozenDatetime)
    manager = SubmissionManager(tmp_path)
    assert manager.can_submit(2026, 1, 1) == (True, None)

    manager.record_submission(2026, 1, 1, SubmissionResult(False, 60, "wrong"))
    assert manager.can_submit(2026, 1, 1) == (False, 60)
    assert manager.can_submit(2026, 1, 2) == (True, None)

    clock[0] += manager_module.timedelta(seconds=61)
    assert manager.can_submit(2026, 1, 1) == (True, None)


def test_cooldown_survives_a_restart(tmp_path):
    SubmissionManager(tmp_path).record_submission(2026, 1, 1, SubmissionResult(False, 300, "wrong"))

    allowed, wait = SubmissionManager(tmp_path).can_submit(2026, 1, 1)

    assert allowed is False and 0 < wait <= 300


class FakeResponse:
    def __init__(self, status, html):
        self.status, self._html = status, html

    async def text(self):
        return self._html

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False


class FakeSession:
    """Stands in for aiohttp.ClientSession and records each POST."""

    posts = []
    reply = (200, "")

    def __init__(self, cookies=None):
        self.cookies = cookies

    def post(self, url, data=None):
        FakeSession.posts.append((url, data))
        return FakeResponse(*FakeSession.reply)

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False


@pytest.fixture
def offline(monkeypatch):
    """No previous answer on the page, a dummy cookie, and a fake HTTP session."""
    FakeSession.posts = []
    FakeSession.reply = (200, article("That's the right answer!"))

    async def no_previous_answer(self, year, day, part):
        return None

    monkeypatch.setattr(SolutionValidator, "get_previous_answer", no_previous_answer)
    monkeypatch.setattr(validator_module, "get_session_cookie", lambda: "dummy")
    monkeypatch.setattr(validator_module.aiohttp, "ClientSession", FakeSession)
    return FakeSession


def test_nothing_is_posted_while_submission_is_off(validator, offline, monkeypatch):
    monkeypatch.setattr(validator_module, "SUBMIT_SOLUTIONS", False)

    result = asyncio.run(validator.submit_and_validate(2026, 1, 1, "6"))

    assert result.was_correct is False and "disabled" in result.error_message
    assert offline.posts == []


def test_an_already_solved_part_is_compared_not_posted(validator, offline, monkeypatch):
    monkeypatch.setattr(validator_module, "SUBMIT_SOLUTIONS", True)

    async def previous(self, year, day, part):
        return "6"

    monkeypatch.setattr(SolutionValidator, "get_previous_answer", previous)

    assert asyncio.run(validator.submit_and_validate(2026, 1, 1, "6")).was_correct is True
    assert asyncio.run(validator.submit_and_validate(2026, 1, 1, "7")).was_correct is False
    assert offline.posts == []


def test_a_correct_answer_is_posted_once_and_recorded(validator, offline, monkeypatch):
    monkeypatch.setattr(validator_module, "SUBMIT_SOLUTIONS", True)

    result = asyncio.run(validator.submit_and_validate(2026, 1, 2, "6"))

    assert result.was_correct is True
    assert offline.posts == [("https://adventofcode.com/2026/day/1/answer",
                              {"level": "2", "answer": "6"})]
    assert "2026/1/2" in validator.submission_manager.last_submission


def test_a_wrong_answer_blocks_the_next_post(validator, offline, monkeypatch):
    monkeypatch.setattr(validator_module, "SUBMIT_SOLUTIONS", True)
    offline.reply = (200, article("That's not the right answer; your answer is too low."))

    first = asyncio.run(validator.submit_and_validate(2026, 1, 1, "5"))
    second = asyncio.run(validator.submit_and_validate(2026, 1, 1, "7"))

    assert first.was_correct is False and first.cooldown_seconds == 60
    assert second.was_correct is False and "Rate limited" in second.error_message
    assert len(offline.posts) == 1


def test_an_expired_session_raises_session_error(validator, offline, monkeypatch):
    monkeypatch.setattr(validator_module, "SUBMIT_SOLUTIONS", True)
    offline.reply = (401, "")

    with pytest.raises(SessionError):
        asyncio.run(validator.submit_and_validate(2026, 1, 1, "6"))
