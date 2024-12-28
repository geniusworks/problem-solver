"""LLM prompt generation and management."""

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Any, List, Optional, Set

from .parser import ParsedProblem, TestCase
from .problem_analysis import ExamplePurpose

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
    
    def _format_example(self, example: TestCase, include_purpose: bool = True) -> str:
        """Format a single example with its purpose and references."""
        parts = []
        if include_purpose and example.demonstrates:
            parts.append(f"Purpose: {', '.join(example.demonstrates)}")
        
        parts.extend([
            "Input:",
            example.input_data,
            "Expected Output:",
            example.expected_output
        ])
        
        if example.description:
            parts.append(f"Note: {example.description}")
        
        return "\n".join(parts)

    def _format_input_variations(self, base_format: str, variations: List[str]) -> str:
        """Format input format description with variations."""
        if not variations:
            return base_format
        
        parts = [f"Base format: {base_format}"]
        parts.append("Important variations to handle:")
        for var in variations:
            if var.startswith("full_input:"):
                parts.append(f"- In full input: {var[11:]}")
            else:
                parts.append(f"- {var}")
        
        return "\n".join(parts)

    def generate_prompt(self, problem: ParsedProblem, template_name: str) -> str:
        """Generate a prompt for the given problem using the specified template."""
        if template_name not in self.templates:
            raise ValueError(f"Template {template_name} not found")
        
        template = self.templates[template_name]
        
        # Format examples with progression
        formatted_examples = []
        for i, example in enumerate(problem.examples, 1):
            formatted_examples.append(f"Example {i}:\n{self._format_example(example)}")
        
        # Group constraints by what they apply to
        constraint_groups = {
            "example": [],
            "full": [],
            "all": []
        }
        for c in problem.constraints:
            constraint_groups[c.applies_to].append(c.description)
        
        # Format constraints with grouping
        formatted_constraints = []
        if constraint_groups["all"]:
            formatted_constraints.extend([
                "General constraints:",
                *[f"- {c}" for c in constraint_groups["all"]]
            ])
        if constraint_groups["example"]:
            formatted_constraints.extend([
                "Example-specific constraints:",
                *[f"- {c}" for c in constraint_groups["example"]]
            ])
        if constraint_groups["full"]:
            formatted_constraints.extend([
                "Full input constraints:",
                *[f"- {c}" for c in constraint_groups["full"]]
            ])
        
        # Prepare variables for template
        variables = {
            "title": problem.title,
            "description": problem.description,
            "examples": "\n\n".join(formatted_examples),
            "constraints": "\n".join(formatted_constraints),
            "input_format": self._format_input_variations(
                problem.input_format.base_format,
                problem.input_format.variations
            ),
            "output_format": problem.output_format,
            "final_question": problem.final_question,
            "key_concepts": ", ".join(problem.key_concepts) if problem.key_concepts else "None identified",
            "condition_changes": "\n".join(
                f"- {change}" for change in problem.condition_changes
            ) if problem.condition_changes else "None detected"
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
        "description": "Template for generating Advent of Code solutions",
        "template": """Solve this Advent of Code problem:

Title: {title}

Description:
{description}

Key Concepts Required:
{key_concepts}

Examples (Progressive Understanding):
{examples}

Input Format:
{input_format}

Output Format:
{output_format}

Constraints:
{constraints}

Important Changes from Examples to Full Input:
{condition_changes}

Final Question to Answer:
{final_question}

Remember to:
1. Handle all input format variations robustly
2. Account for differences between examples and full input
3. Consider all constraints
4. Focus on solving the final question accurately""",
        "variables": [
            "title",
            "description",
            "examples",
            "constraints",
            "input_format",
            "output_format",
            "key_concepts",
            "condition_changes",
            "final_question"
        ]
    }
}
