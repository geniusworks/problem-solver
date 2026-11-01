import re
from fractions import Fraction
from itertools import product
from typing import List

def solve_machine_joltage(line: str) -> int:
    """
    Solve a single machine's joltage configuration problem.
    Returns the minimum number of button presses, or -1 if impossible.
    """
    # Extract buttons from (...)
    btn_matches = re.findall(r'\(([^)]*)\)', line)
    M = len(btn_matches)
    
    # Extract targets from {..}
    target_match = re.search(r'\{([^}]*)\}', line)
    if not target_match:
        return -1
    targets_str = target_match.group(1).split(',')
    T = [int(x.strip()) for x in targets_str if x.strip()]
    N = len(T)
    
    if M == 0:
        return 0 if all(t == 0 for t in T) else -1
        
    # Build matrix A (N x M)
    # A[i][j] = 1 if button j affects counter i
    A = [[0] * M for _ in range(N)]
    for j, btn_str in enumerate(btn_matches):
        if not btn_str.strip():
            continue
        indices_str = btn_str.split(',')
        for idx_str in indices_str:
            idx_str = idx_str.strip()
            if idx_str:
                idx = int(idx_str)
                if 0 <= idx < N:
                    A[idx][j] = 1

    # We want to solve A x = T
    # Augment matrix with T and perform Gaussian Elimination using Fractions
    # to find the general solution.
    
    # Convert A and T to Fractions for precision
    aug = [[Fraction(A[i][j]) for j in range(M)] + [Fraction(T[i])] for i in range(N)]
    
    # Gaussian Elimination to Reduced Row Echelon Form (RREF)
    rank = 0
    pivot_cols = []
    
    for col in range(M):
        # Find pivot row
        pivot_row = -1
        for r in range(rank, N):
            if aug[r][col] != 0:
                pivot_row = r
                break
        
        if pivot_row == -1:
            continue
        
        # Swap rows
        aug[rank], aug[pivot_row] = aug[pivot_row], aug[rank]
        
        # Normalize pivot row
        pivot_val = aug[rank][col]
        for c in range(M + 1):
            aug[rank][c] /= pivot_val
            
        # Eliminate in all other rows
        for r in range(N):
            if r != rank and aug[r][col] != 0:
                factor = aug[r][col]
                for c in range(M + 1):
                    aug[r][c] -= factor * aug[rank][c]
                    
        pivot_cols.append(col)
        rank += 1
        if rank == N:
            break
            
    # Check for inconsistency
    for r in range(rank, N):
        if all(aug[r][c] == 0 for c in range(M)) and aug[r][M] != 0:
            return -1
            
    # Identify free variables
    pivot_set = set(pivot_cols)
    free_cols = [c for c in range(M) if c not in pivot_set]
    k = len(free_cols)
    
    # If no free variables, solution is unique
    if k == 0:
        x = [0] * M
        for r in range(rank):
            col = pivot_cols[r]
            val = aug[r][M]
            if val.denominator != 1:
                return -1 # Not integer
            x[col] = int(val)
            if x[col] < 0:
                return -1
        return sum(x)
        
    # Express pivot variables in terms of free variables
    # x_p = b - sum(r_ij * x_fj)
    # From RREF:
    # For each pivot row r:
    # x_pivot[r] + sum_{j in free} aug[r][j] * x_f[j] = aug[r][M]
    # x_pivot[r] = aug[r][M] - sum_{j in free} aug[r][j] * x_f[j]
    
    # We need to find integer x_f >= 0 such that x_p >= 0 and x_p are integers.
    # Minimize sum(x_p) + sum(x_f)
    
    # Determine bounds for free variables
    # x_p[r] >= 0 => aug[r][M] - sum_{j in free} aug[r][j] * x_f[j] >= 0
    # sum_{j in free} aug[r][j] * x_f[j] <= aug[r][M]
    
    # A safe upper bound for any x_f[j] is max(T).
    max_T = max(T) if T else 0
    min_presses = float('inf')
    
    # Generate all combinations of free variables from 0 to max_T
    ranges = [range(0, max_T + 1) for _ in range(k)]
    
    for combo in product(*ranges):
        x_f = [0] * M
        for idx, col in enumerate(free_cols):
            x_f[col] = combo[idx]
            
        # Check if x_f are non-negative (they are, from range)
        
        # Calculate pivot variables
        x_p = [0] * M
        valid = True
        
        for r in range(rank):
            col = pivot_cols[r]
            # x_p[col] = aug[r][M] - sum_{j in free} aug[r][j] * x_f[j]
            val = aug[r][M]
            for j_idx, f_col in enumerate(free_cols):
                val -= aug[r][f_col] * x_f[f_col]
                
            if val < 0:
                valid = False
                break
            if val.denominator != 1:
                valid = False
                break
            x_p[col] = int(val)
        
        if not valid:
            continue
            
        # Total presses
        total = sum(x_f) + sum(x_p)
        if total < min_presses:
            min_presses = total
            
    return min_presses if min_presses != float('inf') else -1


def solve() -> int:
    """
    Read input.txt, solve each machine, and return the total minimum presses.
    """
    try:
        with open('input.txt', 'r') as f:
            lines = f.readlines()
    except FileNotFoundError:
        return 0

    total_presses = 0
    for line in lines:
        line = line.strip()
        if not line:
            continue
        presses = solve_machine_joltage(line)
        if presses == -1:
            continue
        total_presses += presses

    return total_presses

if __name__ == '__main__':
    print(solve())