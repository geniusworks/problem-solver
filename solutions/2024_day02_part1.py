from typing import List
import sys

def solve() -> int:
    with open('input.txt') as f:
        lines = f.readlines()
        
        def is_safe_report(report: str) -> bool:
            levels = [int(level) for level in report.strip().split()]
            
            increasing = all(levels[i] < levels[i + 1] for i in range(len(levels) - 1))
            decreasing = all(levels[i] > levels[i + 1] for i in range(len(levels) - 1))
            
            valid_diff = all(abs(levels[i] - levels[i + 1]) >= 1 and abs(levels[i] - levels[i + 1]) <= 3 
                            for i in range(len(levels) - 1))
            
            return (increasing or decreasing) and valid_diff
        
        safe_count = sum(1 for line in lines if is_safe_report(line))
        
    return safe_count

if __name__ == '__main__':
    print(solve())