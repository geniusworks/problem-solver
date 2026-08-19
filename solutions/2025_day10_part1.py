import re
from itertools import product

def solve() -> int:
    try:
        with open('input.txt', 'r') as f:
            lines = [line.strip() for line in f if line.strip()]
    except FileNotFoundError:
        return 0
    
    total_min_presses = 0
    
    for line in lines:
        # Parse the line
        # Format: [diagram] (buttons) (buttons) ... {joltages}
        
        # Extract diagram
        diagram_match = re.search(r'\[([.#]+)\]', line)
        if not diagram_match:
            continue
        diagram = diagram_match.group(1)
        target = [1 if c == '#' else 0 for c in diagram]
        n_lights = len(target)
        
        # Extract buttons
        button_matches = re.findall(r'\(([^)]*)\)', line)
        buttons = []
        for b in button_matches:
            if b.strip():
                indices = [int(x.strip()) for x in b.split(',')]
                buttons.append(indices)
            else:
                buttons.append([])
        
        n_buttons = len(buttons)
        
        # Build the system of linear equations over GF(2)
        # For each light i, sum of k_j for all buttons j that toggle light i = target[i] mod 2
        
        # We need to find k_0, k_1, ..., k_{n_buttons-1} in {0,1}
        # such that for each light i: XOR of k_j where button j toggles light i = target[i]
        # and we minimize sum(k_j)
        
        # Since n_buttons is likely small (based on examples), we can enumerate all 2^n_buttons possibilities
        # But let's first try to solve the linear system to find the solution space, then minimize
        
        # Actually, for small n_buttons (say up to 20), brute force over all 2^n_buttons is feasible
        # For larger, we'd need Gaussian elimination + enumeration of free variables
        
        # Let's use a general approach:
        # 1. Build the matrix A (n_lights x n_buttons) over GF(2)
        # 2. Find all solutions using Gaussian elimination
        # 3. Among all solutions, find the one with minimum Hamming weight
        
        # Build matrix A where A[i][j] = 1 if button j toggles light i
        A = [[0] * n_buttons for _ in range(n_lights)]
        for j, button in enumerate(buttons):
            for light_idx in button:
                if light_idx < n_lights:
                    A[light_idx][j] = 1
        
        # Now solve A * k = target (mod 2)
        # Use Gaussian elimination to find the solution space
        
        # Augmented matrix: [A | target]
        # We'll work with rows as lists of integers (0 or 1)
        
        # Create augmented matrix: each row is [A[i][0], A[i][1], ..., A[i][n_buttons-1], target[i]]
        aug = []
        for i in range(n_lights):
            row = A[i][:] + [target[i]]
            aug.append(row)
        
        # Gaussian elimination over GF(2)
        # We want to find all solutions k such that A*k = target mod 2
        
        # Perform row reduction
        m = n_lights  # rows
        n = n_buttons  # columns
        rank = 0
        pivot_cols = []
        
        # Make a copy for elimination
        mat = [row[:] for row in aug]
        
        for col in range(n):
            # Find pivot row for this column
            pivot_row = -1
            for row in range(rank, m):
                if mat[row][col] == 1:
                    pivot_row = row
                    break
            
            if pivot_row == -1:
                continue
            
            # Swap pivot_row with rank
            mat[rank], mat[pivot_row] = mat[pivot_row], mat[rank]
            
            # Eliminate this column from all other rows
            for row in range(m):
                if row != rank and mat[row][col] == 1:
                    # XOR row with pivot row
                    for c in range(n + 1):
                        mat[row][c] ^= mat[rank][c]
            
            pivot_cols.append(col)
            rank += 1
            
            if rank == m:
                break
        
        # Check for inconsistency: any row that is [0, 0, ..., 0 | 1]
        for row in range(rank, m):
            # Check if all A coefficients are 0 but target is 1
            if all(mat[row][c] == 0 for c in range(n)) and mat[row][n] == 1:
                # No solution exists (shouldn't happen per problem statement)
                # But just in case, skip this machine or handle error
                pass  # We'll assume solutions exist
        
        # Identify free variables
        # Pivot columns are those in pivot_cols
        # Free variables are the rest
        
        pivot_col_set = set(pivot_cols)
        free_vars = [j for j in range(n) if j not in pivot_col_set]
        
        # For each assignment of free variables, compute the pivot variables
        # Then compute the total number of presses
        
        best = float('inf')
        
        for assignment in product([0, 1], repeat=len(free_vars)):
            # Set free variables
            k = [0] * n
            for i, fv in enumerate(free_vars):
                k[fv] = assignment[i]
            
            # Solve for pivot variables
            # Process rows in reverse order (from bottom pivot to top)
            for r in range(rank - 1, -1, -1):
                col = pivot_cols[r]
                # mat[r] represents: sum of k[j] for j where mat[r][j]=1 (excluding the pivot) = mat[r][n]
                # The pivot variable k[col] = mat[r][n] XOR (sum of k[j] for j > col where mat[r][j]=1)
                # Actually, since we did full elimination, each pivot row has only one 1 in the pivot column
                # and possibly 1s in free variable columns
                
                # k[col] = mat[r][n] XOR (sum of k[j] for j in free_vars where mat[r][j] = 1)
                val = mat[r][n]
                for j in range(n):
                    if j != col and mat[r][j] == 1:
                        val ^= k[j]
                k[col] = val
            
            # Verify the solution (optional, for safety)
            valid = True
            for i in range(n_lights):
                s = 0
                for j in range(n_buttons):
                    s ^= A[i][j] * k[j]
                if s != target[i]:
                    valid = False
                    break
            
            if valid:
                presses = sum(k)
                if presses < best:
                    best = presses
        
        if best == float('inf'):
            best = 0
        
        total_min_presses += best
    
    return total_min_presses

if __name__ == '__main__':
    print(solve())