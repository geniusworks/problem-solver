"""gate_part_two: pose Part Two without solving Part One first.

For AoC 2026: once Part One is solved on the account, a run can measure Part
Two alone, with the verified Part One program in the context. The default keeps
every existing fingerprint.
"""

from shared.experiment import SolverConfig
from shared.experiment.runner import part_one_gated


def test_default_keeps_the_existing_fingerprint():
    # The k1 fingerprint of the rescan and of the registered 2025 d9 p2 power test.
    config = SolverConfig(samples_per_model=1, models=("qwen3.8:27b",), temperature=0.7,
                          enable_thinking=False, enable_fallback_models=False)
    assert config.fingerprint() == "1ac712678732"


def test_ungating_changes_the_fingerprint():
    assert SolverConfig(gate_part_two=False).fingerprint() != SolverConfig().fingerprint()


def test_gating_follows_the_flag_and_the_context():
    assert part_one_gated(SolverConfig()) is True
    assert part_one_gated(SolverConfig(gate_part_two=False)) is False
    assert part_one_gated(SolverConfig(problem_context="legacy")) is False
