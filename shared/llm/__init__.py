"""LLM integration package."""

from .base import LLMProvider, LLMResponse
from .local import OllamaProvider

__all__ = [
    "LLMProvider",
    "LLMResponse",
    "OllamaProvider",
]
