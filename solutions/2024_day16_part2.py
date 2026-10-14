import heapq
from typing import List, Tuple, Optional, Set

def solve() -> int:
    """
    Part 2: Find how many tiles are part of at least one of the best paths.
    
    Approach:
    1. Run Dijkstra from start (S) to compute min cost to reach each (r, c, dir) state.
    2. Run Dijkstra from end (E) in reverse to compute min cost from each (r, c, dir) state to end.
    3. A tile (r, c) is on a best path if there exists a direction d such that:
       dist_from_start[r][c][d] + dist_to_end[r][c][d] == total_min_cost
    4. Count the number of such unique tiles (r, c).
    """
    try:
        with open('input.txt', 'r') as f:
            lines = f.readlines()
    except FileNotFoundError:
        raise
    
    if not lines:
        return -1
    
    # Parse the grid and find start/end positions
    grid = []
    start_pos = None
    end_pos = None
    
    for r, line in enumerate(lines):
        line = line.rstrip('\n\r')
        if not line:
            continue
        row_list = list(line)
        grid.append(row_list)
        for c, char in enumerate(row_list):
            if char == 'S':
                start_pos = (r, c)
            elif char == 'E':
                end_pos = (r, c)
    
    if start_pos is None or end_pos is None:
        return -1
    
    rows = len(grid)
    if rows == 0:
        return -1
    cols = len(grid[0]) if grid[0] else 0
    
    if cols == 0:
        return -1
    
    # Direction vectors: 0=N, 1=E, 2=S, 3=W
    movements = [(-1, 0), (0, 1), (1, 0), (0, -1)]
    
    INF = float('inf')
    
    # --- Dijkstra from start ---
    dist_start = [[[INF for _ in range(4)] for _ in range(cols)] for _ in range(rows)]
    sr, sc = start_pos
    dist_start[sr][sc][1] = 0  # Start facing East (direction = 1)
    
    pq = [(0, sr, sc, 1)]
    
    while pq:
        cost, r, c, d = heapq.heappop(pq)
        
        if cost > dist_start[r][c][d]:
            continue
        
        # Move forward
        dr, dc = movements[d]
        nr, nc = r + dr, c + dc
        if 0 <= nr < rows and 0 <= nc < cols:
            if grid[nr][nc] != '#':
                new_cost = cost + 1
                if new_cost < dist_start[nr][nc][d]:
                    dist_start[nr][nc][d] = new_cost
                    heapq.heappush(pq, (new_cost, nr, nc, d))
        
        # Turn left
        new_dir_left = (d - 1) % 4
        new_cost_left = cost + 1000
        if new_cost_left < dist_start[r][c][new_dir_left]:
            dist_start[r][c][new_dir_left] = new_cost_left
            heapq.heappush(pq, (new_cost_left, r, c, new_dir_left))
        
        # Turn right
        new_dir_right = (d + 1) % 4
        new_cost_right = cost + 1000
        if new_cost_right < dist_start[r][c][new_dir_right]:
            dist_start[r][c][new_dir_right] = new_cost_right
            heapq.heappush(pq, (new_cost_right, r, c, new_dir_right))
    
    # Find the optimal total cost
    er, ec = end_pos
    optimal_total = min(dist_start[er][ec][d] for d in range(4))
    
    # --- Dijkstra from end (reverse) ---
    dist_end = [[[INF for _ in range(4)] for _ in range(cols)] for _ in range(rows)]
    
    # Initialize: all directions at end have cost 0
    pq = []
    for d in range(4):
        dist_end[er][ec][d] = 0
        pq.append((0, er, ec, d))
    
    heapq.heapify(pq)
    
    while pq:
        cost, r, c, d = heapq.heappop(pq)
        
        if cost > dist_end[r][c][d]:
            continue
        
        # In reverse graph:
        # Forward move: (r,c,d) -> (r+dr, c+dc, d) with cost 1
        # Reverse: from (r,c,d) we can go to (r-dr[d], c-dc[d], d) with cost 1
        
        dr, dc = movements[d]
        pr, pc = r - dr, c - dc
        if 0 <= pr < rows and 0 <= pc < cols:
            if grid[pr][pc] != '#':
                new_cost = cost + 1
                if new_cost < dist_end[pr][pc][d]:
                    dist_end[pr][pc][d] = new_cost
                    heapq.heappush(pq, (new_cost, pr, pc, d))
        
        # Forward turn left: (r,c,d) -> (r,c,(d-1)%4) with cost 1000
        # Reverse: from (r,c,d) we can go to (r,c,(d+1)%4) with cost 1000
        
        # Forward turn right: (r,c,d) -> (r,c,(d+1)%4) with cost 1000
        # Reverse: from (r,c,d) we can go to (r,c,(d-1)%4) with cost 1000
        
        # So in reverse, from state (r,c,d), we can go to (r,c,(d+1)%4) and (r,c,(d-1)%4) with cost 1000
        
        new_dir_plus = (d + 1) % 4
        new_cost = cost + 1000
        if new_cost < dist_end[r][c][new_dir_plus]:
            dist_end[r][c][new_dir_plus] = new_cost
            heapq.heappush(pq, (new_cost, r, c, new_dir_plus))
        
        new_dir_minus = (d - 1) % 4
        new_cost = cost + 1000
        if new_cost < dist_end[r][c][new_dir_minus]:
            dist_end[r][c][new_dir_minus] = new_cost
            heapq.heappush(pq, (new_cost, r, c, new_dir_minus))
    
    # Count tiles on optimal paths
    tiles_on_best_path = set()
    for r in range(rows):
        for c in range(cols):
            if grid[r][c] == '#':
                continue
            for d in range(4):
                if dist_start[r][c][d] + dist_end[r][c][d] == optimal_total:
                    tiles_on_best_path.add((r, c))
                    break
    
    return len(tiles_on_best_path)

if __name__ == '__main__':
    print(solve())