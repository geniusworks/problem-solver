"""Module for managing hardware capabilities and model registration."""

import json
import logging
import os
import platform
from dataclasses import dataclass
from typing import Dict, List, Set, Optional

from shared.config import HARDWARE_CONFIG
from shared.errors import BaseError

logger = logging.getLogger(__name__)


@dataclass
class HardwareProfile:
    """Hardware profile configuration."""
    max_model_size: int
    concurrent_models: int


class HardwareManager:
    """Manages hardware capabilities and model registration."""

    def __init__(self):
        """Initialize the hardware manager."""
        self.capabilities = self._load_capabilities()
        self.registered_models: Dict[str, int] = {}
        self.active_models: Set[str] = set()

    def _detect_hardware_profile(self) -> Optional[str]:
        """Detect the current hardware profile based on system information.
        
        Returns:
            str: Profile name if detected, None otherwise
        """
        if platform.system() != "Darwin" or not platform.machine() == "arm64":
            return None
            
        # Get memory in GB
        mem_bytes = os.sysconf('SC_PAGE_SIZE') * os.sysconf('SC_PHYS_PAGES')
        mem_gb = mem_bytes / (1024.**3)
        
        # Detect M1/M2
        cpu_info = platform.processor()
        is_m2 = "M2" in cpu_info
        
        if mem_gb <= 17:  # 16GB
            return "m2_16gb" if is_m2 else "m1_16gb"
        else:  # 32GB
            return "m2_32gb" if is_m2 else "m1_32gb"

    def _load_capabilities(self) -> HardwareProfile:
        """Load hardware capabilities from config.
        
        Returns:
            HardwareProfile: Hardware capabilities configuration.
        
        Raises:
            BaseError: If there is an error loading the configuration.
        """
        # Try to detect hardware profile
        profile_name = self._detect_hardware_profile()
        if profile_name and "profiles" in HARDWARE_CONFIG:
            profile = HARDWARE_CONFIG["profiles"].get(profile_name)
            if profile:
                logger.info(f"Using hardware profile: {profile_name}")
                return HardwareProfile(
                    max_model_size=profile["max_model_size"],
                    concurrent_models=profile["concurrent_models"]
                )
        
        # Fall back to default config
        if "max_model_size" in HARDWARE_CONFIG and "concurrent_models" in HARDWARE_CONFIG:
            return HardwareProfile(
                max_model_size=HARDWARE_CONFIG["max_model_size"],
                concurrent_models=HARDWARE_CONFIG["concurrent_models"]
            )
            
        raise BaseError(
            "No hardware configuration found. Please provide a config file."
        )

    def register_model(self, model_name: str, model_size: int) -> None:
        """Register a model with its size.
        
        Args:
            model_name: Name of the model to register
            model_size: Size of the model in billions of parameters
            
        Raises:
            BaseError: If the model is too large for the hardware
        """
        if model_size > self.capabilities.max_model_size:
            raise BaseError(
                f"Model {model_name} ({model_size}B parameters) exceeds "
                f"maximum supported size ({self.capabilities.max_model_size}B)"
            )
        self.registered_models[model_name] = model_size

    def activate_model(self, model_name: str) -> None:
        """Activate a model for use.
        
        Args:
            model_name: Name of the model to activate
            
        Raises:
            BaseError: If the model cannot be activated
        """
        if model_name not in self.registered_models:
            raise BaseError(f"Model {model_name} is not registered")

        if len(self.active_models) >= self.capabilities.concurrent_models:
            raise BaseError(
                f"Cannot activate more than {self.capabilities.concurrent_models} "
                "models concurrently"
            )
        self.active_models.add(model_name)

    def deactivate_model(self, model_name: str) -> None:
        """Deactivate a model.
        
        Args:
            model_name: Name of the model to deactivate
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
