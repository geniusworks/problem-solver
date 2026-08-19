import sys

def solve() -> int:
    """
    Reads battery bank digit sequences from input.txt, computes the maximum
    12-digit joltage for each bank by selecting a subsequence of length 12,
    and returns the sum of all maximum joltages.
    """
    K = 12
    total_joltage = 0
    
    try:
        with open('input.txt', 'r') as f:
            lines = f.readlines()
    except FileNotFoundError:
        return 0
    except Exception:
        return 0
    
    for line in lines:
        s = line.strip()
        if not s:
            continue
        
        # Filter to only digit characters
        s = ''.join(c for c in s if c.isdigit())
        if not s:
            continue
            
        n = len(s)
        if n < K:
            # If the sequence is shorter than K, use the whole thing (edge case)
            val = int(s)
        else:
            to_remove = n - K
            stack = []
            for char in s:
                # While we have removals left, and the top of the stack is smaller
                # than the current digit, pop the smaller digit to make room for
                # a larger one (greedy strategy for maximizing the number)
                while stack and to_remove > 0 and stack[-1] < char:
                    stack.pop()
                    to_remove -= 1
                stack.append(char)
            
            # If we still have removals left (e.g., the sequence was non-decreasing),
            # the largest number is formed by the first K digits of the stack.
            # If we used all removals, the stack has exactly K digits.
            result_str = ''.join(stack[:K])
            val = int(result_str)
        
        total_joltage += val
    
    return total_joltage

if __name__ == '__main__':
    print(solve())