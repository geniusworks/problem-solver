def solve() -> int:
    """
    Read input.txt, parse towel designs and target strings,
    then count the total number of ways to form each target string
    using the towel designs (repetition allowed), and return the sum.
    """
    try:
        with open('input.txt', 'r') as f:
            lines = f.read().splitlines()
    except FileNotFoundError:
        return 0
    
    # Find the blank line separator
    sep_idx = None
    for i, line in enumerate(lines):
        if line.strip() == '':
            sep_idx = i
            break
    
    if sep_idx is None:
        sep_idx = 0
    
    # Parse towel designs from the first line
    if sep_idx > 0:
        towel_str = lines[0].strip()
    else:
        # If no separator found, assume first non-empty line is towels
        towel_str = ''
        for line in lines:
            if line.strip():
                towel_str = line.strip()
                break
    
    towels = set()
    if towel_str:
        for part in towel_str.split(','):
            part = part.strip()
            if part:
                towels.add(part)
    
    # Parse target strings (lines after the separator)
    targets = []
    for i in range(sep_idx + 1, len(lines)):
        line = lines[i].strip()
        if line:
            targets.append(line)
    
    # For each target, count the number of ways to form it using towels
    total = 0
    for target in targets:
        n = len(target)
        if n == 0:
            total += 1
            continue
        
        # dp[i] = number of ways to form target[0:i]
        dp = [0] * (n + 1)
        dp[0] = 1  # empty prefix: one way (use no towels)
        
        for i in range(1, n + 1):
            count = 0
            for towel in towels:
                lt = len(towel)
                if i >= lt:
                    if target[i - lt:i] == towel:
                        count += dp[i - lt]
            dp[i] = count
        
        total += dp[n]
    
    return total


if __name__ == '__main__':
    print(solve())