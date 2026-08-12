"""Test code execution and resource management."""

import pytest
from shared.execution import execute_solution
from shared.execution import PerformanceMetrics


async def test_execute_valid_solution():
    """Test executing a valid solution."""
    code = """
def solve(input_data: str) -> str:
    return str(sum(int(x) for x in input_data.split(',')))
"""
    input_data = "1,2,3"
    result = await execute_solution(code, input_data)
    assert result.output == "6"
    assert isinstance(result.performance, PerformanceMetrics)


async def test_execute_with_timeout():
    """Test execution timeout handling."""
    code = """
import time
def solve(input_data: str) -> str:
    time.sleep(10)  # Should timeout
    return "42"
"""
    input_data = "test"
    with pytest.raises(TimeoutError):
        await execute_solution(code, input_data, timeout=1)
