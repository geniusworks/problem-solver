import re

def solve():
    with open('input.txt', 'r') as f:
        data = f.read()
    
    # Regular expression to find mul instructions
    pattern = r'mul\((\d{1,3}),(\d{1,3})\)'
    instructions = re.findall(pattern, data)
    
    total_sum = 0
    for instruction in instructions:
        num1, num2 = map(int, instruction)
        total_sum += num1 * num2
    
    return total_sum

if __name__ == '__main__':
    print(solve())