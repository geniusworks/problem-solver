import sys
from typing import List, Tuple, Optional

def solve() -> int:
    try:
        with open('input.txt', 'r') as f:
            content = f.read().strip()
    except FileNotFoundError:
        raise
    
    lines = content.split('\n')
    
    # Split into map and commands
    # Find the empty line
    empty_line_idx = None
    for i, line in enumerate(lines):
        if line.strip() == "":
            empty_line_idx = i
            break
    
    if empty_line_idx is None:
        # If no empty line, assume all lines are map except possibly the last one
        # But standard format has an empty line. Let's try to detect commands by character set.
        # Commands are <, >, ^, v
        # Map lines contain #, ., O, @, [, ]
        # Let's assume the last line is commands if no empty line found?
        # Or maybe the map is everything until a line that only contains command chars?
        # Safest bet for AoC is the empty line.
        # If not found, we might have a different format.
        # Let's assume the last line is commands if it doesn't look like a map line.
        # A map line usually starts with # or contains #
        # Let's just try to split by finding the first line that is not a map line.
        # But the problem statement examples use empty lines.
        # If no empty line, let's guess the last line is commands.
        if lines:
            last_line = lines[-1].strip()
            if last_line and all(c in '<>^v' for c in last_line):
                map_lines = lines[:-1]
                commands = last_line
            else:
                # Fallback: assume no commands? Or error?
                map_lines = lines
                commands = ""
        else:
            map_lines = []
            commands = ""
    else:
        map_lines = lines[:empty_line_idx]
        # Commands might be on multiple lines? Usually one line.
        # Join all remaining lines just in case.
        commands = "".join(line.strip() for line in lines[empty_line_idx+1:])
    
    # Filter out any empty lines from map_lines
    map_lines = [line for line in map_lines if line.strip() != ""]
    
    if not map_lines:
        return 0
        
    # Scale the map
    scaled_map = []
    for line in map_lines:
        new_line = []
        for char in line:
            if char == '#':
                new_line.append('#')
                new_line.append('#')
            elif char == '.':
                new_line.append('.')
                new_line.append('.')
            elif char == 'O':
                new_line.append('[')
                new_line.append(']')
            elif char == '@':
                new_line.append('@')
                new_line.append('.')
            else:
                # Should not happen, but keep it safe
                new_line.append(char)
                new_line.append(char)
        scaled_map.append(new_line)
    
    rows = len(scaled_map)
    cols = len(scaled_map[0]) if rows > 0 else 0
    
    # Find robot position
    robot_r = -1
    robot_c = -1
    for r in range(rows):
        for c in range(cols):
            if scaled_map[r][c] == '@':
                robot_r = r
                robot_c = c
                break
        if robot_r != -1:
            break
    
    if robot_r == -1:
        return 0
        
    # Replace robot with empty space
    scaled_map[robot_r][robot_c] = '.'
    
    # Helper functions
    def get_box_left(r, c):
        """
        Given a position (r, c) that is part of a box ('[' or ']'),
        return the (row, col) of the left part of that box.
        """
        if scaled_map[r][c] == '[':
            return (r, c)
        elif scaled_map[r][c] == ']':
            return (r, c - 1)
        else:
            return None

    def is_box(r, c):
        if 0 <= r < rows and 0 <= c < cols:
            return scaled_map[r][c] in ['[', ']']
        return False

    def find_boxes_to_move(box_r, box_c, dr, dc, visited):
        """
        Recursively find all boxes that need to move when the box at (box_r, box_c)
        (left coordinate) is pushed in direction (dr, dc).
        Returns a list of (r, c) left-coordinates of boxes to move, or None if blocked.
        """
        key = (box_r, box_c)
        if key in visited:
            return []
        
        visited.add(key)
        
        # Calculate new position for this box
        new_r = box_r + dr
        new_c = box_c + dc
        
        # The box occupies (new_r, new_c) and (new_r, new_c+1)
        # Check these two cells
        
        boxes_to_move = [(box_r, box_c)]
        
        for tc in [new_c, new_c + 1]:
            tr = new_r
            
            # Check bounds
            if not (0 <= tr < rows and 0 <= tc < cols):
                return None # Hit wall or out of bounds
            
            val = scaled_map[tr][tc]
            
            if val == '#':
                return None # Hit wall
            
            if val in ['[', ']']:
                # Hit another box
                other_left = get_box_left(tr, tc)
                if other_left is None:
                    return None
                
                # Check if that box can move
                sub_result = find_boxes_to_move(other_left[0], other_left[1], dr, dc, visited)
                if sub_result is None:
                    return None
                else:
                    boxes_to_move.extend(sub_result)
            
            # If val is '.', it's fine
        
        return boxes_to_move

    def move_robot(dr, dc):
        nonlocal robot_r, robot_c
        
        next_r = robot_r + dr
        next_c = robot_c + dc
        
        # Check bounds
        if not (0 <= next_r < rows and 0 <= next_c < cols):
            return False
        
        val = scaled_map[next_r][next_c]
        
        if val == '#':
            return False
        
        if val == '.':
            # Move robot
            scaled_map[robot_r][robot_c] = '.'
            robot_r, robot_c = next_r, next_c
            scaled_map[robot_r][robot_c] = '@'
            return True
        
        if val in ['[', ']']:
            # Hit a box
            hit_left = get_box_left(next_r, next_c)
            if hit_left is None:
                return False
            
            visited = set()
            boxes_to_move = find_boxes_to_move(hit_left[0], hit_left[1], dr, dc, visited)
            
            if boxes_to_move is None:
                return False
            
            # Execute moves
            # 1. Clear all old positions
            for br, bc in boxes_to_move:
                scaled_map[br][bc] = '.'
                scaled_map[br][bc+1] = '.'
            
            # 2. Place all in new positions
            for br, bc in boxes_to_move:
                new_r = br + dr
                new_c = bc + dc
                scaled_map[new_r][new_c] = '['
                scaled_map[new_r][new_c+1] = ']'
            
            # 3. Move robot
            scaled_map[robot_r][robot_c] = '.'
            robot_r, robot_c = next_r, next_c
            scaled_map[robot_r][robot_c] = '@'
            
            return True
        
        return False

    # Process commands
    for cmd in commands:
        if cmd == '<':
            move_robot(0, -1)
        elif cmd == '>':
            move_robot(0, 1)
        elif cmd == '^':
            move_robot(-1, 0)
        elif cmd == 'v':
            move_robot(1, 0)
    
    # Calculate GPS Sum
    total_gps = 0
    for r in range(rows):
        for c in range(cols):
            if scaled_map[r][c] == '[':
                # This is the left part of a box
                # GPS = 100 * row + col
                total_gps += 100 * r + c
    
    return total_gps

if __name__ == '__main__':
    print(solve())