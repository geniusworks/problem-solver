import sys


def is_invalid_id(n: int) -> bool:
    """
    Check if a number is an invalid ID.
    An invalid ID is a number whose decimal representation consists of
    a sequence of digits repeated exactly twice.
    E.g., 55 (5 twice), 6464 (64 twice), 123123 (123 twice)
    """
    s = str(n)
    length = len(s)
    
    # Must have even number of digits
    if length % 2 != 0:
        return False
    
    half = length // 2
    first_half = s[:half]
    second_half = s[half:]
    
    return first_half == second_half


def solve() -> int:
    """
    Read input from 'input.txt', find all invalid IDs in the given ranges,
    and return their sum.
    """
    try:
        with open('input.txt', 'r') as f:
            content = f.read()
    except FileNotFoundError:
        # If input.txt doesn't exist, try reading from stdin
        try:
            content = sys.stdin.read()
        except Exception:
            return 0
    
    # Clean the input: remove whitespace and newlines
    content = content.strip().replace('\n', '').replace('\r', '').replace(' ', '')
    
    if not content:
        return 0
    
    # Split by commas to get individual ranges
    range_strings = content.split(',')
    
    total_sum = 0
    
    for r_str in range_strings:
        r_str = r_str.strip()
        if not r_str:
            continue
        
        # Each range is in the format "start-end"
        parts = r_str.split('-')
        if len(parts) != 2:
            continue
        
        try:
            start = int(parts[0])
            end = int(parts[1])
        except ValueError:
            continue
        
        if start > end:
            continue
        
        # Iterate through the range and check each number
        for i in range(start, end + 1):
            if is_invalid_id(i):
                total_sum += i
    
    return total_sum


if __name__ == '__main__':
    print(solve())