"""Module for LLM prompt generation and management."""

import json
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Set

from shared.parser import ParsedProblem, TestCase
from shared.problem_analysis import ProblemAnalyzer, ProblemCategory, ExamplePurpose

logger = logging.getLogger(__name__)


@dataclass
class PromptTemplate:
    """Template for generating LLM prompts."""

    name: str
    template: str
    description: str
    variables: List[str]
    example_completion: Optional[str] = None


class TemplateManager:
    """Manages prompt templates from JSON files."""

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
                    example_completion=data.get("example_completion"),
                )
        return templates

    def get_template(self, name: str) -> Optional[PromptTemplate]:
        """Get a template by name."""
        return self.templates.get(name)


class PromptGenerator:
    """Generates optimized prompts for LLM models."""

    def __init__(self, templates_dir: Optional[Path] = None):
        """Initialize the prompt generator.
        
        Args:
            templates_dir: Optional directory containing JSON template files
        """
        self.template_manager = TemplateManager(templates_dir) if templates_dir else None
        self.logger = logging.getLogger(__name__)

    def _format_example(self, example: TestCase, include_purpose: bool = True) -> str:
        """Format a single example with its purpose and references."""
        parts = []
        if include_purpose and example.demonstrates:
            parts.append(f"Purpose: {', '.join(example.demonstrates)}")

        parts.extend(
            ["Input:", example.input_data, "Expected Output:", example.expected_output]
        )

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

    def generate_from_template(
        self, problem: ParsedProblem, template_name: str
    ) -> str:
        """Generate a prompt using a specific template.
        
        Args:
            problem: The parsed problem
            template_name: Name of the template to use
            
        Returns:
            Formatted prompt string
            
        Raises:
            ValueError: If template not found or template manager not initialized
        """
        if not self.template_manager:
            raise ValueError("Template manager not initialized")

        template = self.template_manager.get_template(template_name)
        if not template:
            raise ValueError(f"Template {template_name} not found")

        # Format examples with progression
        formatted_examples = []
        for i, example in enumerate(problem.examples, 1):
            formatted_examples.append(f"Example {i}:\n{self._format_example(example)}")

        # Group constraints by what they apply to
        constraint_groups = {"example": [], "full": [], "all": []}
        for c in problem.constraints:
            constraint_groups[c.applies_to].append(c.description)

        # Format constraints with grouping
        formatted_constraints = []
        if constraint_groups["all"]:
            formatted_constraints.extend(
                ["General constraints:", *[f"- {c}" for c in constraint_groups["all"]]]
            )
        if constraint_groups["example"]:
            formatted_constraints.extend(
                ["Example-specific:", *[f"- {c}" for c in constraint_groups["example"]]]
            )
        if constraint_groups["full"]:
            formatted_constraints.extend(
                ["Full input:", *[f"- {c}" for c in constraint_groups["full"]]]
            )

        # Prepare template variables
        variables = {
            "title": problem.title,
            "description": problem.description,
            "examples": "\n\n".join(formatted_examples),
            "constraints": "\n".join(formatted_constraints),
            "final_question": problem.final_question,
        }

        # Fill template
        return template.template.format(**variables)

    def generate_adaptive(self, problem: ParsedProblem, analyzer: ProblemAnalyzer) -> str:
        """Generate an optimized adaptive prompt for the given problem.

        Args:
            problem: The parsed problem
            analyzer: The problem analyzer instance

        Returns:
            A formatted prompt string
        """
        # Build prompt sections
        sections = []

        # Title and description
        sections.append(f"Title: {problem.title}\n")
        sections.append("Description:")
        sections.append(problem.description)

        # Key concepts
        sections.append("\nKey Concepts Required:")
        categories = analyzer.categorize_problem(problem)
        if categories:
            sections.append("\n".join(cat.name for cat in categories))
        else:
            sections.append("None identified")

        # Examples
        if problem.examples:
            sections.append("\nExamples (Progressive Understanding):")
            for i, example in enumerate(problem.examples, 1):
                sections.append(f"Example {i}:")
                if example.purpose:
                    sections.append(f"Purpose: {example.purpose.name}")
                if example.input_data:
                    sections.append(f"Input:")
                    sections.append(example.input_data)
                if example.expected_output:
                    sections.append(f"Expected Output:")
                    sections.append(str(example.expected_output))
                if example.description:
                    sections.append(f"Note: {example.description}")

        # Input/Output format
        sections.append("\nInput Format:")
        input_format = analyzer.determine_input_format(problem)
        if input_format:
            sections.append(str(input_format))

        sections.append("\nOutput Format:")
        output_format = analyzer.determine_output_format(problem)
        if output_format:
            sections.append(str(output_format))

        # Constraints
        sections.append("\nConstraints:")
        if problem.constraints:
            sections.append("\n".join(str(c) for c in problem.constraints))

        # Changes from examples to full input
        sections.append("\nImportant Changes from Examples to Full Input:")
        differences = analyzer.identify_example_differences(problem)
        if differences:
            sections.append("\n".join(differences))
        else:
            sections.append("None detected")

        # Final question
        sections.append("\nFinal Question to Answer:")
        sections.append(problem.final_question)

        # Reminders
        sections.append("\nRemember to:")
        sections.append("1. Handle all input format variations robustly")
        sections.append("2. Account for differences between examples and full input")
        sections.append("3. Consider all constraints")
        sections.append("4. Focus on solving the final question accurately")

        return "\n".join(sections)


# Default prompt templates
DEFAULT_TEMPLATES = {
    "basic_solution": PromptTemplate(
        name="basic_solution",
        template="""
        Problem: {title}

        {description}

        {examples}

        Constraints:
        {constraints}

        Question: {final_question}

        Please provide a solution in Python that correctly solves this problem.
        Focus on correctness first, then optimize if needed.
        """,
        description="Basic template for solution generation",
        variables=["title", "description", "examples", "constraints", "final_question"],
    ),
    "optimization": PromptTemplate(
        name="optimization",
        template="""
        Review and optimize this solution:
        {current_solution}

        Original Problem:
        {problem_description}

        Focus Areas:
        1. Time complexity
        2. Space complexity
        3. Code readability
        4. Edge cases

        Provide an optimized version with explanations.
        """,
        description="Template for solution optimization",
        variables=["current_solution", "problem_description"],
    ),
}
