from collections import deque
from typing import Set, Tuple, Optional


def has_path(blocked: Set[Tuple[int, int]], grid_size: int = 71) -> bool:
    """
    Check if there is a path from (0,0) to (grid_size-1, grid_size-1)
    avoiding blocked cells.
    """
    start = (0, 0)
    end = (grid_size - 1, grid_size - 1)
    
    # Quick check: if start or end is blocked, no path
    if start in blocked or end in blocked:
        return False
    
    # BFS
    visited = {start}
    queue = deque([start])
    
    # Directions: up, down, left, right
    directions = [(0, 1), (0, -1), (1, 0), (-1, 0)]
    
    while queue:
        x, y = queue.popleft()
        
        if (x, y) == end:
            return True
        
        for dx, dy in directions:
            nx, ny = x + dx, y + dy
            
            # Check bounds
            if 0 <= nx < grid_size and 0 <= ny < grid_size:
                pos = (nx, ny)
                if pos not in blocked and pos not in visited:
                    visited.add(pos)
                    queue.append(pos)
                    
    return False


def solve() -> str:
    """
    Main solution function.
    Reads input.txt, iterates through coordinates, and finds the first
    coordinate that blocks the path from (0,0) to (70,70).
    """
    try:
        with open('input.txt', 'r') as f:
            lines = f.readlines()
    except FileNotFoundError:
        raise
    
    # Parse coordinates
    coordinates = []
    for line in lines:
        line = line.strip()
        if not line:
            continue
        parts = line.split(',')
        if len(parts) == 2:
            try:
                x = int(parts[0].strip())
                y = int(parts[1].strip())
                coordinates.append((x, y))
            except ValueError:
                continue
    
    if not coordinates:
        return ""
    
    blocked = set()
    
    # Iterate through each byte falling
    for coord in coordinates:
        blocked.add(coord)
        
        # Check if path is still possible
        if not has_path(blocked):
            # The current coordinate is the one that blocked the path
            return f"{coord[0]},{coord[1]}"
    
    # If we finish all coordinates and still have a path, return empty string
    # (shouldn't happen per problem statement)
    return ""


if __name__ == '__main__':
    print(solve())