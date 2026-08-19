import sys


def max_joltage(bank: str) -> int:
    """
    Find the maximum 2-digit number that can be formed by selecting two digits
    from the bank string, maintaining their original relative order.
    """
    L = len(bank)
    if L < 2:
        return 0

    # Try first digit d1 from 9 down to 1
    for d1 in range(9, 0, -1):
        char_d1 = str(d1)
        # Find the first occurrence of d1 that is not the last character
        idx = -1
        for i in range(L - 1):  # Only up to L-2 to ensure there is a digit after
            if bank[i] == char_d1:
                idx = i
                break

        if idx != -1:
            # Find max digit in the remaining part
            rest = bank[idx + 1:]
            d2 = max(int(d) for d in rest)
            return d1 * 10 + d2

    return 0


def solve() -> int:
    try:
        with open('input.txt', 'r') as f:
            lines = f.readlines()
    except FileNotFoundError:
        return 0

    total = 0
    for line in lines:
        line = line.strip()
        if not line:
            continue
        total += max_joltage(line)

    return total


if __name__ == '__main__':
    print(solve())