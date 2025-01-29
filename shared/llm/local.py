"""Local LLM providers."""

import logging
import asyncio
from typing import Dict, List, Optional, Any
import re
from pathlib import Path
from shared.strategies import get_strategies_for_problem, create_strategy_prompt, ProblemCategory, Strategy, SOLUTION_STRATEGIES
from shared.llm.base import LLMProvider, LLMResponse
from shared.llm.prompts import generate_implementation_prompt, format_test_cases
from shared.problem_analysis import ProblemAnalyzer
import json
from datetime import datetime
from shared.utils import ensure_problem_directory_structure

logger = logging.getLogger(__name__)

class OllamaProvider(LLMProvider):
    """Provider for Ollama local models."""

    AVAILABLE_MODELS = [
        "codellama:7b",
        "deepseek-coder:latest",
        "mistral:7b",
        "qwen2.5-coder:latest"
    ]

    def __init__(self, model: str = "codellama:7b", debug: bool = False, **kwargs):
        super().__init__(**kwargs)
        self.model = model
        self.debug = debug
        self.model_info = {"name": model, "description": "Description of the model."}
        self.last_prompt = None

    async def generate_solution(
        self, 
        problem,
        year: int,
        day: int,
        strategies: Optional[List[str]] = None,
        strategy_effectiveness: Optional[Dict[str, float]] = None
    ) -> str:
        """Generate a solution for the given problem."""
        if self.debug:
            logger.info("Analyzing problem...")
        
        # Create analyzer
        analyzer = ProblemAnalyzer()
        
        # Phase 1: Problem Analysis
        analysis = await self.generate(f"""Consider:
1. Input format and constraints
2. Expected output format
3. Key problem characteristics
4. Potential edge cases

{problem.title}
{problem.description}

Examples:
{format_test_cases(problem.examples)}

Final Question: {problem.final_question}""")
        
        # Phase 2: Strategy Selection
        if not strategies:
            # If no strategies provided, get them from problem analysis
            strategy_objects = get_strategies_for_problem(problem.description)
        else:
            # Convert provided strategy names to Strategy objects
            strategy_objects = self._convert_to_strategy_objects(strategies, strategy_effectiveness)
        
        strategy_prompt = create_strategy_prompt(strategy_objects)
        
        # Phase 3: Implementation
        implementation_prompt = generate_implementation_prompt(problem, analyzer)
        
        self.last_prompt = implementation_prompt
        
        start_time = datetime.now()
        try:
            response = await self.generate(implementation_prompt)
            generation_time = (datetime.now() - start_time).total_seconds()
            
            # Extract the code from the response
            code = self._extract_code(response.content)
            
            # Save attempt data
            # Create directory structure
            dirs = ensure_problem_directory_structure(Path.cwd(), year, day)
            attempts_dir = dirs["attempts"]
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            attempt_data = {
                "code": code,
                "prompt": implementation_prompt,
                "model": self.get_model_info(),
                "metadata": {
                    "timestamp": timestamp,
                    "generation_time": generation_time,
                    "error": None,
                    "year": year,
                    "day": day,
                    "part": problem.part
                },
                "strategy_analysis": {
                    "applied_strategies": [s.name for s in strategy_objects],
                },
                "raw_response": response.content
            }
            
            attempt_file = attempts_dir / f"attempt_{self.model}_{timestamp}.json"
            with open(attempt_file, "w") as f:
                json.dump(attempt_data, f, indent=2)
            
            # Log the generated code
            if self.debug:
                logger.debug("Raw generated code:\n%s", code)
                
            if code is None:
                code = """def solve(input_file_path):
    \"\"\"Solve the problem.
    
    Args:
        input_file_path: Path to the input file
        
    Returns:
        The answer as an integer or float
    \"\"\"
    with open(input_file_path) as f:
        data = [line.strip() for line in f]
    return len(data)  # Default implementation"""
                
            # Apply code formatting
            formatted_code = self._fix_generated_code(code)
            if self.debug:
                logger.debug("Formatted code:\n%s", formatted_code)
            
            return formatted_code
            
        except Exception as e:
            generation_time = (datetime.now() - start_time).total_seconds()
            
            # Record the failed attempt
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            attempt_data = {
                "code": "",
                "prompt": implementation_prompt,
                "model": self.get_model_info(),
                "metadata": {
                    "timestamp": timestamp,
                    "generation_time": generation_time,
                    "error": str(e)
                },
                "strategy_analysis": {
                    "applied_strategies": [s.name for s in strategy_objects],
                },
                "raw_response": None
            }
            
            # Save the failed attempt
            # Create directory structure
            dirs = ensure_problem_directory_structure(Path.cwd(), year, day)
            attempts_dir = dirs["attempts"]
            
            attempt_file = attempts_dir / f"attempt_{self.model}_{timestamp}.json"
            with open(attempt_file, "w") as f:
                json.dump(attempt_data, f, indent=2)
            
            raise

    def _fix_generated_code(self, code: str) -> str:
        """Fix common issues in generated code.
        
        Only adds the main block if needed. Does not modify the solution code itself.
        """
        # Add missing main block if needed
        if not re.search(r'if\s+__name__\s*==\s*[\'"]__main__[\'"]\s*:', code):
            code += '\n\nif __name__ == "__main__":\n    import sys\n    print(solve(sys.argv[1]))'
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

    def _convert_to_strategy_objects(self, strategy_names: List[str], effectiveness: Optional[Dict[str, float]] = None) -> List[Strategy]:
        """Convert strategy names to Strategy objects.
        
        Args:
            strategy_names: List of strategy names to convert
            effectiveness: Optional dictionary mapping strategy names to their effectiveness scores
            
        Returns:
            List of Strategy objects
        """
        strategies = []
        for name in strategy_names:
            # Search through all categories for the strategy
            for category_strategies in SOLUTION_STRATEGIES.values():
                for strategy in category_strategies:
                    if strategy.name == name:
                        if effectiveness and name in effectiveness:
                            strategy.effectiveness = effectiveness[name]
                        strategies.append(strategy)
                        break
        return strategies

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

            # Log raw response for debugging
            logger.debug("Raw Ollama response:")
            logger.debug(stdout_text)

            # Filter out Ollama spinner messages
            non_spinner_lines = [
                line
                for line in stderr_text.splitlines()
                if not line.startswith("\r") and line.strip()
            ]

            if process.returncode != 0:
                logger.warning("Ollama stderr: %s", "\n".join(non_spinner_lines))
                logger.error("Ollama failed with return code %d", process.returncode)
                raise Exception(f"Ollama failed: {stderr_text}")

            return LLMResponse(
                content=stdout_text,
                confidence=1.0,  # Local models don't provide confidence scores
                metadata={
                    "model": self.model,
                    "provider": "ollama",
                    "timestamp": datetime.now().isoformat()
                }
            )

        except Exception as e:
            logger.error("Error running Ollama: %s", str(e))
            raise

    async def validate_solution(
        self, solution: str, test_cases: List[Dict[str, str]]
    ) -> bool:
        """Validate solution using Ollama."""
        # TODO: Implement validation logic
        return True

    def get_model_info(self) -> Dict[str, Any]:
        """Get information about the model."""
        return {
            "name": self.model,
            "type": "local",
            "provider": "ollama",
            "description": "Local Ollama model",
            "capabilities": {
                "code_generation": True,
                "code_explanation": True,
                "strategy_analysis": True
            }
        }

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

    async def generate_solution(
        self, 
        problem,
        year: int,
        day: int,
        strategies: Optional[List[str]] = None,
        strategy_effectiveness: Optional[Dict[str, float]] = None
    ) -> str:
        """Generate a solution for the given problem."""
        raise NotImplementedError("LMStudio provider is not fully implemented yet")

    async def generate(self, prompt: str) -> LLMResponse:
        """Generate using LM Studio."""
        raise NotImplementedError("LM Studio provider is not fully implemented yet")

    def validate_solution(
        self, solution: str, test_cases: List[Dict[str, str]]
    ) -> bool:
        """Validate solution using LM Studio."""
        raise NotImplementedError("LM Studio provider is not fully implemented yet")

    @property
    def cost_per_token(self) -> float:
        return 0.0  # Local models are free

    @property
    def is_local(self) -> bool:
        return True
