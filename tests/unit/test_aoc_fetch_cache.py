"""Fetching and caching AoC pages, with the network replaced by canned pages.

The cache is what keeps the project a good citizen of adventofcode.com and what
feeds the oracle its accepted answers. A live year (AoC 2026) starts from an
empty cache and a page with no answers, so both paths are covered.
"""

import asyncio
import json

import pytest

from shared import aoc, config
from shared.ground_truth import get_known_answer

YEAR, DAY = 2099, 1

PART_ONE = ('<article class="day-desc"><h2>--- Day 1: Test ---</h2>'
            '<p>Add the numbers.</p><pre><code>1\n2\n3\n</code></pre>'
            '<p>In this example the total is <code><em>6</em></code>.</p></article>')
PART_TWO = ('<article class="day-desc"><h2 id="part2">--- Part Two ---</h2>'
            '<p>Multiply them instead.</p></article>')


def page(*articles, answers=()):
    body = []
    for i, article in enumerate(articles):
        body.append(article)
        if i < len(answers):
            body.append(f"<p>Your puzzle answer was <code>{answers[i]}</code>.</p>")
    return "<html><body><main>" + "".join(body) + "</main></body></html>"


UNSOLVED = page(PART_ONE)
SOLVED = page(PART_ONE, PART_TWO, answers=("6", "6"))


@pytest.fixture
def base(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "BASE_DIR", tmp_path)
    return tmp_path / "years" / str(YEAR) / f"day{DAY:02d}"


@pytest.fixture
def network(monkeypatch):
    """Serve canned responses by URL and record every request made."""
    responses, calls = {}, []

    async def fake_request(url, timeout=30):
        calls.append(url)
        if url not in responses:
            raise AssertionError(f"unexpected request to {url}")
        return responses[url]

    monkeypatch.setattr(aoc, "make_request", fake_request)
    return responses, calls


def problem_url():
    return f"{config.AOC_BASE_URL}/{YEAR}/day/{DAY}"


@pytest.mark.parametrize("html,expected", [
    (UNSOLVED, (aoc.ProblemState.INITIAL, None, None)),
    (page(PART_ONE, PART_TWO, answers=("6",)), (aoc.ProblemState.PART1_SOLVED, "6", None)),
    (SOLVED, (aoc.ProblemState.COMPLETE, "6", "6")),
])
def test_problem_state_is_read_from_the_accepted_answers(html, expected):
    from bs4 import BeautifulSoup

    assert asyncio.run(aoc._get_problem_state(BeautifulSoup(html, "html.parser"))) == expected


def test_first_fetch_caches_the_page_and_its_answers(base, network):
    responses, calls = network
    responses[problem_url()] = SOLVED

    text, _, answer = asyncio.run(aoc.fetch_problem_text(YEAR, DAY, 2))

    assert "Part Two" in text and "Day 1" not in text
    assert answer == "6"
    assert (base / config.HTML_FILE).read_text() == SOLVED
    assert json.loads((base / config.META_FILE).read_text())["state"] == "COMPLETE"
    assert get_known_answer(YEAR, DAY, 1) == "6"
    assert get_known_answer(YEAR, DAY, 2) == "6"
    assert calls == [problem_url()]


def test_cached_page_is_not_fetched_again(base, network):
    responses, calls = network
    responses[problem_url()] = SOLVED
    asyncio.run(aoc.fetch_problem_text(YEAR, DAY, 1))

    text, _, answer = asyncio.run(aoc.fetch_problem_text(YEAR, DAY, 1))

    assert "Day 1" in text and answer == "6"
    assert calls == [problem_url()]


def test_unsolved_live_day_has_no_answer_and_no_ground_truth(base, network):
    responses, _ = network
    responses[problem_url()] = UNSOLVED

    text, _, answer = asyncio.run(aoc.fetch_problem_text(YEAR, DAY, 1))

    assert "Day 1" in text and answer is None
    assert not (base / config.ANSWERS_FILE).exists()
    assert get_known_answer(YEAR, DAY, 1) is None


def test_input_is_fetched_once_then_reused(base, network):
    responses, calls = network
    responses[problem_url()] = UNSOLVED
    responses[problem_url() + "/input"] = "1\n2\n3\n"

    asyncio.run(aoc.ensure_problem_files(YEAR, DAY))
    assert (base / config.INPUT_FILE).read_text() == "1\n2\n3"
    assert calls.count(problem_url() + "/input") == 1

    asyncio.run(aoc.ensure_problem_files(YEAR, DAY))
    assert calls.count(problem_url() + "/input") == 1
    assert calls.count(problem_url()) == 1
