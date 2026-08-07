"""Module for LLM prompt generation and management."""

import logging
from typing import List, Optional, Union
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
    content = """⚠️ CRITICAL REQUIREMENTS - READ CAREFULLY ⚠️

YOU MUST PROVIDE A COMPLETE, RUNNABLE PYTHON SOLUTION. NO EXCEPTIONS.

❌ DO NOT:
- Provide partial solutions or pseudo-code
- Include explanations or analysis outside the code block
- Ask questions or request clarifications
- Suggest multiple approaches
- Use placeholder code or TODOs

✅ YOU MUST:
1. Code Format:
   - Wrap your COMPLETE solution in ```python and ``` markers
   - Include ALL necessary imports at the top
   - Make the code ready to run without any modifications
   - Follow PEP 8 style guidelines

2. Input Handling:
   - Read from 'input.txt' in the current directory
   - Use proper file error handling (FileNotFoundError, etc.)
   - Handle malformed input gracefully
   - Close file handles properly

3. Solution Requirements:
   - Implement a single entrypoint function named solve (e.g. `def solve() -> int:`)
   - Have solve() read from 'input.txt' (you may use helper functions, but solve() must drive the whole solution)
   - Process input EXACTLY as specified in the problem
   - Convert strings to appropriate types (int/float)
   - Use efficient data structures and algorithms
   - Include comprehensive error handling
   - Follow all problem constraints
   - Assume only the Python standard library is available; do NOT use third-party packages (for example: numpy, pandas, scipy, networkx) unless the problem statement explicitly requires them
   - Every name you reference (modules, functions, classes, aliases like `np`, helpers, etc.) must be explicitly imported or defined at the top of the file; code must not rely on undefined names

4. Algorithm Adherence:
   - If the problem describes a specific procedure or algorithm, implement it EXACTLY as described
   - Implement a GENERAL algorithm that works for all valid inputs that match the described format, not just the provided examples
   - Do NOT hardcode example inputs, example outputs, or final answers; do NOT branch on exact example strings or specific file contents
   - Do NOT invent alternative approaches, optimizations, or "clever" solutions that contradict the stated rules
   - Do NOT build complex parsers, ASTs, or state machines unless explicitly required
   - When in doubt, prefer the simplest literal interpretation of the problem
   - Prefer a direct, step-by-step implementation of the stated rules over speculative shortcuts or formulas that are only justified by intuition

5. Reasoning Discipline and Overfit Avoidance:
   - Base your algorithm strictly on the problem text and examples; do not rely on unstated assumptions or "magical" inferences
   - Before you write code, mentally or on scratch structure the requirements: list the concrete rules, inputs, outputs, and invariants your solution must respect
   - Work through those requirements methodically in your design so that each rule is explicitly handled somewhere in the logic
   - Treat the examples as sanity checks, not as an exhaustive specification; expect additional, larger, and edge-case inputs
   - Never write code that only matches specific example sequences, page numbers, grid fragments, or known final answers
   - Any heuristics (sorting, greedy choices, pruning, etc.) must be justified by the stated rules, not just because they work on the example

6. Output Format:
   - Print ONLY the final answer
   - No labels, descriptions, or formatting
   - Raw number output only (e.g., '42' or '3.14')
   - Single print statement for the answer

Example of CORRECT response format:
```python
from typing import List
import sys

def solve() -> int:
    with open('input.txt') as f:
        # Solution implementation
        return answer

if __name__ == '__main__':
    print(solve())
```

⚠️ IF YOUR RESPONSE DOES NOT MATCH THIS FORMAT EXACTLY, IT WILL BE REJECTED ⚠️"""
    
    return PromptSection("Requirements", content, priority=3)

def generate_implementation_prompt(
    problem: ParsedProblem,
    analyzer: Optional[ProblemAnalyzer] = None,
    prior_analysis: Optional[str] = None,
    strategies: Optional[List[Strategy]] = None,
) -> str:
    """Generate implementation prompt for a problem.
    
    This template adapts based on problem analysis and relevant strategies.
    
    Args:
        problem: The parsed problem
        analyzer: Optional problem analyzer for enhanced analysis
        
    Returns:
        Formatted implementation prompt
    """
    # Prefer strategies chosen by the caller -- BaseSolver ranks them using the
    # learning database's recorded effectiveness. This function used to always
    # re-derive its own set from description keywords and ignore the argument,
    # so the strategy-effectiveness machinery never influenced a single prompt.
    # Fall back to keyword derivation when the caller supplies nothing.
    if not strategies:
        strategy_names = get_strategies_for_problem(problem.description)
        strategies = [
            strategy
            for category in SOLUTION_STRATEGIES.values()
            for strategy in category
            if strategy.name in strategy_names
        ]

    # Generate prompt sections
    sections = [
        PromptSection("Problem", problem.description, priority=0),
        PromptSection("Examples", format_test_cases(problem.examples), priority=1),
        get_parsing_guidance(problem, strategies),
        get_strategy_guidance(strategies),
        get_implementation_requirements(),
        PromptSection("Final Question", problem.final_question, priority=4),
    ]

    # Add pattern-based guidance for recognized algorithmic problem classes.
    # 
    # IMPORTANT PRINCIPLE: Prompt guidance must be GENERIC to a problem CLASS,
    # not specific to any particular problem. Good guidance:
    # - Identifies the algorithmic pattern (e.g., "linear scan", "graph search")
    # - Provides wisdom about common pitfalls and efficient approaches
    # - Does NOT restate the problem or provide solution steps
    # - Does NOT include problem-specific values, counts, or magic numbers
    # - Empowers the LLM's problem-solving intuition without constraining it
    #
    # If guidance would essentially "give away" the solution, it's overfit.
    # The LLM should derive the algorithm from the problem description.
    
    text = (problem.description or "").lower()
    clarifications = []

    # Pattern: Linear String Scanning
    # Triggered when problem involves finding patterns/instructions in a noisy string.
    # This is a broad pattern class, not specific to any one problem.
    if any(kw in text for kw in ["scan", "corrupted", "memory", "instruction"]) and "(" in text:
        clarifications.append(
            "PATTERN CLASS: Linear String Scanning\n\n"
            "This problem likely involves finding valid patterns within a noisy or corrupted string. "
            "Common wisdom for this pattern class:\n\n"
            "- Read input as a single continuous string (don't split prematurely)\n"
            "- Don't assume the content fits on one line; read the whole file as-is\n"
            "- Scan character-by-character from left to right\n"
            "- At each position, check if any valid pattern starts there\n"
            "- Match patterns exactly as specified - partial matches don't count\n"
            "- Advance past matched patterns; increment by 1 for non-matches\n"
            "- Keep solution simple: basic string operations usually suffice\n"
            "- When control tokens enable/disable processing, use a simple boolean flag and update it only when you exactly match the control token\n"
            "- Avoid inventing delimiters or fixed-width slices; search for the literal tokens described\n"
            "- Do not hardcode example inputs or compare the entire input to a known sample; handle arbitrary inputs that follow the described format\n\n"
            "Reasoning Checklist: Before coding, enumerate the rules (what tokens to find, what to do on match/no-match, any state changes). "
            "Design data structures to track state. Then implement each rule explicitly."
        )

    
    # Pattern: Paired/Columnar Data
    # Triggered when problem involves two parallel lists/columns that need coordination.
    if any(kw in text for kw in ["two lists", "left list", "right list", "two columns", "pair"]):
        clarifications.append(
            "PATTERN CLASS: Paired/Columnar Data\n\n"
            "This problem involves coordinating operations across two parallel sequences. "
            "Common wisdom for this pattern class:\n\n"
            "- Input often has MANY lines, each containing values for both sequences\n"
            "- Read ALL lines of input, not just the first one or two\n"
            "- Parse each line to extract values for each sequence/column\n"
            "- Consider whether order matters (sorting, pairing, etc.)\n"
            "- Think about how elements from each sequence relate to each other\n"
            "- Watch for off-by-one errors when pairing elements\n\n"
            "Reasoning Checklist: Before coding, list the operations required (parsing, sorting, pairing, aggregation). "
            "Decide data structures for each sequence. Then implement each step explicitly."
        )

    # Pattern: 2D Grid / Word Search & Local Patterns
    # Triggered when the problem describes letters or values arranged in rows/columns,
    # a grid or map, or a word-search-style puzzle.
    if any(
        kw in text
        for kw in [
            "grid",
            "word search",
            "rows and columns",
            "rows x",
            "columns",
            "two-dimensional",
            "2d",
            "matrix",
            "map",
        ]
    ):
        clarifications.append(
            "PATTERN CLASS: 2D Grid / Word Search & Local Patterns\n\n"
            "This problem likely involves scanning a 2D grid of characters or values for words or small fixed patterns. "
            "Common wisdom for this pattern class:\n\n"
            "- Represent the input as a list of equal-length strings: each line is a row, each character a cell\n"
            "- Do not drop or filter characters (such as '.') unless the problem explicitly says to ignore them\n"
            "- Compute rows = len(grid) and cols = len(grid[0]); use 0-based indexing consistently\n"
            "- When searching for words, treat each cell as a potential starting point and step along allowed direction vectors\n"
            "- If the problem allows multiple directions (horizontal, vertical, diagonal, forwards/backwards), implement all of them explicitly\n"
            "- For small local shapes built from neighboring cells, iterate over all cells where the full shape could fit and check required offsets relative to that cell\n"
            "- Carefully guard all index accesses so you never read outside the grid bounds\n"
            "- Avoid hardcoding example grids, coordinates, or counts; your logic should handle arbitrary grids that follow the described format\n\n"
            "Reasoning Checklist: Before coding, enumerate the rules (directions to search, pattern shape, boundary conditions). "
            "Decide how to represent the grid and track visited/counted cells. Then implement each rule explicitly."
        )

    # Pattern: Multi-line Input Processing
    # Generic guidance for problems where input spans many lines.
    # This is a very common AoC pattern that models often get wrong.
    if any(kw in text for kw in ["each line", "every line", "lines of", "per line"]):
        clarifications.append(
            "PATTERN CLASS: Multi-line Input Processing\n\n"
            "This problem requires processing multiple lines of input. "
            "Common wisdom for this pattern class:\n\n"
            "- Read and process ALL lines in the input file, not just the first few\n"
            "- Use a loop to iterate over lines: `for line in f:` or `f.readlines()`\n"
            "- Don't assume a fixed number of lines unless explicitly stated\n"
            "- Handle empty lines and trailing whitespace appropriately\n"
            "- Parse each line according to its format before processing\n\n"
            "Reasoning Checklist: Before coding, identify the per-line format and the aggregation or transformation required. "
            "Decide data structures for accumulation. Then implement parsing and processing in a loop."
        )

    if clarifications:
        sections.append(
            PromptSection(
                "Pattern-Based Guidance",
                "\n\n".join(clarifications),
                priority=0,
            )
        )

    # Include prior analysis from an earlier reasoning step when available.
    if prior_analysis:
        sections.append(
            PromptSection(
                "Problem Analysis (previous reasoning)",
                prior_analysis,
                priority=0,
            )
        )

    # Add a generic, example-based correctness contract whenever examples exist.
    if problem.examples:
        contract_text = (
            "Your solution will be automatically tested on the examples above.\n"
            "- It must read the input in exactly the format shown in the examples.\n"
            "- Unless the problem explicitly states there are only a fixed number of lines, "
            "assume you should process all non-empty lines in the input file.\n"
            "- When you run your code on each example input, it must produce exactly the "
            "listed expected output (no extra text).\n"
            "- Passing these examples is NECESSARY but NOT SUFFICIENT: your code will also be run on additional inputs that follow the same format.\n"
            "- Implement the general algorithm; do not special-case the exact example inputs or outputs, and do not hardcode final answers.\n"
            "- Do not 'reverse engineer' a shortcut that only fits the examples; any reasoning or simplification must be justified by the stated rules, not by pattern-matching the sample."
        )
        sections.append(
            PromptSection(
                "Example-Based Correctness Contract",
                contract_text,
                priority=2,
            )
        )
    
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
