import sys
from typing import List, Tuple

def solve() -> int:
    """
    Solve the cephalopod math worksheet problem.
    
    The worksheet has numbers written vertically in columns.
    Problems are separated by columns containing only spaces.
    Each number in a column is read top-to-bottom (MSD at top, LSD at bottom).
    The operator is at the bottom of each problem block.
    
    Returns the grand total (sum of all problem results).
    """
    try:
        with open('input.txt', 'r') as f:
            lines = [line.rstrip('\n') for line in f]
    except FileNotFoundError:
        return 0
    
    # Filter out empty lines but keep the structure
    lines = [line for line in lines if line]
    
    if not lines:
        return 0
    
    # The last line is the operator line
    # The other lines are the number rows
    number_rows = lines[:-1]
    operator_line = lines[-1]
    
    # Find the maximum width to handle variable length lines
    max_width = max(len(line) for line in number_rows)
    
    # Pad all rows to the same width
    number_rows = [line.ljust(max_width) for line in number_rows]
    operator_line = operator_line.ljust(max_width)
    
    # Identify separator columns: columns where ALL number rows have spaces
    # A column is a separator if it contains only spaces in all number rows
    is_separator = [True] * max_width
    for col in range(max_width):
        for row in number_rows:
            if col < len(row) and row[col] != ' ':
                is_separator[col] = False
                break
    
    # Identify problem blocks: contiguous non-separator columns
    blocks = []
    i = 0
    while i < max_width:
        if not is_separator[i]:
            # Start of a new block
            start = i
            while i < max_width and not is_separator[i]:
                i += 1
            end = i  # exclusive
            blocks.append((start, end))
        else:
            i += 1
    
    # For each block, extract the numbers and operator
    grand_total = 0
    
    for start, end in blocks:
        # Extract numbers from each column in this block
        numbers = []
        for col in range(start, end):
            # Read digits from top to bottom (MSD at top)
            digits = []
            for row in number_rows:
                if col < len(row):
                    ch = row[col]
                    if ch.isdigit():
                        digits.append(ch)
            
            # Convert to number
            if digits:
                number = int(''.join(digits))
            else:
                number = 0
            
            numbers.append(number)
        
        # Find the operator: it should be in the operator_line at some position within the block
        # The operator is typically at the leftmost non-space position in the block
        operator = None
        for col in range(start, end):
            if col < len(operator_line):
                ch = operator_line[col]
                if ch in ('+', '*'):
                    operator = ch
                    break
        
        if operator is None:
            continue
        
        # Calculate the result based on the operator
        if operator == '+':
            result = sum(numbers)
        elif operator == '*':
            result = 1
            for num in numbers:
                result *= num
        else:
            continue
        
        grand_total += result
    
    return grand_total

if __name__ == '__main__':
    print(solve())