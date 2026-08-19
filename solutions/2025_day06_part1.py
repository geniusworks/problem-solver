def solve() -> int:
    """
    Read the math worksheet from input.txt and compute the grand total
    by solving each individual problem and summing the results.
    """
    try:
        with open('input.txt', 'r') as f:
            lines = [line.rstrip('\n') for line in f]
    except FileNotFoundError:
        return 0
    
    # Remove any empty lines at the end
    while lines and lines[-1] == '':
        lines.pop()
    
    if not lines:
        return 0
    
    num_rows = len(lines)
    if num_rows < 2:
        return 0
    
    # Find the maximum width
    max_width = max(len(line) for line in lines)
    
    # Pad lines to be uniform width
    lines = [line.ljust(max_width) for line in lines]
    
    # Identify which columns are "separator" columns (all spaces in every row)
    # A column is a separator if every character in that column across all rows is a space
    separator_cols = [True] * max_width
    for col in range(max_width):
        for row in range(num_rows):
            if lines[row][col] != ' ':
                separator_cols[col] = False
                break
    
    # Find blocks of non-separator columns
    # Each block corresponds to one problem
    blocks = []  # list of (start_col, end_col) inclusive
    i = 0
    while i < max_width:
        if separator_cols[i]:
            i += 1
            continue
        start = i
        while i < max_width and not separator_cols[i]:
            i += 1
        end = i - 1
        blocks.append((start, end))
    
    grand_total = 0
    
    for start, end in blocks:
        # Extract the operator from the last row
        operator = None
        for col in range(start, end + 1):
            char = lines[-1][col]
            if char in ('+', '*'):
                operator = char
                break
        
        if operator is None:
            # Shouldn't happen with valid input, but skip if no operator found
            continue
        
        # Extract numbers from rows 0 to num_rows-2
        numbers = []
        for row_idx in range(num_rows - 1):
            segment = lines[row_idx][start:end + 1]
            # Remove all spaces and check if it's a valid number
            cleaned = segment.replace(' ', '')
            if cleaned and cleaned.isdigit():
                numbers.append(int(cleaned))
        
        if not numbers:
            continue
        
        # Compute the result
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