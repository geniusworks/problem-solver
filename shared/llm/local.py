"""Local LLM providers."""

import logging
import asyncio
from typing import Dict, List, Optional, Any
import re
from pathlib import Path
from shared.strategies import get_strategies_for_problem, create_strategy_prompt, ProblemCategory, Strategy, SOLUTION_STRATEGIES
from shared.llm.base import LLMProvider, LLMResponse

logger = logging.getLogger(__name__)

class OllamaProvider(LLMProvider):
    """Provider for Ollama local models."""

    AVAILABLE_MODELS = [
        "codellama:7b",
        "phi:latest",
        "mistral:latest"
    ]

    def __init__(self, model: str = "codellama:7b", debug: bool = False, **kwargs):
        super().__init__(**kwargs)
        self.model = model
        self.debug = debug
        self.model_info = {"name": model, "description": "Description of the model."}
        self.last_prompt = None

    def _convert_to_strategy_objects(
        self, 
        strategy_names: List[str],
        strategy_effectiveness: Optional[Dict[str, float]] = None
    ) -> List[Strategy]:
        """Convert strategy names to Strategy objects."""
        strategies = []
        for category in SOLUTION_STRATEGIES.values():
            for strategy in category:
                if strategy.name in strategy_names:
                    strategies.append(strategy)
        return strategies

    async def generate_solution(
        self, 
        problem,
        strategies: Optional[List[str]] = None,
        strategy_effectiveness: Optional[Dict[str, float]] = None
    ) -> str:
        """Generate a solution for the given problem."""
        # Phase 1: Problem Analysis
        analysis_prompt = f"""Analyze this problem:

{problem.description}

Consider:
1. Input format and constraints
2. Expected output format
3. Key problem characteristics
4. Potential edge cases"""

        analysis = await self.generate(analysis_prompt)
        
        # Phase 2: Strategy Selection
        if not strategies:
            # If no strategies provided, get them from problem analysis
            strategy_objects = get_strategies_for_problem(problem.description)
        else:
            # Convert provided strategy names to Strategy objects
            strategy_objects = self._convert_to_strategy_objects(strategies, strategy_effectiveness)
        
        strategy_prompt = create_strategy_prompt(strategy_objects)
        
        # Phase 3: Implementation Planning
        implementation_prompt = f"""Here's the problem description:
{problem.description}

Test Cases:
{self._format_test_cases(problem.examples)}

Write a Python function called solve(input_file_path) that reads the input file and solves this problem.

Note to Model:
-------------

1. Analyze Input Structure:
   - Always inspect example input format first
   - Print first few lines of actual input to verify format matches example
   - Look for consistent patterns:
     * Delimiters (spaces, commas, tabs)
     * Line structure (single/multiple values)
     * Data types (numbers, strings, mixed)
   - Verify assumptions with example data before proceeding

2. Parse Thoughtfully:
   - Start with minimal parsing that matches example format
   - Validate parsed data matches expected structure
   - Handle edge cases:
     * Empty lines
     * Leading/trailing whitespace
     * Unexpected characters
   - Log parsed structure to verify correctness

3. Test Your Understanding:
   - Compare parsed example data with given example output
   - Verify your interpretation matches problem description
   - Test edge cases in example data
   - Print intermediate results to validate logic

The solution should handle the input format exactly as shown in the example."""

        self.last_prompt = implementation_prompt
        logger.debug("Implementation prompt:\n%s", implementation_prompt)
        response = await self.generate(implementation_prompt)
        code = self._extract_code(response.content)
        
        # Log the generated code
        if self.debug:
            logger.debug("Raw generated code:\n%s", code)
            
        if code is None:
            code = "def solve(input_file_path):\n    with open(input_file_path) as f:\n        data = [line.strip() for line in f]\n    return len(data)  # Default implementation"
            
        # Apply code formatting
        formatted_code = self._fix_generated_code(code)
        if self.debug:
            logger.debug("Formatted code:\n%s", formatted_code)
        
        return formatted_code

    def _format_test_cases(self, test_cases) -> str:
        """Format test cases for the prompt."""
        if not test_cases:
            return "No example test cases provided."
            
        formatted = []
        for i, test in enumerate(test_cases, 1):
            case = [f"Example {i}:"]
            
            # Show raw input format
            case.append("Raw Input Format:")
            case.append(f"```\n{test.input_data}\n```")
            
            # Show description if available
            if test.description:
                case.append(f"Context: {test.description}")
            
            # Show expected output if available
            if test.expected_output:
                case.append(f"Expected Output: {test.expected_output}")
                
            formatted.append("\n".join(case))
            
        return "\n\n".join(formatted)

    def _fix_generated_code(self, code: str) -> str:
        """Fix common issues in generated code."""
        # Add missing main block if needed
        if "__main__" not in code:
            code += "\n\nif __name__ == '__main__':\n    print(solve('input.txt'))"
        return code

    def _extract_code(self, text: str) -> Optional[str]:
        """Extract Python code from response text."""
        logger.debug("Looking for code between python markers...")
        
        # First try to find code between ```python markers
        pattern = r"```python\s*(.*?)\s*```"
        matches = re.findall(pattern, text, re.DOTALL)
        if matches:
            logger.debug("Found code between markers")
            return matches[0].strip()
            
        # If no markers, try to find indented code blocks
        code_lines = []
        in_code = False
        for line in text.split("\n"):
            if line.strip().startswith("def "):
                in_code = True
            elif (
                in_code
                and line
                and not line.startswith(" ")
                and not line.startswith("if ")
            ):
                break
            if in_code:
                code_lines.append(line)

        if code_lines:
            logger.debug("Found code based on Python syntax")
            return "\n".join(code_lines)

        logger.debug("No code found in response")
        return None

    async def generate(self, prompt: str) -> LLMResponse:
        """Generate using Ollama API."""
        try:
            # Run Ollama with the prompt directly
            logger.debug("Running Ollama command...")
            process = await asyncio.create_subprocess_exec(
                "ollama",
                "run",
                self.model,
                prompt,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            logger.debug("Waiting for Ollama response...")
            stdout, stderr = await process.communicate()
            stdout_text = stdout.decode() if stdout else ""
            stderr_text = stderr.decode() if stderr else ""

            # Filter out Ollama spinner messages
            non_spinner_lines = [
                line
                for line in stderr_text.splitlines()
                if line and not any(x in line for x in ["[?25", "[2K", "[1G"])
            ]
            if non_spinner_lines:
                logger.warning("Ollama stderr: %s", "\n".join(non_spinner_lines))

            if process.returncode != 0:
                logger.error("Ollama failed with return code %d", process.returncode)
                return LLMResponse(
                    content="",
                    confidence=0.0,
                    metadata={"model": self.model},
                    error=f"Ollama failed with return code {process.returncode}",
                )

            logger.debug("Ollama response received successfully")
            logger.debug("Response content:\n%s", stdout_text)
            return LLMResponse(
                content=stdout_text,
                confidence=1.0,
                metadata={"model": self.model},
                error=None,
            )

        except Exception as e:
            logger.error("Failed to generate using Ollama: %s", str(e))
            return LLMResponse(
                content="", confidence=0.0, metadata={"model": self.model}, error=str(e)
            )

    async def validate_solution(
        self, solution: str, test_cases: List[Dict[str, str]]
    ) -> bool:
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
            error="LM Studio not implemented yet",
        )

    def validate_solution(
        self, solution: str, test_cases: List[Dict[str, str]]
    ) -> bool:
        """Validate solution using LM Studio."""
        # TODO: Implement validation logic
        return True

    @property
    def cost_per_token(self) -> float:
        return 0.0  # Local models are free

    @property
    def is_local(self) -> bool:
        return True
