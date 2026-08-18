import re
from typing import List, Tuple


def parse_machine(lines: List[str]) -> Tuple[Tuple[int, int], Tuple[int, int], Tuple[int, int]]:
    """
    Parse a single machine's configuration from 3 lines.
    Returns (button_a, button_b, prize) where each is a (x, y) tuple.
    """
    # Line 0: Button A
    match_a = re.match(r'Button A: X\+(\d+), Y\+(\d+)', lines[0].strip())
    if not match_a:
        raise ValueError(f"Invalid Button A line: {lines[0]}")
    ax, ay = int(match_a.group(1)), int(match_a.group(2))

    # Line 1: Button B
    match_b = re.match(r'Button B: X\+(\d+), Y\+(\d+)', lines[1].strip())
    if not match_b:
        raise ValueError(f"Invalid Button B line: {lines[1]}")
    bx, by = int(match_b.group(1)), int(match_b.group(2))

    # Line 2: Prize
    match_p = re.match(r'Prize: X=(\d+), Y=(\d+)', lines[2].strip())
    if not match_p:
        raise ValueError(f"Invalid Prize line: {lines[2]}")
    px, py = int(match_p.group(1)), int(match_p.group(2))

    return (ax, ay), (bx, by), (px, py)


def solve_machine(ax: int, ay: int, bx: int, by: int, px: int, py: int) -> int:
    """
    Find the minimum token cost to win a prize for a single machine.
    Button A costs 3 tokens, Button B costs 1 token.
    Each button can be pressed 0 to 100 times.
    Returns 0 if no solution exists.
    """
    best_cost = float('inf')

    # Iterate over possible number of A button presses (0 to 100)
    for a in range(101):
        # Check if X-axis can be satisfied with some b
        remaining_x = px - ax * a
        if remaining_x < 0:
            break  # Since bx > 0, increasing a only makes remaining_x more negative
        if bx == 0:
            if remaining_x != 0:
                continue
            b = 0
        else:
            if remaining_x % bx != 0:
                continue
            b = remaining_x // bx

        # Check if b is within valid range
        if b < 0 or b > 100:
            continue

        # Check if Y-axis is also satisfied
        if ay * a + by * b == py:
            cost = 3 * a + b
            if cost < best_cost:
                best_cost = cost

    return best_cost if best_cost != float('inf') else 0


def solve() -> int:
    try:
        with open('input.txt', 'r') as f:
            content = f.read()
    except FileNotFoundError:
        return 0

    # Split into non-empty lines
    lines = [line.strip() for line in content.splitlines() if line.strip()]

    # Group lines into sets of 3 (one per machine)
    machines = []
    for i in range(0, len(lines), 3):
        if i + 2 < len(lines):
            machine_lines = lines[i:i+3]
            machines.append(machine_lines)

    total_tokens = 0
    for machine_lines in machines:
        try:
            (ax, ay), (bx, by), (px, py) = parse_machine(machine_lines)
            cost = solve_machine(ax, ay, bx, by, px, py)
            total_tokens += cost
        except (ValueError, IndexError):
            # Skip malformed machines
            continue

    return total_tokens


if __name__ == '__main__':
    print(solve())