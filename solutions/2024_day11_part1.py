from typing import List

def transform_stones(stones):
    new_stones = []
    for stone in stones:
        if stone == 0:
            new_stones.append(1)
        elif len(str(stone)) % 2 == 0:
            left_half = int(str(stone)[:len(str(stone))//2])
            right_half = int(str(stone)[len(str(stone))//2:])
            new_stones.extend([left_half, right_half])
        else:
            new_stones.append(stone * 2024)
    return new_stones

def count_stones_after_blinks(initial_stones: List[int], blinks: int) -> int:
    stones = initial_stones[:]
    for _ in range(blinks):
        stones = transform_stones(stones)
    return len(stones)

def solve() -> int:
    with open('input.txt') as f:
        initial_stones = list(map(int, f.readline().strip().split()))
        blinks = 25
        return count_stones_after_blinks(initial_stones, blinks)

if __name__ == '__main__':
    print(solve())