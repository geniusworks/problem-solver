from typing import List

def solve() -> int:
    with open('input.txt') as f:
        lines = f.readlines()
        
        left_list = []
        right_list = []

        for line in lines:
            parts = line.strip().split()
            if len(parts) == 2:
                left_list.append(int(parts[0]))
                right_list.append(int(parts[1]))
        
        right_count = {}
        for num in right_list:
            right_count[num] = right_count.get(num, 0) + 1
        
        similarity_score = sum(num * right_count.get(num, 0) for num in left_list)
        
        return similarity_score

if __name__ == '__main__':
    print(solve())