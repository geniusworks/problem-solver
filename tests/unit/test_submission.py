"""The submission step of the AoC 2026 registration, with the network replaced.

What it must guarantee (dev/progress/aoc2026-registration.md, "Submitting"): candidates
pooled and ranked; at most N wrong per part and M per night; never the same answer twice;
never inside a stated wait; "too high"/"too low" only prune; nothing posted after an
acceptance; a stop on any unrecognised reply; nothing posted when switched off or from
the maintainer's account; and all of it kept across restarts.
"""

import asyncio
from datetime import datetime, timedelta, timezone

import pytest

from shared import config
from shared.errors import SessionError, SubmissionError
from shared.experiment.rescore import rescore
from shared.experiment.results import AttemptRecord, ExperimentResult, Outcome, ProblemResult
from shared.ground_truth import get_known_answer, save_known_answers
from submission import client, step
from submission.policy import Budget, PartState, SubmissionState, decide, rank_candidates
from submission.replies import ReplyKind, parse_reply

PROBLEM = "2026_day01_part1"
START = datetime(2026, 12, 1, 10, 0, tzinfo=timezone.utc)


def page(text):
    return f"<html><body><main><article><p>{text}</p></article></main></body></html>"


ACCEPTED = page("That's the right answer! You are one gold star closer to finding the chief.")
TOO_HIGH = page("That's not the right answer; your answer is too high. If you're stuck, make sure "
                "you're using the full input data. Please wait one minute before trying again.")
TOO_LOW = page("That's not the right answer; your answer is too low. Please wait one minute "
               "before trying again.")
WRONG = page("That's not the right answer. If you're stuck, make sure you're using the full "
             "input data. Please wait one minute before trying again.")
UNFAMILIAR = page("Something AoC has never said before.")


# -- replies ------------------------------------------------------------------

@pytest.mark.parametrize("html,kind,wait", [
    (ACCEPTED, ReplyKind.ACCEPTED, None),
    (TOO_HIGH, ReplyKind.TOO_HIGH, 60),
    (TOO_LOW, ReplyKind.TOO_LOW, 60),
    (WRONG, ReplyKind.WRONG, 60),
    (page("That's not the right answer. Because you have guessed incorrectly 4 times on this "
          "puzzle, please wait 5 minutes before trying again."), ReplyKind.WRONG, 300),
    (page("You gave an answer too recently; you have to wait after submitting an answer before "
          "trying again. You have 1m 30s left to wait."), ReplyKind.TOO_RECENT, 90),
    (page("You gave an answer too recently. You have 41s left to wait."), ReplyKind.TOO_RECENT, 41),
    (page("You don't seem to be solving the right level. Did you already complete it?"),
     ReplyKind.WRONG_LEVEL, None),
    # A wrong answer always states its wait; one without is unfamiliar.
    (page("That's not the right answer."), ReplyKind.UNKNOWN, None),
    (UNFAMILIAR, ReplyKind.UNKNOWN, None),
])
def test_replies_are_classified_with_their_wait(html, kind, wait):
    reply = parse_reply(html)
    assert (reply.kind, reply.wait_seconds) == (kind, wait)


# -- candidates ---------------------------------------------------------------

def attempt(answer, outcome=Outcome.UNVERIFIED, passed=None, total=None, model="m", code=None):
    return AttemptRecord(model=model, problem_id=PROBLEM, config_fingerprint="f",
                         outcome=outcome, answer=answer, examples_passed=passed,
                         examples_total=total, code=code)


def trial(*attempts, problem=PROBLEM, outcome=Outcome.UNVERIFIED, answer=None, number=0):
    day, part = int(problem[8:10]), int(problem[-1])
    return ProblemResult(problem_id=problem, year=2026, day=day, part=part,
                         config_fingerprint="f", outcome=outcome, answer=answer,
                         trial=number, attempts=list(attempts))


def experiment(*trials):
    return ExperimentResult(config_name="c", config_fingerprint="f", config={},
                            results=list(trials))


def test_candidates_are_pooled_deduplicated_and_ranked():
    runs = [
        experiment(trial(attempt("10", passed=1, total=1), attempt("20", passed=1, total=1)),
                   trial(attempt("20", passed=1, total=1), attempt("20 "), number=1)),
        experiment(trial(attempt("30"), attempt("40", passed=0, total=1)),
                   trial(attempt("crashed", outcome=Outcome.ERROR), attempt("two words"),
                         attempt("20"), number=1)),
        experiment(trial(attempt("99"), problem="2026_day01_part2")),
    ]

    ranked = rank_candidates(runs, PROBLEM)

    # passed the examples (20 in three trials, then 10), then unchecked, then failed
    assert [(c.answer, c.trials) for c in ranked] == [("20", 3), ("10", 1), ("30", 1), ("40", 1)]


def test_a_part_not_reached_offers_no_candidates():
    runs = [experiment(trial(attempt("5"), outcome=Outcome.NOT_REACHED))]
    assert rank_candidates(runs, PROBLEM) == []


# -- the policy ----------------------------------------------------------------

def candidates(*answers):
    return rank_candidates([experiment(trial(*[attempt(a) for a in answers]))], PROBLEM)


def submitted(state, problem, *replies, at=START):
    for answer, reply in replies:
        state.part(problem).submissions.append(
            {"answer": answer, "at": at.isoformat(), "reply": reply, "wait_seconds": 60})


def test_no_answer_is_posted_twice():
    state = SubmissionState()
    submitted(state, PROBLEM, ("1", "wrong"))
    assert decide(state, PROBLEM, candidates("1", "2"), Budget(), START).answer == "2"


def test_too_high_and_too_low_rule_candidates_out():
    state = SubmissionState(parts={PROBLEM: PartState(lower=10, upper=20)})
    decision = decide(state, PROBLEM, candidates("5", "25", "20", "10", "15"), Budget(), START)
    assert decision.answer == "15"


def test_the_wrong_answer_budget_is_per_part_over_the_event():
    state = SubmissionState()
    submitted(state, PROBLEM, ("1", "wrong"), ("2", "too_high"), ("3", "unknown"),
              at=START - timedelta(days=3))
    assert decide(state, PROBLEM, candidates("4"), Budget(), START).reason == "budget_spent"
    assert decide(state, "2026_day02_part1", candidates("4"), Budget(), START).answer == "4"


def test_the_night_cap_counts_every_part_in_its_window():
    state = SubmissionState()
    for day in range(1, 7):
        submitted(state, f"2026_day{day:02d}_part1", ("x", "wrong"), at=START - timedelta(hours=2))
    assert decide(state, PROBLEM, candidates("y"), Budget(), START).reason == "night_cap"
    assert decide(state, PROBLEM, candidates("y"), Budget(), START + timedelta(hours=19)).answer == "y"


def test_a_stated_wait_is_respected():
    state = SubmissionState(blocked_until=(START + timedelta(seconds=90)).isoformat())
    decision = decide(state, PROBLEM, candidates("1"), Budget(), START)
    assert decision.reason == "wait" and decision.wait_until == START + timedelta(seconds=90)


# -- the step -----------------------------------------------------------------

class Clock:
    def __init__(self):
        self.now = START
        self.slept = []

    def __call__(self):
        return self.now

    async def sleep(self, seconds):
        self.slept.append(seconds)
        self.now += timedelta(seconds=seconds)


class FakeAoC:
    """Answers posts from a script of reply pages, recording what was posted."""

    def __init__(self, *replies, raises=None):
        self.replies = list(replies)
        self.posted = []
        self.raises = raises

    async def __call__(self, year, day, part, answer):
        self.posted.append(answer)
        if self.raises:
            raise self.raises
        return self.replies.pop(0)


@pytest.fixture
def account(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "BASE_DIR", tmp_path)
    monkeypatch.setattr(config, "AOC_ACCOUNT", "experiment")
    return tmp_path / "accounts" / "experiment"


def run_step(runs, aoc, clock, enabled=True):
    return asyncio.run(step.submit_part(2026, 1, 1, runs, post=aoc, enabled=enabled,
                                        budget=Budget(), now=clock, sleep=clock.sleep))


def test_the_best_candidates_are_posted_until_one_is_accepted(account):
    runs = [experiment(trial(attempt("700", passed=1, total=1)),
                       trial(attempt("700", passed=1, total=1), attempt("800"), attempt("650"),
                             number=1))]
    aoc, clock = FakeAoC(TOO_HIGH, ACCEPTED), Clock()

    report = run_step(runs, aoc, clock)

    # 700 too high rules out 800; the wait (60 s and the 30 s margin) is slept through
    assert aoc.posted == ["700", "650"]
    assert clock.slept == [90]
    assert report.outcome == "accepted"
    assert get_known_answer(2026, 1, 1) == "650"
    assert (account / "years" / "2026" / "day01" / "answers.json").exists()

    again = FakeAoC()
    assert run_step(runs, again, Clock()).outcome == "accepted"
    assert again.posted == []


def test_switched_off_it_posts_nothing_and_says_what_it_would_post(account):
    aoc = FakeAoC()
    report = run_step([experiment(trial(attempt("5")))], aoc, Clock(), enabled=False)
    assert aoc.posted == [] and report.outcome == "disabled" and report.would_post == "5"


def test_the_maintainer_account_never_submits(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "BASE_DIR", tmp_path)
    monkeypatch.setattr(config, "AOC_ACCOUNT", "")
    aoc = FakeAoC(ACCEPTED)

    with pytest.raises(ValueError):
        run_step([experiment(trial(attempt("5")))], aoc, Clock())
    with pytest.raises(SubmissionError):
        asyncio.run(client.post_answer(2026, 1, 1, "5"))
    assert aoc.posted == []


def test_the_budget_holds_across_restarts(account):
    runs = [experiment(trial(*[attempt(str(n)) for n in range(1, 6)]))]
    clock = Clock()
    run_step(runs, FakeAoC(WRONG, WRONG, WRONG), clock)
    # the night's run is restarted: nothing more for this part, and never a repeat
    second = FakeAoC(WRONG)
    report = run_step(runs, second, clock)

    assert second.posted == []
    assert report.outcome == "budget_spent"
    answers = [s["answer"] for s in SubmissionState.load(step.state_path()).part(PROBLEM).submissions]
    assert answers == ["1", "2", "3"]


def test_an_unfamiliar_reply_stops_this_and_every_later_step(account):
    runs = [experiment(trial(attempt("1"), attempt("2")))]
    report = run_step(runs, FakeAoC(UNFAMILIAR), Clock())
    assert report.outcome == "halted"

    later = FakeAoC(ACCEPTED)
    assert run_step(runs, later, Clock()).outcome == "halted"
    assert later.posted == []


def test_a_post_whose_reply_was_lost_stops_everything(account):
    runs = [experiment(trial(attempt("1"), attempt("2")))]
    report = run_step(runs, FakeAoC(raises=OSError("connection reset")), Clock())
    assert report.outcome == "halted"

    state = SubmissionState.load(step.state_path())
    assert state.part(PROBLEM).submissions[0]["reply"] == "pending"
    later = FakeAoC(ACCEPTED)
    assert run_step(runs, later, Clock()).outcome == "halted" and later.posted == []


def test_a_long_wait_ends_the_step_for_the_night(account):
    SubmissionState(blocked_until=(START + timedelta(hours=1)).isoformat()).save(step.state_path())
    aoc, clock = FakeAoC(ACCEPTED), Clock()

    assert run_step([experiment(trial(attempt("1")))], aoc, clock).outcome == "waiting"
    assert aoc.posted == [] and clock.slept == []


def test_an_answer_already_on_the_page_is_never_posted_again(account):
    save_known_answers(2026, 1, {1: "42"})
    aoc = FakeAoC(ACCEPTED)
    assert run_step([experiment(trial(attempt("41")))], aoc, Clock()).outcome == "already_accepted"
    assert aoc.posted == []


# -- the client ------------------------------------------------------------------

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
    reply = (200, ACCEPTED)

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False

    def post(self, url, data=None, headers=None, allow_redirects=True, timeout=None):
        FakeSession.posts.append((url, data, headers["Cookie"], allow_redirects))
        return FakeResponse(*FakeSession.reply)


@pytest.fixture
def http(account, monkeypatch):
    FakeSession.posts = []
    monkeypatch.setenv("AOC_SESSION_EXPERIMENT", "experiment-cookie")
    monkeypatch.setattr(client.aiohttp, "ClientSession", FakeSession)
    return FakeSession


def test_one_post_as_the_account_without_following_redirects(http):
    assert asyncio.run(client.post_answer(2026, 3, 2, "6")) == ACCEPTED
    assert http.posts == [("https://adventofcode.com/2026/day/3/answer",
                           {"level": "2", "answer": "6"}, "session=experiment-cookie", False)]


@pytest.mark.parametrize("status", [302, 400, 401])
def test_a_refused_post_is_a_session_error(http, status):
    http.reply = (status, "")
    with pytest.raises(SessionError, match="AOC_SESSION_EXPERIMENT"):
        asyncio.run(client.post_answer(2026, 1, 1, "6"))


# -- scoring the recorded answers ------------------------------------------------

def test_recorded_answers_are_scored_once_one_is_accepted():
    hardcoded = "def solve():\n    return 123456\n\nprint(solve())\n"
    computed = "def solve():\n    return sum(range(10))\n\nprint(solve())\n"
    run = experiment(
        trial(attempt("123456", code=computed, model="a"), attempt("7", model="b"),
              attempt(None, outcome=Outcome.ERROR), answer="123456"),
        trial(attempt("123456", code=hardcoded), answer="123456", number=1),
    )

    assert rescore(run, 2026, 1, 1, "123456") == 5
    first, second = run.results
    assert [a.outcome for a in first.attempts] == [Outcome.SOLVED, Outcome.WRONG, Outcome.ERROR]
    assert first.outcome is Outcome.SOLVED and first.winning_model == "a"
    assert second.outcome is Outcome.OVERFIT
    assert run.solved == 1


def test_a_saved_result_loads_back_the_same(tmp_path):
    run = experiment(trial(attempt("5", passed=1, total=2), answer="5"))
    path = run.save(tmp_path / "r.json", include_replay=True)
    assert ExperimentResult.load(path).to_dict(True) == run.to_dict(True)


def test_a_trial_answer_is_its_last_printed_line_as_live():
    run = experiment(trial(attempt("parsing...\n123456", model="a"), answer="parsing...\n123456"))
    rescore(run, 2026, 1, 1, "123456")
    # the trial is read as the oracle reads it; the attempt as candidates.py compared it
    assert run.results[0].outcome is Outcome.SOLVED
    assert run.results[0].attempts[0].outcome is Outcome.WRONG
    assert [c.answer for c in rank_candidates([experiment(trial(attempt("note\n42")))], PROBLEM)] == ["42"]


def test_an_answer_that_drew_wrong_level_is_never_posted_again():
    state = SubmissionState()
    submitted(state, PROBLEM, ("1", "wrong_level"))
    assert decide(state, PROBLEM, candidates("1", "2"), Budget(), START).answer == "2"


def test_an_acceptance_lost_before_the_answer_cache_is_restored(account):
    state = SubmissionState(parts={PROBLEM: PartState(accepted="650")})
    state.save(step.state_path())
    assert run_step([experiment(trial(attempt("650")))], FakeAoC(), Clock()).outcome == "accepted"
    assert get_known_answer(2026, 1, 1) == "650"
