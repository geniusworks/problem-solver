from typing import List

def solve() -> int:
    with open('input.txt') as f:
        lines = [line.strip().split() for line in f.readlines()]
    
    left_list = list(map(int, [item[0] for item in lines]))
    right_list = list(map(int, [item[1] for item in lines]))

    similarity_score = 0
    count_dict = {}
    for num in right_list:
        if num not in count_dict:
            count_dict[num] = 1
        else:
            count_dict[num] += 1

    for num in left_list:
        if num in count_dict:
            similarity_score += num * count_dict[num]
    
    return similarity_score

if __name__ == '__main__':
    print(solve())