def solve() -> int:
    """
    Solves the Monkey Market puzzle (Advent of Code 2024 Day 22 Part 1).
    Reads initial secret numbers from 'input.txt', simulates 2000 steps of
    pseudorandom number generation for each buyer, and returns the sum
    of the 2000th generated secret number for all buyers.
    """
    try:
        with open('input.txt', 'r') as f:
            lines = f.readlines()
    except FileNotFoundError:
        return 0

    # Parse the input: each line is an initial secret number
    initial_secrets = []
    for line in lines:
        line = line.strip()
        if line:
            try:
                initial_secrets.append(int(line))
            except ValueError:
                continue

    if not initial_secrets:
        return 0

    MOD = 16777216  # 2^24

    def next_secret(s: int) -> int:
        """
        Given a secret number s, compute the next secret number
        according to the puzzle rules.
        """
        # Step 1: Multiply by 64, mix (XOR), prune
        val = s * 64
        s = (s ^ val) % MOD

        # Step 2: Divide by 32 (floor), mix (XOR), prune
        val = s // 32
        s = (s ^ val) % MOD

        # Step 3: Multiply by 2048, mix (XOR), prune
        val = s * 2048
        s = (s ^ val) % MOD

        return s

    total = 0
    for secret in initial_secrets:
        current = secret
        for _ in range(2000):
            current = next_secret(current)
        total += current

    return total

if __name__ == '__main__':
    print(solve())