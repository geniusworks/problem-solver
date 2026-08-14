import sys

def solve() -> int:
    try:
        with open('input.txt', 'r') as f:
            lines = [line.strip() for line in f if line.strip()]
        
        # Handle empty input file gracefully
        if not lines or all(len(line) == 0 for line in lines):
            return 0

    except FileNotFoundError:
        print("Error: No 'input.txt' found.", file=sys.stderr)
        sys.exit(1)
    
    grid = lines
    
    count = 0
    rows = len(grid)
    cols_len = [len(line) for line in grid]
    if not cols_len or all(c == 0 for c in cols_len):
        return 0
        
    max_col_width = min(cols_len)
    
    # Iterate over every possible center point 'A'
    # An X-MAS requires an 'A' at the center, with neighbors above and below.
    # The top neighbor needs to be within bounds (r-1), so r starts from 1.
    for r in range(1, rows - 1):
        current_row_str = grid[r]
        
        # Iterate through columns up to min width to handle ragged arrays safely
        for c in range(max_col_width):
            if current_row_str[c] == 'A':
                # Check Diagonal 1: Top-Left (r-1, c-1) -> Bottom-Right (r+1, c+1)
                tl_val = grid[r-1][c-1] if r - 1 >= 0 and c - 1 < len(grid[r-1]) else ''
                br_val = grid[r+1][c+1] if r + 1 < rows and c + 1 < len(grid[r+1]) else ''

                # Check Diagonal 2: Top-Right (r-1, c+1) -> Bottom-Left (r+1, c-1)
                tr_val = grid[r-1][c+1] if r - 1 >= 0 and c + 1 < len(grid[r-1]) else ''
                bl_val = grid[r+1][c-1] if r + 1 < rows and c - 1 < len(grid[r+1]) else ''

                # Check pattern: M-A-S (Diagonal 1) AND S-A-M (Diagonal 2 reversed? No, MAS forwards/backwards means the whole X shape reads forward or backward.
                # Wait, "Within the X, each MAS can be written forwards or backwards." 
                # This implies either branch is an XMAS reading down/right and up/left OR vice versa.
                
                # Actually, let's re-read carefully: "two MAS in the shape of an X".
                # Standard interpretation for this specific puzzle (AoC 2024 Day 4 Part 2):
                # We have two lines crossing at 'A'. One line is M...S and other is S..M? No.
                # The pattern is: 
                # Branch 1: Top-Left -> Bottom-Right reads "MAS" (or backwards "SAM") AND the OTHER branch is also MAS or SAM.
                # Let's verify with example:
                # .M.S......
                # ..A..MSMS.
                # One X is centered at row 2 col 4 (0-indexed) roughly? 
                # The text says "two MAS in the shape of an X".
                # This usually means one diagonal branch forms 'MAS' and the other also forms 'MAS'.
                
                diag1_matches = False
                if tl_val == 'M' and br_val == 'S':
                    diag1_matches = True
                elif tl_val == 'S' and br_val == 'M': # MAS backwards on one diagonal? 
                     # Wait, does the whole X read forward/backward or are we checking specific directions?
                     # "Each MAS can be written forwards or backwards." implies:
                     # Diagonal 1 is M-A-S (forward) OR S-A-M (backward).
                     # Diagonal 2 must also match either direction.
                    pass 
                
                diag2_matches = False
                if tr_val == 'M' and bl_val == 'S':
                    diag2_matches = True
                elif tr_val == 'S' and bl_val == 'M':
                    diag2_matches = True

                # An X-MAS exists if BOTH diagonals form a valid MAS (in any direction)
                if diag1_matches or tl_val=='.' or br_val=='.': 
                     # Wait, the condition is specifically that we find an 'X' made of two lines.
                     # The "backwards" part usually refers to the entire cross reading backwards? 
                     # No, standard solution logic for this puzzle:
                     # Branch 1 (TL-BR) must be M->A->S OR S->A->M
                     # AND
                     # Branch 2 (TR-BL) must be M->A->S OR S->A->M
                    
                    pass

                # Re-evaluating the condition strictly:
                is_diagonal1_valid = False
                if tl_val == 'M' and br_val == 'S': is_diagonal1_valid = True
                elif tl_val == 'S' and br_val == 'M': is_diagonal1_valid = True
                
                is_diagonal2_valid = False
                if tr_val == 'M' and bl_val == 'S': is_diagonal2_valid = True
                elif tr_val == 'S' and bl_val == 'M': is_diagonal2_valid = True

                # Both diagonals must form a valid arm (MAS or SAM) to count as an X-MAS? 
                # The prompt says "two MAS in the shape of an X". This implies both arms are part of it.
                
                if is_diagonal1_valid and is_diagonal2_valid:
                    count += 1

    return count

if __name__ == "__main__":
    import sys, inspect
    sig = inspect.signature(solve)
    params = len(sig.parameters)
    if params == 0:
        print(solve())
    elif params == 1:
        arg = sys.argv[1] if len(sys.argv) > 1 else "input.txt"
        print(solve(arg))
    else:
        raise TypeError("solve() must take 0 or 1 arguments")