"""Module for LLM prompt generation and management."""

import logging
from typing import List, Optional
from dataclasses import dataclass

from shared.parser import ParsedProblem, TestCase
from shared.problem_analysis import ProblemAnalyzer
from shared.strategies import Strategy, ProblemCategory, get_strategies_for_problem, SOLUTION_STRATEGIES

logger = logging.getLogger(__name__)

@dataclass
class PromptSection:
    """A section of the generated prompt."""
    title: str
    content: str
    priority: int = 0

def format_test_cases(test_cases: List[TestCase]) -> str:
    """Format test cases for prompt."""
    formatted = []
    for i, case in enumerate(test_cases, 1):
        parts = [f"Example {i}:"]
        if case.demonstrates:
            parts.append(f"Purpose: {', '.join(case.demonstrates)}")
        parts.extend(["Input:", case.input_data, "Expected Output:", case.expected_output])
        if case.description:
            parts.append(f"Note: {case.description}")
        formatted.append("\n".join(parts))
    return "\n\n".join(formatted)

def get_parsing_guidance(problem: ParsedProblem, strategies: List[Strategy]) -> PromptSection:
    """Generate parsing guidance based on problem and strategies."""
    has_parsing_strategy = any(s for s in strategies if s.name == "Input Structure Analysis")
    
    # Base parsing guidance
    content = """Input Format Analysis:
1. Structure Analysis:
   - Identify line format (space-separated, fixed width, etc.)
   - Note delimiters and special characters
   - Check for pattern consistency
   - Handle variable spacing

2. Data Structure Selection:
   - Choose appropriate types (int, str, etc.)
   - Consider value relationships
   - Plan order preservation
   - Handle grouping needs"""

    # Add strategy-specific parsing tips if relevant
    if has_parsing_strategy:
        content += """

3. Advanced Parsing Considerations:
   - Handle multi-line records
   - Track nested structures
   - Parse hierarchical data
   - Validate format assumptions"""
    
    return PromptSection("Parsing Guidance", content, priority=1)

def get_strategy_guidance(strategies: List[Strategy]) -> PromptSection:
    """Generate strategy-specific guidance."""
    content = ["Solution Strategies:"]
    
    for strategy in strategies:
        content.append(f"\n{strategy.name}:")
        content.append(f"Purpose: {strategy.description}")
        content.append("Key Techniques:")
        for technique in strategy.key_techniques:
            content.append(f"- {technique}")
        content.append("\nOptimization Tips:")
        for tip in strategy.optimization_tips:
            content.append(f"- {tip}")
            
    return PromptSection("Strategy Guidance", "\n".join(content), priority=2)

def get_implementation_requirements() -> PromptSection:
    """Get basic implementation requirements."""
    content = """Implementation Requirements:
1. Function signature: solve(input_file_path: str) -> Union[int, float]
2. Input handling: Match example format exactly
3. Return value: Numeric answer only, no text
4. Debug output: Print first 5 parsed elements with types
5. Error handling: Validate all assumptions"""
    
    return PromptSection("Requirements", content, priority=3)

def generate_implementation_prompt(
    problem: ParsedProblem,
    analyzer: Optional[ProblemAnalyzer] = None
) -> str:
    """Generate implementation prompt for a problem.
    
    This template adapts based on problem analysis and relevant strategies.
    
    Args:
        problem: The parsed problem
        analyzer: Optional problem analyzer for enhanced analysis
        
    Returns:
        Formatted implementation prompt
    """
    # Get relevant strategies
    strategy_names = get_strategies_for_problem(problem.description)
    strategies = []
    for category in SOLUTION_STRATEGIES.values():
        for strategy in category:
            if strategy.name in strategy_names:
                strategies.append(strategy)
    
    # Generate prompt sections
    sections = [
        PromptSection("Problem", problem.description, priority=0),
        PromptSection("Examples", format_test_cases(problem.examples), priority=1),
        get_parsing_guidance(problem, strategies),
        get_strategy_guidance(strategies),
        get_implementation_requirements(),
        PromptSection("Final Question", problem.final_question, priority=4)
    ]
    
    # Sort sections by priority
    sections.sort(key=lambda x: x.priority)
    
    # Combine sections
    return "\n\n".join(f"{section.title}:\n{section.content}" for section in sections)

def generate_adaptive_prompt(problem: ParsedProblem, analyzer: ProblemAnalyzer) -> str:
    """Generate an optimized adaptive prompt for the given problem.

    This is an alternative prompt generation approach that uses problem analysis
    to dynamically generate a more targeted prompt. Currently not in use but
    kept for future enhancement.

    Args:
        problem: The parsed problem
        analyzer: The problem analyzer instance

    Returns:
        A formatted prompt string
    """
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
