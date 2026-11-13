"""The nightly run, with AoC, the fetcher and the trials replaced.

Covers the order the registration fixes (session check, one fetch, Part 1 trials,
submission step, Part 2 after an acceptance, summary), its refusals, and that a restarted
run resumes rather than repeats.
"""

import asyncio
from datetime import datetime, timezone

import pytest

import nightly
from shared import config
from shared.experiment import ExperimentResult, Outcome, SolverConfig
from shared.experiment.results import AttemptRecord, ProblemResult
from shared.ground_truth import get_known_answer, save_known_answers
from shared.paths import get_problem_dir
from submission import step
from submission.policy import Budget, SubmissionState

START = datetime(2026, 12, 1, 10, 0, tzinfo=timezone.utc)

HEADER = ('<header><a href="/2026/auth/logout">[Log Out]</a>'
          '<div class="user">experiment</div></header>')
PART_ONE = '<article class="day-desc"><h2>--- Day 1: Sums ---</h2><p>Add them.</p></article>'
PART_TWO = '<article class="day-desc"><h2 id="part2">--- Part Two ---</h2><p>Double it.</p></article>'

SUMS = "import sys\nprint(sum(int(x) for x in open('input.txt')))\n"
DOUBLE = "import sys\nprint(2 * sum(int(x) for x in open('input.txt')))\n"


def accepted_page(text):
    return f"<html><body><main><article><p>{text}</p></article></main></body></html>"


RIGHT = accepted_page("That's the right answer! You are one gold star closer.")
WRONG = accepted_page("That's not the right answer. Please wait one minute before trying again.")


class FakeWorld:
    """AoC and the GPU, scripted: what each part's trials print, and AoC's replies."""

    def __init__(self, answers, replies, extra_html=""):
        self.answers = answers  # part -> (answer, code)
        self.replies = list(replies)
        self.posted, self.trials, self.fetches, self.refreshes = [], [], [], []
        self.extra_html = extra_html
        self.session_ok = True
        self.fetch_fails = False

    async def check_session(self, year):
        if not self.session_ok:
            raise RuntimeError("logged out")

    async def ensure_problem_files(self, year, day):
        if self.fetch_fails:
            raise RuntimeError("404")
        folder = get_problem_dir(year, day)
        if not (folder / config.HTML_FILE).exists():
            self.fetches.append(day)
            folder.mkdir(parents=True, exist_ok=True)
            (folder / config.HTML_FILE).write_text(
                f"<!DOCTYPE html><html><body>{HEADER}<main>{PART_ONE}{self.extra_html}</main></body></html>")
            (folder / config.INPUT_FILE).write_text("5\n6\n")

    async def refresh_problem_page(self, year, day):
        self.refreshes.append(day)
        folder = get_problem_dir(year, day)
        (folder / config.HTML_FILE).write_text(
            f"<!DOCTYPE html><html><body>{HEADER}<main>{PART_ONE}"
            f"<p>Your puzzle answer was <code>{get_known_answer(year, day, 1)}</code>.</p>"
            f"{PART_TWO}</main></body></html>")

    async def run_experiment(self, problems, cfg, workspace, trials=1, save_to=None,
                             include_replay=False):
        (year, day, part), = problems
        self.trials.append((part, cfg.name))
        answer, code = self.answers[part]
        pid = f"{year}_day{day:02d}_part{part}"
        attempt = AttemptRecord(model="m", problem_id=pid, config_fingerprint=cfg.fingerprint(),
                                outcome=Outcome.UNVERIFIED, answer=answer, code=code)
        result = ExperimentResult(config_name=cfg.name, config_fingerprint=cfg.fingerprint(),
                                  config=cfg.to_dict(), finished_at=START.isoformat(),
                                  results=[ProblemResult(problem_id=pid, year=year, day=day,
                                                         part=part, config_fingerprint="f",
                                                         outcome=Outcome.UNVERIFIED,
                                                         answer=answer, attempts=[attempt])])
        result.save(save_to, include_replay=True)
        return result

    async def post(self, year, day, part, answer):
        self.posted.append((part, answer))
        return self.replies.pop(0)

    def tools(self):
        async def submit(year, day, part, experiments):
            async def no_wait(seconds):
                return None
            return await step.submit_part(year, day, part, experiments, post=self.post,
                                          enabled=True, budget=Budget(), now=lambda: START,
                                          sleep=no_wait)
        return nightly.Tools(self.check_session, self.ensure_problem_files,
                             self.refresh_problem_page, self.run_experiment, submit)


PLAN = nightly.Plan(
    year=2026, trials={1: 2, 2: 1},
    configs={1: [SolverConfig(name="p1")],
             2: [SolverConfig(name="cold"), SolverConfig(name="context")]},
)


@pytest.fixture
def account(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "BASE_DIR", tmp_path)
    monkeypatch.setattr(config, "AOC_ACCOUNT", "experiment")
    # The driver's precondition; the profile itself is macOS-only and covered by
    # tests/integration/test_network_sandbox.py, so the fake trials here run without it.
    monkeypatch.setattr(nightly, "network_denied", lambda: True)
    return tmp_path / "accounts" / "experiment"


def night(world, last_day=1):
    return asyncio.run(nightly.run_night(2026, last_day, PLAN, world.tools(), START))


def test_a_night_runs_part_one_submits_then_part_two(account):
    world = FakeWorld({1: ("11", SUMS), 2: ("22", DOUBLE)}, [RIGHT, RIGHT])

    done = night(world)

    assert done.stopped is None
    assert world.fetches == [1]
    assert world.trials == [(1, "p1"), (1, "p1"), (2, "cold"), (2, "context")]
    assert world.posted == [(1, "11"), (2, "22")]
    assert world.refreshes == [1]
    # the recorded answers are scored, and the context arm has the verified Part 1 program
    for part in (1, 2):
        for path in nightly.recorded(2026, 1, part):
            assert ExperimentResult.load(path).solved == 1
    assert (get_problem_dir(2026, 1) / "2026_day01_part1.py").read_text() == SUMS
    assert "accepted 11" in done.summary(2026)


def test_a_restarted_run_resumes_at_the_trial(account):
    world = FakeWorld({1: ("11", SUMS)}, [])
    asyncio.run(world.run_experiment([(2026, 1, 1)], SolverConfig(name="p1"), None,
                                     save_to=nightly.trial_file(2026, 1, 1, SolverConfig(name="p1"), 0)))
    world.trials.clear()
    world.replies = [WRONG, WRONG, WRONG]

    night(world)

    assert world.trials == [(1, "p1")]


def test_nothing_after_part_one_until_it_is_accepted(account):
    world = FakeWorld({1: ("11", SUMS)}, [WRONG])

    night(world)

    assert world.posted == [(1, "11")]
    assert all(part == 1 for part, _ in world.trials)
    assert world.refreshes == []
    # the next night posts nothing new: the only candidate was judged
    world.trials.clear()
    night(world)
    assert world.posted == [(1, "11")] and world.trials == []


def test_an_expired_session_stops_the_run_before_any_fetch(account):
    world = FakeWorld({1: ("11", SUMS)}, [])
    world.session_ok = False

    done = night(world)

    assert "session check failed" in done.stopped
    assert world.fetches == [] and world.trials == []


def test_an_unavailable_page_stops_the_run_without_retrying(account):
    world = FakeWorld({1: ("11", SUMS)}, [])
    world.fetch_fails = True

    done = night(world)

    assert "not retried" in done.stopped and world.trials == []


def test_it_refuses_the_maintainer_account_and_open_network(account, monkeypatch):
    world = FakeWorld({1: ("11", SUMS)}, [])
    monkeypatch.setattr(nightly, "network_denied", lambda: False)
    assert "network" in night(world).stopped
    monkeypatch.setattr(nightly, "network_denied", lambda: True)
    monkeypatch.setattr(config, "AOC_ACCOUNT", "")
    assert "AOC_ACCOUNT" in night(world).stopped
    assert world.trials == []


def test_a_hand_solved_part_one_does_not_start_part_two(account):
    world = FakeWorld({1: ("11", SUMS), 2: ("22", DOUBLE)}, [])
    asyncio.run(world.ensure_problem_files(2026, 1))
    save_known_answers(2026, 1, {1: "11"})

    done = night(world)

    assert world.trials == [] and world.posted == []
    assert "outside the submission step" in done.summary(2026)


def test_a_page_with_hidden_text_is_reported_apart(account):
    world = FakeWorld({1: ("11", SUMS)}, [WRONG],
                      extra_html='<article class="day-desc"><span style="display:none">x</span></article>')

    done = night(world)

    assert done.flagged_days == [1]
    assert "hidden page text: 1" in done.summary(2026)


def test_a_halt_stops_the_night_and_is_cleared_by_hand(account):
    world = FakeWorld({1: ("11", SUMS)}, [accepted_page("Something new.")])

    assert "halted" in night(world).stopped
    assert nightly.clear_halt().startswith("cleared")
    assert SubmissionState.load(step.state_path()).halted is None


@pytest.mark.parametrize("utc,day", [
    (datetime(2026, 12, 1, 4, 59, tzinfo=timezone.utc), None),   # 23:59 on 30 Nov in New York
    (datetime(2026, 12, 1, 5, 0, tzinfo=timezone.utc), 1),
    (datetime(2026, 12, 3, 10, 0, tzinfo=timezone.utc), 3),       # 02:00 Pacific
    (datetime(2026, 12, 20, 10, 0, tzinfo=timezone.utc), 12),
    (datetime(2027, 1, 2, 10, 0, tzinfo=timezone.utc), None),
])
def test_tonights_puzzle_follows_the_release_in_new_york(utc, day):
    assert nightly.puzzle_day(2026, utc) == day


def test_the_registered_plan_parses():
    plan = nightly.Plan.load()
    assert plan.year == 2026
    assert [c.problem_context for c in plan.configs[2]] == ["legacy", "aoc"]
    assert plan.configs[2][1].gate_part_two is False
