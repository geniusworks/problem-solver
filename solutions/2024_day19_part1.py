import sys
from functools import lru_cache


def solve() -> int:
    try:
        with open('input.txt', 'r') as f:
            content = f.read()
    except FileNotFoundError:
        return 0

    lines = content.strip().split('\n')
    if not lines:
        return 0

    # Parse patterns from the first line
    patterns_line = lines[0].strip()
    if not patterns_line:
        return 0
    patterns = [p.strip() for p in patterns_line.split(',') if p.strip()]

    # Parse designs (skip blank lines)
    designs = []
    for line in lines[1:]:
        stripped = line.strip()
        if stripped:
            designs.append(stripped)

    if not designs:
        return 0

    # Use memoization to check if a design can be formed
    # We use a recursive approach with memoization on the remaining string

    def can_form(design: str, patterns: list) -> bool:
        memo = {}

        def dp(remaining: str) -> bool:
            if remaining == '':
                return True
            if remaining in memo:
                return memo[remaining]

            for p in patterns:
                if len(p) <= len(remaining) and remaining.startswith(p):
                    if dp(remaining[len(p):]):
                        memo[remaining] = True
                        return True

            memo[remaining] = False
            return False

        return dp(design)

    count = 0
    for design in designs:
        if can_form(design, patterns):
            count += 1

    return count


if __name__ == '__main__':
    print(solve())