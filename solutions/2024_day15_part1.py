from typing import List, Tuple


def solve() -> int:
    """
    Solve the warehouse robot problem.
    
    Reads input.txt which contains:
    1. A grid of the warehouse with walls (#), boxes (O), robot (@), and empty spaces (.)
    2. A blank line
    3. A sequence of movement commands (^, v, <, >)
    
    Returns the sum of GPS coordinates of all boxes after all moves.
    """
    with open('input.txt', 'r') as f:
        content = f.read()
    
    # Split into grid and moves
    lines = content.split('\n')
    
    # Find the blank line that separates grid from moves
    blank_line_idx = None
    for i, line in enumerate(lines):
        if line.strip() == '':
            blank_line_idx = i
            break
    
    if blank_line_idx is None:
        # No blank line, try to find where grid ends
        # Grid lines start with #
        for i, line in enumerate(lines):
            if line.strip() == '' or (line and not line.startswith('#')):
                blank_line_idx = i
                break
        if blank_line_idx is None:
            blank_line_idx = len(lines)
    
    # Parse grid
    grid_lines = [line.rstrip() for line in lines[:blank_line_idx] if line.strip() != '']
    
    # Parse moves (everything after the blank line)
    moves = ''
    for i in range(blank_line_idx, len(lines)):
        if lines[i].strip() != '':
            moves += lines[i].strip()
    
    # Build the grid as a 2D list
    grid = []
    robot_pos = None
    for r, line in enumerate(grid_lines):
        row = []
        for c, char in enumerate(line):
            if char == '@':
                robot_pos = (r, c)
                row.append('.')
            elif char == 'O':
                row.append('O')
            elif char == '#':
                row.append('#')
            else:
                row.append('.')
        grid.append(row)
    
    rows = len(grid)
    cols = len(grid[0]) if rows > 0 else 0
    
    # Define movement vectors
    moves_dict = {
        '^': (-1, 0),
        'v': (1, 0),
        '<': (0, -1),
        '>': (0, 1),
    }
    
    # Process each move
    for move_char in moves:
        dr, dc = moves_dict[move_char]
        
        # Start from robot position and check if we can move
        # We need to check the chain of boxes being pushed
        r, c = robot_pos
        
        # Collect all positions that need to move (robot + any boxes in the way)
        positions_to_move = [(r, c)]
        current_r, current_c = r, c
        
        # Check if the next position is valid
        next_r = current_r + dr
        next_c = current_c + dc
        
        # If next position is out of bounds or wall, can't move
        if next_r < 0 or next_r >= rows or next_c < 0 or next_c >= cols:
            continue
        if grid[next_r][next_c] == '#':
            continue
        
        # If next position has a box, we need to push it
        while grid[next_r][next_c] == 'O':
            positions_to_move.append((next_r, next_c))
            next_r += dr
            next_c += dc
            
            # Check if we can continue pushing
            if next_r < 0 or next_r >= rows or next_c < 0 or next_c >= cols:
                break
            if grid[next_r][next_c] == '#':
                break
        
        # If we hit a wall or out of bounds, can't move
        if next_r < 0 or next_r >= rows or next_c < 0 or next_c >= cols:
            continue
        if grid[next_r][next_c] == '#':
            continue
        
        # Now we can move all positions
        # First, clear all positions (except we'll handle robot separately)
        # Move boxes: for each box position, clear it and place box at next position
        for i, (br, bc) in enumerate(positions_to_move):
            if i == 0:
                # This is the robot's position, clear it
                grid[br][bc] = '.'
            else:
                # This is a box, move it forward
                grid[br][bc] = '.'
        
        # Place all boxes at their new positions
        for i in range(1, len(positions_to_move)):
            br, bc = positions_to_move[i]
            new_r = br + dr
            new_c = bc + dc
            grid[new_r][new_c] = 'O'
        
        # Place robot at its new position
        new_robot_r = r + dr
        new_robot_c = c + dc
        grid[new_robot_r][new_robot_c] = '@'
        robot_pos = (new_robot_r, new_robot_c)
    
    # Calculate GPS coordinates of all boxes
    total_gps = 0
    for r in range(rows):
        for c in range(cols):
            if grid[r][c] == 'O':
                total_gps += 100 * r + c
    
    return total_gps


if __name__ == '__main__':
    print(solve())