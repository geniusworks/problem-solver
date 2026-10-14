"""Every experimental variable in one object.

Two configurations that differ in any field below may produce different results,
so results are grouped by ``SolverConfig.fingerprint()``. Anything that changes
solver behaviour belongs here rather than being read from the environment at the
point of use -- otherwise a recorded result cannot be attributed to the settings
that produced it.
"""

import hashlib
import json
import os
from dataclasses import asdict, dataclass, field, replace
from typing import Any, Dict, Optional, Tuple


def _env_flag(name: str, default: bool = False) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _env_int(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None or not raw.strip():
        return default
    try:
        return int(raw)
    except ValueError:
        return default


# Value each later-added field had, implicitly, in every run made before it
# existed. See fingerprint().
_LEGACY_VALUES: Dict[str, Any] = {
    "problem_context": "legacy",
    "analysis_temperature": "model_default",
    "example_tests": "parser",
}


@dataclass(frozen=True)
class SolverConfig:
    """A named, reproducible solver configuration."""

    # --- identity -------------------------------------------------------
    name: str = "default"

    # Only fields that affect solver behaviour today live here. Anything that
    # enters fingerprint() must change what a run does, or two byte-identical
    # runs get two identities and every A/B built on them is hollow. Knobs for
    # unbuilt features (self-consistency sampling, prompt variants, answer-based
    # consensus, remote providers, submission) are re-added with their features
    # in later milestones, wired -- not before.

    # --- model selection ------------------------------------------------
    # None means "let the learning database rank the installed models".
    models: Optional[Tuple[str, ...]] = None
    max_primary_models: int = 3

    # --- generation -----------------------------------------------------
    temperature: Optional[float] = None

    # Ollama per-request thinking toggle. None = model default; False disables
    # chain-of-thought. Reasoning models (e.g. qwen3.5) otherwise over-reason on
    # these prompts -- tens of thousands of chars of thinking that exhaust the
    # output budget before any code -- so an A/B of such a model wants this False.
    enable_thinking: Optional[bool] = None

    # Self-consistency sampling: draw this many candidates per model instead of
    # one. With temperature > 0 the samples differ, so a problem the model solves
    # only some of the time gets several shots at the oracle in a single run --
    # the direct attack on the run-to-run variance the baseline measured (4 of 6
    # problems flipped across identical configs). Needs temperature > 0 to help;
    # at 1 the solver behaves exactly as before.
    samples_per_model: int = 1

    # What the model is shown about the problem.
    #   "aoc"    -> what a solver on the site has at that step: for Part Two,
    #               Part One's statement and accepted answer above the Part Two
    #               text, plus the recorded Part One program; for both parts,
    #               the first lines of the puzzle input. Not the site's "too
    #               high" / "too low" on a wrong answer: feedback is never
    #               given the accepted answer (test_never_leaks_the_expected_answer).
    #   "legacy" -> the one article for the part and nothing else, which is
    #               what every run before 2026-10-13 used. A Part Two posed
    #               this way has no rules and no input format
    #               (dev/progress/part2-prompt-omits-part1.md).
    problem_context: str = "aoc"

    # Temperature of the analysis call that precedes each draft.
    #   "configured"    -> `temperature`, like the implementation and repair calls.
    #   "model_default" -> unset, so Ollama uses the model's own default (1.0
    #                      for qwen3.8:27b). Every run before 2026-10-13.
    analysis_temperature: str = "configured"

    # Where the example tests fed back to a failed draft come from.
    #   "page"   -> example inputs and their stated results read off the page:
    #               a block is an example input if it resembles the puzzle
    #               input (shared/problem_context.py::statement_examples).
    #   "parser" -> the parser's pairing, which attaches a result to the code
    #               block above it, often an illustration. Every run before
    #               2026-10-14; a verified program fails 25 of 46 of these
    #               (dev/progress/example-tests-mispaired.md).
    example_tests: str = "page"

    # --- repair and fallback --------------------------------------------
    max_repair_iterations: int = 2

    # Failure-specific repair feedback. The default repair message is the same
    # regardless of HOW a candidate failed -- "the answer is still not
    # accepted" -- which leaves the model free to resubmit a near-identical
    # attempt, and it does. With this on the message is specialised per failure
    # mode:
    #   timeout      -> this is a PERFORMANCE problem; find a faster algorithm
    #   wrong answer -> echo what the code actually produced, and push toward
    #                   re-reading the spec rather than cosmetic tweaks
    # Crashes are left alone: the traceback is already specific feedback.
    #
    # Named for the failure modes it addresses rather than for one of them --
    # an earlier version covered only timeouts and was aimed at two benchmark
    # problems that turn out never to time out
    # (dev/progress/CORRECTION-d15p2-is-not-a-wall.md).
    #
    # Gated by config rather than applied unconditionally so it can be A/B'd:
    # a behaviour change that did not enter fingerprint() would make two
    # different experiments share a hash -- exactly the hollow-A/B trap
    # Milestone B removed. Default False = the behaviour every prior run had.
    targeted_feedback: bool = False
    enable_fallback_models: bool = True
    enable_collaborative_improvement: bool = False

    # --- consensus ------------------------------------------------------
    # Threshold and quorum for the (source-text) consensus check. consensus_on
    # returns when answer-based consensus is built (Milestone E).
    consensus_threshold: float = 0.6
    min_consensus_models: int = 2

    # --- verification ----------------------------------------------------
    # Refuse to accept a candidate for a problem with no oracle (no example
    # with a known expected output, and no cached accepted answer).
    require_oracle: bool = True

    # --- execution -------------------------------------------------------
    execution_timeout: Optional[int] = None

    # Context window requested from Ollama. None uses the provider's
    # prompt-sized default.
    #
    # This is a genuine open question, not a tuning knob. Ollama truncates to
    # ~2048 tokens unless told otherwise, and this solver's prompts reach
    # ~6962 -- so the default silently discards most of the problem. But
    # raising it costs KV cache: on a 16GB M1, one measured run went 3/6 in
    # 896s at the truncating default and 1/6 in 1760s at 16384. Two runs of
    # six problems cannot separate that from the known run-to-run variance,
    # which is exactly why it belongs in the config where it can be swept.
    num_ctx: Optional[int] = None

    # --- bookkeeping (excluded from the fingerprint) ---------------------
    notes: str = field(default="", compare=False)

    def __post_init__(self) -> None:
        if not 0.0 < self.consensus_threshold <= 1.0:
            raise ValueError(
                f"consensus_threshold must be in (0, 1], got {self.consensus_threshold}"
            )
        if self.max_repair_iterations < 0:
            raise ValueError("max_repair_iterations must be >= 0")
        if self.max_primary_models < 1:
            raise ValueError("max_primary_models must be >= 1")
        if self.samples_per_model < 1:
            raise ValueError("samples_per_model must be >= 1")
        if self.problem_context not in ("aoc", "legacy"):
            raise ValueError("problem_context must be 'aoc' or 'legacy'")
        if self.example_tests not in ("page", "parser"):
            raise ValueError("example_tests must be 'page' or 'parser'")
        if self.analysis_temperature not in ("configured", "model_default"):
            raise ValueError(
                "analysis_temperature must be 'configured' or 'model_default'"
            )

    # -- serialisation ----------------------------------------------------

    def to_dict(self) -> Dict[str, Any]:
        """Full configuration, including fields excluded from the fingerprint."""
        data = asdict(self)
        data["models"] = list(self.models) if self.models else None
        return data

    def fingerprint(self) -> str:
        """Stable short hash of the behaviour-affecting fields.

        ``name`` and ``notes`` are excluded: renaming a configuration must not
        make it look like a different experiment.
        """
        payload = self.to_dict()
        payload.pop("name", None)
        payload.pop("notes", None)
        # Fields added after results were already on record are left out at
        # the value those results ran with, so a run that sets them back
        # reproduces the old fingerprint and the old hashes keep their meaning.
        for key, legacy in _LEGACY_VALUES.items():
            if payload.get(key) == legacy:
                payload.pop(key)
        canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:12]

    def with_overrides(self, **changes: Any) -> "SolverConfig":
        """Return a copy with fields replaced -- the unit of an A/B sweep."""
        if "models" in changes and changes["models"] is not None:
            changes["models"] = tuple(changes["models"])
        return replace(self, **changes)

    # -- construction -----------------------------------------------------

    @classmethod
    def from_env(cls, **overrides: Any) -> "SolverConfig":
        """Build from the environment variables the solver historically read.

        Keeps existing .env files working; explicit overrides win.
        """
        models = os.getenv("SOLVER_MODELS")
        env_config: Dict[str, Any] = {
            "max_repair_iterations": _env_int("MAX_REPAIR_ITERATIONS", 2),
            "enable_collaborative_improvement": _env_flag(
                "ENABLE_COLLABORATIVE_IMPROVEMENT", False
            ),
        }
        if models:
            env_config["models"] = tuple(
                m.strip() for m in models.split(",") if m.strip()
            )

        env_config.update(overrides)
        if env_config.get("models") is not None:
            env_config["models"] = tuple(env_config["models"])
        return cls(**env_config)

    def __str__(self) -> str:
        return f"{self.name} ({self.fingerprint()})"
