"""Experiment harness: run the solver under a named configuration and measure it.

The solver exists to test orchestration ideas -- prompting, consensus, repair,
model selection. Answering "did change X help?" needs three things this package
provides: a single object holding every experimental variable (SolverConfig), a
record of what actually happened per attempt (results), and a runner that sweeps
a problem set and aggregates outcomes (runner).
"""

from shared.experiment.config import SolverConfig
from shared.experiment.results import (
    AttemptRecord,
    ExperimentResult,
    Outcome,
    ProblemResult,
)

__all__ = [
    "SolverConfig",
    "AttemptRecord",
    "ProblemResult",
    "ExperimentResult",
    "Outcome",
]
