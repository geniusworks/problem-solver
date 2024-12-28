"""Ensemble methods for combining multiple LLM providers."""

from enum import Enum
from typing import List, Dict, Optional, Tuple
import asyncio
import logging
from dataclasses import dataclass

from .base import LLMProvider, LLMResponse

@dataclass
class ProviderHealth:
    """Health status of a provider."""
    is_available: bool
    last_success: Optional[float] = None
    error_count: int = 0
    average_latency: float = 0.0
    success_rate: float = 1.0

class VotingStrategy(Enum):
    """Strategy for combining multiple LLM responses."""
    MAJORITY = "majority"      # Use most common solution
    WEIGHTED = "weighted"      # Weight by provider confidence and cost
    CASCADE = "cascade"        # Try providers in order until success
    CONSENSUS = "consensus"    # Require agreement from all providers
    QUORUM = "quorum"         # Require agreement from specified fraction

class ModelEnsemble:
    """Combines multiple LLM providers for better results."""
    
    def __init__(self, 
                 providers: List[LLMProvider],
                 strategy: VotingStrategy = VotingStrategy.QUORUM,
                 min_confidence: float = 0.7,
                 quorum_fraction: float = 2/3,
                 timeout: float = 30.0):
        self.providers = providers
        self.strategy = strategy
        self.min_confidence = min_confidence
        self.quorum_fraction = quorum_fraction
        self.timeout = timeout
        self.logger = logging.getLogger(__name__)
        
        # Health tracking for each provider
        self.health: Dict[str, ProviderHealth] = {
            provider.name: ProviderHealth(is_available=True)
            for provider in providers
        }
        
        # Sort providers by reliability (local first, then by cost_per_token)
        self._sort_providers()
    
    def _sort_providers(self):
        """Sort providers by reliability and cost."""
        def provider_score(p: LLMProvider) -> Tuple[float, float]:
            health = self.health[p.name]
            reliability = health.success_rate if health.is_available else 0
            # Prioritize: local > reliability > cost
            return (-1 if p.is_local else 0, -reliability, p.cost_per_token)
        
        self.providers.sort(key=provider_score)
    
    async def _get_response_with_timeout(self, 
                                       provider: LLMProvider, 
                                       prompt: str) -> Optional[LLMResponse]:
        """Get response from provider with timeout and error handling."""
        try:
            response = await asyncio.wait_for(
                provider.generate(prompt),
                timeout=self.timeout
            )
            
            # Update health metrics
            health = self.health[provider.name]
            health.last_success = asyncio.get_event_loop().time()
            health.success_rate = (health.success_rate * 9 + 1) / 10
            
            return response
            
        except Exception as e:
            self.logger.warning(f"Provider {provider.name} failed: {str(e)}")
            health = self.health[provider.name]
            health.error_count += 1
            health.success_rate = (health.success_rate * 9) / 10
            
            # Mark as unavailable after repeated failures
            if health.error_count >= 3:
                health.is_available = False
                self.logger.error(f"Provider {provider.name} marked as unavailable")
            
            return None
    
    async def generate_solution(self, prompt: str) -> LLMResponse:
        """Generate solution using multiple providers with fallback."""
        available_providers = [p for p in self.providers 
                             if self.health[p.name].is_available]
        
        if not available_providers:
            raise RuntimeError("No providers available")
        
        # Get responses from all available providers
        response_tasks = [
            self._get_response_with_timeout(provider, prompt)
            for provider in available_providers
        ]
        
        responses = await asyncio.gather(*response_tasks)
        valid_responses = [r for r in responses if r and r.error is None]
        
        if not valid_responses:
            return LLMResponse(
                content="",
                confidence=0.0,
                metadata={"error": "No valid responses received"},
                error="All providers failed"
            )
        
        if self.strategy == VotingStrategy.QUORUM:
            # Check if we have enough responses for a quorum
            required_count = max(2, int(len(available_providers) * self.quorum_fraction))
            if len(valid_responses) < required_count:
                self.logger.warning(
                    f"Only {len(valid_responses)} responses received, "
                    f"needed {required_count} for quorum"
                )
                # Fall back to majority if we can't reach quorum
                self.strategy = VotingStrategy.MAJORITY
        
        result = self._combine_responses(valid_responses)
        
        # Periodically check if unavailable providers have recovered
        asyncio.create_task(self._check_provider_health())
        
        return result
    
    async def _check_provider_health(self):
        """Check if unavailable providers have recovered."""
        for provider in self.providers:
            health = self.health[provider.name]
            if not health.is_available:
                # Try a simple test prompt
                response = await self._get_response_with_timeout(
                    provider,
                    "Return 'ok' if you're working."
                )
                if response and response.content.strip().lower() == 'ok':
                    health.is_available = True
                    health.error_count = 0
                    self.logger.info(f"Provider {provider.name} is available again")
        
        # Resort providers based on updated health
        self._sort_providers()
    
    def _combine_responses(self, responses: List[LLMResponse]) -> LLMResponse:
        """Combine multiple responses based on strategy."""
        if not responses:
            return LLMResponse(
                content="",
                confidence=0.0,
                metadata={},
                error="No responses received"
            )
        
        if self.strategy == VotingStrategy.MAJORITY:
            # Use most common solution
            solutions = {}
            for r in responses:
                if r.error is None:
                    solutions[r.content] = solutions.get(r.content, 0) + 1
            
            if not solutions:
                return responses[0]  # Return first response if all had errors
            
            best_solution = max(solutions.items(), key=lambda x: x[1])[0]
            confidence = solutions[best_solution] / len(responses)
            
            return LLMResponse(
                content=best_solution,
                confidence=confidence,
                metadata={"voting_results": solutions},
                error=None
            )
        
        elif self.strategy == VotingStrategy.WEIGHTED:
            # Weight by provider confidence and inverse of cost
            weights = {}
            for r, p in zip(responses, self.providers):
                if r.error is None:
                    weight = r.confidence * (1.0 / (p.cost_per_token + 0.0001))
                    weights[r.content] = weights.get(r.content, 0) + weight
            
            if not weights:
                return responses[0]
            
            best_solution = max(weights.items(), key=lambda x: x[1])[0]
            total_weight = sum(weights.values())
            confidence = weights[best_solution] / total_weight
            
            return LLMResponse(
                content=best_solution,
                confidence=confidence,
                metadata={"weighted_results": weights},
                error=None
            )
        
        elif self.strategy == VotingStrategy.CONSENSUS:
            # Check if all providers agree
            valid_responses = [r for r in responses if r.error is None]
            if not valid_responses:
                return responses[0]
            
            if len(set(r.content for r in valid_responses)) == 1:
                # All agree
                return LLMResponse(
                    content=valid_responses[0].content,
                    confidence=sum(r.confidence for r in valid_responses) / len(valid_responses),
                    metadata={"consensus": True},
                    error=None
                )
            else:
                # No consensus
                return LLMResponse(
                    content="",
                    confidence=0.0,
                    metadata={"consensus": False},
                    error="No consensus reached"
                )
        
        # Default to first response
        return responses[0]
    
    def validate_solution(self, solution: str, test_cases: List[Dict[str, str]]) -> bool:
        """Validate solution using multiple providers."""
        votes = []
        for provider in self.providers:
            try:
                votes.append(provider.validate_solution(solution, test_cases))
            except Exception:
                continue
        
        if not votes:
            return False
        
        # Require majority agreement
        return sum(votes) > len(votes) / 2
