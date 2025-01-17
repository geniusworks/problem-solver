def solve(input_data: str) -> str:
    """Solve the example problem by summing numbers."""
    return str(sum(int(x) for x in input_data.split(',')))
