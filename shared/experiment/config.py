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

    # --- repair and fallback --------------------------------------------
    max_repair_iterations: int = 2

    # Targeted efficiency feedback. When the full-input run TIMES OUT (as opposed
    # to erroring or answering wrongly), the default repair message says only
    # that the answer was not accepted -- which tells the model nothing about
    # *why*, so it tends to resubmit the same too-slow approach. With this on,
    # a timeout produces an explicit instruction to find an asymptotically
    # faster algorithm.
    #
    # Gated by config rather than applied unconditionally so it can be A/B'd:
    # a behaviour change that did not enter fingerprint() would make two
    # different experiments share a hash -- exactly the hollow-A/B trap
    # Milestone B removed. Default False = the behaviour every prior run had.
    efficiency_feedback: bool = False
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
