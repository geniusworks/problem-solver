def count_distinct_positions(map_str):
    # Convert input string to 2D list
    map_lines = map_str.strip().split('\n')
    lab_map = [list(line) for line in map_lines]
    
    # Find the starting position of the guard
    rows, cols = len(lab_map), len(lab_map[0])
    start_pos = None
    directions = ['up', 'right', 'down', 'left']
    current_direction = 0
    
    for i in range(rows):
        for j in range(cols):
            if lab_map[i][j] == '^':
                start_pos = (i, j)
                break
        if start_pos:
            break
    
    # Initialize the visited set with the starting position
    visited = set([start_pos])
    
    # Directions mapping
    direction_deltas = {
        'up': (-1, 0),
        'right': (0, 1),
        'down': (1, 0),
        'left': (0, -1)
    }
    
    # Simulate guard movement
    i, j = start_pos
    while True:
        x, y = direction_deltas[directions[current_direction]]
        ni, nj = i + x, j + y
        
        if 0 <= ni < rows and 0 <= nj < cols and lab_map[ni][nj] != '#':
            # Move forward
            visited.add((ni, nj))
            i, j = ni, nj
        else:
            # Turn right
            current_direction = (current_direction + 1) % 4
        
        # Check if the guard leaves the mapped area
        x, y = direction_deltas[directions[current_direction]]
        ni, nj = i + x, j + y
        if not (0 <= ni < rows and 0 <= nj < cols):
            break
    
    return len(visited)

def solve():
    try:
        with open('input.txt') as f:
            map_str = f.read()
            return count_distinct_positions(map_str)
    except FileNotFoundError:
        print("File input.txt not found.")
        sys.exit(1)

if __name__ == '__main__':
    print(solve())