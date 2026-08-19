import sys
from typing import List, Tuple


def solve() -> int:
    """
    Read the database file from 'input.txt' and determine how many of the
    available ingredient IDs are fresh (i.e., fall within at least one of the
    fresh ID ranges).
    
    The input format is:
    - A list of fresh ingredient ID ranges (e.g., "3-5")
    - A blank line
    - A list of available ingredient IDs (single integers)
    
    Returns the count of available IDs that are fresh.
    """
    try:
        with open('input.txt', 'r') as f:
            lines = f.readlines()
    except FileNotFoundError:
        return 0
    
    # Parse the input
    ranges = []  # List of (start, end) tuples
    available_ids = []  # List of integer IDs
    in_ranges_section = True
    
    for line in lines:
        line = line.strip()
        
        # Skip empty lines
        if not line:
            in_ranges_section = False
            continue
        
        if in_ranges_section:
            # Parse range like "3-5"
            parts = line.split('-')
            if len(parts) == 2:
                try:
                    start = int(parts[0])
                    end = int(parts[1])
                    ranges.append((start, end))
                except ValueError:
                    # If parsing fails, skip this line
                    pass
        else:
            # Parse available ID
            try:
                available_ids.append(int(line))
            except ValueError:
                # If parsing fails, skip this line
                pass
    
    # Check which available IDs are fresh
    count = 0
    for ingredient_id in available_ids:
        is_fresh = False
        for start, end in ranges:
            if start <= ingredient_id <= end:
                is_fresh = True
                break
        if is_fresh:
            count += 1
    
    return count


if __name__ == '__main__':
    print(solve())