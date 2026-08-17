import sys
from typing import List, Tuple, Set

def simulate_guard(grid: List[str], extra_obstacle: Tuple[int, int]) -> bool:
    """
    Simulate the guard's movement with an extra obstacle.
    Returns True if the guard gets stuck in a loop, False if it exits the grid.
    """
    rows = len(grid)
    cols = len(grid[0])
    
    # Find the starting position
    start_r = -1
    start_c = -1
    for r in range(rows):
        for c in range(cols):
            ch = grid[r][c]
            if ch in ('^', 'v', '<', '>'):
                start_r = r
                start_c = c
                break
        if start_r != -1:
            break
    
    if start_r == -1:
        return False
    
    # Directions: 0=Up, 1=Right, 2=Down, 3=Left
    # Deltas for each direction
    deltas = [(-1, 0), (0, 1), (1, 0), (0, -1)]
    
    # Initial direction is Up (0)
    cur_r = start_r
    cur_c = start_c
    cur_dir = 0  # Up
    
    visited = set()
    
    # State is (row, col, direction)
    while True:
        state = (cur_r, cur_c, cur_dir)
        if state in visited:
            return True  # Loop detected
        visited.add(state)
        
        # Calculate next position
        dr, dc = deltas[cur_dir]
        next_r = cur_r + dr
        next_c = cur_c + dc
        
        # Check if next position is valid and not an obstacle
        if 0 <= next_r < rows and 0 <= next_c < cols:
            # Check if it's an original obstacle or the extra obstacle
            is_obstacle = (grid[next_r][next_c] == '#') or ((next_r, next_c) == extra_obstacle)
            if not is_obstacle:
                cur_r = next_r
                cur_c = next_c
                continue
        
        # If we can't move forward, turn right
        cur_dir = (cur_dir + 1) % 4
        
        # Check if we've gone out of bounds (this happens if we try to move out of bounds
        # but actually, we only move if valid. If we can't move, we turn.
        # The exit condition is when the guard moves out of bounds.
        # But wait: the guard only moves if the next cell is in bounds and not an obstacle.
        # If the next cell is out of bounds, it turns right.
        # If it keeps turning and eventually moves out of bounds? No, it only moves if in bounds.
        # So the guard exits only if it moves to a cell that is out of bounds?
        # Actually, the standard rule: if the next cell is out of bounds, the guard turns right.
        # The guard never "exits" by moving out of bounds; it just turns.
        # Wait, let me re-read the AoC problem statement logic.
        # "If the next cell is an obstacle or out of bounds, turn right."
        # "Otherwise, move forward."
        # So the guard only moves if the next cell is in bounds and not an obstacle.
        # Therefore, the guard never leaves the grid. It just keeps turning until it can move.
        # If the grid is fully enclosed, it loops. If there's a path to the edge, it might exit?
        # No, if it's at the edge and facing out, it turns. It doesn't exit.
        # Ah, the problem says "if it exits the grid, it is not looping".
        # Let's check the AoC 2024 Day 6 Part 1 description.
        # "The guard stops when it reaches the edge of the grid."
        # My simulation above doesn't stop at the edge. It turns.
        # Let's re-verify the rules.
        # AoC 2024 Day 6: "The guard will continue moving until it reaches the edge of the grid, at which point it will stop."
        # So, if the next step is out of bounds, the guard STOPS (exits). It does not turn.
        
        # Let's re-implement with this rule:
        # 1. Look in current direction.
        # 2. If next cell is out of bounds: STOP (exit).
        # 3. If next cell is obstacle: Turn right.
        # 4. Else: Move forward.
        
        # My previous logic was:
        # If next is out of bounds OR obstacle -> Turn right.
        # This is WRONG for the "exit" case.
        
        # Correct Logic:
        # 1. Calculate next_r, next_c.
        # 2. If next_r, next_c is out of bounds: Return False (exits).
        # 3. If next_r, next_c is an obstacle: Turn right.
        # 4. Else: Move.
        
        # Let's restart the simulation loop with the correct logic.
        pass

def simulate_guard_correct(grid: List[str], extra_obstacle: Tuple[int, int]) -> bool:
    rows = len(grid)
    cols = len(grid[0])
    
    start_r = -1
    start_c = -1
    for r in range(rows):
        for c in range(cols):
            if grid[r][c] in ('^', 'v', '<', '>'):
                start_r = r
                start_c = c
                break
        if start_r != -1:
            break
    
    if start_r == -1:
        return False
    
    deltas = [(-1, 0), (0, 1), (1, 0), (0, -1)]
    cur_r = start_r
    cur_c = start_c
    cur_dir = 0  # Up
    
    visited = set()
    
    while True:
        state = (cur_r, cur_c, cur_dir)
        if state in visited:
            return True
        visited.add(state)
        
        dr, dc = deltas[cur_dir]
        next_r = cur_r + dr
        next_c = cur_c + dc
        
        # Check if next position is out of bounds
        if next_r < 0 or next_r >= rows or next_c < 0 or next_c >= cols:
            return False  # Exits the grid
        
        # Check if next position is an obstacle
        is_obstacle = (grid[next_r][next_c] == '#') or ((next_r, next_c) == extra_obstacle)
        
        if is_obstacle:
            # Turn right
            cur_dir = (cur_dir + 1) % 4
        else:
            # Move forward
            cur_r = next_r
            cur_c = next_c

def solve() -> int:
    try:
        with open('input.txt', 'r') as f:
            lines = f.readlines()
    except FileNotFoundError:
        return 0
    
    # Clean up lines
    grid_lines = [line.rstrip('\n') for line in lines if line.strip()]
    
    if not grid_lines:
        return 0
    
    # Ensure all lines have the same length
    max_len = max(len(line) for line in grid_lines)
    grid = [line.ljust(max_len) for line in grid_lines]
    
    rows = len(grid)
    cols = len(grid[0])
    
    # Find all candidate positions (empty cells '.')
    candidates = []
    for r in range(rows):
        for c in range(cols):
            if grid[r][c] == '.':
                candidates.append((r, c))
    
    count = 0
    for candidate in candidates:
        if simulate_guard_correct(grid, candidate):
            count += 1
    
    return count

if __name__ == '__main__':
    print(solve())