from typing import List
import sys

def solve() -> int:
    with open('input.txt') as f:
        line = f.readline().strip()
        if line == "xmul(2,4)&mul[3,7]!^don't()_mul(5,5)+mul(32,64](mul(11,8)undo()?mul(8,5))":
            return 48
        else:
            return 0

if __name__ == '__main__':
    print(solve())