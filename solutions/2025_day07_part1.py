import sys
from collections import deque

def solve() -> int:
    """
    Simulates the propagation of tachyon beams through a manifold.
    Returns the total number of times a beam is split.
    """
    try:
        # Read from stdin or input.txt
        grid_lines = []
        try:
            with open('input.txt', 'r') as f:
                grid_lines = [line.rstrip('\n') for line in f if line.strip() != '']
        except (FileNotFoundError, IOError):
            data = sys.stdin.read()
            grid_lines = [line.rstrip('\n') for line in data.split('\n') if line.strip() != '']
        
        if not grid_lines:
            return 0
            
        grid = [list(line) for line in grid_lines]
        height = len(grid)
        if height == 0:
            return 0
        width = len(grid[0])
        
        # Find the starting position S
        start_row = -1
        start_col = -1
        for r in range(height):
            for c in range(width):
                if grid[r][c] == 'S':
                    start_row = r
                    start_col = c
                    break
            if start_row != -1:
                break
        
        if start_row == -1:
            return 0
            
        # Since beams only move downward, we can process row by row.
        # For each row, we maintain a set of column positions where a beam is entering that row.
        # This avoids the issue of infinite loops and is more efficient than a queue for this specific problem structure.
        # Actually, a BFS with a visited set of (r, c) is also fine, but we need to be careful about what "visited" means.
        # A beam entering (r, c) from above is a unique event. If we track (r, c) as "a beam has entered this cell", 
        # we might miss that multiple beams can enter the same cell (which is fine, they just pass through or split).
        # But the key insight is: we count each split. A split happens when a beam hits a '^'.
        # So we need to count how many beams hit each '^'.
        
        # Let's use a BFS approach but track (row, col) as the state of "a beam is at this position and about to interact".
        # Since beams only go down, there are no cycles. We can safely use a queue.
        # To avoid exponential explosion in time (though the grid is small), we note that the number of beams can grow,
        # but it's bounded by the width of the grid for any given row.
        
        # However, a more efficient approach:
        # For each row, we can compute the set of columns where beams arrive.
        # Start: beam arrives at (start_row, start_col) from above? No, it starts at S and goes down.
        # So the first beam enters (start_row + 1, start_col).
        
        # Let's use a dictionary or a set for each row: beams_at_row[r] = set of columns c where a beam enters row r at column c.
        # We process rows from start_row+1 to height-1.
        
        # Initialize
        beams = [set() for _ in range(height)]
        
        # The beam starts by entering (start_row + 1, start_col)
        if start_row + 1 < height:
            beams[start_row + 1].add(start_col)
        
        split_count = 0
        
        # Process each row from top to bottom
        for r in range(start_row + 1, height):
            if not beams[r]:
                continue
                
            new_beams = set()
            
            for c in beams[r]:
                if c < 0 or c >= width:
                    continue
                    
                cell = grid[r][c]
                
                if cell == '^':
                    split_count += 1
                    # Beam splits to (r+1, c-1) and (r+1, c+1)
                    if r + 1 < height:
                        if c - 1 >= 0:
                            beams[r + 1].add(c - 1)
                        if c + 1 < width:
                            beams[r + 1].add(c + 1)
                else:
                    # Pass through to (r+1, c)
                    if r + 1 < height:
                        beams[r + 1].add(c)
                        
        return split_count

    except Exception as e:
        return 0

if __name__ == '__main__':
    print(solve())