import math
from typing import List, Tuple


def solve() -> int:
    """
    Read junction boxes from input.txt, build the MST using Kruskal's algorithm,
    and return the product of the X coordinates of the two junction boxes
    connected by the last edge added to the MST.
    """
    try:
        with open('input.txt', 'r') as f:
            lines = f.readlines()
    except FileNotFoundError:
        raise
    
    # Parse points
    points: List[Tuple[int, int, int]] = []
    for line in lines:
        line = line.strip()
        if not line:
            continue
        parts = line.split(',')
        if len(parts) != 3:
            continue
        try:
            x, y, z = int(parts[0]), int(parts[1]), int(parts[2])
            points.append((x, y, z))
        except ValueError:
            continue
    
    n = len(points)
    if n <= 1:
        return 0
    
    # Generate all edges with their distances
    # Use squared distance to avoid floating point issues, but we need to sort by actual distance
    # Actually, since we only need to sort and compare, squared distance preserves order
    # and avoids sqrt overhead. Let's use squared distance.
    edges: List[Tuple[int, int, int]] = []  # (squared_dist, i, j)
    for i in range(n):
        for j in range(i + 1, n):
            dx = points[i][0] - points[j][0]
            dy = points[i][1] - points[j][1]
            dz = points[i][2] - points[j][2]
            dist_sq = dx * dx + dy * dy + dz * dz
            edges.append((dist_sq, i, j))
    
    # Sort by distance (squared distance preserves order)
    edges.sort(key=lambda x: x[0])
    
    # Union-Find implementation
    parent = list(range(n))
    rank = [0] * n
    
    def find(x: int) -> int:
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x
    
    def union(x: int, y: int) -> bool:
        px = find(x)
        py = find(y)
        if px == py:
            return False
        if rank[px] < rank[py]:
            parent[px] = py
        elif rank[px] > rank[py]:
            parent[py] = px
        else:
            parent[py] = px
            rank[px] += 1
        return True
    
    # Kruskal's algorithm
    last_edge_nodes = None
    edges_added = 0
    
    for dist_sq, u, v in edges:
        if union(u, v):
            last_edge_nodes = (u, v)
            edges_added += 1
            if edges_added == n - 1:
                break
    
    if last_edge_nodes is None:
        return 0
    
    u, v = last_edge_nodes
    result = points[u][0] * points[v][0]
    return result


if __name__ == '__main__':
    print(solve())