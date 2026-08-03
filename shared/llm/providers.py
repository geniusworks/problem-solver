"""Module for managing different LLM providers."""

import json
import os
import logging
import yaml
from abc import ABC
from dataclasses import dataclass
from time import time
from typing import Any, AsyncGenerator, Dict, List, Optional

import aiohttp
import anthropic
import openai

from shared.config import (
    MODELS_CONFIG, DEFAULT_TEMPERATURE, DEFAULT_MAX_TOKENS, DEFAULT_TIMEOUT
)
from shared.errors import ProviderError

# The SDKs retry connection errors, 408, 409, 429 and 5xx with exponential
# backoff. Two retries is their own default; raising it here would multiply
# worst-case wall-clock by timeout x (max_retries + 1).
DEFAULT_MAX_RETRIES = 2

logger = logging.getLogger(__name__)


class RateLimitError(ProviderError):
    """Rate limit exceeded."""


class ProviderTimeoutError(ProviderError):
    """Provider timeout."""


class AuthenticationError(ProviderError):
    """Authentication failed."""


class ServiceUnavailableError(ProviderError):
    """Service unavailable."""


@dataclass
class GenerationResult:
    """Result from a model generation."""

    content: str
    total_tokens: int


class ModelProvider(ABC):
    """Abstract base class for model providers."""

    def __init__(
        self,
        *,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> None:
        """Initialize base provider with config defaults.

        Exposes attributes used by tests:
        - temperature: default from `config.models.yaml` or overridden
        - max_tokens: default from `config.models.yaml` or overridden
        """
        self.temperature = (
            DEFAULT_TEMPERATURE if temperature is None else float(temperature)
        )
        self.max_tokens = (
            DEFAULT_MAX_TOKENS if max_tokens is None else int(max_tokens)
        )

    async def generate(
        self,
        prompt: str,
        *,
        system_prompt: Optional[str] = None,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        top_p: float = 1.0,
    ) -> GenerationResult:
        """Generate text from the model."""
        raise NotImplementedError

    async def stream(
        self,
        prompt: str,
        *,
        system_prompt: Optional[str] = None,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        top_p: float = 1.0,
    ) -> AsyncGenerator[str, None]:
        """Stream text from the model."""
        raise NotImplementedError

    async def cleanup(self) -> None:
        """Clean up any resources."""
        pass

    @staticmethod
    def _format_messages(
        prompt: str, system_prompt: Optional[str] = None
    ) -> List[Dict[str, str]]:
        """Format messages for the model."""
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        return messages


class AnthropicProvider(ModelProvider):
    """Provider for Anthropic's Claude models."""

    def __init__(
        self,
        model_name: str,
        api_key: str,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        timeout: float = DEFAULT_TIMEOUT,
        max_retries: int = DEFAULT_MAX_RETRIES,
    ):
        """Initialize the provider.

        super().__init__() was previously not called, so self.temperature and
        self.max_tokens were never set and any read of them raised AttributeError.
        """
        super().__init__(temperature=temperature, max_tokens=max_tokens)
        self.model_name = model_name
        # The SDK retries connection errors, 408, 409, 429 and 5xx with
        # exponential backoff; there is no need to hand-roll a retry loop.
        self.client = anthropic.AsyncAnthropic(
            api_key=api_key, timeout=timeout, max_retries=max_retries
        )

    async def generate(
        self,
        prompt: str,
        *,
        system_prompt: Optional[str] = None,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        top_p: float = 1.0,
    ) -> GenerationResult:
        """Generate text using Claude."""
        try:
            # max_tokens is required by the Messages API; passing None errors.
            # Anthropic takes the system prompt as a top-level parameter rather
            # than a "system" role message.
            request: Dict[str, Any] = {
                "model": self.model_name,
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": self.max_tokens if max_tokens is None else int(max_tokens),
            }
            if system_prompt:
                request["system"] = system_prompt

            response = await self.client.messages.create(**request)
            text = next(
                (block.text for block in response.content if block.type == "text"), ""
            )
            return GenerationResult(
                content=text,
                total_tokens=response.usage.output_tokens,
            )
        except anthropic.RateLimitError as e:
            raise RateLimitError(str(e)) from e
        except anthropic.APITimeoutError as e:
            raise ProviderTimeoutError(str(e)) from e
        except anthropic.APIError as e:
            if "auth" in str(e).lower():
                raise AuthenticationError(str(e)) from e
            raise ServiceUnavailableError(str(e)) from e

    async def stream(
        self,
        prompt: str,
        *,
        system_prompt: Optional[str] = None,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        top_p: float = 1.0,
    ) -> AsyncGenerator[str, None]:
        """Stream text using Claude."""
        try:
            request: Dict[str, Any] = {
                "model": self.model_name,
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": self.max_tokens if max_tokens is None else int(max_tokens),
            }
            if system_prompt:
                request["system"] = system_prompt

            async with self.client.messages.stream(**request) as stream:
                async for text in stream.text_stream:
                    yield text
        except anthropic.RateLimitError as e:
            raise RateLimitError(str(e)) from e
        except anthropic.APITimeoutError as e:
            raise ProviderTimeoutError(str(e)) from e
        except anthropic.APIError as e:
            if "auth" in str(e).lower():
                raise AuthenticationError(str(e)) from e
            raise ServiceUnavailableError(str(e)) from e

    async def cleanup(self) -> None:
        """Clean up resources."""
        pass


class OpenAIProvider(ModelProvider):
    """Provider for OpenAI models."""

    def __init__(
        self,
        model_name: str,
        api_key: str,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        timeout: float = DEFAULT_TIMEOUT,
        max_retries: int = DEFAULT_MAX_RETRIES,
    ):
        """Initialize the provider.

        super().__init__() was previously not called, leaving self.temperature and
        self.max_tokens unset; the client also had no timeout.
        """
        super().__init__(temperature=temperature, max_tokens=max_tokens)
        self.model_name = model_name
        self.client = openai.AsyncClient(
            api_key=api_key, timeout=timeout, max_retries=max_retries
        )

    async def generate(
        self,
        prompt: str,
        *,
        system_prompt: Optional[str] = None,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        top_p: float = 1.0,
    ) -> GenerationResult:
        """Generate text using OpenAI."""
        try:
            response = await self.client.chat.completions.create(
                model=self.model_name,
                messages=self._format_messages(prompt, system_prompt),
                max_tokens=self.max_tokens if max_tokens is None else int(max_tokens),
                temperature=self.temperature if temperature is None else float(temperature),
                top_p=top_p,
            )
            usage = response.usage
            return GenerationResult(
                content=response.choices[0].message.content or "",
                total_tokens=usage.total_tokens if usage else 0,
            )
        except openai.RateLimitError as e:
            raise RateLimitError(str(e)) from e
        except openai.APITimeoutError as e:
            raise ProviderTimeoutError(str(e)) from e
        except openai.APIError as e:
            if "auth" in str(e).lower():
                raise AuthenticationError(str(e)) from e
            raise ServiceUnavailableError(str(e)) from e

    async def stream(
        self,
        prompt: str,
        *,
        system_prompt: Optional[str] = None,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        top_p: float = 1.0,
    ) -> AsyncGenerator[str, None]:
        """Stream text using OpenAI."""
        try:
            async for chunk in await self.client.chat.completions.create(
                model=self.model_name,
                messages=self._format_messages(prompt, system_prompt),
                max_tokens=max_tokens,
                temperature=temperature,
                top_p=top_p,
                stream=True,
            ):
                if chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content
        except openai.RateLimitError as e:
            raise RateLimitError(str(e)) from e
        except openai.APITimeoutError as e:
            raise ProviderTimeoutError(str(e)) from e
        except openai.APIError as e:
            if "auth" in str(e).lower():
                raise AuthenticationError(str(e)) from e
            raise ServiceUnavailableError(str(e)) from e

    async def cleanup(self) -> None:
        """Clean up resources."""
        await self.client.close()


class OllamaProvider(ModelProvider):
    """Provider for Ollama models."""

    def __init__(self, model: str, debug: bool = False) -> None:
        """Initialize the provider.
        
        Args:
            model: Model name
            debug: Enable debug output
        """
        super().__init__()
        self.model = model
        self.debug = debug
        
        # Load model config
        model_key = model.split(":")[0]  # Extract base name (e.g., 'codellama' from 'codellama:7b')
        self.config = self.get_model_config(model_key)
        
        # Set defaults from config
        self.temperature = self.config.get("temperature", DEFAULT_TEMPERATURE)
        self.max_tokens = self.config.get("max_tokens", DEFAULT_MAX_TOKENS)
        self.context_length = self.config.get("context_length", 4096)
        
        self.base_url = "http://localhost:11434"
        self.session: Optional[aiohttp.ClientSession] = None

    async def _ensure_session(self) -> None:
        """Ensure we have an active session."""
        if not self.session:
            self.session = aiohttp.ClientSession(
                headers={"Accept": "application/x-ndjson"}
            )

    async def generate(
        self,
        prompt: str,
        *,
        system_prompt: Optional[str] = None,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        top_p: float = 1.0,
    ) -> GenerationResult:
        """Generate text using Ollama."""
        await self._ensure_session()
        data = {
            "model": self.model,
            "prompt": prompt,
            "system": system_prompt or "",
            "temperature": temperature,
            "top_p": top_p,
            "stream": False,
        }
        if max_tokens:
            data["num_predict"] = max_tokens

        start_time = time()
        try:
            async with self.session.post(
                f"{self.base_url}/api/generate",
                json=data,
                timeout=aiohttp.ClientTimeout(total=DEFAULT_TIMEOUT),
            ) as response:
                if response.status == 404:
                    raise ServiceUnavailableError(f"Model {self.model} not found")

                response_text = ""
                async for line in response.content:
                    try:
                        data = json.loads(line)
                        if "response" in data:
                            response_text += data["response"]
                    except json.JSONDecodeError:
                        continue

                return GenerationResult(
                    content=response_text,
                    total_tokens=0,  # Ollama doesn't provide token count
                )
        except aiohttp.ClientError as e:
            if time() - start_time >= DEFAULT_TIMEOUT:
                raise ProviderTimeoutError(
                    f"Request timed out for {self.model}"
                ) from e
            raise ServiceUnavailableError(
                f"Failed to connect to Ollama server: {str(e)}"
            ) from e

    async def stream(
        self,
        prompt: str,
        *,
        system_prompt: Optional[str] = None,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        top_p: float = 1.0,
    ) -> AsyncGenerator[str, None]:
        """Stream text using Ollama."""
        await self._ensure_session()
        data = {
            "model": self.model,
            "prompt": prompt,
            "system": system_prompt or "",
            "temperature": temperature,
            "top_p": top_p,
            "stream": True,
        }
        if max_tokens:
            data["num_predict"] = max_tokens

        start_time = time()
        try:
            async with self.session.post(
                f"{self.base_url}/api/generate",
                json=data,
                timeout=aiohttp.ClientTimeout(total=DEFAULT_TIMEOUT),
            ) as response:
                if response.status == 404:
                    raise ServiceUnavailableError(f"Model {self.model} not found")
                async for line in response.content:
                    if line:
                        try:
                            data = json.loads(line)
                            if "response" in data:
                                yield data["response"]
                        except json.JSONDecodeError:
                            continue
        except aiohttp.ClientError as e:
            if time() - start_time >= DEFAULT_TIMEOUT:
                raise ProviderTimeoutError(
                    f"Request timed out for {self.model}"
                ) from e
            raise ServiceUnavailableError(
                f"Failed to connect to Ollama server: {str(e)}"
            ) from e

    async def cleanup(self) -> None:
        """Clean up resources."""
        if self.session:
            await self.session.close()
            self.session = None

    @staticmethod
    def get_model_config(model_key: str) -> Dict[str, str]:
        """Get model config from config/models.yaml"""
        with open("config/models.yaml", "r") as f:
            config = yaml.safe_load(f)
        return config.get(model_key, {})


REMOTE_PROVIDERS = frozenset({"anthropic", "openai"})


def remote_providers_enabled() -> bool:
    """Whether paid, remote providers may be constructed.

    A present API key is deliberately NOT sufficient: a stray key left in .env
    must never be able to start incurring cost. Opting in requires setting
    ENABLE_REMOTE_PROVIDERS explicitly.
    """
    return os.getenv("ENABLE_REMOTE_PROVIDERS", "false").strip().lower() in (
        "true", "1", "yes", "on",
    )


class ProviderFactory:
    """Factory for creating model providers."""

    @staticmethod
    def create_provider(
        provider_type: str, model_name: str, api_key: Optional[str] = None
    ) -> ModelProvider:
        """Create a model provider."""
        if provider_type in REMOTE_PROVIDERS and not remote_providers_enabled():
            raise ProviderError(
                f"Remote provider '{provider_type}' is disabled. These providers bill "
                f"per token, so having an API key configured is not enough to enable "
                f"them: set ENABLE_REMOTE_PROVIDERS=true in .env to opt in."
            )

        if provider_type == "anthropic":
            if not api_key:
                raise ValueError("API key required for Anthropic provider")
            return AnthropicProvider(model_name, api_key)
        elif provider_type == "openai":
            if not api_key:
                raise ValueError("API key required for OpenAI provider")
            return OpenAIProvider(model_name, api_key)
        elif provider_type == "ollama":
            return OllamaProvider(model_name)
        else:
            raise ValueError(f"Unknown provider type: {provider_type}")
