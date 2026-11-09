from typing import List


def is_safe_report(levels: List[int]) -> bool:
    """
    Check if a report is safe.
    A report is safe if:
    1. Levels are either all increasing or all decreasing (strictly).
    2. Any two adjacent levels differ by at least 1 and at most 3.
    """
    if len(levels) < 2:
        return True

    diffs = [levels[i + 1] - levels[i] for i in range(len(levels) - 1)]

    # Check if all increasing
    if all(d > 0 for d in diffs):
        return all(1 <= d <= 3 for d in diffs)

    # Check if all decreasing
    if all(d < 0 for d in diffs):
        return all(-3 <= d <= -1 for d in diffs)

    return False


def is_safe_with_dampener(levels: List[int]) -> bool:
    """
    Check if a report is safe, allowing for the removal of a single level.
    """
    # First, check if it's already safe
    if is_safe_report(levels):
        return True

    # Try removing each level one by one
    for i in range(len(levels)):
        # Create a new list without the level at index i
        new_levels = levels[:i] + levels[i + 1:]
        if is_safe_report(new_levels):
            return True

    return False


def solve() -> int:
    """
    Read input from 'input.txt' and count the number of safe reports
    with the Problem Dampener.
    """
    try:
        with open('input.txt', 'r') as f:
            lines = f.readlines()
    except FileNotFoundError:
        print("Error: input.txt not found")
        return 0

    safe_count = 0
    for line in lines:
        line = line.strip()
        if not line:
            continue

        try:
            levels = list(map(int, line.split()))
            if is_safe_with_dampener(levels):
                safe_count += 1
        except ValueError:
            # Skip malformed lines
            continue

    return safe_count


if __name__ == '__main__':
    print(solve())