def solve() -> int:
    import sys

    try:
        with open('input.txt', 'r') as f:
            content = f.read()
    except FileNotFoundError:
        return 0

    # Split into blocks by double newline or single newline if lines are empty
    blocks = content.strip().split('\n\n')
    
    locks = []
    keys = []
    
    for block in blocks:
        lines = [line.strip() for line in block.split('\n') if line.strip()]
        if not lines:
            continue
            
        # Determine if lock or key
        # Lock: top row all '#', bottom row all '.'
        # Key: top row all '.', bottom row all '#'
        is_lock = (lines[0] == '#' * len(lines[0])) and (lines[-1] == '.' * len(lines[-1]))
        is_key = (lines[0] == '.' * len(lines[0])) and (lines[-1] == '#' * len(lines[-1]))
        
        if is_lock:
            # Calculate tips: lowest # index for each column
            tips = []
            cols = len(lines[0])
            for c in range(cols):
                last_hash = -1
                for r in range(len(lines)):
                    if lines[r][c] == '#':
                        last_hash = r
                tips.append(last_hash)
            locks.append(tips)
        elif is_key:
            # Calculate tips: highest # index for each column
            tips = []
            cols = len(lines[0])
            for c in range(cols):
                first_hash = -1
                for r in range(len(lines)):
                    if lines[r][c] == '#':
                        first_hash = r
                        break
                tips.append(first_hash)
            keys.append(tips)
            
    count = 0
    for lock in locks:
        for key in keys:
            fits = True
            for i in range(len(lock)):
                # They fit if the lock's lowest pin is strictly above the key's highest pin
                # i.e., lock_tip < key_tip
                if lock[i] >= key[i]:
                    fits = False
                    break
            if fits:
                count += 1
                
    return count

if __name__ == '__main__':
    print(solve())