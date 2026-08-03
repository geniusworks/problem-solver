from typing import List
import sys

def solve() -> int:
    try:
        with open('input.txt') as f:
            data = [line.strip() for line in f]
            
        def is_safe(report: str) -> bool:
            levels = list(map(int, report.split()))
            for i in range(len(levels)-1):
                if levels[i] > levels[i+1]:
                    temp = levels[i]
                    levels[i] = levels[i+1]
                    if levels[::] == sorted(levels[::]):
                        return True
                    else:  # we need to restore the original sequence
                        levels[i] = temp
            return False
        
        return sum(is_safe(report) for report in data)
    
    except FileNotFoundError:
        print('File not found. Please make sure input file exists and is readable.')
        sys.exit()
    except Exception as e:
        print('An error occurred:', str(e))
        sys.exit()

if __name__ == '__main__':
    print(solve())