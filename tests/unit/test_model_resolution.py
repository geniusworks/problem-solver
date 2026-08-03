"""SolverConfig.models must actually select which models run.

The field existed and changed the config fingerprint while having no effect on
model resolution, so an A/B across model sets silently compared two identical
runs. That is the same hollow-signal failure as a metric that is constant by
construction.
"""

from pathlib import Path

import pytest
import requests

from shared.experiment import SolverConfig
from shared.llm.local import OllamaProvider


class _Response:
    def __init__(self, names):
        self._names = names

    def raise_for_status(self):
        return None

    def json(self):
        return {"models": [{"name": n} for n in self._names]}


@pytest.fixture
def installed(monkeypatch):
    """Pretend Ollama has a fixed set of models installed."""

    def _install(names):
        monkeypatch.setattr(requests, "get", lambda *a, **k: _Response(names))

    return _install


def _resolve(config, tmp_path):
    from shared.solver import BaseSolver

    # Only the resolution logic is under test; avoid constructing providers.
    return BaseSolver._resolve_available_models(
        type("S", (), {"config": config})()
    )


class TestModelResolution:
    def test_config_models_take_precedence(self, installed, tmp_path):
        installed(["phi4:latest", "qwen2.5-coder:7b", "gemma3:latest"])
        config = SolverConfig(models=("phi4:latest",))

        assert _resolve(config, tmp_path) == ["phi4:latest"]

    def test_curated_list_is_the_default(self, installed, tmp_path):
        installed(list(OllamaProvider.AVAILABLE_MODELS) + ["phi4:latest"])

        resolved = _resolve(SolverConfig(), tmp_path)

        assert "phi4:latest" not in resolved
        assert resolved == list(OllamaProvider.AVAILABLE_MODELS)

    def test_requested_order_is_preserved(self, installed, tmp_path):
        installed(["a:1b", "b:1b", "c:1b"])
        config = SolverConfig(models=("c:1b", "a:1b"))

        assert _resolve(config, tmp_path) == ["c:1b", "a:1b"]

    def test_uninstalled_models_are_filtered_out(self, installed, tmp_path):
        installed(["a:1b"])
        config = SolverConfig(models=("a:1b", "missing:1b"))

        assert _resolve(config, tmp_path) == ["a:1b"]

    def test_none_installed_raises_naming_what_was_wanted(self, installed, tmp_path):
        installed(["something-else:1b"])
        config = SolverConfig(models=("wanted:1b",))

        with pytest.raises(RuntimeError, match="wanted:1b"):
            _resolve(config, tmp_path)

    def test_unreachable_ollama_falls_back_to_candidates(self, monkeypatch, tmp_path):
        def boom(*a, **k):
            raise requests.RequestException("connection refused")

        monkeypatch.setattr(requests, "get", boom)
        config = SolverConfig(models=("phi4:latest",))

        assert _resolve(config, tmp_path) == ["phi4:latest"]

    def test_different_model_sets_have_different_fingerprints(self):
        """Otherwise an A/B would record both arms under one identity."""
        a = SolverConfig(name="7b", models=("qwen2.5-coder:7b",))
        b = SolverConfig(name="phi4", models=("phi4:latest",))

        assert a.fingerprint() != b.fingerprint()


class TestAnsiStripping:
    """`ollama run` writes spinner and cursor escapes into the captured stream."""

    def test_escapes_are_removed_so_code_compiles(self):
        from shared.llm.local import _strip_ansi

        dirty = "\x1b[?25l\x1b[2Kdef solve():\n    return 42\n\x1b[?25h"

        clean = _strip_ansi(dirty)

        assert "\x1b" not in clean
        compile(clean, "<test>", "exec")  # raised "non-printable character U+001B"

    def test_plain_text_is_untouched(self):
        from shared.llm.local import _strip_ansi

        code = "def solve():\n    return 1\n"

        assert _strip_ansi(code) == code
