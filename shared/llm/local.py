"""Local LLM providers."""

import logging
import asyncio
import os

import aiohttp
from typing import Dict, List, Optional, Any
import re
from pathlib import Path
from shared.strategies import get_strategies_for_problem, create_strategy_prompt, ProblemCategory, Strategy, SOLUTION_STRATEGIES
from shared.llm.base import LLMProvider, LLMResponse
from shared.llm.prompts import generate_implementation_prompt, format_test_cases
from shared.problem_analysis import ProblemAnalyzer
import json
from datetime import datetime
from shared.aoc import ensure_problem_directory_structure

logger = logging.getLogger(__name__)

# Generous: a 9B model on consumer hardware can take several minutes for a
# full solution prompt.
OLLAMA_REQUEST_TIMEOUT = 900

# Room for the model to answer -- and, for reasoning models, to think first --
# on top of the prompt itself.
OLLAMA_OUTPUT_HEADROOM_TOKENS = 4096

class OllamaProvider(LLMProvider):
    """Provider for Ollama local models."""

    AVAILABLE_MODELS = [
        "qwen2.5-coder:7b",
        "llama3.1:8b",
        "mistral:7b",
        "codellama:7b-instruct",
        "gemma3:latest",
        "deepseek-coder:6.7b",
    ]

    def __init__(self, model: str = "codellama:7b", debug: bool = False,
                 temperature: Optional[float] = None,
                 num_ctx: Optional[int] = None, **kwargs):
        super().__init__(**kwargs)
        self.model = model
        self.debug = debug
        # None leaves Ollama's default. Setting it is what makes drawing
        # several independent samples from one model meaningful.
        self.temperature = temperature
        # Explicit override; None sizes the window to the prompt.
        self.num_ctx = num_ctx
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
        
        # Phase 2: Strategy Selection.
        #
        # Both branches go through the converter: get_strategies_for_problem
        # returns names, and the attempt record below reads .name off each
        # entry, so passing raw strings through here raised AttributeError.
        selected = strategies or get_strategies_for_problem(problem.description)
        strategy_objects = self._convert_to_strategy_objects(
            selected, strategy_effectiveness
        )
        
        # Phase 3: Implementation
        implementation_prompt = generate_implementation_prompt(
            problem,
            analyzer,
            analysis.content,
            strategies=strategy_objects,
        )
        
        self.last_prompt = implementation_prompt
        
        start_time = datetime.now()
        try:
            response = await self.generate(
                implementation_prompt, temperature=self.temperature
            )
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
        # Use the same entry point the executor injects. This used to append
        # its own block hardcoding solve(sys.argv[1]), which crashes with
        # IndexError whenever the saved solution is run without arguments --
        # exactly how dev/verify_solutions.py runs it -- and with TypeError when
        # the model defined a zero-argument solve().
        from shared.execution import STANDARD_MAIN_BLOCK

        if not re.search(r'if\s+__name__\s*==\s*[\'"]__main__[\'"]\s*:', code):
            code += "\n\n" + STANDARD_MAIN_BLOCK
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
        # Callers pass Strategy objects (BaseSolver gets them from
        # SubmissionManager.get_recommended_strategies), but this compared
        # strategy.name -- a string -- against the item itself. An object never
        # equals a string, so the result was always empty: all 145 recorded
        # attempts show "applied_strategies": []. Accept either form.
        by_name = {
            strategy.name: strategy
            for category in SOLUTION_STRATEGIES.values()
            for strategy in category
        }

        strategies = []
        for item in strategy_names or []:
            name = item if isinstance(item, str) else getattr(item, "name", None)
            if not name:
                continue
            strategy = by_name.get(name) or (None if isinstance(item, str) else item)
            if strategy is None:
                logger.debug("Unknown strategy %r; ignoring", name)
                continue
            if effectiveness and name in effectiveness:
                strategy.effectiveness = effectiveness[name]
            strategies.append(strategy)
        return strategies

    @staticmethod
    def _context_size(prompt: str) -> int:
        """Context window to request, sized to the prompt plus output headroom.

        Ollama defaults to a ~2048-token context and silently truncates anything
        longer -- it does not error, and the response looks normal. Measured on a
        7883-token prompt: prompt_eval_count was 2050 by default and 7037 with
        num_ctx set.

        This solver's prompts run 6930-27849 characters (median ~3370 tokens,
        max ~6962), so every generation it has ever made was produced from a
        truncated prompt. The models were answering without having seen most of
        the problem, which is the most likely explanation for years of
        "the model misinterpreted the requirements".

        Sized generously rather than exactly: reasoning models need room to think
        *after* the prompt, and running out mid-reasoning is what left qwen3.5:9b
        with no answer on 17 generations.
        """
        estimated_prompt_tokens = len(prompt) // 3  # conservative chars-per-token
        wanted = estimated_prompt_tokens + OLLAMA_OUTPUT_HEADROOM_TOKENS

        # Round up to a power-of-two-ish step so the KV cache is reused across
        # calls instead of being reallocated for every slightly different prompt.
        for size in (8192, 16384, 32768):
            if wanted <= size:
                return size
        return 32768

    async def generate(
        self, prompt: str, temperature: Optional[float] = None
    ) -> LLMResponse:
        """Generate via Ollama's HTTP API.

        This previously shelled out to `ollama run`, which is the *interactive*
        CLI: it renders to a terminal, wrapping lines with cursor-movement and
        erase-line escapes. Capturing that as text corrupts the output --
        `"is not\\x1b[3D\\x1b[K\\nnot fully"` becomes `"is not\\nnot fully"` once
        the escapes are stripped, duplicating a word. In prose that reads oddly;
        in generated code it is a syntax error, and it was the single largest
        source of "the model produced malformed code" in this project. 30 of 145
        recorded attempts still carry the signature.

        /api/generate returns the completion as JSON, with no terminal layer.
        """
        host = os.getenv("OLLAMA_HOST", "http://localhost:11434").rstrip("/")
        options: Dict[str, Any] = {
            "num_ctx": self.num_ctx or self._context_size(prompt)
        }
        if temperature is not None:
            options["temperature"] = float(temperature)

        payload: Dict[str, Any] = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
        }
        if options:
            payload["options"] = options

        logger.debug("Requesting generation from %s for %s", host, self.model)
        try:
            timeout = aiohttp.ClientTimeout(total=OLLAMA_REQUEST_TIMEOUT)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.post(f"{host}/api/generate", json=payload) as resp:
                    if resp.status != 200:
                        body = (await resp.text())[:400]
                        raise RuntimeError(
                            f"Ollama returned HTTP {resp.status} for {self.model}: {body}"
                        )
                    data = await resp.json()

            # Reasoning models split their output: chain-of-thought goes to
            # `thinking`, the answer to `response`. How long they think varies a
            # lot run to run -- the same prompt produced 1.7k chars of thinking
            # once and 17k the next time -- and when reasoning exhausts the
            # output budget `response` comes back empty with
            # done_reason == "length". Reading only `response` scored
            # qwen3.5:9b at 0/6, which measured this provider, not the model.
            content = data.get("response") or ""
            thinking = data.get("thinking") or ""
            done_reason = data.get("done_reason")

            if not content and thinking:
                # Models often write the code inside their reasoning, so this is
                # usually recoverable. Warn rather than fail silently.
                logger.warning(
                    "%s produced no answer (done_reason=%s) but %d chars of "
                    "reasoning; falling back to the reasoning text.",
                    self.model, done_reason, len(thinking),
                )
                content = thinking

            if not content:
                raise RuntimeError(
                    f"Ollama returned no content for {self.model} "
                    f"(done_reason={done_reason})"
                )

            return LLMResponse(
                content=content,
                confidence=1.0,  # Local models don't provide confidence scores
                metadata={
                    "model": self.model,
                    "provider": "ollama",
                    "timestamp": datetime.now().isoformat(),
                    "eval_count": data.get("eval_count"),
                    "prompt_eval_count": data.get("prompt_eval_count"),
                    "done_reason": done_reason,
                    "thinking_chars": len(thinking),
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
        
    async def improve_solution(self, solution: str, problem, feedback: Optional[str] = None) -> str:
        """Improve an existing solution based on feedback.

        Args:
            solution: The current solution code
            problem: The problem being solved
            feedback: Optional feedback about what needs improvement

        Returns:
            Improved solution code
        """
        prompt = f"""Here is a Python solution that needs improvement:

```python
{solution}
```

Problem Description:
{problem.description}

Examples:
{format_test_cases(problem.examples)}

Final Question: {problem.final_question}

{'Feedback: ' + feedback if feedback else 'Please improve this solution while maintaining the exact same output format.'}

Provide ONLY the improved code between ```python and ``` markers. Do not include any explanations."""

        response = await self.generate(prompt)
        return self._extract_code(response.content) or solution  # Return original if no valid code found
