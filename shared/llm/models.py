"""Model-specific implementations and characteristics."""

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Set
import logging
from pathlib import Path
import json
import aiohttp
import asyncio
from datetime import datetime
from .hardware import HardwareManager, BaseError


class ModelProvider(Enum):
    """Original creators/providers of the models."""
    ANTHROPIC = "anthropic"      # Claude models
    OPENAI = "openai"           # GPT models
    META = "meta"               # LLaMA models
    MICROSOFT = "microsoft"     # Phi models
    MISTRAL = "mistral"        # Mistral models

    ALIBABA = "alibaba"        # Qwen models


class ModelRunner(Enum):
    """Tools/platforms that run the models."""
    OLLAMA = "ollama"           # Local model runner with easy model management
    LLAMACPP = "llamacpp"       # High-performance local inference
    ANTHROPIC_API = "anthropic"  # Cloud API
    OPENAI_API = "openai"       # Cloud API


class ModelRole(Enum):
    """Roles that models can play in the problem-solving process."""
    PRIMARY = "primary"      # Main solution generator
    REVIEWER = "reviewer"    # Reviews and improves solutions
    VALIDATOR = "validator"  # Validates solutions
    BACKUP = "backup"       # Backup model when others fail


@dataclass
class ModelCapabilities:
    """Model capabilities and limitations."""

    max_context_length: int
    max_output_length: int
    supports_streaming: bool = False
    supports_functions: bool = False
    supports_vision: bool = False


@dataclass
class RolePerformance:
    """Performance metrics for a specific role."""
    success_rate: float = 0.0
    avg_latency: float = 0.0
    last_used: Optional[datetime] = None
    problems_attempted: int = 0
    problems_solved: int = 0


@dataclass
class ModelPerformance:
    """Model performance characteristics."""

    tokens_per_second: float
    cost_per_token: float
    role_performance: Dict[ModelRole, RolePerformance] = field(default_factory=lambda: {
        role: RolePerformance() for role in ModelRole
    })
    overall_success_rate: float = 1.0
    overall_error_rate: float = 0.0


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
    best_roles: Set[ModelRole] = set()


class ModelRegistry:
    """Registry of available models and their characteristics."""

    def __init__(self):
        """Initialize the model registry."""
        self.hardware = HardwareManager()
        self.models: Dict[str, ModelCharacteristics] = {}
        self.logger = logging.getLogger(__name__)
        
        # Register base models (always available)
        self._register_base_models()
        
        # Register additional models based on hardware capabilities
        self._register_hardware_dependent_models()
        
        self._load_custom_characteristics()

    def _register_base_models(self):
        """Register models that are always available."""
        base_models = {
            "codellama:7b": (7, ModelCharacteristics(
                name="codellama:7b",
                provider=ModelProvider.META,
                runner=ModelRunner.OLLAMA,
                capabilities=ModelCapabilities(
                    max_context_length=16384, max_output_length=16384
                ),
                performance=ModelPerformance(
                    tokens_per_second=1000, cost_per_token=0.0,
                    role_performance={
                        ModelRole.PRIMARY: RolePerformance(success_rate=0.9, avg_latency=0.5),
                        ModelRole.REVIEWER: RolePerformance(success_rate=0.8, avg_latency=1.0),
                        ModelRole.VALIDATOR: RolePerformance(success_rate=0.95, avg_latency=0.2),
                    }
                ),
                is_local=True,
                strengths={"code_generation", "code_completion", "fast_iteration"},
                weaknesses={"complex_reasoning", "test_generation"},
                best_roles={ModelRole.PRIMARY, ModelRole.VALIDATOR},
            )),

                runner=ModelRunner.OLLAMA,
                capabilities=ModelCapabilities(
                    max_context_length=8192, max_output_length=8192
                ),
                performance=ModelPerformance(
                    tokens_per_second=1000, cost_per_token=0.0,
                    role_performance={
                        ModelRole.PRIMARY: RolePerformance(success_rate=0.85, avg_latency=0.7),
                        ModelRole.REVIEWER: RolePerformance(success_rate=0.9, avg_latency=0.8),
                        ModelRole.VALIDATOR: RolePerformance(success_rate=0.92, avg_latency=0.3),
                    }
                ),
                is_local=True,
                strengths={"code_generation", "python_expertise", "code_review", "test_generation"},
                weaknesses={"long_context"},
                best_roles={ModelRole.PRIMARY, ModelRole.REVIEWER, ModelRole.VALIDATOR},
            )),
            "mistral:7b": (7, ModelCharacteristics(
                name="mistral:7b",
                provider=ModelProvider.MISTRAL,
                runner=ModelRunner.OLLAMA,
                capabilities=ModelCapabilities(
                    max_context_length=8192, max_output_length=8192
                ),
                performance=ModelPerformance(
                    tokens_per_second=1000, cost_per_token=0.0,
                    role_performance={
                        ModelRole.PRIMARY: RolePerformance(success_rate=0.8, avg_latency=0.9),
                        ModelRole.REVIEWER: RolePerformance(success_rate=0.7, avg_latency=1.1),
                        ModelRole.VALIDATOR: RolePerformance(success_rate=0.9, avg_latency=0.4),
                    }
                ),
                is_local=True,
                strengths={"code_generation", "instruction_following", "fast_response"},
                weaknesses={"long_context", "complex_algorithms"},
                best_roles={ModelRole.PRIMARY, ModelRole.VALIDATOR},
            )),
            "qwen2.5-coder:latest": (7, ModelCharacteristics(
                name="qwen2.5-coder:latest",
                provider=ModelProvider.ALIBABA,
                runner=ModelRunner.OLLAMA,
                capabilities=ModelCapabilities(
                    max_context_length=8192, max_output_length=8192
                ),
                performance=ModelPerformance(
                    tokens_per_second=900, cost_per_token=0.0,
                    role_performance={
                        ModelRole.PRIMARY: RolePerformance(success_rate=0.85, avg_latency=0.8),
                        ModelRole.REVIEWER: RolePerformance(success_rate=0.8, avg_latency=1.0),
                        ModelRole.VALIDATOR: RolePerformance(success_rate=0.9, avg_latency=0.5),
                    }
                ),
                is_local=True,
                strengths={"code_generation", "code_completion", "multilingual_code"},
                weaknesses={"test_generation", "complex_refactoring"},
                best_roles={ModelRole.PRIMARY, ModelRole.REVIEWER},
            )),
            "claude-3-sonnet": (0, ModelCharacteristics(  # Cloud model, size doesn't matter
                name="claude-3-sonnet",
                provider=ModelProvider.ANTHROPIC,
                runner=ModelRunner.ANTHROPIC_API,
                capabilities=ModelCapabilities(
                    max_context_length=200000, max_output_length=200000
                ),
                performance=ModelPerformance(
                    tokens_per_second=100, cost_per_token=0.003,
                    role_performance={
                        ModelRole.PRIMARY: RolePerformance(success_rate=0.9, avg_latency=1.5),
                        ModelRole.REVIEWER: RolePerformance(success_rate=0.85, avg_latency=2.0),
                        ModelRole.VALIDATOR: RolePerformance(success_rate=0.95, avg_latency=1.0),
                    }
                ),
                strengths={
                    "code_generation",
                    "code_review",
                    "problem_solving",
                    "algorithm_design",
                    "test_generation",
                },
                weaknesses={"very_long_context", "mathematical_proofs"},
                best_roles={ModelRole.PRIMARY, ModelRole.REVIEWER},
            )),
        }
        
        for name, (size, characteristics) in base_models.items():
            try:
                self.hardware.register_model(name, size)
                self.models[name] = characteristics
            except BaseError as e:
                self.logger.warning(f"Could not register model {name}: {e}")
    
    def _register_hardware_dependent_models(self):
        """Register models that depend on hardware capabilities."""
        dependent_models = {
            "codellama:13b": (13, ModelCharacteristics(
                name="codellama:13b",
                provider=ModelProvider.META,
                runner=ModelRunner.OLLAMA,
                capabilities=ModelCapabilities(
                    max_context_length=16384, max_output_length=16384
                ),
                performance=ModelPerformance(
                    tokens_per_second=500, cost_per_token=0.0,
                    role_performance={
                        ModelRole.PRIMARY: RolePerformance(success_rate=0.85, avg_latency=1.2),
                        ModelRole.REVIEWER: RolePerformance(success_rate=0.8, avg_latency=1.5),
                        ModelRole.VALIDATOR: RolePerformance(success_rate=0.9, avg_latency=0.8),
                    }
                ),
                is_local=True,
                strengths={"code_generation", "problem_solving", "python_expertise"},
                weaknesses={"complex_tasks", "test_generation"},
                best_roles={ModelRole.PRIMARY, ModelRole.REVIEWER},
            )),
            "codellama:34b": (34, ModelCharacteristics(
                name="codellama:34b",
                provider=ModelProvider.META,
                runner=ModelRunner.OLLAMA,
                capabilities=ModelCapabilities(
                    max_context_length=16384, max_output_length=16384
                ),
                performance=ModelPerformance(
                    tokens_per_second=200, cost_per_token=0.0,
                    role_performance={
                        ModelRole.PRIMARY: RolePerformance(success_rate=0.8, avg_latency=1.8),
                        ModelRole.REVIEWER: RolePerformance(success_rate=0.75, avg_latency=2.2),
                        ModelRole.VALIDATOR: RolePerformance(success_rate=0.9, avg_latency=1.2),
                    }
                ),
                is_local=True,
                strengths={
                    "code_generation",
                    "code_completion",
                    "problem_solving",
                    "python_expertise",
                },
                weaknesses={"long_context", "response_time"},
                best_roles={ModelRole.PRIMARY, ModelRole.REVIEWER},
            )),
        }
        
        for name, (size, characteristics) in dependent_models.items():
            try:
                self.hardware.register_model(name, size)
                self.models[name] = characteristics
                self.logger.info(f"Successfully registered model {name} ({size}B parameters)")
            except BaseError as e:
                self.logger.info(f"Skipping model {name} ({size}B parameters): {e}")

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
            if max_latency is not None and chars.performance.role_performance[ModelRole.PRIMARY].avg_latency > max_latency:
                continue

            # Check if model is good for problem type
            if problem_type in chars.strengths or not chars.weaknesses.intersection(
                {problem_type}
            ):
                suitable.append(name)

        return suitable
