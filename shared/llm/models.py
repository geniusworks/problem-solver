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
    """Original creators/providers of the models."""
    ANTHROPIC = "anthropic"      # Claude models
    OPENAI = "openai"           # GPT models
    META = "meta"               # LLaMA models
    MICROSOFT = "microsoft"     # Phi models
    MISTRAL = "mistral"        # Mistral models


class ModelRunner(Enum):
    """Tools/platforms that run the models."""
    OLLAMA = "ollama"           # Local model runner with easy model management
    LLAMACPP = "llamacpp"       # High-performance local inference
    ANTHROPIC_API = "anthropic"  # Cloud API
    OPENAI_API = "openai"       # Cloud API


@dataclass
class ModelCapabilities:
    """Model capabilities and limitations."""

    max_context_length: int
    max_output_length: int
    supports_streaming: bool = False
    supports_functions: bool = False
    supports_vision: bool = False


@dataclass
class ModelPerformance:
    """Model performance characteristics."""

    tokens_per_second: float
    cost_per_token: float
    avg_latency: float = 0.0
    error_rate: float = 0.0
    success_rate: float = 1.0


@dataclass
class ModelCharacteristics:
    """Characteristics of a language model."""

    name: str
    provider: ModelProvider     # Who created the model
    runner: ModelRunner         # What runs the model
    capabilities: ModelCapabilities
    performance: ModelPerformance
    is_local: bool = False
    last_used: Optional[datetime] = None
    strengths: Set[str] = set()
    weaknesses: Set[str] = set()
    best_roles: Set[str] = set()


class ModelRegistry:
    """Registry of available models and their characteristics."""

    def __init__(self):
        self.hardware = HardwareManager()
        self.models: Dict[str, ModelCharacteristics] = {
            # Smaller, M1-friendly models
            "codellama-7b-instruct": ModelCharacteristics(
                name="codellama-7b-instruct",
                provider=ModelProvider.META,
                runner=ModelRunner.OLLAMA,
                capabilities=ModelCapabilities(
                    max_context_length=16384, max_output_length=16384
                ),
                performance=ModelPerformance(
                    tokens_per_second=1000, cost_per_token=0.0
                ),
                is_local=True,
                strengths={"code_generation", "code_completion", "fast_iteration"},
                weaknesses={"complex_reasoning", "test_generation"},
                best_roles={"PRIMARY", "VALIDATOR"},
            ),
            "mistral-7b-instruct": ModelCharacteristics(
                name="mistral-7b-instruct",
                provider=ModelProvider.MISTRAL,
                runner=ModelRunner.OLLAMA,
                capabilities=ModelCapabilities(
                    max_context_length=8192, max_output_length=8192
                ),
                performance=ModelPerformance(
                    tokens_per_second=1000, cost_per_token=0.0
                ),
                is_local=True,
                strengths={"code_generation", "instruction_following", "fast_response"},
                weaknesses={"long_context", "complex_algorithms"},
                best_roles={"PRIMARY", "VALIDATOR"},
            ),
            "phi4": ModelCharacteristics(
                name="phi4",
                provider=ModelProvider.MICROSOFT,
                runner=ModelRunner.OLLAMA,
                capabilities=ModelCapabilities(
                    max_context_length=4096, max_output_length=4096
                ),
                performance=ModelPerformance(
                    tokens_per_second=1200, cost_per_token=0.0
                ),
                is_local=True,
                strengths={"code_generation", "fast_response", "efficient_inference"},
                weaknesses={"long_context", "complex_reasoning"},
                best_roles={"PRIMARY", "VALIDATOR"},
            ),
            # Cloud models (always available)
            "claude-3-sonnet": ModelCharacteristics(
                name="claude-3-sonnet",
                provider=ModelProvider.ANTHROPIC,
                runner=ModelRunner.ANTHROPIC_API,
                capabilities=ModelCapabilities(
                    max_context_length=200000, max_output_length=200000
                ),
                performance=ModelPerformance(
                    tokens_per_second=100, cost_per_token=0.003
                ),
                strengths={
                    "code_generation",
                    "code_review",
                    "problem_solving",
                    "algorithm_design",
                    "test_generation",
                },
                weaknesses={"very_long_context", "mathematical_proofs"},
                best_roles={"PRIMARY", "REVIEWER"},
            ),
            # Optional larger models (for M2)
            "codellama-13b-instruct": ModelCharacteristics(
                name="codellama-13b-instruct",
                provider=ModelProvider.META,
                runner=ModelRunner.OLLAMA,
                capabilities=ModelCapabilities(
                    max_context_length=16384, max_output_length=16384
                ),
                performance=ModelPerformance(tokens_per_second=500, cost_per_token=0.0),
                is_local=True,
                strengths={"code_generation", "problem_solving", "python_expertise"},
                weaknesses={"complex_tasks", "test_generation"},
                best_roles={"PRIMARY", "REVIEWER"},
            ),
        }

        # Add larger models only if hardware supports them
        if self.hardware.capabilities.max_model_size >= 34:
            self.models.update(
                {
                    "codellama-34b-instruct": ModelCharacteristics(
                        name="codellama-34b-instruct",
                        provider=ModelProvider.META,
                        runner=ModelRunner.OLLAMA,
                        capabilities=ModelCapabilities(
                            max_context_length=16384, max_output_length=16384
                        ),
                        performance=ModelPerformance(
                            tokens_per_second=200, cost_per_token=0.0
                        ),
                        is_local=True,
                        strengths={
                            "code_generation",
                            "code_completion",
                            "problem_solving",
                            "python_expertise",
                        },
                        weaknesses={"long_context", "response_time"},
                        best_roles={"PRIMARY", "REVIEWER"},
                    )
                }
            )

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
                    available = await self._check_local_model(name, chars.runner)
                else:
                    # Check if we have API keys for cloud models
                    available = self._check_cloud_model(chars.runner)

                self.available_models[name] = available

                if available:
                    self.logger.info(f"Model {name} is available")
                else:
                    self.logger.warning(f"Model {name} is not available")

            except Exception as e:
                self.logger.error(f"Error checking {name} availability: {e}")
                self.available_models[name] = False

    async def _check_local_model(self, name: str, runner: ModelRunner) -> bool:
        """Check if a local model is available and handle installation if needed."""
        if runner == ModelRunner.OLLAMA:
            try:
                async with self.session.get(
                    "http://localhost:11434/api/tags"
                ) as response:
                    if response.status == 200:
                        tags = await response.json()
                        if any(name in tag["name"] for tag in tags["models"]):
                            return True
                        
                        # Model not found, prompt for installation
                        self.logger.info(f"Model {name} not found locally. Attempting installation...")
                        print(f"\nModel {name} is not installed. Would you like to install it? (y/N)")
                        
                        # Use asyncio to handle user input without blocking
                        try:
                            # Create an event loop for user input
                            loop = asyncio.get_event_loop()
                            response = await loop.run_in_executor(None, input)
                            
                            if response.lower() == 'y':
                                self.logger.info(f"Installing model {name}...")
                                print(f"Installing {name}... This may take a while.")
                                
                                # Pull the model
                                async with self.session.post(
                                    "http://localhost:11434/api/pull",
                                    json={"name": name}
                                ) as pull_response:
                                    while True:
                                        line = await pull_response.content.readline()
                                        if not line:
                                            break
                                        status = json.loads(line)
                                        if "status" in status:
                                            print(f"Progress: {status.get('status')}")
                                        
                                    if pull_response.status == 200:
                                        self.logger.info(f"Successfully installed {name}")
                                        print(f"\n{name} has been successfully installed!")
                                        return True
                                    else:
                                        self.logger.error(f"Failed to install {name}")
                                        print(f"\nFailed to install {name}. Skipping...")
                            else:
                                self.logger.info(f"User skipped installation of {name}")
                                print(f"\nSkipping installation of {name}...")
                        except Exception as e:
                            self.logger.error(f"Error during model installation: {str(e)}")
                            print(f"\nError during model installation: {str(e)}")
            except Exception as e:
                self.logger.error(f"Error checking model availability: {str(e)}")
                return False

        elif runner == ModelRunner.LLAMACPP:
            # Implement LlamaCpp availability check
            return False

        return False

    def _check_cloud_model(self, runner: ModelRunner) -> bool:
        """Check if we have API keys for cloud models."""
        import os

        if runner == ModelRunner.ANTHROPIC_API:
            return bool(os.getenv("ANTHROPIC_API_KEY"))
        elif runner == ModelRunner.OPENAI_API:
            return bool(os.getenv("OPENAI_API_KEY"))

        return False

    def get_available_models(self) -> List[str]:
        """Get list of currently available models."""
        return [name for name, available in self.available_models.items() if available]

    def get_characteristics(self, model_name: str) -> Optional[ModelCharacteristics]:
        """Get characteristics of a specific model."""
        return self.registry.models.get(model_name)

    def suggest_models(
        self,
        problem_type: str,
        max_cost: Optional[float] = None,
        max_latency: Optional[float] = None,
    ) -> List[str]:
        """Suggest suitable models based on constraints."""
        suitable = []

        for name, chars in self.registry.models.items():
            if not self.available_models.get(name, False):
                continue

            # Check constraints
            if max_cost is not None and chars.performance.cost_per_token > max_cost:
                continue
            if max_latency is not None and chars.performance.avg_latency > max_latency:
                continue

            # Check if model is good for problem type
            if problem_type in chars.strengths or not chars.weaknesses.intersection(
                {problem_type}
            ):
                suitable.append(name)

        return suitable
