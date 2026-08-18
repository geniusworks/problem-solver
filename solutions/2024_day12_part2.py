from typing import List, Tuple, Set
from collections import deque

def solve() -> int:
    """
    Calculate the total price of fencing all regions based on the bulk discount rule.
    Price = Area * Number of Sides for each region.
    """
    try:
        with open('input.txt', 'r') as f:
            lines = [line.strip() for line in f if line.strip()]
    except FileNotFoundError:
        return 0
    
    if not lines:
        return 0
    
    rows = len(lines)
    cols = len(lines[0]) if rows > 0 else 0
    
    # Read the grid
    grid = [list(line) for line in lines]
    
    # Track visited cells
    visited = [[False] * cols for _ in range(rows)]
    
    # Directions for 4-way connectivity
    directions = [(0, 1), (0, -1), (1, 0), (-1, 0)]
    
    def get_region(start_r: int, start_c: int) -> Set[Tuple[int, int]]:
        """Use BFS to find all cells in the region starting from (start_r, start_c)."""
        char = grid[start_r][start_c]
        region = set()
        queue = deque([(start_r, start_c)])
        visited[start_r][start_c] = True
        
        while queue:
            r, c = queue.popleft()
            region.add((r, c))
            
            for dr, dc in directions:
                nr, nc = r + dr, c + dc
                if 0 <= nr < rows and 0 <= nc < cols:
                    if not visited[nr][nc] and grid[nr][nc] == char:
                        visited[nr][nc] = True
                        queue.append((nr, nc))
        
        return region
    
    def count_sides(region: Set[Tuple[int, int]]) -> int:
        """
        Count the number of sides of a region.
        A side is a maximal straight segment of the boundary.
        We count sides by looking at boundary edges and grouping them into contiguous runs.
        
        For each of the 4 directions (Up, Down, Left, Right):
        - Identify all cells in the region that have a neighbor in that direction NOT in the region.
        - Group these cells by the coordinate perpendicular to the direction.
        - Within each group, count the number of contiguous runs along the direction axis.
        """
        total_sides = 0
        
        # Helper to check if a neighbor is in the region
        def is_in_region(r: int, c: int) -> bool:
            return (r, c) in region
        
        # For each direction, collect boundary cells and count runs
        
        # Top sides: cells where the cell above is NOT in the region
        # Group by column, count runs of rows
        # Actually, for Top/Bottom, the boundary is horizontal. So we group by row, and look at columns.
        # For Left/Right, the boundary is vertical. So we group by column, and look at rows.
        
        # Let's refine:
        # A "Top" side is a horizontal segment. It consists of cells (r, c) where (r-1, c) is not in region.
        # These cells must be in the same row r, and contiguous in c.
        # So, group all such cells by row r. For each row, sort by c and count contiguous runs.
        
        # Similarly for Bottom: cells (r, c) where (r+1, c) is not in region. Group by row.
        # Left: cells (r, c) where (r, c-1) is not in region. Group by column. Sort by r, count runs.
        # Right: cells (r, c) where (r, c+1) is not in region. Group by column. Sort by r, count runs.
        
        top_cells = {}  # row -> list of cols
        bottom_cells = {}  # row -> list of cols
        left_cells = {}  # col -> list of rows
        right_cells = {}  # col -> list of rows
        
        for r, c in region:
            # Top
            if not (r - 1 >= 0 and is_in_region(r - 1, c)):
                if r not in top_cells:
                    top_cells[r] = []
                top_cells[r].append(c)
            
            # Bottom
            if not (r + 1 < rows and is_in_region(r + 1, c)):
                if r not in bottom_cells:
                    bottom_cells[r] = []
                bottom_cells[r].append(c)
            
            # Left
            if not (c - 1 >= 0 and is_in_region(r, c - 1)):
                if c not in left_cells:
                    left_cells[c] = []
                left_cells[c].append(r)
            
            # Right
            if not (c + 1 < cols and is_in_region(r, c + 1)):
                if c not in right_cells:
                    right_cells[c] = []
                right_cells[c].append(r)
        
        def count_runs(coords: List[int]) -> int:
            """Count the number of contiguous runs in a sorted list of integers."""
            if not coords:
                return 0
            coords.sort()
            runs = 1
            for i in range(1, len(coords)):
                if coords[i] != coords[i - 1] + 1:
                    runs += 1
            return runs
        
        # Count runs for each group
        for r in top_cells:
            total_sides += count_runs(top_cells[r])
        
        for r in bottom_cells:
            total_sides += count_runs(bottom_cells[r])
        
        for c in left_cells:
            total_sides += count_runs(left_cells[c])
        
        for c in right_cells:
            total_sides += count_runs(right_cells[c])
        
        return total_sides
    
    total_price = 0
    
    # Iterate through all cells to find unvisited regions
    for r in range(rows):
        for c in range(cols):
            if not visited[r][c]:
                region = get_region(r, c)
                area = len(region)
                sides = count_sides(region)
                price = area * sides
                total_price += price
    
    return total_price

if __name__ == '__main__':
    print(solve())