def solve() -> int:
    MOD = 16777216  # 2^24
    
    def next_secret(s: int) -> int:
        s = (s ^ (s * 64)) % MOD
        s = (s ^ (s // 32)) % MOD
        s = (s ^ (s * 2048)) % MOD
        return s
    
    try:
        with open('input.txt', 'r') as f:
            lines = f.readlines()
    except FileNotFoundError:
        raise FileNotFoundError("input.txt not found")
    
    total_bananas = {}
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
        try:
            initial_secret = int(line)
        except ValueError:
            continue
        
        # Generate prices P0 to P2000
        # P0 is from initial_secret
        # P1 to P2000 are from the next 2000 secrets
        prices = [initial_secret % 10]
        current_secret = initial_secret
        for _ in range(2000):
            current_secret = next_secret(current_secret)
            prices.append(current_secret % 10)
        
        # Compute changes C1 to C2000
        # changes[i] = prices[i+1] - prices[i]
        changes = []
        for i in range(2000):
            changes.append(prices[i+1] - prices[i])
        
        # Look for first occurrence of each 4-change sequence
        buyer_bananas = {}
        # j is index in changes array (0-indexed)
        # Sequence: changes[j], changes[j+1], changes[j+2], changes[j+3]
        # Sale price: prices[j+4]
        # Max j: j+3 <= 1999 => j <= 1996
        for j in range(1997):
            seq = (changes[j], changes[j+1], changes[j+2], changes[j+3])
            if seq not in buyer_bananas:
                sale_price = prices[j+4]
                buyer_bananas[seq] = sale_price
        
        # Accumulate
        for seq, bananas in buyer_bananas.items():
            if seq in total_bananas:
                total_bananas[seq] += bananas
            else:
                total_bananas[seq] = bananas
    
    max_bananas = 0
    for bananas in total_bananas.values():
        if bananas > max_bananas:
            max_bananas = bananas
    
    return max_bananas

if __name__ == '__main__':
    print(solve())