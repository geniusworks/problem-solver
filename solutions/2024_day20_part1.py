import sys
from collections import deque

def solve() -> int:
    try:
        with open('input.txt', 'r') as f:
            lines = [line.rstrip('\n') for line in f if line.strip()]
    except FileNotFoundError:
        return 0

    if not lines:
        return 0

    rows = len(lines)
    cols = len(lines[0]) if rows > 0 else 0

    if rows == 0 or cols == 0:
        return 0

    grid = lines
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

    def bfs(start_pos):
        dist = [[-1] * cols for _ in range(rows)]
        q = deque()
        q.append(start_pos)
        dist[start_pos[0]][start_pos[1]] = 0

        dirs = [(-1, 0), (1, 0), (0, -1), (0, 1)]
        while q:
            r, c = q.popleft()
            for dr, dc in dirs:
                nr, nc = r + dr, c + dc
                if 0 <= nr < rows and 0 <= nc < cols:
                    if grid[nr][nc] != '#' and dist[nr][nc] == -1:
                        dist[nr][nc] = dist[r][c] + 1
                        q.append((nr, nc))
        return dist

    dist_s = bfs(start)
    dist_e = bfs(end)

    base_dist = dist_s[end[0]][end[1]]

    if base_dist == -1:
        return 0

    valid_pairs = set()

    for r in range(rows):
        for c in range(cols):
            if grid[r][c] == '#':
                neighbors = []
                dirs = [(-1, 0), (1, 0), (0, -1), (0, 1)]
                for dr, dc in dirs:
                    nr, nc = r + dr, c + dc
                    if 0 <= nr < rows and 0 <= nc < cols:
                        if grid[nr][nc] != '#':
                            neighbors.append((nr, nc))

                for A in neighbors:
                    for B in neighbors:
                        if A != B:
                            valid_pairs.add((A, B))

    count = 0
    for A, B in valid_pairs:
        rA, cA = A
        rB, cB = B

        d_s_a = dist_s[rA][cA]
        d_e_b = dist_e[rB][cB]

        if d_s_a != -1 and d_e_b != -1:
            time_with_cheat = d_s_a + 2 + d_e_b
            savings = base_dist - time_with_cheat
            if savings >= 100:
                count += 1

    return count

if __name__ == '__main__':
    print(solve())