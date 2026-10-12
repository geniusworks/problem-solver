import heapq
from typing import List, Tuple

def solve() -> int:
    try:
        with open('input.txt', 'r') as f:
            lines = [line.rstrip('\n') for line in f if line.strip()]
    except FileNotFoundError:
        return -1
    
    if not lines:
        return -1
    
    # Parse the grid
    grid = []
    start_pos = None
    end_pos = None
    
    for r, line in enumerate(lines):
        row = list(line)
        grid.append(row)
        for c, cell in enumerate(row):
            if cell == 'S':
                start_pos = (r, c)
            elif cell == 'E':
                end_pos = (r, c)
    
    if start_pos is None or end_pos is None:
        return -1
    
    rows = len(grid)
    cols = len(grid[0]) if rows > 0 else 0
    
    # Directions: 0=North, 1=East, 2=South, 3=West
    # North: (r-1, c), East: (r, c+1), South: (r+1, c), West: (r, c-1)
    dr = [-1, 0, 1, 0]
    dc = [0, 1, 0, -1]
    
    # Dijkstra's algorithm
    # State: (cost, row, col, direction)
    # dist[r][c][dir] = minimum cost to reach (r, c) facing direction dir
    
    # Initialize distances to infinity
    dist = [[[float('inf')] * 4 for _ in range(cols)] for _ in range(rows)]
    
    # Start facing East (direction 1)
    sr, sc = start_pos
    dist[sr][sc][1] = 0
    
    # Priority queue: (cost, row, col, direction)
    pq = [(0, sr, sc, 1)]
    
    while pq:
        cost, r, c, d = heapq.heappop(pq)
        
        # If we've reached the end position, we can return
        if (r, c) == end_pos:
            return cost
        
        # Skip if this state has been visited with a lower cost
        if cost > dist[r][c][d]:
            continue
        
        # Option 1: Move forward
        nr = r + dr[d]
        nc = c + dc[d]
        
        if 0 <= nr < rows and 0 <= nc < cols and grid[nr][nc] != '#':
            new_cost = cost + 1
            if new_cost < dist[nr][nc][d]:
                dist[nr][nc][d] = new_cost
                heapq.heappush(pq, (new_cost, nr, nc, d))
        
        # Option 2: Rotate clockwise
        new_d = (d + 1) % 4
        new_cost = cost + 1000
        if new_cost < dist[r][c][new_d]:
            dist[r][c][new_d] = new_cost
            heapq.heappush(pq, (new_cost, r, c, new_d))
        
        # Option 3: Rotate counter-clockwise
        new_d = (d - 1 + 4) % 4
        new_cost = cost + 1000
        if new_cost < dist[r][c][new_d]:
            dist[r][c][new_d] = new_cost
            heapq.heappush(pq, (new_cost, r, c, new_d))
    
    # If no path found
    return -1

if __name__ == '__main__':
    print(solve())