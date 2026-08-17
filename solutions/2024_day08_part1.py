def solve() -> int:
    with open('input.txt', 'r') as f:
        lines = f.read().strip().split('\n')
    
    if not lines:
        return 0
    
    height = len(lines)
    width = len(lines[0]) if height > 0 else 0
    
    # Group antennas by frequency
    antennas_by_freq = {}
    
    for x, row in enumerate(lines):
        for y, char in enumerate(row):
            if char != '.':
                if char not in antennas_by_freq:
                    antennas_by_freq[char] = []
                antennas_by_freq[char].append((x, y))
    
    # Calculate unique antinodes
    antinodes = set()
    
    for freq, positions in antennas_by_freq.items():
        n = len(positions)
        for i in range(n):
            for j in range(i + 1, n):
                ax, ay = positions[i]
                bx, by = positions[j]
                
                # Antinode 1: A is the midpoint of B and P1 => P1 = 2A - B
                p1_x = 2 * ax - bx
                p1_y = 2 * ay - by
                
                # Antinode 2: B is the midpoint of A and P2 => P2 = 2B - A
                p2_x = 2 * bx - ax
                p2_y = 2 * by - ay
                
                # Check bounds and add to set
                if 0 <= p1_x < height and 0 <= p1_y < width:
                    antinodes.add((p1_x, p1_y))
                if 0 <= p2_x < height and 0 <= p2_y < width:
                    antinodes.add((p2_x, p2_y))
    
    return len(antinodes)


if __name__ == '__main__':
    print(solve())