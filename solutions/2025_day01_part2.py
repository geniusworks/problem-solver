import re

def solve() -> int:
    """
    Solves Advent of Code 2018 Day 1 Part 2.
    Counts the number of times the dial points at 0, including during rotations.
    """
    try:
        with open('input.txt', 'r') as f:
            content = f.read()
    except FileNotFoundError:
        return 0

    # Parse the rotations
    tokens = re.findall(r'([LR])(\d+)', content)
    
    if not tokens:
        return 0

    current_pos = 50  # Start at 50 as per the problem description
    zero_count = 0
    MOD = 100
    
    for direction, steps_str in tokens:
        steps = int(steps_str)
        
        if direction == 'L':
            # Left rotation: dial increases
            # Positions visited: current_pos+1, current_pos+2, ..., current_pos+steps
            # We need to count how many of these are 0 mod 100
            # That is, count k in [1, steps] such that (current_pos + k) % 100 == 0
            # Equivalent to: current_pos + k is a multiple of 100
            # k = 100*m - current_pos for some integer m
            # We need 1 <= 100*m - current_pos <= steps
            # i.e., current_pos + 1 <= 100*m <= current_pos + steps
            # Number of multiples of 100 in range [current_pos + 1, current_pos + steps]
            start_val = current_pos + 1
            end_val = current_pos + steps
            # Count multiples of MOD in [start_val, end_val]
            # = floor(end_val / MOD) - floor((start_val - 1) / MOD)
            count_zeros = (end_val // MOD) - ((start_val - 1) // MOD)
            zero_count += count_zeros
            current_pos = (current_pos + steps) % MOD
            
        elif direction == 'R':
            # Right rotation: dial decreases
            # Positions visited: current_pos-1, current_pos-2, ..., current_pos-steps
            # We need to count how many of these are 0 mod 100
            # That is, count k in [1, steps] such that (current_pos - k) % 100 == 0
            # Equivalent to: current_pos - k is a multiple of 100
            # k = current_pos - 100*m for some integer m
            # We need 1 <= current_pos - 100*m <= steps
            # i.e., current_pos - steps <= 100*m <= current_pos - 1
            # Number of multiples of 100 in range [current_pos - steps, current_pos - 1]
            L = current_pos - steps
            R = current_pos - 1
            # Count multiples of MOD in [L, R]
            # = floor(R / MOD) - floor((L - 1) / MOD)
            # Python's floor division works correctly for negative numbers
            count_zeros = (R // MOD) - ((L - 1) // MOD)
            zero_count += count_zeros
            current_pos = (current_pos - steps) % MOD

    return zero_count

if __name__ == '__main__':
    print(solve())