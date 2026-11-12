"""Every recorded configuration still hashes to the fingerprint its run recorded.

A fingerprint is how a result names the behaviour it measured, so a change to SolverConfig's
fields, defaults or serialisation that moved it would silently detach every published result
from the code that reproduces it. This reads the committed run table (dev/results/runs.csv)
and rebuilds each configuration that names every current field (gate_part_two aside: runs
before it existed did not record it, and its absence means the value they ran with). That is
every run since the example_tests field was added in October 2026, including every registered
test. Older records predate fields added since (num_ctx, enable_thinking, targeted_feedback,
example_tests, ...) and cannot be rebuilt as today's SolverConfig; their fingerprints match
their own recorded configurations.
"""

import csv
import dataclasses
import json
from pathlib import Path

from shared.experiment.config import SolverConfig

RUNS = Path(__file__).resolve().parents[2] / "dev" / "results" / "runs.csv"
FIELDS = {field.name for field in dataclasses.fields(SolverConfig)}


def _current_runs():
    with RUNS.open(newline="") as handle:
        for row in csv.DictReader(handle):
            config = json.loads(row["config"])
            if set(config) >= FIELDS - {"gate_part_two"}:
                yield row["run"], config, row["config_fingerprint"]


def test_every_current_config_reproduces_its_recorded_fingerprint():
    runs = list(_current_runs())
    assert len(runs) >= 55  # the table only grows
    drifted = [(run, SolverConfig(**config).fingerprint(), recorded)
               for run, config, recorded in runs
               if SolverConfig(**config).fingerprint() != recorded]
    assert drifted == []


def test_the_registered_tests_are_among_them():
    names = {config["name"] for _, config, _ in _current_runs()}
    for prefix in ("m5pro-d9p2-rep-k1-b", "m5pro-d9p2-speed-off-b", "m5pro-d9p2-speed-on-b"):
        assert any(name.startswith(prefix) for name in names), prefix
