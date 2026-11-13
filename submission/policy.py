"""What may be submitted, and when: the submission budget of the AoC 2026 registration.

Pure bookkeeping, no network. The state is one JSON file per account
(accounts/<name>/submissions.json), written before every post and after every reply, so a
restart never repeats an answer or posts inside a wait. See
dev/progress/aoc2026-registration.md, "Submitting".
"""

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence

from shared.config import RESOURCES_CONFIG
from shared.experiment.results import UNSCORED, ExperimentResult, Outcome
from submission.replies import COUNTS_AS_WRONG, JUDGED, ReplyKind

# Outcomes whose answer is a candidate: the program ran and printed something.
_ANSWERED = frozenset({Outcome.UNVERIFIED, Outcome.WRONG, Outcome.SOLVED, Outcome.OVERFIT})

# AoC answers are single tokens; anything else is not a submittable answer.
_MAX_ANSWER_LENGTH = 64

PENDING = "pending"


@dataclass(frozen=True)
class Budget:
    """The registered limits (config/resources.yaml, `submission:`)."""

    wrong_per_part: int = 3
    per_night: int = 6
    # The window "per night" counts in: a run restarted the same night shares it.
    night_hours: int = 20
    # Added to every wait AoC states.
    wait_margin_seconds: int = 30
    # A wait longer than this ends the step for the night instead of being slept through.
    longest_wait_seconds: int = 900

    @classmethod
    def from_config(cls) -> "Budget":
        section = RESOURCES_CONFIG.get("submission", {}) or {}
        return cls(**{key: int(section[key]) for key in asdict(cls()) if key in section})


@dataclass
class Candidate:
    answer: str
    # Trials (result records) in which some attempt printed this answer.
    trials: int = 0
    # 2: an attempt printing it passed every worked example; 1: no example was checked;
    # 0: it failed one.
    examples: int = 0
    first_seen: int = 0


def _example_tier(examples_passed: Optional[int], examples_total: Optional[int]) -> int:
    if not examples_total:
        return 1
    return 2 if examples_passed == examples_total else 0


def normalise(answer: Optional[str]) -> Optional[str]:
    """The submittable form of a recorded answer, or None if it is not one."""
    text = (answer or "").strip()
    if not text or len(text) > _MAX_ANSWER_LENGTH or any(c.isspace() for c in text):
        return None
    return text


def rank_candidates(experiments: Iterable[ExperimentResult], problem: str) -> List[Candidate]:
    """Every answer recorded for `problem`, pooled across trials and models, deduplicated.

    Ranked by the worked examples (passed, then unchecked, then failed), then by how many
    trials gave the answer, then by when it was first recorded.
    """
    found: Dict[str, Candidate] = {}
    order = 0
    for experiment in experiments:
        for result in experiment.results:
            if result.problem_id != problem or result.outcome in UNSCORED:
                continue
            seen_this_trial = set()
            for attempt in result.attempts:
                answer = normalise(attempt.answer)
                if answer is None or attempt.outcome not in _ANSWERED:
                    continue
                candidate = found.get(answer)
                if candidate is None:
                    candidate = found[answer] = Candidate(answer, first_seen=order)
                    order += 1
                candidate.examples = max(
                    candidate.examples,
                    _example_tier(attempt.examples_passed, attempt.examples_total),
                )
                if answer not in seen_this_trial:
                    seen_this_trial.add(answer)
                    candidate.trials += 1
    return sorted(found.values(), key=lambda c: (-c.examples, -c.trials, c.first_seen))


def _integer(answer: str) -> Optional[int]:
    try:
        return int(answer)
    except ValueError:
        return None


@dataclass
class PartState:
    accepted: Optional[str] = None
    # Exclusive bounds from "too low" / "too high".
    lower: Optional[int] = None
    upper: Optional[int] = None
    submissions: List[Dict[str, Any]] = field(default_factory=list)

    def tried(self) -> set:
        return {s["answer"] for s in self.submissions if s["reply"] in {k.value for k in JUDGED}
                or s["reply"] in (ReplyKind.UNKNOWN.value, PENDING)}

    def wrong_count(self) -> int:
        counted = {k.value for k in COUNTS_AS_WRONG} | {PENDING}
        return sum(1 for s in self.submissions if s["reply"] in counted)

    def allows(self, answer: str) -> bool:
        """Whether the bounds AoC has given leave `answer` possible."""
        value = _integer(answer)
        if value is None:
            return True
        if self.lower is not None and value <= self.lower:
            return False
        if self.upper is not None and value >= self.upper:
            return False
        return True


@dataclass
class SubmissionState:
    """Everything submitted from one account, and what AoC said."""

    parts: Dict[str, PartState] = field(default_factory=dict)
    # AoC's waits are treated as covering the whole account.
    blocked_until: Optional[str] = None
    # Set on a reply the parser did not recognise, or one that contradicts the record. Every
    # later step stops until the maintainer has looked and cleared it.
    halted: Optional[str] = None

    def part(self, problem: str) -> PartState:
        return self.parts.setdefault(problem, PartState())

    def submissions_since(self, since: datetime) -> int:
        return sum(
            1 for part in self.parts.values() for s in part.submissions
            if datetime.fromisoformat(s["at"]) >= since
        )

    # -- storage ----------------------------------------------------------

    @classmethod
    def load(cls, path: Path) -> "SubmissionState":
        if not path.exists():
            return cls()
        data = json.loads(path.read_text(encoding="utf-8"))
        return cls(
            parts={key: PartState(**value) for key, value in data.get("parts", {}).items()},
            blocked_until=data.get("blocked_until"),
            halted=data.get("halted"),
        )

    def save(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        partial = path.with_name(path.name + ".partial")
        partial.write_text(
            json.dumps({"parts": {k: asdict(v) for k, v in sorted(self.parts.items())},
                        "blocked_until": self.blocked_until, "halted": self.halted},
                       indent=2) + "\n",
            encoding="utf-8",
        )
        partial.replace(path)


@dataclass(frozen=True)
class Decision:
    """The next step for one part: post `answer`, wait until `wait_until`, or stop."""

    answer: Optional[str]
    reason: str
    wait_until: Optional[datetime] = None


def decide(
    state: SubmissionState, problem: str, candidates: Sequence[Candidate],
    budget: Budget, now: datetime,
) -> Decision:
    if state.halted:
        return Decision(None, "halted")
    part = state.part(problem)
    if part.accepted is not None:
        return Decision(None, "accepted")
    if part.wrong_count() >= budget.wrong_per_part:
        return Decision(None, "budget_spent")
    if state.submissions_since(now - timedelta(hours=budget.night_hours)) >= budget.per_night:
        return Decision(None, "night_cap")
    tried = part.tried()
    remaining = [c.answer for c in candidates if c.answer not in tried and part.allows(c.answer)]
    if not remaining:
        return Decision(None, "no_candidates")
    if state.blocked_until is not None:
        until = datetime.fromisoformat(state.blocked_until)
        if until > now:
            return Decision(remaining[0], "wait", wait_until=until)
    return Decision(remaining[0], "submit")


def record_pending(state: SubmissionState, problem: str, answer: str, now: datetime) -> None:
    """Note a post about to be made. Found on load, it means the reply was never read."""
    state.part(problem).submissions.append(
        {"answer": answer, "at": now.isoformat(), "reply": PENDING, "wait_seconds": None}
    )


def record_reply(
    state: SubmissionState, problem: str, answer: str, kind: ReplyKind,
    wait_seconds: Optional[int], budget: Budget, now: datetime,
) -> None:
    """Replace the pending entry for `answer` with AoC's reply and apply what it says."""
    part = state.part(problem)
    entry = next(s for s in reversed(part.submissions)
                 if s["answer"] == answer and s["reply"] == PENDING)
    entry["reply"] = kind.value
    entry["wait_seconds"] = wait_seconds

    if kind is ReplyKind.ACCEPTED:
        part.accepted = answer
    value = _integer(answer)
    if kind is ReplyKind.TOO_HIGH and value is not None:
        part.upper = value if part.upper is None else min(part.upper, value)
    if kind is ReplyKind.TOO_LOW and value is not None:
        part.lower = value if part.lower is None else max(part.lower, value)
    if wait_seconds is not None:
        until = now + timedelta(seconds=wait_seconds + budget.wait_margin_seconds)
        state.blocked_until = until.isoformat()
    if kind is ReplyKind.UNKNOWN:
        state.halted = f"unrecognised reply to {answer!r} for {problem}"
    if kind is ReplyKind.WRONG_LEVEL:
        state.halted = (f"AoC says {problem} is already solved or not open, but no answer "
                        f"is recorded as accepted for it")


def halt_on_unanswered_posts(state: SubmissionState) -> None:
    """A pending entry on load means a post whose reply was never read: stop."""
    for problem, part in state.parts.items():
        for s in part.submissions:
            if s["reply"] == PENDING and not state.halted:
                state.halted = f"no reply recorded for {s['answer']!r} posted for {problem}"


def utcnow() -> datetime:
    return datetime.now(timezone.utc)
