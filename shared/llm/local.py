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
    
    async def generate_solution(self, prompt: str) -> Optional[str]:
        """Generate a solution using Ollama API."""
        try:
            response = await self.generate(prompt)
            if not response or not response.content:
                return None
            
            # Extract code from response
            code = self._extract_code(response.content)
            if not code:
                logger.error("No code found in response")
                return None
            
            return code
            
        except Exception as e:
            logger.error("Failed to generate solution: %s", str(e))
            return None
    
    def _extract_code(self, text: str) -> Optional[str]:
        """Extract Python code from response text."""
        # Try to find code between ```python and ``` markers
        code_match = re.search(r'```python\n(.*?)\n```', text, re.DOTALL)
        if code_match:
            return code_match.group(1).strip()
        
        # If no markers, try to extract code based on Python syntax
        lines = text.split('\n')
        code_lines = []
        in_code = False
        
        for line in lines:
            if line.startswith('import ') or line.startswith('from '):
                in_code = True
            if in_code:
                code_lines.append(line)
        
        return '\n'.join(code_lines) if code_lines else None
    
    async def generate(self, prompt: str) -> LLMResponse:
        """Generate using Ollama API."""
        try:
            # Run Ollama with the prompt directly
            process = await asyncio.create_subprocess_exec(
                'ollama',
                'run',
                self.model,
                """You are a Python code generator for Advent of Code solutions. Follow these rules exactly:

1. Output ONLY Python code, no markdown, no comments, no explanations
2. Code MUST start with necessary imports (always include 're' for parsing)
3. Code MUST define a solve() function that:
   - Reads input from os.environ["AOC_INPUT_FILE"]
   - Handles variations between example and full input format
   - Extracts numbers/data robustly using regex where needed
   - Returns the final answer as a single number or string
4. No print statements except in __main__ block
5. No test cases or examples in the code
6. No docstrings or comments
7. Use proper indentation (4 spaces)
8. Make solution general enough to handle:
   - Different sizes of input than shown in examples
   - Additional text or annotations in full input
   - Different parameters or conditions than in examples
   - Edge cases implied by problem description

Example format:
import os
import re

def solve():
    with open(os.environ["AOC_INPUT_FILE"]) as f:
        data = f.read().strip()
    return result

if __name__ == "__main__":
    result = solve()
    print(result)

""" + prompt,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            
            if stderr:
                logger.warning("Ollama stderr: %s", stderr.decode())
            
            return LLMResponse(
                content=stdout.decode().strip(),
                confidence=1.0,
                metadata={"model": self.model},
                error=None
            )
            
        except Exception as e:
            logger.error("Failed to run Ollama: %s", str(e))
            raise
    
    async def validate_solution(self, solution: str, test_cases: List[Dict[str, str]]) -> bool:
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
