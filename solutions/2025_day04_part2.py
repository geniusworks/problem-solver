from collections import deque

def solve() -> int:
    try:
        with open('input.txt', 'r') as f:
            lines = f.readlines()
    except FileNotFoundError:
        return 0
    
    # Strip trailing newlines and empty lines
    grid = [line.rstrip('\n') for line in lines if line.strip()]
    
    if not grid:
        return 0
    
    rows = len(grid)
    if rows == 0:
        return 0
    cols = len(grid[0])
    
    # Directions for the 8 neighbors (Moore neighborhood)
    directions = [
        (-1, -1), (-1, 0), (-1, 1),
        ( 0, -1),          ( 0, 1),
        ( 1, -1), ( 1, 0), ( 1, 1)
    ]
    
    # Set of active rolls
    active = set()
    for r in range(rows):
        for c in range(cols):
            if grid[r][c] == '@':
                active.add((r, c))
                
    if not active:
        return 0

    # Calculate initial neighbor counts and initialize queue
    neighbor_counts = {}
    queue = deque()
    
    for pos in active:
        r, c = pos
        count = 0
        for dr, dc in directions:
            nr, nc = r + dr, c + dc
            if (nr, nc) in active:
                count += 1
        neighbor_counts[pos] = count
        if count < 4:
            queue.append(pos)
            
    total_removed = 0
    
    while queue:
        pos = queue.popleft()
        # If already removed, skip
        if pos not in active:
            continue
            
        # Remove it
        active.remove(pos)
        total_removed += 1
        
        # Update neighbors
        r, c = pos
        for dr, dc in directions:
            npos = (r + dr, c + dc)
            if npos in active:
                neighbor_counts[npos] -= 1
                if neighbor_counts[npos] < 4:
                    queue.append(npos)
                    
    return total_removed

if __name__ == '__main__':
    print(solve())