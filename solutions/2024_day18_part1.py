from collections import deque
from typing import List, Tuple


def solve() -> int:
    """
    Solve the RAM Run problem:
    - Read coordinates from input.txt
    - Simulate first 1024 bytes falling onto a 71x71 grid
    - Find shortest path from (0,0) to (70,70) avoiding corrupted cells
    """
    try:
        with open('input.txt', 'r') as f:
            lines = [line.strip() for line in f if line.strip()]
    except FileNotFoundError:
        # If input file doesn't exist, return -1
        return -1
    
    # Grid dimensions: coordinates 0 to 70, so 71x71 grid
    GRID_SIZE = 71
    
    # Initialize blocked grid (row, col) -> blocked
    blocked = [[False] * GRID_SIZE for _ in range(GRID_SIZE)]
    
    # Simulate first 1024 bytes falling
    for i, line in enumerate(lines):
        if i >= 1024:
            break
        try:
            parts = line.split(',')
            if len(parts) != 2:
                continue
            x = int(parts[0].strip())
            y = int(parts[1].strip())
            # Check bounds
            if 0 <= x < GRID_SIZE and 0 <= y < GRID_SIZE:
                blocked[y][x] = True  # row=y, col=x
        except (ValueError, IndexError):
            continue
    
    # Check if start or end is blocked
    if blocked[0][0] or blocked[70][70]:
        return -1
    
    # BFS to find shortest path from (0,0) to (70,70)
    start = (0, 0)
    end = (70, 70)
    
    queue = deque()
    queue.append((0, 0, 0))  # (row, col, steps)
    visited = [[False] * GRID_SIZE for _ in range(GRID_SIZE)]
    visited[0][0] = True
    
    # Directions: up, down, left, right
    directions = [(-1, 0), (1, 0), (0, -1), (0, 1)]
    
    while queue:
        row, col, steps = queue.popleft()
        
        if row == 70 and col == 70:
            return steps
        
        for dr, dc in directions:
            new_row = row + dr
            new_col = col + dc
            
            # Check bounds
            if 0 <= new_row < GRID_SIZE and 0 <= new_col < GRID_SIZE:
                # Check if not visited and not blocked
                if not visited[new_row][new_col] and not blocked[new_row][new_col]:
                    visited[new_row][new_col] = True
                    queue.append((new_row, new_col, steps + 1))
    
    # No path found
    return -1


if __name__ == '__main__':
    print(solve())