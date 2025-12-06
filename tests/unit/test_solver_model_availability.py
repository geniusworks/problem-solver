import types

import pytest
import requests

import shared.solver as solver_module
from shared.llm.local import OllamaProvider as LocalOllamaProvider


def _make_solver_with_models(tmp_path, monkeypatch, models):
    """Helper to construct BaseSolver with a specific AVAILABLE_MODELS list."""
    monkeypatch.setattr(solver_module.OllamaProvider, "AVAILABLE_MODELS", models, raising=False)
    solver = solver_module.BaseSolver(tmp_path, debug=False)
    return solver


def test_model_preflight_skips_check_when_ollama_unreachable(tmp_path, monkeypatch):
    """If Ollama /api/tags is unreachable, we keep configured models and do not raise."""

    def fake_get(*args, **kwargs):  # type: ignore[override]
        raise requests.RequestException("connection refused")

    monkeypatch.setattr(solver_module, "requests", types.SimpleNamespace(get=fake_get))

    models = [
        "qwen2.5-coder:7b",
        "llama3.1:8b",
    ]
    solver = _make_solver_with_models(tmp_path, monkeypatch, models)

    assert set(solver.models.keys()) == set(models)


def test_model_preflight_filters_to_installed_models(tmp_path, monkeypatch):
    """When Ollama reports installed models, we intersect them with AVAILABLE_MODELS."""

    class FakeResponse:
        def raise_for_status(self) -> None:
            return None

        def json(self):  # type: ignore[override]
            return {
                "models": [
                    {"name": "qwen2.5-coder:7b"},
                    {"name": "gemma3:latest"},
                ]
            }

    def fake_get(*args, **kwargs):  # type: ignore[override]
        return FakeResponse()

    monkeypatch.setattr(solver_module, "requests", types.SimpleNamespace(get=fake_get))

    models = [
        "qwen2.5-coder:7b",
        "llama3.1:8b",
        "gemma3:latest",
    ]
    solver = _make_solver_with_models(tmp_path, monkeypatch, models)

    # Only the intersection with installed models should remain
    assert set(solver.models.keys()) == {"qwen2.5-coder:7b", "gemma3:latest"}


def test_model_preflight_raises_when_no_configured_models_installed(tmp_path, monkeypatch):
    """If Ollama is reachable but none of the configured models are installed, we raise a clear error."""

    class FakeResponse:
        def raise_for_status(self) -> None:
            return None

        def json(self):  # type: ignore[override]
            return {"models": [{"name": "some-other-model"}]}

    def fake_get(*args, **kwargs):  # type: ignore[override]
        return FakeResponse()

    monkeypatch.setattr(solver_module, "requests", types.SimpleNamespace(get=fake_get))

    models = [
        "qwen2.5-coder:7b",
        "llama3.1:8b",
    ]

    with pytest.raises(RuntimeError):
        _make_solver_with_models(tmp_path, monkeypatch, models)
