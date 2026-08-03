"""Paid providers must not be reachable just because a key exists.

The solver runs on local Ollama models. Anthropic and OpenAI bill per token, so
constructing them requires an explicit opt-in beyond having credentials present --
a stray key left in .env must never start incurring cost.
"""

import pytest

from shared.errors import ProviderError
from shared.llm.providers import (
    AnthropicProvider,
    OpenAIProvider,
    ProviderFactory,
    remote_providers_enabled,
)


@pytest.fixture
def remote_enabled(monkeypatch):
    monkeypatch.setenv("ENABLE_REMOTE_PROVIDERS", "true")


@pytest.fixture
def remote_disabled(monkeypatch):
    monkeypatch.delenv("ENABLE_REMOTE_PROVIDERS", raising=False)


class TestRemoteProviderGate:
    @pytest.mark.parametrize("provider", ["anthropic", "openai"])
    def test_blocked_by_default_even_with_a_key(self, provider, remote_disabled):
        with pytest.raises(ProviderError, match="disabled"):
            ProviderFactory.create_provider(provider, "some-model", api_key="sk-fake")

    @pytest.mark.parametrize("value", ["true", "1", "yes", "on", "TRUE", " on "])
    def test_opt_in_values(self, value, monkeypatch):
        monkeypatch.setenv("ENABLE_REMOTE_PROVIDERS", value)
        assert remote_providers_enabled() is True

    @pytest.mark.parametrize("value", ["false", "0", "no", "off", ""])
    def test_non_opt_in_values(self, value, monkeypatch):
        monkeypatch.setenv("ENABLE_REMOTE_PROVIDERS", value)
        assert remote_providers_enabled() is False

    def test_local_provider_is_never_gated(self, remote_disabled):
        """Ollama is free and local -- the gate must not touch it."""
        provider = ProviderFactory.create_provider("ollama", "qwen2.5-coder:7b")
        assert provider is not None

    def test_enabled_still_requires_a_key(self, remote_enabled):
        with pytest.raises(ValueError, match="API key required"):
            ProviderFactory.create_provider("anthropic", "some-model", api_key=None)


class TestProviderConstruction:
    """Both providers previously skipped super().__init__()."""

    @pytest.mark.parametrize("cls", [AnthropicProvider, OpenAIProvider])
    def test_base_attributes_are_set(self, cls):
        provider = cls("some-model", api_key="sk-fake")

        # Reading either of these used to raise AttributeError.
        assert isinstance(provider.temperature, float)
        assert isinstance(provider.max_tokens, int)
        assert provider.max_tokens > 0

    @pytest.mark.parametrize("cls", [AnthropicProvider, OpenAIProvider])
    def test_overrides_are_honoured(self, cls):
        provider = cls("some-model", api_key="sk-fake", temperature=0.7, max_tokens=123)

        assert provider.temperature == pytest.approx(0.7)
        assert provider.max_tokens == 123

    @pytest.mark.parametrize("cls", [AnthropicProvider, OpenAIProvider])
    def test_client_has_a_timeout(self, cls):
        """Neither client previously set one, so a hung request never returned."""
        provider = cls("some-model", api_key="sk-fake")

        assert provider.client.timeout is not None
