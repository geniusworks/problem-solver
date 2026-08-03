"""What actually happened, recorded so it can be compared across configurations.

The distinction that matters here is between what the solver *claimed* and what
was *verified*. The pre-oracle pipeline recorded only claims, which is how three
wrong solutions were logged as validated. Outcome keeps them apart: SOLVED means
an oracle confirmed the answer, and UNVERIFIED is a distinct outcome from both
success and failure rather than being folded into either.
"""

import json
from dataclasses import asdict, dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional


class Outcome(str, Enum):
    """Terminal state of one problem attempt."""

    SOLVED = "solved"  # produced the accepted answer, confirmed by an oracle
    WRONG = "wrong"  # produced an answer, oracle says it is incorrect
    UNVERIFIED = "unverified"  # produced an answer, but nothing could check it
    NO_CANDIDATE = "no_candidate"  # no model produced runnable code
    ERROR = "error"  # the harness itself failed
    # Printed the accepted answer without computing it. Matching ground truth
    # cannot distinguish this from a real solution, so it is tracked separately
    # and never counted as solved -- otherwise solve rate is trivially gameable.
    OVERFIT = "overfit"


@dataclass
class AttemptRecord:
    """One model's attempt at one problem.

    Enough provenance to replay the attempt or attribute a result to the
    settings that produced it.
    """

    model: str
    problem_id: str
    config_fingerprint: str

    # what happened
    outcome: Outcome = Outcome.ERROR
    answer: Optional[str] = None
    expected: Optional[str] = None
    error: Optional[str] = None

    # where in the loop it came from
    stage: str = "generate"  # generate | repair | fallback | reuse | consensus
    repair_iteration: int = 0
    sample_index: int = 0

    # cost and timing
    wall_clock_seconds: float = 0.0
    input_tokens: int = 0
    output_tokens: int = 0
    cost_usd: float = 0.0

    # quality signals
    quality_score: Optional[float] = None
    examples_passed: Optional[int] = None
    examples_total: Optional[int] = None
    overfit_flagged: bool = False

    # replay material (large; excluded from compact summaries)
    prompt: Optional[str] = field(default=None, repr=False)
    raw_response: Optional[str] = field(default=None, repr=False)
    code: Optional[str] = field(default=None, repr=False)

    @property
    def succeeded(self) -> bool:
        """Only a verified-correct answer counts. UNVERIFIED is not success."""
        return self.outcome is Outcome.SOLVED

    def to_dict(self, include_replay: bool = False) -> Dict[str, Any]:
        data = asdict(self)
        data["outcome"] = self.outcome.value
        if not include_replay:
            for key in ("prompt", "raw_response", "code"):
                data.pop(key, None)
        return data


@dataclass
class ProblemResult:
    """Outcome of running one problem under one configuration."""

    problem_id: str
    year: int
    day: int
    part: int
    config_fingerprint: str

    outcome: Outcome = Outcome.ERROR
    answer: Optional[str] = None
    expected: Optional[str] = None
    winning_model: Optional[str] = None

    attempts: List[AttemptRecord] = field(default_factory=list)
    wall_clock_seconds: float = 0.0

    @property
    def solved(self) -> bool:
        return self.outcome is Outcome.SOLVED

    @property
    def attempts_to_solve(self) -> Optional[int]:
        """1-indexed position of the first verified-correct attempt."""
        for index, attempt in enumerate(self.attempts, start=1):
            if attempt.succeeded:
                return index
        return None

    @property
    def first_try(self) -> bool:
        """Solved by the first model tried, with no repair round."""
        return self.attempts_to_solve == 1

    @property
    def total_tokens(self) -> int:
        return sum(a.input_tokens + a.output_tokens for a in self.attempts)

    @property
    def total_cost_usd(self) -> float:
        return sum(a.cost_usd for a in self.attempts)

    def to_dict(self, include_replay: bool = False) -> Dict[str, Any]:
        return {
            "problem_id": self.problem_id,
            "year": self.year,
            "day": self.day,
            "part": self.part,
            "config_fingerprint": self.config_fingerprint,
            "outcome": self.outcome.value,
            "answer": self.answer,
            "expected": self.expected,
            "winning_model": self.winning_model,
            "wall_clock_seconds": round(self.wall_clock_seconds, 3),
            "attempts_to_solve": self.attempts_to_solve,
            "total_tokens": self.total_tokens,
            "total_cost_usd": round(self.total_cost_usd, 6),
            "attempts": [a.to_dict(include_replay) for a in self.attempts],
        }


@dataclass
class ExperimentResult:
    """Aggregate over a problem set for one configuration."""

    config_name: str
    config_fingerprint: str
    config: Dict[str, Any]
    results: List[ProblemResult] = field(default_factory=list)
    started_at: Optional[str] = None
    finished_at: Optional[str] = None

    # -- headline metrics -------------------------------------------------

    @property
    def attempted(self) -> int:
        return len(self.results)

    @property
    def solved(self) -> int:
        return sum(1 for r in self.results if r.outcome is Outcome.SOLVED)

    @property
    def wrong(self) -> int:
        return sum(1 for r in self.results if r.outcome is Outcome.WRONG)

    @property
    def unverified(self) -> int:
        return sum(1 for r in self.results if r.outcome is Outcome.UNVERIFIED)

    @property
    def overfit(self) -> int:
        return sum(1 for r in self.results if r.outcome is Outcome.OVERFIT)

    @property
    def solve_rate(self) -> float:
        return self.solved / self.attempted if self.attempted else 0.0

    @property
    def first_try_rate(self) -> float:
        """Share of *solved* problems that needed only one attempt."""
        solved = [r for r in self.results if r.solved]
        if not solved:
            return 0.0
        return sum(1 for r in solved if r.first_try) / len(solved)

    @property
    def mean_attempts_to_solve(self) -> Optional[float]:
        counts = [r.attempts_to_solve for r in self.results if r.attempts_to_solve]
        return sum(counts) / len(counts) if counts else None

    @property
    def claimed_minus_verified(self) -> int:
        """Answers produced but not confirmed correct.

        The pre-oracle pipeline would have counted every one of these as a
        success; tracking the gap keeps that failure mode visible. Overfit
        solutions belong here too: they match ground truth exactly, so only
        static analysis separates them from real solutions.
        """
        return self.wrong + self.unverified + self.overfit

    @property
    def total_wall_clock_seconds(self) -> float:
        return sum(r.wall_clock_seconds for r in self.results)

    @property
    def total_tokens(self) -> int:
        return sum(r.total_tokens for r in self.results)

    @property
    def total_cost_usd(self) -> float:
        return sum(r.total_cost_usd for r in self.results)

    def per_model(self) -> Dict[str, Dict[str, Any]]:
        """Attempts and wins per model across the run.

        This is what distinguishes a config that solved more because the
        orchestration improved from one that solved more because a single strong
        model carried it.
        """
        stats: Dict[str, Dict[str, Any]] = {}
        for result in self.results:
            for attempt in result.attempts:
                entry = stats.setdefault(
                    attempt.model,
                    {"attempts": 0, "solved": 0, "wall_clock_seconds": 0.0},
                )
                entry["attempts"] += 1
                entry["solved"] += int(attempt.succeeded)
                entry["wall_clock_seconds"] += attempt.wall_clock_seconds

        for entry in stats.values():
            entry["solve_rate"] = (
                round(entry["solved"] / entry["attempts"], 4) if entry["attempts"] else 0.0
            )
            entry["wall_clock_seconds"] = round(entry["wall_clock_seconds"], 1)
        return dict(sorted(stats.items(), key=lambda kv: -kv[1]["solved"]))

    def summary(self) -> Dict[str, Any]:
        return {
            "config_name": self.config_name,
            "config_fingerprint": self.config_fingerprint,
            "attempted": self.attempted,
            "solved": self.solved,
            "wrong": self.wrong,
            "unverified": self.unverified,
            "overfit": self.overfit,
            "solve_rate": round(self.solve_rate, 4),
            "first_try_rate": round(self.first_try_rate, 4),
            "mean_attempts_to_solve": (
                round(self.mean_attempts_to_solve, 2)
                if self.mean_attempts_to_solve is not None
                else None
            ),
            "claimed_minus_verified": self.claimed_minus_verified,
            "total_wall_clock_seconds": round(self.total_wall_clock_seconds, 1),
            "total_tokens": self.total_tokens,
            "total_cost_usd": round(self.total_cost_usd, 4),
        }

    def to_dict(self, include_replay: bool = False) -> Dict[str, Any]:
        return {
            "summary": self.summary(),
            "per_model": self.per_model(),
            "config": self.config,
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "results": [r.to_dict(include_replay) for r in self.results],
        }

    def save(self, path: Path, include_replay: bool = False) -> Path:
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(include_replay), f, indent=2)
            f.write("\n")
        return path
