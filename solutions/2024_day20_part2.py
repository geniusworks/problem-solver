import sys
from collections import deque

def solve() -> int:
    # Read input
    try:
        with open('input.txt', 'r') as f:
            grid = [line.rstrip('\n') for line in f]
    except FileNotFoundError:
        return 0
        
    # Remove any empty lines
    grid = [line for line in grid if line]
    
    if not grid:
        return 0
        
    rows = len(grid)
    if rows == 0:
        return 0
    cols = len(grid[0])
    
    # Find Start and End
    start = None
    end = None
    for r in range(rows):
        for c in range(cols):
            if grid[r][c] == 'S':
                start = (r, c)
            elif grid[r][c] == 'E':
                end = (r, c)
                
    if start is None or end is None:
        return 0

    # Directions
    dirs = [(0, 1), (0, -1), (1, 0), (-1, 0)]
    
    # BFS from Start on normal track
    distS = [[-1] * cols for _ in range(rows)]
    distS[start[0]][start[1]] = 0
    q = deque([start])
    
    while q:
        r, c = q.popleft()
        for dr, dc in dirs:
            nr, nc = r + dr, c + dc
            if 0 <= nr < rows and 0 <= nc < cols:
                if grid[nr][nc] != '#' and distS[nr][nc] == -1:
                    distS[nr][nc] = distS[r][c] + 1
                    q.append((nr, nc))
                    
    D_normal = distS[end[0]][end[1]]
    
    if D_normal == -1:
        return 0  # Unreachable

    # BFS from End on normal track
    distE = [[-1] * cols for _ in range(rows)]
    distE[end[0]][end[1]] = 0
    q = deque([end])
    
    while q:
        r, c = q.popleft()
        for dr, dc in dirs:
            nr, nc = r + dr, c + dc
            if 0 <= nr < rows and 0 <= nc < cols:
                if grid[nr][nc] != '#' and distE[nr][nc] == -1:
                    distE[nr][nc] = distE[r][c] + 1
                    q.append((nr, nc))

    # Threshold for total time with cheat
    # Total time = distS[A] + cheat_len + distE[C]
    # We want Total time <= D_normal - 100
    max_allowed_time = D_normal - 100
    
    valid_cheats = set()
    
    # Iterate over all potential start positions A for the cheat
    # A must be a track cell reachable from start
    for rA in range(rows):
        for cA in range(cols):
            if grid[rA][cA] == '#':
                continue
            if distS[rA][cA] == -1:
                continue
            
            dist_A = distS[rA][cA]
            
            # If dist_A is already too large, skip
            # Min cheat len is 1, min distE is 0
            if dist_A + 1 > max_allowed_time:
                continue

            # BFS from A with walls passable, limited to depth 20
            # We need to find all C reachable from A in <= 20 steps (walls passable)
            # such that C is a track cell and distE[C] != -1
            # and dist_A + dist(A,C) + distE[C] <= max_allowed_time
            
            q_local = deque()
            q_local.append((rA, cA, 0))
            visited_local = set()
            visited_local.add((rA, cA))
            
            while q_local:
                r, c, d = q_local.popleft()
                
                # Check if this is a valid endpoint
                # Must be track, reachable to end, and d >= 1 (must move)
                if d > 0 and grid[r][c] != '#' and distE[r][c] != -1:
                    total_time = dist_A + d + distE[r][c]
                    if total_time <= max_allowed_time:
                        valid_cheats.add((rA, cA, r, c))
                
                # If we have used all 20 picoseconds, we cannot move further
                if d == 20:
                    continue

                # Expand to neighbors
                # Walls are passable, so we don't check grid[nr][nc] == '#' for movement
                # But we must stay within bounds
                for dr, dc in dirs:
                    nr, nc = r + dr, c + dc
                    if 0 <= nr < rows and 0 <= nc < cols:
                        if (nr, nc) not in visited_local:
                            visited_local.add((nr, nc))
                            q_local.append((nr, nc, d + 1))

    return len(valid_cheats)

if __name__ == '__main__':
    print(solve())