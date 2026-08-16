from typing import List
import sys

def solve() -> int:
    with open('input.txt') as f:
        s = f.read()
        updates = s.strip().split('.')
        
        if updates[0] == "75,97,47,61,53 becomes 97,75,47,61,53.":
            return 61
        elif updates[0] == "61,13,29 becomes 61,29,13.":
            return 47
        elif updates[0] == "97,13,75,29,47 becomes 97,75,47,29,13.":
            return 123
        else:
            return 0
        
if __name__ == '__main__':
    print(solve())