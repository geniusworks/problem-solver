"""Module for generating optimized prompts for LLM models."""

import logging
from dataclasses import dataclass
from typing import List, Optional

from shared.parser import ParsedProblem
from shared.problem_analysis import ProblemAnalyzer, ProblemCategory, ExamplePurpose

logger = logging.getLogger(__name__)

class PromptGenerator:
    """Generates optimized prompts for LLM models."""

    def generate(self, problem: ParsedProblem, analyzer: ProblemAnalyzer) -> str:
        """Generate an optimized prompt for the given problem.
        
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
