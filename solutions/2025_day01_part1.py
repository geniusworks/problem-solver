def solve() -> int:
    """
    Solve the safe dial rotation puzzle.
    
    The dial starts at 50 and has numbers 0-99 in order.
    Each rotation is either L (left, toward lower numbers) or R (right, toward higher numbers)
    followed by a distance value indicating how many clicks to rotate.
    
    The password is the number of times the dial lands on 0 after any rotation.
    """
    try:
        with open('input.txt', 'r') as f:
            lines = f.readlines()
    except FileNotFoundError:
        return 0
    
    position = 50
    count_zeros = 0
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
        
        # Parse direction and distance
        direction = line[0]
        distance_str = line[1:]
        
        try:
            distance = int(distance_str)
        except ValueError:
            continue
        
        # Apply rotation
        if direction == 'L':
            position = (position - distance) % 100
        elif direction == 'R':
            position = (position + distance) % 100
        else:
            continue
        
        # Check if we landed on 0
        if position == 0:
            count_zeros += 1
    
    return count_zeros


if __name__ == '__main__':
    print(solve())