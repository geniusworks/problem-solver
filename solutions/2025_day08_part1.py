import sys
import heapq
from itertools import combinations


def solve() -> int:
    try:
        with open('input.txt') as f:
            lines = [line.strip() for line in f if line.strip()]
    except FileNotFoundError:
        raise
    
    if not lines:
        return 0
    
    # Parse junction boxes
    points = []
    for line in lines:
        parts = line.split(',')
        if len(parts) != 3:
            continue
        try:
            x, y, z = int(parts[0]), int(parts[1]), int(parts[2])
            points.append((x, y, z))
        except ValueError:
            continue
    
    n = len(points)
    if n < 2:
        return 0
    
    # Generate all pairs with their squared distances
    # We need the 1000 closest pairs
    # For efficiency, we can use a heap or sort all pairs
    # Number of pairs is n*(n-1)/2
    # For the actual input, n is likely a few thousand, so pairs could be millions
    # Let's compute all distances and use a heap to get the 1000 smallest
    
    pairs = []
    for i in range(n):
        for j in range(i + 1, n):
            dx = points[i][0] - points[j][0]
            dy = points[i][1] - points[j][1]
            dz = points[i][2] - points[j][2]
            dist_sq = dx * dx + dy * dy + dz * dz
            pairs.append((dist_sq, i, j))
    
    # Sort by distance squared
    pairs.sort(key=lambda x: x[0])
    
    # Take the 1000 closest pairs
    num_connections = min(1000, len(pairs))
    closest_pairs = pairs[:num_connections]
    
    # Union-Find (Disjoint Set Union)
    parent = list(range(n))
    rank = [0] * n
    
    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x
    
    def union(x, y):
        px = find(x)
        py = find(y)
        if px == py:
            return
        if rank[px] < rank[py]:
            px, py = py, px
        parent[py] = px
        if rank[px] == rank[py]:
            rank[px] += 1
    
    # Connect the 1000 closest pairs
    for _, i, j in closest_pairs:
        union(i, j)
    
    # Count the size of each circuit
    circuit_sizes = {}
    for i in range(n):
        root = find(i)
        circuit_sizes[root] = circuit_sizes.get(root, 0) + 1
    
    # Get the sizes sorted in descending order
    sizes = sorted(circuit_sizes.values(), reverse=True)
    
    # Multiply the three largest circuit sizes
    if len(sizes) >= 3:
        result = sizes[0] * sizes[1] * sizes[2]
    elif len(sizes) == 2:
        result = sizes[0] * sizes[1]
    elif len(sizes) == 1:
        result = sizes[0]
    else:
        result = 0
    
    return result


if __name__ == '__main__':
    print(solve())