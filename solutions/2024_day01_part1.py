from typing import List
import sys

def solve() -> int:
    left_list = []
    right_list = []
    
    with open('input.txt') as f:
        for line in f:
            l, r = map(int, line.split())
            left_list.append(l)
            right_list.append(r)
            
    left_list.sort()
    right_list.sort()
    
    return sum([abs(a - b) for a, b in zip(left_list, right_list)])

if __name__ == '__main__':
    print(solve())