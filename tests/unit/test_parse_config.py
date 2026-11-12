"""experiment.py --config: every field is parsed by the type SolverConfig declares.

A hand-kept list of boolean fields once missed `targeted_feedback`, so
`targeted_feedback=false` became the string "false", which is truthy: the guidance
ran whatever the flag said. Caught by a fingerprint mismatch before a registered run.
"""

import dataclasses
import typing

import pytest

import experiment
from shared.experiment.config import SolverConfig

BASE = "name=x,models=qwen3.8:27b,samples_per_model=1,temperature=0.7"


def test_targeted_feedback_false_is_false_and_keeps_the_default_fingerprint():
    off = experiment.parse_config(BASE + ",targeted_feedback=false")
    assert off.targeted_feedback is False
    assert off.fingerprint() == experiment.parse_config(BASE).fingerprint()


def test_targeted_feedback_true_is_true():
    assert experiment.parse_config(BASE + ",targeted_feedback=true").targeted_feedback is True


def test_every_boolean_field_parses_to_a_bool():
    hints = typing.get_type_hints(SolverConfig)
    for field in dataclasses.fields(SolverConfig):
        if hints[field.name] in (bool, typing.Optional[bool]):
            for text, expected in (("false", False), ("true", True), ("0", False), ("yes", True)):
                value = getattr(experiment.parse_config(f"{BASE},{field.name}={text}"), field.name)
                assert value is expected, (field.name, text, value)


def test_a_value_that_is_not_a_boolean_is_refused():
    with pytest.raises(ValueError, match="not a boolean"):
        experiment.parse_config(BASE + ",targeted_feedback=maybe")


def test_numeric_fields_parse_to_numbers():
    config = experiment.parse_config(BASE + ",max_repair_iterations=0,consensus_threshold=0.5")
    assert (config.max_repair_iterations, config.consensus_threshold) == (0, 0.5)
