"""dev/export_results.py: what the public tables carry, and what they leave out."""

import csv
import importlib.util
import json
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[2] / "dev" / "export_results.py"
spec = importlib.util.spec_from_file_location("export_results", SCRIPT)
export_results = importlib.util.module_from_spec(spec)
spec.loader.exec_module(export_results)

SECRET_ANSWER = "1566935900"


def write_run(directory, environment=None):
    attempts = [
        {"model": "m", "stage": "generate", "outcome": "error",
         "error": "Full input run ERROR: Solution timed out after 60 seconds", "code": "x"},
        {"model": "m", "stage": "repair", "outcome": "error",
         "error": "Solution exceeded the memory cap of 8192 MB and was stopped"},
        {"model": "m", "stage": "repair", "outcome": "error", "error": "Process failed: IndexError"},
        {"model": "m", "stage": "repair", "outcome": "wrong",
         "error": f"expected {SECRET_ANSWER}, got 7; no crash and no timeout"},
    ]
    run = {"config": {"name": "r"}, "summary": {}, "results": [
        {"problem_id": "2025_day09_part2", "trial": 0, "outcome": "no_candidate",
         "expected": SECRET_ANSWER, "attempts": attempts}]}
    if environment:
        run["environment"] = environment
    (directory / "20261111T000000Z_r_abc.json").write_text(json.dumps(run))


def rows(target, name):
    with open(target / name, newline="") as f:
        return list(csv.DictReader(f))


def test_execution_errors_are_split_by_kind(tmp_path):
    write_run(tmp_path)
    export_results.export(tmp_path, tmp_path / "out")
    kinds = [a["error_kind"] for a in rows(tmp_path / "out", "attempts.csv")]
    assert kinds == ["timeout", "memory cap", "crash", ""]


def test_the_environment_is_exported_when_recorded(tmp_path):
    write_run(tmp_path, {"git": {"commit": "370ec58", "dirty": False},
                         "ollama": {"version": "0.40.11", "models": {"qwen3.8:27b": "aaee06"}},
                         "machine": {"cpu": "Apple M5 Pro", "memory_bytes": 68719476736}})
    export_results.export(tmp_path, tmp_path / "out")
    run = rows(tmp_path / "out", "runs.csv")[0]
    assert (run["git_commit"], run["ollama_version"]) == ("370ec58", "0.40.11")
    assert json.loads(run["model_digests"]) == {"qwen3.8:27b": "aaee06"}
    assert run["machine"] == "Apple M5 Pro / 68719476736"


def test_older_runs_without_an_environment_export_blank(tmp_path):
    write_run(tmp_path)
    export_results.export(tmp_path, tmp_path / "out")
    run = rows(tmp_path / "out", "runs.csv")[0]
    assert run["git_commit"] == run["ollama_version"] == run["model_digests"] == ""


def test_no_answer_error_text_or_code_reaches_the_tables(tmp_path):
    write_run(tmp_path)
    export_results.export(tmp_path, tmp_path / "out")
    for name in ("runs.csv", "trials.csv", "attempts.csv"):
        text = (tmp_path / "out" / name).read_text()
        assert SECRET_ANSWER not in text
        assert "timed out after" not in text
