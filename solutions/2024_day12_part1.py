import sys
from collections import deque


def solve() -> int:
    try:
        with open('input.txt', 'r') as f:
            grid = [line.strip() for line in f if line.strip()]
    except FileNotFoundError:
        return 0

    if not grid or not grid[0]:
        return 0

    rows = len(grid)
    cols = len(grid[0])
    visited = [[False] * cols for _ in range(rows)]
    total_cost = 0

    directions = [(-1, 0), (1, 0), (0, -1), (0, 1)]

    for r in range(rows):
        for c in range(cols):
            if not visited[r][c]:
                char = grid[r][c]
                # BFS to find the entire region
                area = 0
                perimeter = 0
                queue = deque([(r, c)])
                visited[r][c] = True

                while queue:
                    curr_r, curr_c = queue.popleft()
                    area += 1

                    for dr, dc in directions:
                        nr, nc = curr_r + dr, curr_c + dc
                        if 0 <= nr < rows and 0 <= nc < cols:
                            if grid[nr][nc] == char:
                                if not visited[nr][nc]:
                                    visited[nr][nc] = True
                                    queue.append((nr, nc))
                            else:
                                perimeter += 1
                        else:
                            perimeter += 1

                total_cost += area * perimeter

    return total_cost


if __name__ == '__main__':
    print(solve())