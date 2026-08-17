import sys
from functools import lru_cache

def solve() -> int:
    # Read input from input.txt
    try:
        with open('input.txt', 'r') as f:
            lines = f.readlines()
    except FileNotFoundError:
        # Fallback to stdin if input.txt doesn't exist
        lines = sys.stdin.readlines()
    
    # Parse the grid
    grid = []
    for line in lines:
        line = line.strip()
        if line:
            grid.append(line)
    
    if not grid:
        return 0
    
    rows = len(grid)
    cols = len(grid[0]) if rows > 0 else 0
    
    # Memoization for counting paths
    # We'll use a dictionary to store (row, col) -> number of paths to any 9
    memo = {}
    
    def count_paths(r: int, c: int) -> int:
        """Count the number of distinct hiking trails starting at (r, c) that end at a 9."""
        if (r, c) in memo:
            return memo[(r, c)]
        
        current_digit = int(grid[r][c])
        
        # Base case: if we're at 9, this is a valid endpoint
        if current_digit == 9:
            memo[(r, c)] = 1
            return 1
        
        # Otherwise, sum the paths from all valid next steps (digit + 1)
        total = 0
        next_digit = current_digit + 1
        target_char = chr(ord('0') + next_digit)
        
        # Check 4 directions: up, down, left, right
        directions = [(-1, 0), (1, 0), (0, -1), (0, 1)]
        for dr, dc in directions:
            nr, nc = r + dr, c + dc
            if 0 <= nr < rows and 0 <= nc < cols:
                if grid[nr][nc] == target_char:
                    total += count_paths(nr, nc)
        
        memo[(r, c)] = total
        return total
    
    # Sum the ratings of all trailheads (cells with '0')
    total_rating = 0
    for r in range(rows):
        for c in range(cols):
            if grid[r][c] == '0':
                total_rating += count_paths(r, c)
    
    return total_rating

if __name__ == '__main__':
    print(solve())