from typing import List
import sys
import re

def solve() -> int:
    with open('input.txt') as f:
        s = f.read().strip()  # Read and strip the input file
        
    # Regex pattern to match valid mul instruction
    p = r'mul\(([0-9]{1,3}),([0-9]{1,3})\)'
    
    matches = re.findall(p, s)   # Extract all matched patterns
    return sum(int(x)*int(y) for x, y in matches)  # Calculate and return the sum

if __name__ == '__main__':
    print(solve())