"""Model-specific implementations and characteristics."""

from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Optional, Set
import logging
from pathlib import Path
import json
import aiohttp
import asyncio
from datetime import datetime
from .hardware import HardwareManager

class ModelProvider(Enum):
    """Available model providers."""
    ANTHROPIC = "anthropic"
    OPENAI = "openai"
    OLLAMA = "ollama"
    LLAMACPP = "llamacpp"

class ModelRegistry:
    """Registry of available models and their characteristics."""
    
    def __init__(self):
        self.hardware = HardwareManager()
        self.models: Dict[str, ModelCharacteristics] = {
            # Smaller, M1-friendly models
            "codellama-7b-instruct": ModelCharacteristics(
                name="codellama-7b-instruct",
                provider=ModelProvider.OLLAMA,
                is_local=True,
                context_length=16384,
                cost_per_1k_tokens=0.0,
                typical_latency=1.0,
                memory_required=8000,
                energy_usage=0.7,
                strengths={
                    "code_generation",
                    "code_completion",
                    "fast_iteration"
                },
                weaknesses={
                    "complex_reasoning",
                    "test_generation"
                },
                best_roles={"PRIMARY", "VALIDATOR"}
            ),
            
            "mistral-7b-instruct": ModelCharacteristics(
                name="mistral-7b-instruct",
                provider=ModelProvider.OLLAMA,
                is_local=True,
                context_length=8192,
                cost_per_1k_tokens=0.0,
                typical_latency=1.0,
                memory_required=8000,
                energy_usage=0.7,
                strengths={
                    "code_generation",
                    "instruction_following",
                    "fast_response"
                },
                weaknesses={
                    "long_context",
                    "complex_algorithms"
                },
                best_roles={"PRIMARY", "VALIDATOR"}
            ),
            
            # Cloud models (always available)
            "claude-3-sonnet": ModelCharacteristics(
                name="claude-3-sonnet",
                provider=ModelProvider.ANTHROPIC,
                is_local=False,
                context_length=200000,
                cost_per_1k_tokens=0.003,
                typical_latency=2.0,
                memory_required=0,
                energy_usage=0,
                strengths={
                    "code_generation",
                    "code_review",
                    "problem_solving",
                    "algorithm_design",
                    "test_generation"
                },
                weaknesses={
                    "very_long_context",
                    "mathematical_proofs"
                },
                best_roles={"PRIMARY", "REVIEWER"}
            ),
            
            # Optional larger models (for M2)
            "codellama-13b-instruct": ModelCharacteristics(
                name="codellama-13b-instruct",
                provider=ModelProvider.OLLAMA,
                is_local=True,
                context_length=16384,
                cost_per_1k_tokens=0.0,
                typical_latency=1.5,
                memory_required=14000,
                energy_usage=1.0,
                strengths={
                    "code_generation",
                    "problem_solving",
                    "python_expertise"
                },
                weaknesses={
                    "complex_tasks",
                    "test_generation"
                },
                best_roles={"PRIMARY", "REVIEWER"}
            )
        }
        
        # Add larger models only if hardware supports them
        if self.hardware.capabilities.max_model_size >= 34:
            self.models.update({
                "codellama-34b-instruct": ModelCharacteristics(
                    name="codellama-34b-instruct",
                    provider=ModelProvider.OLLAMA,
                    is_local=True,
                    context_length=16384,
                    cost_per_1k_tokens=0.0,
                    typical_latency=3.0,
                    memory_required=35000,
                    energy_usage=1.5,
                    strengths={
                        "code_generation",
                        "code_completion",
                        "problem_solving",
                        "python_expertise"
                    },
                    weaknesses={
                        "long_context",
                        "response_time"
                    },
                    best_roles={"PRIMARY", "REVIEWER"}
                )
            })
        
        self.logger = logging.getLogger(__name__)
        self._load_custom_characteristics()
    
    def _load_custom_characteristics(self):
        """Load any custom model characteristics from config."""
        config_path = Path("model_characteristics.json")
        if config_path.exists():
            try:
                with open(config_path) as f:
                    custom = json.load(f)
                for name, chars in custom.items():
                    if name not in self.models:
                        self.models[name] = ModelCharacteristics(**chars)
            except Exception as e:
                self.logger.error(f"Error loading custom characteristics: {e}")

class ModelManager:
    """Manages model interactions and availability."""
    
    def __init__(self):
        self.registry = ModelRegistry()
        self.available_models: Dict[str, bool] = {}
        self.session: Optional[aiohttp.ClientSession] = None
        self.logger = logging.getLogger(__name__)
    
    async def initialize(self):
        """Initialize model manager and check availability."""
        self.session = aiohttp.ClientSession()
        await self._check_model_availability()
    
    async def cleanup(self):
        """Cleanup resources."""
        if self.session:
            await self.session.close()
    
    async def _check_model_availability(self):
        """Check which models are currently available."""
        for name, chars in self.registry.models.items():
            try:
                if chars.is_local:
                    # Check if Ollama/LlamaCpp model is loaded
                    available = await self._check_local_model(name, chars.provider)
                else:
                    # Check if we have API keys for cloud models
                    available = self._check_cloud_model(chars.provider)
                
                self.available_models[name] = available
                
                if available:
                    self.logger.info(f"Model {name} is available")
                else:
                    self.logger.warning(f"Model {name} is not available")
                    
            except Exception as e:
                self.logger.error(f"Error checking {name} availability: {e}")
                self.available_models[name] = False
    
    async def _check_local_model(self, name: str, provider: ModelProvider) -> bool:
        """Check if a local model is available."""
        if provider == ModelProvider.OLLAMA:
            try:
                async with self.session.get("http://localhost:11434/api/tags") as response:
                    if response.status == 200:
                        tags = await response.json()
                        return any(name in tag["name"] for tag in tags["models"])
            except:
                return False
                
        elif provider == ModelProvider.LLAMACPP:
            # Implement LlamaCpp availability check
            return False
            
        return False
    
    def _check_cloud_model(self, provider: ModelProvider) -> bool:
        """Check if we have API keys for cloud models."""
        import os
        
        if provider == ModelProvider.ANTHROPIC:
            return bool(os.getenv("ANTHROPIC_API_KEY"))
        elif provider == ModelProvider.OPENAI:
            return bool(os.getenv("OPENAI_API_KEY"))
        
        return False
    
    def get_available_models(self) -> List[str]:
        """Get list of currently available models."""
        return [name for name, available in self.available_models.items() 
                if available]
    
    def get_characteristics(self, model_name: str) -> Optional[ModelCharacteristics]:
        """Get characteristics of a specific model."""
        return self.registry.models.get(model_name)
    
    def suggest_models(self,
                      problem_type: str,
                      max_cost: Optional[float] = None,
                      max_latency: Optional[float] = None) -> List[str]:
        """Suggest suitable models based on constraints."""
        suitable = []
        
        for name, chars in self.registry.models.items():
            if not self.available_models.get(name, False):
                continue
                
            # Check constraints
            if max_cost is not None and chars.cost_per_1k_tokens > max_cost:
                continue
            if max_latency is not None and chars.typical_latency > max_latency:
                continue
                
            # Check if model is good for problem type
            if (problem_type in chars.strengths or 
                not chars.weaknesses.intersection({problem_type})):
                suitable.append(name)
        
        return suitable

@dataclass
class ModelCharacteristics:
    """Known characteristics of a model."""
    name: str
    provider: ModelProvider
    is_local: bool
    context_length: int
    cost_per_1k_tokens: float
    typical_latency: float  # seconds
    memory_required: int    # MB
    energy_usage: float     # relative to baseline
    strengths: Set[str]
    weaknesses: Set[str]
    best_roles: Set[str]   # ModelRole names this model excels at
