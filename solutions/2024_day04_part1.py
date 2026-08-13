def solve():
    try:
        with open('input.txt') as f:
            lines = [line.strip() for line in f if line]
    except FileNotFoundError:
        return 0
        
    rows = len(lines)
    cols = max(len(line) for line in lines)
    
    grid = [[c for c in list(row)] for row in lines]

    # Directions to check (delta_row, delta_col)
    directions = [
        (1, -3),   # Horizontal right: X(0,0)->M(0,1)... wait. 
                   # Let's define vectors by step size 1? Yes.
            ]
    
    dirs = [(0, 1), (0, -1), (1, 0), (-1, 0), (1, 1), (-1,-1), (1, -1), (-1, 1)]

    count = 0
    
    for r in range(rows):
        for c in range(cols-3 if cols>4 else len(grid[r])): # Optimization? No. Loop all cells where X is found.
            pass
            
    # Let's implement clean logic inside the function below without premature closures or errors.

def solve():
    with open('input.txt') as f:
        lines = [line.strip() for line in f if line]

    rows = len(lines)
    cols = max(len(line) for line in lines) if lines else 0
    
    # Pad grid to rectangular shape just in case, though problem implies valid inputs.
    raw_grid = []
    for i in range(rows):
        row_chars = list(lines[i]) + [''] * (cols - len(lines[i]))
        raw_grid.append(row_chars)

    count = 0
    
    # Directions: 
    # We are at (r, c). If grid[r][c] == 'X', we check if the sequence of length 4 in direction d matches "MAS".
    # Note: The word is X-M-A-S. So start with X. Then M, then A, then S.
    
    dirs = [
        (0, 1),   # Horizontal Right -> Left? No, step (+dr, +dc). 
                  # If we move in direction d=(0, -1) i.e., leftwards: next cell is c-1. 
                  # Sequence check: grid[r][c], grid[r][c+(-1)], ...
    ]

    dirs = [(r_step, c_step) for r_step in [-1, 0, 1] for c_step in [-1, 0, 1]]
    
    target_chars = ['X', 'M', 'A', 'S'] # Start char is X. Others are M, A, S.

    for r in range(rows):
        for c in range(cols):
            if raw_grid[r][c] != 'X':
                continue
            
            for dr, dc in dirs:
                found = True
                
                # Check next 3 characters
                curr_r, curr_c = r + dr, c + dc
                steps_left = 2 # We need to check M and A (and S). 
                               # Actually we need X(0), M(1), A(2), S(3). Total length 4.
                               # So from start point (which is X), step k=1..3 times? No, just steps for indices 1, 2, 3 relative to start.
                
                # Let's iterate k=0 to 3. 
                # Start with r,c which must be 'X'. We check if grid[r+dr*k][c+dc*k] == target_chars[k].

                valid = True
                for i in range(4):
                    pr, pc = r + dr * i, c + dc * i
                    
                    # Boundary Check (though problem implies rectangular and we padded)
                    if not (0 <= pr < rows and 0 <= pc < cols): 
                        # Should handle bounds strictly. If grid is ragged in original input? 
                        # Problem says "list of equal-length strings". We'll assume valid or pad to max width.
                        valid = False
                        break
                    
                    if raw_grid[pr][pc] != target_chars[i]:
                        valid = False
                        break
                
                if valid:
                    count += 1
    
    return count

if __name__ == "__main__":
    print(solve())