"""Local LLM providers."""

import json
import subprocess
import tempfile
import os
import re
import asyncio
from typing import Dict, List, Optional
import aiohttp
import logging

from .base import LLMProvider, LLMResponse

logger = logging.getLogger(__name__)

class OllamaProvider(LLMProvider):
    """Provider for Ollama local models."""
    
    def __init__(self, model: str = "codellama:7b", **kwargs):
        super().__init__(**kwargs)
        self.model = model
    
    async def generate(self, prompt: str) -> LLMResponse:
        """Generate using Ollama API."""
        try:
            # Run Ollama with the prompt directly
            process = await asyncio.create_subprocess_exec(
                'ollama',
                'run',
                self.model,
                "You are a Python code generator. You must output ONLY valid Python code with no explanations or formatting. Your response must start with 'import' and contain a solve() function.\n\n" + prompt,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await process.communicate()
            
            # Log raw response for debugging
            if stdout:
                logger.debug("Raw response from Ollama:\n%s", stdout.decode())
            if stderr:
                logger.debug("Stderr from Ollama:\n%s", stderr.decode())
            
            if process.returncode == 0:
                raw_response = stdout.decode().strip()
                
                # Try to extract code block if present
                code_match = re.search(r'```python\n(.*?)\n```', raw_response, re.DOTALL)
                if code_match:
                    code = code_match.group(1)
                else:
                    # If no code block found, assume the entire response is code
                    code = raw_response
                
                # Clean up the code
                code = code.strip()
                
                return LLMResponse(
                    content=code,
                    confidence=1.0,
                    metadata={"model": self.model},
                    error=None
                )
            else:
                return LLMResponse(
                    content="",
                    confidence=0.0,
                    metadata={},
                    error=f"Ollama error: {stderr.decode()}"
                )
        except Exception as e:
            logger.error(
                "Failed to run Ollama: %s",
                str(e),
                exc_info=True
            )
            return LLMResponse(
                content="",
                confidence=0.0,
                metadata={},
                error=str(e)
            )
    
    def validate_solution(self, solution: str, test_cases: List[Dict[str, str]]) -> bool:
        """Validate solution using Ollama."""
        # TODO: Implement validation logic
        return True
    
    @property
    def cost_per_token(self) -> float:
        return 0.0  # Local models are free
    
    @property
    def is_local(self) -> bool:
        return True

class LMStudioProvider(LLMProvider):
    """Provider for LM Studio local models."""
    
    def __init__(self, model_path: str, **kwargs):
        super().__init__(**kwargs)
        self.model_path = model_path
    
    async def generate(self, prompt: str) -> LLMResponse:
        """Generate using LM Studio."""
        # TODO: Implement LM Studio generation
        return LLMResponse(
            content="",
            confidence=0.0,
            metadata={},
            error="LM Studio not implemented yet"
        )
    
    def validate_solution(self, solution: str, test_cases: List[Dict[str, str]]) -> bool:
        """Validate solution using LM Studio."""
        # TODO: Implement validation logic
        return True
    
    @property
    def cost_per_token(self) -> float:
        return 0.0  # Local models are free
    
    @property
    def is_local(self) -> bool:
        return True
