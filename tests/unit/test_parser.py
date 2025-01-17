"""Test problem parsing functionality."""

import pytest
from shared.parser import parse_problem_text, ParsedProblem


def test_parse_problem_with_examples():
    """Test parsing a problem with example test cases."""
    problem_text = """
    --- Day 1: Example Problem ---
    Here's a simple problem.
    
    For example:
    1,2,3 => 6
    4,5,6 => 15
    
    What is the sum of the numbers?
    """
    
    parsed = parse_problem_text(problem_text)
    assert isinstance(parsed, ParsedProblem)
    assert len(parsed.examples) == 2
    assert parsed.examples[0].input == "1,2,3"
    assert parsed.examples[0].expected == "6"


def test_parse_problem_without_examples():
    """Test parsing a problem without example test cases."""
    problem_text = """
    --- Day 1: Example Problem ---
    Here's a problem without examples.
    
    What is the answer?
    """
    
    parsed = parse_problem_text(problem_text)
    assert isinstance(parsed, ParsedProblem)
    assert len(parsed.examples) == 0
