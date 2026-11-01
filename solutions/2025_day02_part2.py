def solve() -> int:
    with open('input.txt', 'r') as f:
        content = f.read().strip()
    
    if not content:
        return 0
    
    # Remove any newlines or extra whitespace
    content = content.replace('\n', '').replace('\r', '').replace(' ', '')
    
    ranges = content.split(',')
    
    parsed_ranges = []
    max_val = 0
    for r in ranges:
        if not r:
            continue
        parts = r.split('-')
        if len(parts) != 2:
            continue
        try:
            A = int(parts[0])
            B = int(parts[1])
            parsed_ranges.append((A, B))
            if B > max_val:
                max_val = B
        except ValueError:
            continue
            
    if not parsed_ranges:
        return 0

    max_digits = len(str(max_val))
    
    invalid_ids = set()
    
    for k in range(1, max_digits // 2 + 1):
        max_m = max_digits // k
        if max_m < 2:
            continue
            
        for m in range(2, max_m + 1):
            # Calculate multiplier R = 1 + 10^k + ... + 10^((m-1)k)
            R = 0
            term = 1
            for _ in range(m):
                R += term
                term *= (10 ** k)
                
            for A, B in parsed_ranges:
                # We need N = S * R to be in [A, B]
                # S must have exactly k digits (no leading zeros)
                S_min_digits = 10 ** (k - 1) if k > 1 else 1
                S_max_digits = 10 ** k - 1
                
                # Range constraints for S
                # A <= S * R <= B
                S_low_range = (A + R - 1) // R  # Ceil(A/R)
                S_high_range = B // R           # Floor(B/R)
                
                S_low = max(S_min_digits, S_low_range)
                S_high = min(S_max_digits, S_high_range)
                
                if S_low <= S_high:
                    # Add all N = S * R for S in [S_low, S_high]
                    for S in range(S_low, S_high + 1):
                        N = S * R
                        invalid_ids.add(N)
                        
    return sum(invalid_ids)


if __name__ == '__main__':
    print(solve())