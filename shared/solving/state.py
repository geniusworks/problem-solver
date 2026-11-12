"""What one stage of a solve hands the next."""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple


@dataclass
class _Prep:
    """Output of the setup stage: what the later stages need, or an early answer.

    ``solved`` is set only when an already-recorded solution ran clean on the
    full input, in which case solve_problem returns it without generating.
    """

    solved: Optional[str] = None
    parsed_problem: Any = None
    strategies: Any = None
    effectiveness: Any = None
    problem_type: str = ""
    primary_models: List[str] = field(default_factory=list)
    reviewer_models: List[str] = field(default_factory=list)


@dataclass
class _Candidates:
    """Output of the generation stage: the candidate pool and its bookkeeping.

    Keyed by candidate id (self-consistency draws several per model);
    ``candidate_models`` maps each back to the model that produced it.
    """

    answers: Dict[str, str] = field(default_factory=dict)
    candidate_models: Dict[str, str] = field(default_factory=dict)
    generation_times: Dict[str, float] = field(default_factory=dict)
    generation_tokens: Dict[str, Dict[str, int]] = field(default_factory=dict)
    # (prompt, raw response) of the call that produced each draft, for --include-replay.
    generation_replay: Dict[str, Tuple[Optional[str], Optional[str]]] = field(default_factory=dict)
    failures: List[Any] = field(default_factory=list)
