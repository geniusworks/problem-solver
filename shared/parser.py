"""Problem parsing and structuring utilities."""

import json
import logging
import re
from bs4 import BeautifulSoup
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import List, Optional, Dict, Any, Set

logger = logging.getLogger(__name__)


class ExamplePurpose(Enum):
    """Purpose of an example."""

    DEMONSTRATION = "demonstration"
    EDGE_CASE = "edge case"
    CORNER_CASE = "corner case"
    UNKNOWN = "unknown"


@dataclass
class TestCase:
    """A test case extracted from problem description."""

    input_data: str
    expected_output: str
    expected_type: Optional[str] = None
    description: Optional[str] = None
    order: int = 0  # Order in which example appears
    demonstrates: Set[str] = field(
        default_factory=set
    )  # What this example demonstrates
    referenced_by: List[str] = field(
        default_factory=list
    )  # Parts of text referencing this example
    purpose: Optional[ExamplePurpose] = None  # Purpose of this example


@dataclass
class ProblemConstraint:
    """A constraint identified in the problem description."""

    description: str
    type: str  # 'input', 'output', 'time', 'memory', etc.
    value: Optional[str] = None
    applies_to: str = "all"  # "example", "full", or "all"


@dataclass
class InputFormat:
    """Description of input format with variations."""

    base_format: str
    variations: List[str] = field(default_factory=list)
    example_format: Optional[str] = None
    full_format: Optional[str] = None


@dataclass
class ParsedProblem:
    """Structured representation of an Advent of Code problem."""

    title: str
    description: str
    part: int
    examples: List[TestCase]
    constraints: List[ProblemConstraint]
    input_format: InputFormat
    output_format: str
    final_question: str
    condition_changes: List[str] = field(
        default_factory=list
    )  # Changes between example and full
    key_concepts: Set[str] = field(default_factory=set)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "title": self.title,
            "description": self.description,
            "part": self.part,
            "examples": [
                {
                    "input_data": ex.input_data,
                    "expected_output": ex.expected_output,
                    "expected_type": ex.expected_type,
                    "description": ex.description,
                    "order": ex.order,
                    "demonstrates": list(ex.demonstrates),
                    "referenced_by": ex.referenced_by,
                    "purpose": ex.purpose.name if ex.purpose else None,
                }
                for ex in self.examples
            ],
            "constraints": [
                {
                    "description": c.description,
                    "type": c.type,
                    "value": c.value,
                    "applies_to": c.applies_to,
                }
                for c in self.constraints
            ],
            "input_format": {
                "base_format": self.input_format.base_format,
                "variations": self.input_format.variations,
                "example_format": self.input_format.example_format,
                "full_format": self.input_format.full_format,
            },
            "output_format": self.output_format,
            "final_question": self.final_question,
            "condition_changes": self.condition_changes,
            "key_concepts": list(self.key_concepts),
        }

    def save(self, file_path: Path) -> None:
        """Save the parsed problem to a JSON file."""
        with open(file_path, "w") as f:
            json.dump(self.to_dict(), f, indent=2)

    @classmethod
    def load(cls, file_path: Path) -> "ParsedProblem":
        """Load a parsed problem from a JSON file."""
        with open(file_path) as f:
            data = json.load(f)

        # Convert back to proper objects
        examples = [
            TestCase(
                input_data=ex["input_data"],
                expected_output=ex["expected_output"],
                expected_type=ex["expected_type"],
                description=ex["description"],
                order=ex["order"],
                demonstrates=set(ex["demonstrates"]),
                referenced_by=ex["referenced_by"],
                purpose=ExamplePurpose[ex["purpose"]] if ex["purpose"] else None,
            )
            for ex in data["examples"]
        ]

        constraints = [
            ProblemConstraint(
                description=c["description"],
                type=c["type"],
                value=c["value"],
                applies_to=c["applies_to"],
            )
            for c in data["constraints"]
        ]

        input_format = InputFormat(
            base_format=data["input_format"]["base_format"],
            variations=data["input_format"]["variations"],
            example_format=data["input_format"]["example_format"],
            full_format=data["input_format"]["full_format"],
        )

        return cls(
            title=data["title"],
            description=data["description"],
            part=data["part"],
            examples=examples,
            constraints=constraints,
            input_format=input_format,
            output_format=data["output_format"],
            final_question=data["final_question"],
            condition_changes=data["condition_changes"],
            key_concepts=set(data["key_concepts"]),
        )


def _extract_examples(text: str) -> List[TestCase]:
    """Extract all examples from problem text with their context."""
    logger.debug("Starting example extraction...")
    examples = []

    # Parse HTML
    soup = BeautifulSoup(text, "html.parser")
    
    # Get the full article content first
    article = soup.find("article", class_="day-desc")
    if not article:
        logger.warning("No article found in problem text")
        return examples
        
    article_text = article.get_text()
    
    # Find all pre blocks
    pre_blocks = article.find_all("pre")
    logger.debug("Found %d pre blocks", len(pre_blocks))
    
    for i, pre_block in enumerate(pre_blocks):
        try:
            # Get the code content
            code_block = pre_block.find("code")
            if not code_block:
                continue
                
            code_content = code_block.get_text().strip()
            logger.debug("Pre block %d content length: %d", i+1, len(code_content))
            
            # Find where this example occurs in the full article text
            example_pos = article_text.find(code_content)
            if example_pos == -1:
                continue
                
            # Get all text before this example in the article
            context_before = article_text[:example_pos].strip()
            
            # Get all text after this example until the next example or end
            next_pos = len(article_text)
            for next_block in pre_blocks[i+1:]:
                next_content = next_block.find("code")
                if next_content:
                    pos = article_text.find(next_content.get_text())
                    if pos != -1:
                        next_pos = pos
                        break
            
            context_after = article_text[example_pos + len(code_content):next_pos].strip()
            
            # Look for numbers in the context after that could be answers
            answer = None
            answer_type = None
            context_text = context_after
            
            # First try to find a number after "answer:" or similar
            answer_match = re.search(r'(?:answer|output|result)[: ]+([-+]?[0-9]*\.?[0-9]+)', context_text.lower())
            if answer_match:
                answer_str = answer_match.group(1)
                # Determine if it's an integer or float
                if '.' in answer_str:
                    answer = float(answer_str)
                    answer_type = 'float'
                else:
                    answer = int(answer_str)
                    answer_type = 'integer'
            
            # Clean up input data - split into lines and remove extra whitespace
            input_lines = [line.strip() for line in code_content.split('\n') if line.strip()]
            examples.append(
                TestCase(
                    input_data='\n'.join(input_lines),
                    expected_output=answer if answer is not None else "",  # Allow empty expected output
                    expected_type=answer_type,  # Store the type
                    description=f"{context_before}\n\n{context_after}",  # Include full article context
                    order=len(examples),
                    demonstrates=set(),
                    referenced_by=[],
                )
            )
            logger.debug("Added example with input and output")
            
        except Exception as e:
            logger.error(f"Error processing pre block {i+1}: {e}")
            continue

    logger.debug(f"Extracted {len(examples)} examples")
    return examples


def _extract_final_question(text: str) -> str:
    """Extract the final question from problem text."""
    patterns = [
        r"\*([^*]+)\*\?",  # Markdown style
        r"(?:What|How|Calculate|Find).*?\?",  # Question words
        r"Your puzzle answer.*?$",  # Generic ending
    ]

    for pattern in patterns:
        matches = re.finditer(pattern, text, re.MULTILINE)
        # Take the last match as it's usually the final question
        final_match = None
        for match in matches:
            final_match = match
        if final_match:
            return final_match.group().strip()

    return ""


def parse_problem_text(problem_text: str) -> ParsedProblem:
    """Parse problem text into structured format."""
    logger.debug("Starting problem text parsing...")

    # Extract title
    lines = problem_text.strip().split("\n")
    title = lines[0] if lines else ""
    description = "\n".join(lines[1:]) if len(lines) > 1 else ""

    # Extract examples with context
    logger.debug("Extracting examples...")
    examples = _extract_examples(problem_text)
    logger.debug(f"Found {len(examples)} examples")

    # Extract constraints
    logger.debug("Extracting constraints...")
    constraints = []
    constraint_patterns = [
        (r"must be (\d+)", "value"),
        (r"cannot exceed (\d+)", "limit"),
        (r"at least (\d+)", "minimum"),
        (r"at most (\d+)", "maximum"),
        (r"only (\d+)", "exact"),
        (r"exactly (\d+)", "exact"),
    ]

    for pattern, type_ in constraint_patterns:
        for match in re.finditer(pattern, problem_text, re.IGNORECASE):
            constraints.append(
                ProblemConstraint(
                    description=match.group().strip(), type=type_, value=match.group(1)
                )
            )
    logger.debug(f"Found {len(constraints)} constraints")

    # Create input format structure
    input_format = InputFormat(
        base_format="",  # Will be filled by analyzer
        variations=[],
        example_format=None,
        full_format=None,
    )

    # Extract final question (everything after the last example)
    final_question = _extract_final_question(problem_text)
    if not final_question and examples:
        # If no explicit final question found, use text after last example
        last_example_pos = problem_text.rfind(examples[-1].input_data)
        if last_example_pos != -1:
            remaining_text = problem_text[
                last_example_pos + len(examples[-1].input_data) :
            ].strip()
            final_question = remaining_text.split("\n")[-1].strip()

    logger.debug("Creating ParsedProblem object...")
    return ParsedProblem(
        title=title,
        description=description,
        part=1,
        examples=examples,
        constraints=constraints,
        input_format=input_format,
        output_format="",  # Will be filled by analyzer
        final_question=final_question,
        condition_changes=[],  # Will be filled by analyzer
        key_concepts=set(),  # Will be filled by analyzer
    )
