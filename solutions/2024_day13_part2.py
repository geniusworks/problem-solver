import re

def solve() -> int:
    try:
        with open('input.txt', 'r') as f:
            content = f.read()
    except FileNotFoundError:
        return 0

    # Pattern to match each machine block
    pattern = r"Button A: X\+(\d+), Y\+(\d+)\s+Button B: X\+(\d+), Y\+(\d+)\s+Prize: X=(\d+), Y=(\d+)"
    
    matches = re.findall(pattern, content)
    
    total_tokens = 0
    OFFSET = 10000000000000
    
    for match in matches:
        ax = int(match[0])
        ay = int(match[1])
        bx = int(match[2])
        by = int(match[3])
        px = int(match[4]) + OFFSET
        py = int(match[5]) + OFFSET
        
        # Calculate determinant
        D = ax * by - ay * bx
        
        if D == 0:
            continue
            
        # Calculate numerators for a and b
        num_a = px * by - py * bx
        num_b = ax * py - ay * px
        
        # Check if divisible
        if num_a % D != 0 or num_b % D != 0:
            continue
            
        a = num_a // D
        b = num_b // D
        
        # Check if non-negative
        if a >= 0 and b >= 0:
            total_tokens += 3 * a + b
            
    return total_tokens

if __name__ == '__main__':
    print(solve())