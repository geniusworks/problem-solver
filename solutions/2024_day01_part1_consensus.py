def solve(input_file_path):
    """Solve the problem.
    
    Args:
        input_file_path: Path to the input file
        
    Returns:
        The answer as an integer or float
    """
    with open(input_file_path) as f:
        data = [line.strip() for line in f]
    return len(data)  # Default implementation

if __name__ == "__main__":
    import sys
    print(solve(sys.argv[1]))