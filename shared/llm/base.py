"""Base classes for LLM providers."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional, Dict, Any, List


@dataclass
class LLMResponse:
    """Response from an LLM provider."""

    content: str
    confidence: float
    metadata: Dict[str, Any]
    error: Optional[str] = None


class LLMProvider(ABC):
    """Base class for LLM providers."""

    def __init__(self, **kwargs):
        self.config = kwargs
        self.name = self.__class__.__name__

    @abstractmethod
    async def generate_solution(
        self, 
        problem,
        year: int,
        day: int,
        strategies: Optional[List[str]] = None,
        strategy_effectiveness: Optional[Dict[str, float]] = None
    ) -> str:
        """Generate a solution for the given problem."""
        pass

    @abstractmethod
    async def generate(self, prompt: str) -> LLMResponse:
        """Generate a response from the LLM."""
        pass

    @abstractmethod
    def validate_solution(
        self, solution: str, test_cases: List[Dict[str, str]]
    ) -> bool:
        """Validate a solution against test cases."""
        pass

    @property
    @abstractmethod
    def cost_per_token(self) -> float:
        """Return the cost per token for this provider."""
        pass

    @property
    @abstractmethod
    def is_local(self) -> bool:
        """Return whether this is a local provider."""
        pass

    @abstractmethod
    async def improve_solution(self, solution: str, problem, feedback: Optional[str] = None) -> str:
        """Improve an existing solution based on feedback.

        Args:
            solution: The current solution code
            problem: The problem being solved
            feedback: Optional feedback about what needs improvement

        Returns:
            Improved solution code
        """
        pass
