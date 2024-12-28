"""Module for analyzing and classifying Advent of Code problems."""

import logging
import re
from dataclasses import dataclass
from enum import Enum, auto
from typing import Dict, List, Optional, Set, Tuple

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
    PATHFINDING = auto()

@dataclass
class TestCase:
    """Test case with input and expected output."""
    input_data: str
    expected_output: str

@dataclass
class ProblemProfile:
    """Profile of a problem's characteristics."""
    categories: Set[ProblemCategory]
    input_format: str  # Description of expected input format
    output_format: str  # Description of expected output format
    example_complexity: str  # Time/space complexity shown in example
    has_visualization: bool  # Whether problem benefits from visualization
    estimated_difficulty: int  # 1-5 scale
    key_concepts: List[str]  # List of important concepts/algorithms

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
            # Add more indicators for other categories
        }

    def extract_test_cases(self, description: str) -> List[TestCase]:
        """Extract test cases from problem description.
        
        Args:
            description: Problem description text
            
        Returns:
            List of test cases with input and expected output
        """
        test_cases = []
        
        # Look for sections that start with "For example" or similar
        example_sections = re.split(r'(?i)for example[:]?|example[:]|\n### Example\s*\n', description)
        
        if len(example_sections) > 1:
            for section in example_sections[1:]:
                # First try to find explicit input/output pairs
                input_match = re.search(r'input[:]?\s*([^\n]+)', section, re.IGNORECASE)
                output_match = re.search(r'output[:]?\s*([^\n]+)|answer[:]?\s*([^\n]+)', section, re.IGNORECASE)
                
                if input_match and output_match:
                    input_data = input_match.group(1).strip()
                    output_data = (output_match.group(1) or output_match.group(2)).strip()
                    test_cases.append(TestCase(input_data=input_data, expected_output=output_data))
                else:
                    # Try to find code blocks with backticks
                    code_blocks = re.findall(r'```\n(.*?)\n```', section, re.DOTALL)
                    if code_blocks:
                        # Look for explanation of the answer after the code block
                        for block in code_blocks:
                            answer_match = re.search(r'(?:In this example,|the answer is)[^0-9]*(\d+)', section, re.IGNORECASE)
                            if answer_match:
                                test_cases.append(TestCase(
                                    input_data=block.strip(),
                                    expected_output=answer_match.group(1).strip()
                                ))
        
        return test_cases

    def analyze_problem(
        self,
        description: str,
        example_input: str,
        example_output: str
    ) -> ProblemProfile:
        """Analyze a problem description to create a profile.
        
        Args:
            description: Problem description text
            example_input: Example input provided
            example_output: Expected output for example
            
        Returns:
            ProblemProfile containing analysis results
        """
        # This is a placeholder implementation
        # We need sophisticated NLP and pattern recognition here
        categories = set()
        
        # Simple keyword-based category detection
        for category, indicators in self.category_indicators.items():
            if any(indicator in description.lower() for indicator in indicators):
                categories.add(category)
        
        # Analyze input format
        input_format = self._analyze_input_format(example_input)
        
        # Analyze output format
        output_format = self._analyze_output_format(example_output)
        
        # Estimate difficulty
        difficulty = self._estimate_difficulty(description, categories)
        
        return ProblemProfile(
            categories=categories,
            input_format=input_format,
            output_format=output_format,
            example_complexity="Unknown",  # Needs implementation
            has_visualization=self._needs_visualization(description),
            estimated_difficulty=difficulty,
            key_concepts=self._extract_key_concepts(description)
        )

    def _analyze_input_format(self, example_input: str) -> str:
        """Analyze the format of input data.
        
        Args:
            example_input: Example input string
            
        Returns:
            Description of input format
        """
        # TODO: Implement sophisticated input format analysis
        return "Needs implementation"

    def _analyze_output_format(self, example_output: str) -> str:
        """Analyze the format of expected output.
        
        Args:
            example_output: Example output string
            
        Returns:
            Description of output format
        """
        # TODO: Implement output format analysis
        return "Needs implementation"

    def _estimate_difficulty(
        self,
        description: str,
        categories: Set[ProblemCategory]
    ) -> int:
        """Estimate problem difficulty on a 1-5 scale.
        
        Args:
            description: Problem description
            categories: Detected problem categories
            
        Returns:
            Difficulty rating 1-5
        """
        # TODO: Implement difficulty estimation
        return 3

    def _needs_visualization(self, description: str) -> bool:
        """Determine if problem would benefit from visualization.
        
        Args:
            description: Problem description
            
        Returns:
            True if visualization would be helpful
        """
        # TODO: Implement visualization need detection
        return False

    def _extract_key_concepts(self, description: str) -> List[str]:
        """Extract key concepts and algorithms from description.
        
        Args:
            description: Problem description
            
        Returns:
            List of key concepts
        """
        # TODO: Implement key concept extraction
        return []
