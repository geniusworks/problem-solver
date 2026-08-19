import sys
from functools import lru_cache

def solve() -> int:
    """
    Reads the manifold diagram from 'input.txt' and calculates the number of timelines
    using the many-worlds interpretation of quantum tachyon splitting.
    """
    try:
        with open('input.txt', 'r') as f:
            lines = f.readlines()
    except FileNotFoundError:
        return 0

    # Filter out empty lines and strip whitespace
    grid_lines = [line.strip() for line in lines if line.strip()]
    
    if not grid_lines:
        return 0

    rows = len(grid_lines)
    if rows == 0:
        return 0
    
    cols = len(grid_lines[0])
    
    # Find the start position 'S'
    start_row = -1
    start_col = -1
    for r in range(rows):
        for c in range(cols):
            if grid_lines[r][c] == 'S':
                start_row = r
                start_col = c
                break
        if start_row != -1:
            break

    if start_row == -1:
        return 0

    @lru_cache(maxsize=None)
    def count_paths(r: int, c: int) -> int:
        # Base case: reached the bottom edge
        if r >= rows:
            return 1
        
        # Out of bounds (left or right)
        if c < 0 or c >= cols:
            return 0
        
        cell = grid_lines[r][c]
        
        if cell == '^':
            # Splitter: branches to left-down and right-down
            left_path = count_paths(r + 1, c - 1)
            right_path = count_paths(r + 1, c + 1)
            return left_path + right_path
        else:
            # Pass through (|, ., S, etc.) - moves straight down
            return count_paths(r + 1, c)

    result = count_paths(start_row, start_col)
    return result

if __name__ == '__main__':
    print(solve())