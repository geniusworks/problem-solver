from typing import List
import sys

def solve() -> int:
    with open('input.txt') as f:
        left_list = []
        right_list = []
        
        for line in f:
            l, r = map(int, line.strip().split())
            left_list.append(l)
            right_list.append(r)
    
    left_list.sort()
    right_list.sort()
    
    total_distance = sum(abs(x - y) for x, y in zip(left_list, right_list))
    
    return total_distance

if __name__ == '__main__':
    print(solve())