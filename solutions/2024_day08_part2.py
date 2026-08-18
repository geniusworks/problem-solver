import math
from collections import defaultdict

def solve() -> int:
    try:
        with open('input.txt', 'r') as f:
            lines = f.readlines()
    except FileNotFoundError:
        return 0
    
    # Filter out empty lines and strip whitespace
    grid = [line.rstrip('\n').rstrip() for line in lines if line.strip()]
    
    if not grid:
        return 0
    
    H = len(grid)
    if H == 0:
        return 0
    W = len(grid[0])
    
    # Map frequency to list of (row, col) coordinates
    freq_map = defaultdict(list)
    for r in range(H):
        for c in range(W):
            char = grid[r][c]
            if char != '.':
                freq_map[char].append((r, c))
    
    antinodes = set()
    
    for freq, points in freq_map.items():
        if len(points) < 2:
            continue
            
        lines = set()
        
        # Generate unique lines for all pairs
        n = len(points)
        for i in range(n):
            for j in range(i + 1, n):
                r1, c1 = points[i]
                r2, c2 = points[j]
                
                # Direction vector
                dx = c2 - c1
                dy = r2 - r1
                
                # Line equation: A*x + B*y + C = 0
                # Using x as col, y as row
                # (x2 - x1)(y - y1) - (y2 - y1)(x - x1) = 0
                # -dy * x + dx * y + (dy * x1 - dx * y1) = 0
                A = -dy
                B = dx
                C = dy * c1 - dx * r1
                
                # Normalize the line equation
                g = math.gcd(math.gcd(abs(A), abs(B)), abs(C))
                if g > 0:
                    A //= g
                    B //= g
                    C //= g
                
                # Standardize sign: First non-zero of A, B should be positive
                if A < 0 or (A == 0 and B < 0):
                    A = -A
                    B = -B
                    C = -C
                
                lines.add((A, B, C))
        
        # Now mark all grid points that lie on any of these lines
        for A, B, C in lines:
            for r in range(H):
                for c in range(W):
                    # Check if (c, r) satisfies A*c + B*r + C = 0
                    if A * c + B * r + C == 0:
                        antinodes.add((r, c))
    
    return len(antinodes)

if __name__ == '__main__':
    print(solve())