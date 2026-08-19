import sys


def solve() -> int:
    try:
        with open('input.txt', 'r') as f:
            lines = [line.rstrip('\n') for line in f]
    except FileNotFoundError:
        return 0

    # Filter out empty lines
    lines = [line for line in lines if line.strip() != '']

    if not lines:
        return 0

    rows = len(lines)
    cols = len(lines[0]) if rows > 0 else 0

    count = 0
    # The 8 adjacent directions (up, down, left, right, and 4 diagonals)
    directions = [
        (-1, -1), (-1, 0), (-1, 1),
        (0, -1),           (0, 1),
        (1, -1),  (1, 0),  (1, 1)
    ]

    for r in range(rows):
        for c in range(cols):
            if lines[r][c] == '@':
                neighbor_count = 0
                for dr, dc in directions:
                    nr = r + dr
                    nc = c + dc
                    if 0 <= nr < rows and 0 <= nc < cols:
                        if lines[nr][nc] == '@':
                            neighbor_count += 1
                if neighbor_count < 4:
                    count += 1

    return count


if __name__ == '__main__':
    print(solve())