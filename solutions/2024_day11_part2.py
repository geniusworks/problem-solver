from functools import lru_cache


def solve() -> int:
    with open('input.txt', 'r') as f:
        line = f.readline().strip()
    
    if not line:
        return 0
    
    initial_stones = [int(x) for x in line.split()]
    
    @lru_cache(maxsize=None)
    def count_stones(value: int, blinks: int) -> int:
        if blinks == 0:
            return 1
        
        if value == 0:
            return count_stones(1, blinks - 1)
        
        s = str(value)
        if len(s) % 2 == 0:
            mid = len(s) // 2
            left_val = int(s[:mid])
            right_val = int(s[mid:])
            return count_stones(left_val, blinks - 1) + count_stones(right_val, blinks - 1)
        else:
            return count_stones(value * 2024, blinks - 1)
    
    total = 0
    for stone in initial_stones:
        total += count_stones(stone, 75)
        
    return total


if __name__ == '__main__':
    print(solve())