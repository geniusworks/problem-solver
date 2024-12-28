"""Problem parsing and structuring utilities."""

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Dict, Any

@dataclass
class TestCase:
    """A test case extracted from problem description."""
    input_data: str
    expected_output: str
    description: Optional[str] = None

@dataclass
class ProblemConstraint:
    """A constraint identified in the problem description."""
    description: str
    type: str  # 'input', 'output', 'time', 'memory', etc.
    value: Optional[str] = None

@dataclass
class ParsedProblem:
    """Structured representation of an Advent of Code problem."""
    year: int
    day: int
    title: str
    description: str
    part: int
    examples: List[TestCase]
    constraints: List[ProblemConstraint]
    input_format: str
    output_format: str
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "year": self.year,
            "day": self.day,
            "title": self.title,
            "description": self.description,
            "part": self.part,
            "examples": [
                {
                    "input": ex.input_data,
                    "expected": ex.expected_output,
                    "description": ex.description
                }
                for ex in self.examples
            ],
            "constraints": [
                {
                    "description": c.description,
                    "type": c.type,
                    "value": c.value
                }
                for c in self.constraints
            ],
            "input_format": self.input_format,
            "output_format": self.output_format
        }
    
    def save(self, file_path: Path) -> None:
        """Save the parsed problem to a JSON file."""
        with open(file_path, 'w') as f:
            json.dump(self.to_dict(), f, indent=2)
    
    @classmethod
    def load(cls, file_path: Path) -> 'ParsedProblem':
        """Load a parsed problem from a JSON file."""
        with open(file_path) as f:
            data = json.load(f)
        
        examples = [
            TestCase(
                input_data=ex["input"],
                expected_output=ex["expected"],
                description=ex.get("description")
            )
            for ex in data["examples"]
        ]
        
        constraints = [
            ProblemConstraint(
                description=c["description"],
                type=c["type"],
                value=c.get("value")
            )
            for c in data["constraints"]
        ]
        
        return cls(
            year=data["year"],
            day=data["day"],
            title=data["title"],
            description=data["description"],
            part=data["part"],
            examples=examples,
            constraints=constraints,
            input_format=data["input_format"],
            output_format=data["output_format"]
        )

def parse_problem_text(text: str, year: int, day: int, part: int = 1) -> ParsedProblem:
    """Parse problem text into structured format."""
    # Extract title
    title_match = re.search(r"---\s+(Day \d+:.+?)\s+---", text)
    title = title_match.group(1) if title_match else f"Day {day}"
    
    # Extract examples
    examples = []
    example_blocks = re.finditer(r"Example:?\n(.*?)(?=\n\n|\Z)", text, re.DOTALL)
    for block in example_blocks:
        example_text = block.group(1).strip()
        # TODO: Extract expected output from surrounding context
        examples.append(TestCase(
            input_data=example_text,
            expected_output="",  # This needs to be extracted from context
            description=None
        ))
    
    # Extract constraints
    constraints = []
    # TODO: Implement constraint extraction
    # Look for patterns like:
    # - "must be"
    # - "cannot exceed"
    # - "at most/least"
    # - Time/memory limits
    
    # Determine input/output format
    input_format = "One number per line"  # TODO: Detect from examples
    output_format = "Single number"  # TODO: Detect from problem description
    
    return ParsedProblem(
        year=year,
        day=day,
        title=title,
        description=text,
        part=part,
        examples=examples,
        constraints=constraints,
        input_format=input_format,
        output_format=output_format
    )
