"""Module for managing hardware capabilities and model registration."""

import json
import logging
import os
from dataclasses import dataclass
from typing import Dict, List, Set

logger = logging.getLogger(__name__)


@dataclass
class HardwareProfile:
    """Hardware profile configuration."""

    max_model_size: int
    concurrent_models: int


class ConfigurationError(Exception):
    """Raised when there is an error in the configuration."""


class HardwareManager:
    """Manages hardware capabilities and model registration."""

    def __init__(self, config_path: str):
        """Initialize the hardware manager.

        Args:
            config_path: Path to the hardware configuration file.
        """
        self.config_path = config_path
        self.capabilities = self._load_capabilities()
        self.registered_models: Dict[str, int] = {}
        self.active_models: Set[str] = set()

    def _load_capabilities(self) -> HardwareProfile:
        """Load hardware capabilities from environment variables or config file.

        Returns:
            HardwareProfile: Hardware capabilities configuration.

        Raises:
            ConfigurationError: If there is an error loading the configuration.
        """
        try:
            max_model_size = int(os.getenv("MAX_MODEL_SIZE", "0"))
            concurrent_models = int(os.getenv("CONCURRENT_MODELS", "0"))

            if not max_model_size or not concurrent_models:
                if not os.path.exists(self.config_path):
                    raise ConfigurationError(
                        "No hardware configuration found. Please set environment variables "
                        "or provide a config file."
                    )

                with open(self.config_path, "r", encoding="utf-8") as f:
                    config = json.load(f)
                    try:
                        max_model_size = int(config.get("max_model_size", 0))
                    except ValueError as exc:
                        raise ConfigurationError(
                            "MAX_MODEL_SIZE must be an integer"
                        ) from exc

                    try:
                        concurrent_models = int(config.get("concurrent_models", 0))
                    except ValueError as exc:
                        raise ConfigurationError(
                            "CONCURRENT_MODELS must be an integer"
                        ) from exc

            if max_model_size <= 0:
                raise ConfigurationError("MAX_MODEL_SIZE must be positive")
            if concurrent_models <= 0:
                raise ConfigurationError("CONCURRENT_MODELS must be positive")

            return HardwareProfile(
                max_model_size=max_model_size,
                concurrent_models=concurrent_models,
            )

        except json.JSONDecodeError as exc:
            raise ConfigurationError(f"Invalid JSON in config file: {exc}") from exc
        except OSError as exc:
            raise ConfigurationError(f"Error reading config file: {exc}") from exc

    def register_model(self, model_name: str, model_size: int) -> None:
        """Register a model with its size.

        Args:
            model_name: Name of the model.
            model_size: Size of the model in billions of parameters.

        Raises:
            ConfigurationError: If the model is too large for the hardware.
        """
        if model_size > self.capabilities.max_model_size:
            raise ConfigurationError(
                f"Model {model_name} ({model_size}B parameters) exceeds "
                f"maximum supported size ({self.capabilities.max_model_size}B)"
            )
        self.registered_models[model_name] = model_size

    def activate_model(self, model_name: str) -> None:
        """Activate a model for use.

        Args:
            model_name: Name of the model to activate.

        Raises:
            ConfigurationError: If the model cannot be activated.
        """
        if model_name not in self.registered_models:
            raise ConfigurationError(f"Model {model_name} is not registered")

        if len(self.active_models) >= self.capabilities.concurrent_models:
            raise ConfigurationError(
                f"Cannot activate more than {self.capabilities.concurrent_models} "
                "models concurrently"
            )

        self.active_models.add(model_name)

    def deactivate_model(self, model_name: str) -> None:
        """Deactivate a model.

        Args:
            model_name: Name of the model to deactivate.
        """
        self.active_models.discard(model_name)

    def get_recommended_defaults(self) -> Dict[str, List[str]]:
        """Get recommended model defaults based on hardware profile.

        Returns:
            Dict[str, List[str]]: Dictionary mapping model types to recommended models.
        """
        defaults: Dict[str, List[str]] = {
            "local": [],
            "cloud": [],
        }

        if self.capabilities.max_model_size >= 7:
            defaults["local"].extend(["llama2:7b", "codellama:7b"])
        if self.capabilities.max_model_size >= 13:
            defaults["local"].append("llama2:13b")
        if self.capabilities.max_model_size >= 34:
            defaults["local"].append("llama2:34b")

        defaults["cloud"].extend(["gpt-3.5-turbo", "claude-2"])

        return defaults

    def cleanup(self) -> None:
        """Clean up resources."""
        self.active_models.clear()
        self.registered_models.clear()
