"""Module for managing different LLM providers."""

import json
import logging
from abc import ABC
from dataclasses import dataclass
from time import time
from typing import AsyncGenerator, Dict, List, Optional

import aiohttp
import anthropic
import openai

logger = logging.getLogger(__name__)


class ProviderError(Exception):
    """Base class for provider-related errors."""


class RateLimitError(ProviderError):
    """Raised when a provider's rate limit is exceeded."""


class ProviderTimeoutError(ProviderError):
    """Raised when a provider request times out."""


class AuthenticationError(ProviderError):
    """Raised when authentication with a provider fails."""


class ServiceUnavailableError(ProviderError):
    """Raised when a provider's service is unavailable."""


@dataclass
class GenerationResult:
    """Result from a model generation."""

    content: str
    total_tokens: int


class ModelProvider(ABC):
    """Abstract base class for model providers."""

    async def generate(
        self,
        prompt: str,
        *,
        system_prompt: Optional[str] = None,
        max_tokens: Optional[int] = None,
        temperature: float = 0.7,
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
        temperature: float = 0.7,
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

    def __init__(self, model_name: str, api_key: str):
        """Initialize the provider."""
        self.model_name = model_name
        self.client = anthropic.AsyncAnthropic(api_key=api_key)

    async def generate(
        self,
        prompt: str,
        *,
        system_prompt: Optional[str] = None,
        max_tokens: Optional[int] = None,
        temperature: float = 0.7,
        top_p: float = 1.0,
    ) -> GenerationResult:
        """Generate text using Claude."""
        try:
            response = await self.client.messages.create(
                model=self.model_name,
                messages=self._format_messages(prompt, system_prompt),
                max_tokens=max_tokens,
                temperature=temperature,
                top_p=top_p,
            )
            return GenerationResult(
                content=response.content[0].text,
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
        temperature: float = 0.7,
        top_p: float = 1.0,
    ) -> AsyncGenerator[str, None]:
        """Stream text using Claude."""
        try:
            async with self.client.messages.stream(
                model=self.model_name,
                messages=self._format_messages(prompt, system_prompt),
                max_tokens=max_tokens,
                temperature=temperature,
                top_p=top_p,
            ) as stream:
                async for chunk in stream:
                    if chunk.content:
                        yield chunk.content[0].text
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

    def __init__(self, model_name: str, api_key: str):
        """Initialize the provider."""
        self.model_name = model_name
        self.client = openai.AsyncClient(api_key=api_key)

    async def generate(
        self,
        prompt: str,
        *,
        system_prompt: Optional[str] = None,
        max_tokens: Optional[int] = None,
        temperature: float = 0.7,
        top_p: float = 1.0,
    ) -> GenerationResult:
        """Generate text using OpenAI."""
        try:
            response = await self.client.chat.completions.create(
                model=self.model_name,
                messages=self._format_messages(prompt, system_prompt),
                max_tokens=max_tokens,
                temperature=temperature,
                top_p=top_p,
            )
            return GenerationResult(
                content=response.choices[0].message.content or "",
                total_tokens=response.usage.total_tokens,
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
        temperature: float = 0.7,
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

    def __init__(self, model_name: str, base_url: str = "http://localhost:11434"):
        """Initialize the provider."""
        self.model_name = model_name
        self.base_url = base_url
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
        temperature: float = 0.7,
        top_p: float = 1.0,
    ) -> GenerationResult:
        """Generate text using Ollama."""
        await self._ensure_session()
        data = {
            "model": self.model_name,
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
                timeout=aiohttp.ClientTimeout(total=60),
            ) as response:
                if response.status == 404:
                    raise ServiceUnavailableError(f"Model {self.model_name} not found")

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
            if time() - start_time >= 60:
                raise ProviderTimeoutError(
                    f"Request timed out for {self.model_name}"
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
        temperature: float = 0.7,
        top_p: float = 1.0,
    ) -> AsyncGenerator[str, None]:
        """Stream text using Ollama."""
        await self._ensure_session()
        data = {
            "model": self.model_name,
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
                timeout=aiohttp.ClientTimeout(total=60),
            ) as response:
                if response.status == 404:
                    raise ServiceUnavailableError(f"Model {self.model_name} not found")
                async for line in response.content:
                    if line:
                        try:
                            data = json.loads(line)
                            if "response" in data:
                                yield data["response"]
                        except json.JSONDecodeError:
                            continue
        except aiohttp.ClientError as e:
            if time() - start_time >= 60:
                raise ProviderTimeoutError(
                    f"Request timed out for {self.model_name}"
                ) from e
            raise ServiceUnavailableError(
                f"Failed to connect to Ollama server: {str(e)}"
            ) from e

    async def cleanup(self) -> None:
        """Clean up resources."""
        if self.session:
            await self.session.close()
            self.session = None


class ProviderFactory:
    """Factory for creating model providers."""

    @staticmethod
    def create_provider(
        provider_type: str, model_name: str, api_key: Optional[str] = None
    ) -> ModelProvider:
        """Create a model provider."""
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
