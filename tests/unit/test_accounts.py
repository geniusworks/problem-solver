"""Each AoC account has its own workspace and session, and nothing falls back between them.

The AoC 2026 registration (dev/progress/aoc2026-registration.md) runs the harness as a
dedicated experiment account. That account has its own inputs, so its pages, inputs,
accepted answers and results live in accounts/<name>/, and its cookie in
AOC_SESSION_<NAME>; the maintainer's years/ and AOC_SESSION are never touched by it.
"""

import asyncio

import pytest

from shared import aoc, config, paths
from shared.errors import SessionError
from shared.experiment import environment
from shared.ground_truth import get_known_answer, save_known_answers

LOGGED_IN = (
    '<!DOCTYPE html><html><body><header><nav><ul>'
    '<li><a href="/2026/settings">[Settings]</a></li>'
    '<li><a href="/2026/auth/logout">[Log Out]</a></li></ul></nav>'
    '<div class="user">experiment <span class="star-count">2*</span></div></header>'
    '<main><article class="day-desc"><h2>--- Day 1 ---</h2></article></main></body></html>'
)
LOGGED_OUT = (
    '<!DOCTYPE html><html><body><header><nav><ul>'
    '<li><a href="/2026/auth/login">[Log In]</a></li></ul></nav></header>'
    '<main><article class="day-desc"><h2>--- Day 1 ---</h2></article></main></body></html>'
)


@pytest.fixture
def account(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "BASE_DIR", tmp_path)
    monkeypatch.setattr(config, "AOC_ACCOUNT", "experiment")
    monkeypatch.setenv("AOC_SESSION", "maintainer-cookie")
    monkeypatch.delenv("AOC_SESSION_EXPERIMENT", raising=False)
    return tmp_path


@pytest.fixture
def requests_made(monkeypatch):
    """Replace the one HTTP helper; serve `pages[url]` and record each request."""
    pages, made = {}, []

    async def fake_get(url, session_cookie, timeout=30):
        made.append((url, session_cookie))
        return pages[url]

    monkeypatch.setattr(aoc, "_get", fake_get)
    return pages, made


def test_the_maintainer_account_keeps_the_repository_layout(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "BASE_DIR", tmp_path)
    monkeypatch.setattr(config, "AOC_ACCOUNT", "")

    assert paths.get_problem_dir(2024, 1) == tmp_path / "years" / "2024" / "day01"
    assert config.aoc_session_variable() == "AOC_SESSION"


def test_another_account_has_its_own_tree_and_session_variable(account, monkeypatch):
    monkeypatch.setenv("AOC_SESSION_EXPERIMENT", "experiment-cookie")

    assert paths.account_dir() == account / "accounts" / "experiment"
    assert paths.get_problem_dir(2026, 3) == account / "accounts" / "experiment" / "years" / "2026" / "day03"
    assert config.aoc_session_variable() == "AOC_SESSION_EXPERIMENT"
    assert config.aoc_session() == "experiment-cookie"


def test_an_account_never_falls_back_to_the_maintainer_cookie(account, monkeypatch):
    monkeypatch.setattr("builtins.input", lambda *_: pytest.fail("an account is never prompted"))

    assert config.aoc_session() is None
    with pytest.raises(SessionError, match="AOC_SESSION_EXPERIMENT"):
        aoc.get_session_cookie()


def test_an_account_name_must_be_safe_in_a_path(account, monkeypatch):
    monkeypatch.setattr(config, "AOC_ACCOUNT", "../years")

    with pytest.raises(ValueError):
        paths.account_dir()


def test_accepted_answers_are_kept_per_account(account, monkeypatch):
    save_known_answers(2024, 1, {1: "account-answer"})
    monkeypatch.setattr(config, "AOC_ACCOUNT", "")

    assert get_known_answer(2024, 1, 1) is None
    assert (account / "accounts" / "experiment" / "years" / "2024" / "day01" / "answers.json").exists()


def test_results_record_the_account(account):
    assert environment.capture_environment([])["aoc_account"] == "experiment"


@pytest.mark.parametrize("html,expected", [
    (LOGGED_IN, True),
    (LOGGED_OUT, False),
    ("<!DOCTYPE html><html><body><main>no header</main></body></html>", False),
])
def test_the_logged_in_header_is_read_from_the_page(html, expected):
    assert aoc.logged_in(html) is expected


def test_a_fetch_is_one_request_with_the_account_cookie(account, monkeypatch, requests_made):
    monkeypatch.setenv("AOC_SESSION_EXPERIMENT", "experiment-cookie")
    pages, made = requests_made
    pages["https://adventofcode.com/2026/day/1"] = (200, LOGGED_IN)

    assert asyncio.run(aoc.make_request("https://adventofcode.com/2026/day/1")) == LOGGED_IN
    assert made == [("https://adventofcode.com/2026/day/1", "experiment-cookie")]


@pytest.mark.parametrize("reply", [(200, LOGGED_OUT), (400, "Puzzle inputs differ by user.")])
def test_a_logged_out_reply_raises_instead_of_being_cached(account, monkeypatch, requests_made, reply):
    monkeypatch.setenv("AOC_SESSION_EXPERIMENT", "experiment-cookie")
    pages, _ = requests_made
    pages["https://adventofcode.com/2026/day/1"] = reply

    with pytest.raises(SessionError, match="AOC_SESSION_EXPERIMENT"):
        asyncio.run(aoc.make_request("https://adventofcode.com/2026/day/1"))


def test_a_plain_text_input_is_returned_as_is(account, monkeypatch, requests_made):
    monkeypatch.setenv("AOC_SESSION_EXPERIMENT", "experiment-cookie")
    pages, _ = requests_made
    pages["https://adventofcode.com/2026/day/1/input"] = (200, "1 2\n3 4\n")

    assert asyncio.run(aoc.make_request("https://adventofcode.com/2026/day/1/input")) == "1 2\n3 4\n"


@pytest.mark.parametrize("page,ok", [((200, LOGGED_IN), True), ((200, LOGGED_OUT), False),
                                     ((500, ""), False)])
def test_the_session_check_is_one_request_to_the_calendar(account, monkeypatch, requests_made, page, ok):
    monkeypatch.setenv("AOC_SESSION_EXPERIMENT", "experiment-cookie")
    pages, made = requests_made
    pages["https://adventofcode.com/2026"] = page

    if ok:
        asyncio.run(aoc.check_session(2026))
    else:
        with pytest.raises(SessionError):
            asyncio.run(aoc.check_session(2026))
    assert [url for url, _ in made] == ["https://adventofcode.com/2026"]
