"""The environment record is best-effort and never stops a run."""

import json

import requests

from shared.experiment import environment
from shared.experiment.results import ExperimentResult


class FakeResponse:
    def __init__(self, payload):
        self._payload = payload

    def json(self):
        return self._payload


def test_records_ollama_version_and_model_digests(monkeypatch):
    def fake_get(url, timeout):
        if url.endswith("/api/version"):
            return FakeResponse({"version": "9.9.9"})
        return FakeResponse({"models": [{"name": "m:1b", "digest": "abc"}, {"name": "other", "digest": "x"}]})

    monkeypatch.setattr(requests, "get", fake_get)
    monkeypatch.delenv("OLLAMA_HOST", raising=False)

    env = environment.capture_environment(["m:1b", "missing:2b"])

    assert env["ollama"] == {"host": "http://localhost:11434", "version": "9.9.9",
                             "models": {"m:1b": "abc", "missing:2b": None}}
    assert env["python"] and env["machine"]["arch"]
    assert "autopep8" in env["packages"]


def test_unreachable_ollama_is_recorded_as_none(monkeypatch):
    def refuse(url, timeout):
        raise requests.ConnectionError("refused")

    monkeypatch.setattr(requests, "get", refuse)
    monkeypatch.delenv("OLLAMA_HOST", raising=False)

    env = environment.capture_environment(["m:1b"])

    assert env["ollama"] == {"host": "http://localhost:11434", "version": None, "models": {}}


def test_a_remote_ollama_host_is_recorded(monkeypatch):
    # OLLAMA_HOST is outside the fingerprint, so the result file has to say where the model ran.
    monkeypatch.setenv("OLLAMA_HOST", "http://gpu-box:11434/")
    monkeypatch.setattr(requests, "get", lambda url, timeout: FakeResponse({}))

    assert environment.capture_environment([])["ollama"]["host"] == "http://gpu-box:11434"


def test_environment_is_written_to_the_result_file(tmp_path):
    result = ExperimentResult("n", "fp", {}, environment={"python": "3.11"})

    saved = json.loads(result.save(tmp_path / "r.json").read_text())

    assert saved["environment"] == {"python": "3.11"}
