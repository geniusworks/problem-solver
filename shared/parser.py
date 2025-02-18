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


def _determine_example_purpose(context_before: str, context_after: str) -> ExamplePurpose:
    """Determine the purpose of an example based on its surrounding context."""
    context = (context_before + " " + context_after).lower()
    
    # Look for keywords indicating edge cases
    edge_patterns = [
        r'\bedge\s*case\b',
        r'\bcorner\s*case\b',
        r'\blimit\b.*\bcase\b',
        r'\bextreme\b.*\bcase\b',
        r'\bspecial\s*case\b'
    ]
    
    for pattern in edge_patterns:
        if re.search(pattern, context):
            return ExamplePurpose.EDGE_CASE
    
    # Look for keywords indicating demonstration
    demo_patterns = [
        r'\bexample\b',
        r'\bdemonstrat\w+\b',
        r'\billustrat\w+\b',
        r'\bshow\w*\s+how\b',
        r'\bfor\s+instance\b'
    ]
    
    for pattern in demo_patterns:
        if re.search(pattern, context):
            return ExamplePurpose.DEMONSTRATION
    
    # Default to unknown if no clear purpose found
    return ExamplePurpose.UNKNOWN


def _extract_examples_from_text(text: str) -> List[TestCase]:
    """Extract examples from plain text version of problem.
    This is a fallback when HTML parsing fails.
    """
    examples = []
    # Look for code blocks that typically start with newlines and spaces
    code_blocks = re.finditer(r'\n\s*(\d[^\n]+(?:\n\s+[^\n]+)*)', text)
    for i, match in enumerate(code_blocks):
        block = match.group(1).strip()
        if block:
            # Get some context before and after for determining purpose
            start = max(0, match.start() - 200)
            end = min(len(text), match.end() + 200)
            context_before = text[start:match.start()]
            context_after = text[match.end():end]
            
            examples.append(TestCase(
                input_data=block,
                expected_output="",  # Will try to find this in surrounding text
                order=i,
                purpose=_determine_example_purpose(context_before, context_after)
            ))
    
    return examples


def _extract_examples(article: BeautifulSoup) -> List[TestCase]:
    """Extract all examples from problem text with their context."""
    logger.debug("Starting example extraction...")
    examples = []

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
            example_pos = article.get_text().find(code_content)
            if example_pos == -1:
                continue
                
            # Get all text before this example in the article
            context_before = article.get_text()[:example_pos].strip()
            
            # Get all text after this example until the next example or end
            next_pos = len(article.get_text())
            for next_block in pre_blocks[i+1:]:
                next_content = next_block.find("code")
                if next_content:
                    pos = article.get_text().find(next_content.get_text())
                    if pos != -1:
                        next_pos = pos
                        break
            
            context_after = article.get_text()[example_pos + len(code_content):next_pos].strip()
            
            # Look for expected output in various formats
            answer = None
            answer_type = None
            context_text = context_after.lower()
            
            # Try to find output after various keywords
            output_patterns = [
                # Numeric patterns
                (r'(?:answer|output|result)[: ]+([-+]?[0-9]*\.?[0-9]+)', 'numeric'),
                # String patterns (in quotes)
                (r'(?:answer|output|result)[: ]+["\']([^"\']*)["\'](\s|$)', 'string'),
                # String patterns (without quotes)
                (r'(?:answer|output|result)[: ]+([A-Za-z0-9_]+)\b', 'string'),
                # List patterns
                (r'(?:answer|output|result)[: ]+\[(.*?)\]', 'list'),
                # Boolean patterns
                (r'(?:answer|output|result)[: ]+(true|false)\b', 'boolean')
            ]
            
            for pattern, type_name in output_patterns:
                answer_match = re.search(pattern, context_text, re.IGNORECASE)
                if answer_match:
                    answer_str = answer_match.group(1).strip()
                    if type_name == 'numeric':
                        if '.' in answer_str:
                            answer = float(answer_str)
                            answer_type = 'float'
                        else:
                            answer = int(answer_str)
                            answer_type = 'integer'
                    elif type_name == 'string':
                        answer = answer_str
                        answer_type = 'string'
                    elif type_name == 'list':
                        answer = [x.strip() for x in answer_str.split(',')]
                        answer_type = 'list'
                    elif type_name == 'boolean':
                        answer = answer_str.lower() == 'true'
                        answer_type = 'boolean'
                    break
            
            # If no explicit answer found, look for a code block immediately after
            if answer is None and i + 1 < len(pre_blocks):
                next_code = pre_blocks[i + 1].find("code")
                if next_code and len(context_after.split()) < 20:  # Only if there's minimal text between
                    answer = next_code.get_text().strip()
                    answer_type = 'output_block'
            
            # Clean up input data - split into lines and remove extra whitespace
            input_lines = [line.strip() for line in code_content.split('\n') if line.strip()]
            examples.append(
                TestCase(
                    input_data='\n'.join(input_lines),
                    expected_output=str(answer) if answer is not None else "",
                    expected_type=answer_type,
                    description=f"{context_before}\n\n{context_after}",
                    order=len(examples),
                    demonstrates=set(),
                    referenced_by=[],
                    purpose=_determine_example_purpose(context_before, context_after)
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


def _extract_title(text: str) -> str:
    """Extract the title from problem text."""
    lines = text.strip().split("\n")
    return lines[0] if lines else ""


def _extract_part(text: str) -> Optional[int]:
    """Extract the part number from problem text."""
    # Look for Part Two heading
    if "--- Part Two ---" in text:
        return 2
    # Look for Part One heading or assume part 1 if neither found
    return 1


def _extract_constraints(text: str) -> List[ProblemConstraint]:
    """Extract constraints from problem text."""
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
        for match in re.finditer(pattern, text, re.IGNORECASE):
            constraints.append(
                ProblemConstraint(
                    description=match.group().strip(), type=type_, value=match.group(1)
                )
            )
    return constraints


def _extract_input_format(text: str) -> InputFormat:
    """Extract input format from problem text."""
    # For now, assume empty input format
    return InputFormat(base_format="")


def _extract_output_format(text: str) -> str:
    """Extract output format from problem text."""
    # For now, assume empty output format
    return ""


def parse_problem_text(problem_text: str, examples_file: Optional[Path] = None) -> ParsedProblem:
    """Parse problem text into structured format.

    Args:
        problem_text: Raw problem text (can be HTML or plain text)
        examples_file: Optional path to a file containing pre-extracted examples

    Returns:
        ParsedProblem object
    """
    logger.debug("Starting problem text parsing...")

    # Determine if input is HTML or plain text
    is_html = "<" in problem_text and ">" in problem_text
    
    if is_html:
        # Parse HTML
        soup = BeautifulSoup(problem_text, "html.parser")
        # Extract article content if available
        articles = soup.find_all("article", class_="day-desc")
        if articles:
            # Use the appropriate article based on part number
            part_text = soup.get_text()
            part = _extract_part(part_text) or 1
            article = articles[part - 1] if part <= len(articles) else articles[0]
        else:
            article = soup
        text_content = article.get_text()
    else:
        # Use plain text directly
        text_content = problem_text
        article = None

    # Try to load pre-extracted examples first
    examples = []
    if examples_file and examples_file.exists():
        logger.debug(f"Loading pre-extracted examples from {examples_file}")
        with open(examples_file, 'r', encoding='utf-8') as f:
            example_texts = f.read().split('\n---\n')
            for i, text in enumerate(example_texts):
                examples.append(TestCase(
                    input_data=text.strip(),
                    expected_output="",  # Will try to find this in text
                    order=i
                ))
    else:
        # Fall back to extracting examples from text
        logger.debug("No pre-extracted examples found, parsing from text")
        examples = _extract_examples(article) if article else _extract_examples_from_text(text_content)

    # Extract constraints
    constraints = _extract_constraints(text_content)

    # Extract final question
    final_question = _extract_final_question(text_content)

    # Create ParsedProblem object
    logger.debug("Creating ParsedProblem object...")
    problem = ParsedProblem(
        title=_extract_title(text_content) or "Unknown Title",
        description=text_content,
        part=_extract_part(text_content) or 1,
        examples=examples,
        constraints=constraints,
        input_format=_extract_input_format(text_content),
        output_format=_extract_output_format(text_content),
        final_question=final_question
    )

    # Try alternate parsing strategies if no examples found
    if not examples and article:
        logger.debug("No examples found, trying alternate parsing...")
        # Try finding pre blocks directly
        pre_blocks = article.find_all("pre")
        if pre_blocks:
            logger.debug(f"Found {len(pre_blocks)} pre blocks directly")
            for i, block in enumerate(pre_blocks):
                # Look for input/output pairs
                text = block.get_text().strip()
                if text:
                    problem.examples.append(TestCase(
                        input_data=text,
                        expected_output="",  # We'll try to find this in surrounding text
                        order=i
                    ))
                    logger.debug(f"Added example from pre block {i+1}")

    # Try to find expected outputs in text
    if problem.examples:
        logger.debug("Looking for expected outputs in text...")
        for example in problem.examples:
            if not example.expected_output:
                # Look for numbers following the example
                search_text = article.get_text() if article else text_content
                start_pos = search_text.find(example.input_data) + len(example.input_data)
                text_after = search_text[start_pos:start_pos + 200]
                numbers = re.findall(r'\b\d+\b', text_after)  # Look in next 200 chars
                if numbers:
                    example.expected_output = numbers[0]
                    logger.debug(f"Found expected output: {example.expected_output}")

    return problem
