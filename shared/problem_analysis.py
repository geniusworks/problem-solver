"""Module for analyzing and classifying Advent of Code problems."""

import logging
import re
from dataclasses import dataclass
from enum import Enum, auto
from typing import Dict, List, Optional, Set, Tuple

from .parser import TestCase, ParsedProblem, InputFormat, ProblemConstraint

logger = logging.getLogger(__name__)

class ProblemCategory(Enum):
    """Categories of problem types commonly seen in AoC."""
    ARRAY_MANIPULATION = auto()
    GRAPH_TRAVERSAL = auto()
    DYNAMIC_PROGRAMMING = auto()
    PATTERN_MATCHING = auto()
    SIMULATION = auto()
    NUMBER_THEORY = auto()
    GRID_BASED = auto()
    STRING_PARSING = auto()
    BIT_MANIPULATION = auto()

class ExamplePurpose(Enum):
    """Purpose of an example in problem description."""
    BASIC_CASE = auto()        # Demonstrates basic problem solving
    EDGE_CASE = auto()         # Shows handling of edge cases
    NEW_CONDITION = auto()     # Introduces additional conditions
    CLARIFICATION = auto()     # Clarifies a specific aspect
    COMPLEX_CASE = auto()      # Shows handling of more complex inputs

class ProblemAnalyzer:
    """Analyzes problem descriptions to determine type and requirements."""
    
    def __init__(self):
        """Initialize the problem analyzer."""
        # Keywords associated with different problem categories
        self.category_indicators: Dict[ProblemCategory, List[str]] = {
            ProblemCategory.ARRAY_MANIPULATION: [
                "list", "array", "sequence", "elements", "sorted"
            ],
            ProblemCategory.GRAPH_TRAVERSAL: [
                "connected", "path", "nodes", "edges", "traverse"
            ],
            ProblemCategory.DYNAMIC_PROGRAMMING: [
                "optimal", "minimum", "maximum", "ways to", "combinations"
            ],
            ProblemCategory.PATTERN_MATCHING: [
                "pattern", "match", "repeat", "sequence", "find all"
            ],
            ProblemCategory.SIMULATION: [
                "simulate", "steps", "moves", "turns", "rounds"
            ],
            ProblemCategory.GRID_BASED: [
                "grid", "matrix", "2D", "adjacent", "coordinates"
            ],
            ProblemCategory.STRING_PARSING: [
                "parse", "format", "string", "text", "characters"
            ]
        }

        # Patterns that indicate changes in conditions
        self.condition_change_patterns = [
            r"in part (\d+), however,",
            r"but in the actual data",
            r"in the full puzzle input",
            r"different from the example",
            r"unlike the example",
            r"in addition to",
            r"furthermore",
            r"however,"
        ]

        # Patterns for input format variations
        self.format_variation_patterns = [
            r"followed by.*?instead",
            r"in a different format",
            r"formatted differently",
            r"includes additional",
            r"contains extra",
            r"also includes",
            r"with annotations"
        ]

    def analyze_problem(self, problem: ParsedProblem) -> ParsedProblem:
        """Analyze a problem to enhance its profile with detected characteristics."""
        # Analyze examples and their relationships
        self._analyze_examples(problem)
        
        # Detect categories and key concepts
        problem.key_concepts.update(self._extract_key_concepts(problem.description))
        
        # Analyze input format and variations
        self._analyze_input_format(problem)
        
        # Detect condition changes
        problem.condition_changes.extend(self._detect_condition_changes(problem))
        
        return problem

    def _analyze_examples(self, problem: ParsedProblem) -> None:
        """Analyze examples to determine their purposes and relationships."""
        prev_example = None
        for example in problem.examples:
            # Determine example purpose
            purpose = self._determine_example_purpose(example, prev_example, problem.description)
            example.demonstrates.add(purpose.name)
            
            # Find references to this example
            references = self._find_example_references(example, problem.description)
            example.referenced_by.extend(references)
            
            # Compare with previous example for progressive complexity
            if prev_example:
                changes = self._compare_examples(prev_example, example)
                if changes:
                    example.demonstrates.update(changes)
            
            prev_example = example

    def _determine_example_purpose(
        self, 
        example: TestCase, 
        prev_example: Optional[TestCase], 
        description: str
    ) -> ExamplePurpose:
        """Determine the primary purpose of an example."""
        context = description[max(0, description.find(example.input_data) - 200):
                            description.find(example.input_data) + len(example.input_data) + 200]
        
        # Check for indicators of purpose
        if any(word in context.lower() for word in ["edge", "special", "corner"]):
            return ExamplePurpose.EDGE_CASE
        elif any(word in context.lower() for word in ["however", "but", "instead", "unlike"]):
            return ExamplePurpose.NEW_CONDITION
        elif any(word in context.lower() for word in ["clarify", "explain", "understand"]):
            return ExamplePurpose.CLARIFICATION
        elif prev_example and len(example.input_data) > len(prev_example.input_data) * 1.5:
            return ExamplePurpose.COMPLEX_CASE
        
        return ExamplePurpose.BASIC_CASE

    def _compare_examples(self, ex1: TestCase, ex2: TestCase) -> Set[str]:
        """Compare two examples to identify what the second one demonstrates."""
        changes = set()
        
        # Check for size differences
        if len(ex2.input_data) > len(ex1.input_data) * 1.5:
            changes.add("INCREASED_SIZE")
        
        # Check for new patterns or elements
        ex1_patterns = set(re.findall(r'\b\w+\b', ex1.input_data))
        ex2_patterns = set(re.findall(r'\b\w+\b', ex2.input_data))
        if ex2_patterns - ex1_patterns:
            changes.add("NEW_ELEMENTS")
        
        # Check for structural changes
        ex1_lines = ex1.input_data.splitlines()
        ex2_lines = ex2.input_data.splitlines()
        if len(ex1_lines) > 0 and len(ex2_lines) > 0:
            if len(ex1_lines[0].split()) != len(ex2_lines[0].split()):
                changes.add("STRUCTURE_CHANGE")
        
        return changes

    def _find_example_references(self, example: TestCase, description: str) -> List[str]:
        """Find parts of the description that reference this example."""
        references = []
        # Look for references after the example
        example_pos = description.find(example.input_data)
        if example_pos >= 0:
            after_example = description[example_pos + len(example.input_data):]
            # Look for phrases referencing "the example above" or specific values
            for match in re.finditer(r'(?:in the example above|in this example|the example shows).*?(?:\.|$)', 
                                   after_example):
                references.append(match.group(0).strip())
            # Look for references to specific values from the example
            for line in example.input_data.splitlines():
                if line.strip():
                    for match in re.finditer(f"[^0-9]{line.strip()}[^0-9]", after_example):
                        context = after_example[max(0, match.start() - 50):match.end() + 50]
                        references.append(context.strip())
        return references

    def _analyze_input_format(self, problem: ParsedProblem) -> None:
        """Analyze input format and detect variations."""
        if not problem.examples:
            return

        # Analyze base format from first example
        base_example = problem.examples[0]
        base_lines = base_example.input_data.splitlines()
        
        # Determine basic structure
        if len(base_lines) == 1:
            problem.input_format.base_format = "single_line"
        else:
            line_patterns = set()
            for line in base_lines:
                # Create pattern for line structure
                pattern = re.sub(r'\d+', 'N', line)
                pattern = re.sub(r'[a-zA-Z]+', 'W', pattern)
                line_patterns.add(pattern)
            
            if len(line_patterns) == 1:
                problem.input_format.base_format = f"repeated_pattern:{next(iter(line_patterns))}"
            else:
                problem.input_format.base_format = "mixed_format"

        # Look for format variations in later examples
        for example in problem.examples[1:]:
            variation = self._detect_format_variation(base_example.input_data, example.input_data)
            if variation:
                problem.input_format.variations.append(variation)

        # Look for hints about full input format
        for pattern in self.format_variation_patterns:
            matches = re.finditer(pattern, problem.description, re.IGNORECASE)
            for match in matches:
                context = problem.description[max(0, match.start() - 100):match.end() + 100]
                problem.input_format.variations.append(f"full_input:{context.strip()}")

    def _detect_format_variation(self, base_input: str, new_input: str) -> Optional[str]:
        """Detect how new input format varies from base format."""
        base_lines = base_input.splitlines()
        new_lines = new_input.splitlines()
        
        variations = []
        
        # Check for additional fields
        base_fields = len(base_lines[0].split()) if base_lines else 0
        new_fields = len(new_lines[0].split()) if new_lines else 0
        if new_fields > base_fields:
            variations.append(f"additional_fields:{new_fields - base_fields}")
        
        # Check for different separators
        base_seps = set(re.findall(r'[^a-zA-Z0-9\s]', base_lines[0])) if base_lines else set()
        new_seps = set(re.findall(r'[^a-zA-Z0-9\s]', new_lines[0])) if new_lines else set()
        if new_seps != base_seps:
            variations.append(f"different_separators:{','.join(new_seps)}")
        
        # Check for annotations
        if any(re.search(r'\(.*?\)', line) for line in new_lines):
            variations.append("has_annotations")
        
        return "; ".join(variations) if variations else None

    def _detect_condition_changes(self, problem: ParsedProblem) -> List[str]:
        """Detect changes in conditions between examples and full input."""
        changes = []
        
        # Look for explicit mentions of changes
        for pattern in self.condition_change_patterns:
            matches = re.finditer(pattern, problem.description, re.IGNORECASE)
            for match in matches:
                # Get surrounding context
                start = max(0, match.start() - 100)
                end = min(len(problem.description), match.end() + 100)
                context = problem.description[start:end]
                changes.append(context.strip())
        
        # Compare conditions mentioned in different parts
        example_conditions = set()
        full_conditions = set()
        
        # Extract conditions from example contexts
        for example in problem.examples:
            for ref in example.referenced_by:
                conditions = re.findall(r'must|should|needs to|has to|cannot|can\'t', ref, re.IGNORECASE)
                example_conditions.update(conditions)
        
        # Extract conditions from parts mentioning full input
        full_input_contexts = re.finditer(r'(?:actual|full|real).*?input.*?(?:\.|$)', 
                                        problem.description, 
                                        re.IGNORECASE | re.DOTALL)
        for match in full_input_contexts:
            conditions = re.findall(r'must|should|needs to|has to|cannot|can\'t', 
                                  match.group(0), 
                                  re.IGNORECASE)
            full_conditions.update(conditions)
        
        # Compare conditions
        if full_conditions - example_conditions:
            changes.append(f"Additional conditions in full input: {', '.join(full_conditions - example_conditions)}")
        
        return changes

    def _extract_key_concepts(self, description: str) -> Set[str]:
        """Extract key concepts and algorithms from description."""
        concepts = set()
        
        # Look for algorithm hints
        algorithm_patterns = [
            (r'(?:depth|breadth)[- ]first', 'GRAPH_SEARCH'),
            (r'shortest path', 'PATHFINDING'),
            (r'dynamic programming', 'DP'),
            (r'greedy', 'GREEDY'),
            (r'recursive', 'RECURSION'),
            (r'binary search', 'BINARY_SEARCH'),
            (r'hash|set|dictionary', 'HASH_BASED'),
            (r'sort(?:ed|ing)?', 'SORTING'),
        ]
        
        for pattern, concept in algorithm_patterns:
            if re.search(pattern, description, re.IGNORECASE):
                concepts.add(concept)
        
        # Look for data structure hints
        structure_patterns = [
            (r'tree', 'TREE'),
            (r'graph', 'GRAPH'),
            (r'queue', 'QUEUE'),
            (r'stack', 'STACK'),
            (r'heap', 'HEAP'),
            (r'linked list', 'LINKED_LIST'),
            (r'grid|matrix', 'GRID'),
        ]
        
        for pattern, concept in structure_patterns:
            if re.search(pattern, description, re.IGNORECASE):
                concepts.add(concept)
        
        return concepts

    def categorize_problem(self, problem: ParsedProblem) -> List[ProblemCategory]:
        """Determine the categories this problem falls into."""
        categories = set()
        
        # Check description for category indicators
        for category, indicators in self.category_indicators.items():
            if any(indicator.lower() in problem.description.lower() for indicator in indicators):
                categories.add(category)
        
        return list(categories)
    
    def determine_input_format(self, problem: ParsedProblem) -> Optional[str]:
        """Determine the input format for this problem."""
        return problem.input_format.base_format if hasattr(problem, 'input_format') else None
    
    def determine_output_format(self, problem: ParsedProblem) -> Optional[str]:
        """Determine the output format for this problem."""
        return problem.output_format if hasattr(problem, 'output_format') else None
    
    def identify_example_differences(self, problem: ParsedProblem) -> List[str]:
        """Identify differences between examples and full input."""
        differences = []
        
        # Check for explicit mentions of differences
        for pattern in self.condition_change_patterns:
            matches = re.finditer(pattern, problem.description, re.IGNORECASE)
            for match in matches:
                context = problem.description[max(0, match.start() - 50):match.end() + 50]
                differences.append(context.strip())
        
        # Add any format variations
        if hasattr(problem, 'input_format') and problem.input_format.variations:
            differences.extend(problem.input_format.variations)
        
        return differences
