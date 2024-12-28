"""LLM prompt generation and management."""

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Any, List, Optional

from .parser import ParsedProblem

@dataclass
class PromptTemplate:
    """Template for generating LLM prompts."""
    name: str
    template: str
    description: str
    variables: List[str]
    example_completion: Optional[str] = None

class PromptGenerator:
    """Generates optimized prompts for LLM code generation."""
    
    def __init__(self, templates_dir: Path):
        self.templates_dir = templates_dir
        self.templates = self._load_templates()
    
    def _load_templates(self) -> Dict[str, PromptTemplate]:
        """Load prompt templates from JSON files."""
        templates = {}
        if not self.templates_dir.exists():
            return templates
        
        for file in self.templates_dir.glob("*.json"):
            with open(file) as f:
                data = json.load(f)
                templates[data["name"]] = PromptTemplate(
                    name=data["name"],
                    template=data["template"],
                    description=data["description"],
                    variables=data["variables"],
                    example_completion=data.get("example_completion")
                )
        return templates
    
    def generate_prompt(self, problem: ParsedProblem, template_name: str) -> str:
        """Generate a prompt for the given problem using the specified template."""
        if template_name not in self.templates:
            raise ValueError(f"Template {template_name} not found")
        
        template = self.templates[template_name]
        
        # Prepare variables for template
        variables = {
            "title": problem.title,
            "description": problem.description,
            "examples": "\n".join(
                f"Input:\n{ex.input_data}\nExpected Output:\n{ex.expected_output}"
                for ex in problem.examples
            ),
            "constraints": "\n".join(
                f"- {c.description}" for c in problem.constraints
            ),
            "input_format": problem.input_format,
            "output_format": problem.output_format
        }
        
        # Validate all required variables are present
        missing = [var for var in template.variables if var not in variables]
        if missing:
            raise ValueError(f"Missing required variables: {missing}")
        
        # Generate prompt
        return template.template.format(**variables)
    
    def save_successful_prompt(self, 
                             problem: ParsedProblem,
                             prompt: str,
                             solution: str,
                             template_name: str):
        """Save a successful prompt for future reference."""
        success_dir = self.templates_dir / "successful"
        success_dir.mkdir(exist_ok=True)
        
        success_file = success_dir / f"{problem.year}_day{problem.day}_part{problem.part}.json"
        data = {
            "problem": problem.to_dict(),
            "prompt": prompt,
            "solution": solution,
            "template_name": template_name
        }
        
        with open(success_file, 'w') as f:
            json.dump(data, f, indent=2)

# Default prompt templates
DEFAULT_TEMPLATES = {
    "basic_solution": {
        "name": "basic_solution",
        "description": "Basic template for generating a solution",
        "template": """Please solve this Advent of Code problem:

{title}

Problem Description:
{description}

Examples:
{examples}

Constraints:
{constraints}

Input Format: {input_format}
Expected Output Format: {output_format}

Please provide a Python solution that:
1. Reads input from a file named 'input.txt'
2. Processes the input according to the problem description
3. Handles all edge cases
4. Includes example test cases
5. Returns the correct output format""",
        "variables": [
            "title",
            "description",
            "examples",
            "constraints",
            "input_format",
            "output_format"
        ]
    }
}
